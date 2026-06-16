# -*- coding: utf-8 -*-
"""
CLI Automated Media Backup Tool (ADB Version)
Backup foto/video dari HP Android via adb pull.
Zero Python dependency (selain library standar), hanya butuh adb di PATH.
"""

import ctypes
import os
import subprocess
import sys
import time
import io
import tarfile
from ctypes import wintypes

import safe_names

# ============================================================================
# KONFIGURASI PENGGUNA
# ============================================================================
DEVICE_MOUNT_POINT = "/sdcard"
PC_BACKUP_DIR = os.path.join(os.path.expanduser("~"), "Backup_Media_HP")
VALID_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tiff",
    ".webp",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".wmv",
    ".flv",
    ".webm",
    ".3gp",
)
SCAN_PATHS = [
    "/sdcard/DCIM",
    "/sdcard/Download",
    "/sdcard/Pictures",
    "/sdcard/Movies",
    "/sdcard/Telegram",
    "/sdcard/WhatsApp",
    "/sdcard/Instagram",
    "/sdcard/Screenshots",
    "/sdcard/Camera",
    "/sdcard/DCIM/Camera",
    "/sdcard/DCIM/Screenshots",
]
CHUNK_SIZE = 1024 * 1024
POLL_INTERVAL = 2
PROGRESS_BAR_WIDTH = 40
PROGRESS_UPDATE_INTERVAL = 0.1
COPY_MODE = "copy"

ADB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools")
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
ADB_ZIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools.zip")
# ============================================================================


def enable_ansi_colors():
    kernel32 = ctypes.windll.kernel32
    h_stdout = kernel32.GetStdHandle(-11)
    mode = wintypes.DWORD()
    kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode))
    mode = mode.value | 0x0004
    kernel32.SetConsoleMode(h_stdout, mode)


def get_adb_path():
    adb_exe = os.path.join(ADB_DIR, "adb.exe")
    if os.path.exists(adb_exe):
        return adb_exe
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path, "adb.exe")
        if os.path.exists(candidate):
            return candidate
    return None


def download_and_extract_adb():
    adb_exe = os.path.join(ADB_DIR, "adb.exe")
    if os.path.exists(adb_exe):
        return True

    print(f"[ADB] ADB belum ditemukan. Mencoba download otomatis...")
    print(f"[ADB] Sumber: {ADB_URL}")

    try:
        import urllib.request

        print(f"[ADB] Downloading platform-tools...")
        urllib.request.urlretrieve(ADB_URL, ADB_ZIP)
        print(f"[ADB] Download selesai.")
    except Exception as e:
        print(f"[ERROR] Gagal download ADB: {e}")
        print("       Silakan download manual dari:")
        print("       https://developer.android.com/studio/releases/platform-tools")
        print(f"       Ekstrak ke: {ADB_DIR}")
        return False

    try:
        import zipfile

        print(f"[ADB] Mengekstrak...")
        with zipfile.ZipFile(ADB_ZIP, "r") as z:
            extract_dir = os.path.dirname(os.path.abspath(__file__))
            z.extractall(extract_dir)
        print(f"[ADB] Ekstraksi selesai.")

        if os.path.exists(ADB_ZIP):
            os.remove(ADB_ZIP)

        return os.path.exists(adb_exe)
    except Exception as e:
        print(f"[ERROR] Gagal ekstrak ADB: {e}")
        return False


def ensure_adb():
    adb_path = get_adb_path()
    if adb_path:
        return adb_path

    if download_and_extract_adb():
        adb_path = get_adb_path()
        if adb_path:
            if ADB_DIR not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ADB_DIR + os.pathsep + os.environ.get("PATH", "")
            return adb_path

    return None


ADB_PATH = None


def adb_run(args, timeout=300):
    global ADB_PATH
    if ADB_PATH is None:
        ADB_PATH = ensure_adb()
        if ADB_PATH is None:
            return None, "ADB tidak dapat diinstal secara otomatis.", 1
    cmd = [ADB_PATH] + args
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        stdout = (
            result.stdout.decode("utf-8", errors="surrogateescape") if result.stdout else ""
        )
        stderr = (
            result.stderr.decode("utf-8", errors="surrogateescape") if result.stderr else ""
        )
        return stdout.strip(), stderr.strip(), result.returncode
    except FileNotFoundError:
        ADB_PATH = None
        return None, "ADB tidak ditemukan! Mencoba install ulang...", 1
    except Exception as e:
        return None, str(e), 1


def check_adb():
    stdout, stderr, rc = adb_run(["devices"], timeout=10)
    if rc != 0:
        return False, stderr or "ADB tidak ditemukan"
    lines = [
        l.strip() for l in stdout.split("\n") if l.strip() and not l.startswith("List")
    ]
    if not lines:
        return False, "Tidak ada device Android terhubung"
    for line in lines:
        if "device" in line and "unauthorized" not in line:
            return True, line.split()[0]
    return False, "Device unauthorized atau offline"


def wait_for_device():
    print("[IDLE] Menunggu HP Android terhubung via USB...")
    print("       Pastikan USB Debugging sudah aktif dan HP terhubung.\n")
    while True:
        ok, info = check_adb()
        if ok:
            print(f"[FOUND] Device terdeteksi: {info}")
            return info
        print(f"[IDLE] {info}. Mengecek ulang dalam {POLL_INTERVAL} detik...")
        try:
            choice = (
                input(
                    "       Tekan 'M' untuk retry manual, atau Enter untuk cek lagi: "
                )
                .strip()
                .upper()
            )
            if choice == "M":
                print("       Menunggu device... (colokin HP jika belum)")
                time.sleep(POLL_INTERVAL)
        except EOFError:
            pass
        time.sleep(POLL_INTERVAL)


def escape_adb_shell(s):
    """Escape string untuk digunakan di dalam double quotes adb shell."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")


def adb_list_files_recursive():
    all_files = []
    seen_paths = set()

    print(f"[SCAN] Melakukan deep scan via ADB (direct listing)...")
    scan_start = time.time()

    # Gunakan stack untuk menghindari rekursi dalam
    stack = list(SCAN_PATHS)
    
    while stack:
        current_path = stack.pop()
        # adb ls lebih stabil dari adb shell find untuk karakter spesial
        stdout, stderr, rc = adb_run(["ls", current_path], timeout=60)
        if rc != 0 or not stdout:
            continue
            
        for line in stdout.splitlines():
            # Format adb ls: <hex_mode> <hex_size> <hex_mtime> <name>
            parts = line.split(maxsplit=3)
            if len(parts) < 4:
                continue
            
            mode_str, size_str, _, name = parts
            if name in (".", ".."):
                continue
            
            full_path = f"{current_path.rstrip('/')}/{name}"
            if full_path in seen_paths:
                continue
            seen_paths.add(full_path)
            
            try:
                mode = int(mode_str, 16)
                size = int(size_str, 16)
            except ValueError:
                continue
                
            if mode & 0o40000:  # Directory
                stack.append(full_path)
            elif mode & 0o100000:  # File
                ext = os.path.splitext(name)[1].lower()
                if ext in VALID_EXTENSIONS:
                    all_files.append({"path": full_path, "size": size, "name": name})

    elapsed = time.time() - scan_start
    print(f"       Scan selesai dalam {elapsed:.1f} detik")
    print(f"       Total file media ditemukan: {len(all_files)}")
    return all_files


def get_existing_files(backup_dir):
    existing = set()
    if not os.path.exists(backup_dir):
        return existing
    for root, dirs, files in os.walk(backup_dir):
        for f in files:
            filepath = os.path.join(root, f)
            if os.path.getsize(filepath) > 0:
                existing.add(f)
    return existing


def filter_new_files(media_files, existing_files):
    new_files = []
    for item in media_files:
        if item["name"] not in existing_files:
            new_files.append(item)
    return new_files


def filter_new_files_by_path(media_files, backup_dir, existing_paths):
    new_files = []
    for item in media_files:
        rel_path = os.path.relpath(item["path"], DEVICE_MOUNT_POINT)
        dst_path = os.path.join(backup_dir, rel_path)
        if safe_names.norm_path(dst_path) not in existing_paths:
            new_files.append(item)
    return new_files


def clean_zero_byte_files(root: str) -> int:
    if not os.path.exists(root):
        return 0
    cleaned = 0
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                if os.path.getsize(filepath) == 0:
                    os.remove(filepath)
                    cleaned += 1
            except OSError:
                pass
    return cleaned


def format_size(size_bytes):
    if size_bytes is None:
        return "Unknown"
    size_bytes = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def clear_line():
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def draw_progress_bar(percent, filename, transferred, total_size, speed_mbps=None):
    filled = int(PROGRESS_BAR_WIDTH * percent / 100)
    bar = "█" * filled + "░" * (PROGRESS_BAR_WIDTH - filled)
    fname = filename[:25]
    status = f"\r\033[K[{bar}] {percent:5.1f}% | {fname:25s} | {format_size(transferred)}/{format_size(total_size)}"
    if speed_mbps is not None and speed_mbps > 0:
        status += f" | {speed_mbps:.1f} MB/s"
    sys.stdout.write(status)
    sys.stdout.flush()


def draw_folder_progress(
    folder_percent,
    overall_percent,
    folder_name,
    file_idx,
    total_files,
    folder_transferred,
    folder_total,
    speed_mbps,
):
    bar_width = 30
    filled = int(bar_width * folder_percent / 100)
    bar = "█" * filled + "░" * (bar_width - filled)

    display_folder = folder_name[:20] if len(folder_name) > 20 else folder_name
    status = (
        f"\r\033[K[{bar}] {folder_percent:5.1f}% | "
        f"{display_folder:20s} | "
        f"{file_idx}/{total_files} | "
        f"{format_size(folder_transferred)}/{format_size(folder_total)} | "
        f"Total: {overall_percent:5.1f}%"
    )
    if speed_mbps is not None and speed_mbps > 0:
        status += f" | {speed_mbps:.1f} MB/s"
    sys.stdout.write(status)
    sys.stdout.flush()


def pull_file_with_tar(remote_path, local_path, timeout=120, debug=False):
    """
    Pull file from Android using tar streaming via adb exec-out.
    Uses hex-escaped filenames to handle Unicode/emoji correctly.
    
    Returns: (success: bool, transferred_bytes: int, error_msg: str)
    """
    if ADB_PATH is None:
        return False, 0, "ADB not available"
    
    parent_dir = os.path.dirname(remote_path)
    filename = os.path.basename(remote_path)
    
    # Step 1: List parent dir untuk dapat actual filename dari device
    stdout, stderr, rc = adb_run(["ls", parent_dir], timeout=10)
    if rc != 0:
        return False, 0, f"Cannot list parent dir: {stderr[:100]}"
    
    # Parse adb ls output untuk cari matching file
    actual_filename = None
    for line in stdout.splitlines():
        parts = line.split(maxsplit=3)
        if len(parts) >= 4:
            list_filename = parts[3]
            if list_filename.lower() == filename.lower():
                actual_filename = list_filename
                break
    
    if not actual_filename:
        return False, 0, f"File not found in directory listing"
    
    # Step 2: Write filename ke temp file dengan hex escapes (ASCII-safe)
    fname_bytes = actual_filename.encode('utf-8')
    hex_escapes = ''.join(f'\\x{b:02x}' for b in fname_bytes)
    temp_fname_path = f"/data/local/tmp/backup_fname_{int(time.time() * 1000)}.txt"
    
    write_cmd = f"echo -ne '{hex_escapes}' > {temp_fname_path}"
    
    result = subprocess.run(
        [ADB_PATH, "exec-out", write_cmd],
        capture_output=True,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    
    if result.returncode != 0:
        err = result.stderr.decode('utf-8', errors='replace')[:100]
        return False, 0, f"Write filename failed: {err}"
    
    # Step 3: Tar dengan --files-from (filename dari temp file)
    escaped_parent = parent_dir.replace("'", "'\\''")
    tar_cmd = f"cd '{escaped_parent}' && tar -cf - --files-from={temp_fname_path}"
    
    try:
        proc = subprocess.Popen(
            [ADB_PATH, "exec-out", tar_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        
        tar_data, stderr_data = proc.communicate(timeout=timeout)
        
        # Cleanup temp file
        subprocess.run(
            [ADB_PATH, "exec-out", f"rm -f {temp_fname_path}"],
            capture_output=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        
        if proc.returncode != 0:
            err = stderr_data.decode('utf-8', errors='replace')[:200] if stderr_data else "unknown"
            return False, 0, f"tar exit code {proc.returncode}: {err}"
        
        if not tar_data or len(tar_data) < 512:
            return False, 0, f"tar output too small: {len(tar_data) if tar_data else 0} bytes"
        
        # Extract from tar stream in memory
        tar_stream = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_stream, mode='r') as tar:
            members = tar.getmembers()
            if not members:
                return False, 0, "tar archive empty"
            
            member = members[0]
            file_data = tar.extractfile(member)
            if file_data is None:
                return False, 0, "cannot extract file from tar"
            
            file_content = file_data.read()
        
        # Write to destination
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        with open(local_path, 'wb') as f:
            f.write(file_content)
        
        return True, len(file_content), ""
    except Exception as e:
        # Cleanup on error
        subprocess.run(
            [ADB_PATH, "exec-out", f"rm -f {temp_fname_path}"],
            capture_output=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return False, 0, str(e)[:200]


def adb_pull_file_with_progress(
    remote_path, local_path, item_size, total_transferred, total_size, folder_info
):
    dst_dir = os.path.dirname(local_path)
    os.makedirs(dst_dir, exist_ok=True)

    if ADB_PATH is None:
        return False, 0

    local_filename = os.path.basename(local_path)
    temp_local_path = f"{local_path}.tmp"
    
    # Unpack folder info untuk progress display
    folder_name, total_files_in_folder, file_idx = folder_info

    # Verifikasi ukuran asli di HP sebelum transfer via adb ls (lebih stabil dari shell stat)
    stdout, _, rc = adb_run(["ls", remote_path], timeout=10)
    if rc == 0 and stdout:
        parts = stdout.splitlines()[0].split(maxsplit=3)
        if len(parts) >= 4:
            try:
                item_size = int(parts[1], 16)
            except ValueError:
                pass
    
    if item_size <= 0:
        # Jika ukuran tetap 0 atau gagal ls, kita tidak bisa verifikasi progress dengan benar
        # tapi coba tetap pull jika file ada.
        pass

    # Solusi FINAL menggunakan adb exec-out dan find by size+path pattern
    # exec-out lebih reliable untuk binary data dibanding shell
    # Kita gunakan find dengan size sebagai filter tambahan untuk identifikasi file
    
    parent_dir = os.path.dirname(remote_path)
    filename = os.path.basename(remote_path)
    
    # Strategy: gunakan dd dengan skip/count berdasarkan position di ls output
    # Atau lebih simple: fallback ke adb pull untuk ASCII, workaround untuk non-ASCII
    
    # Check apakah filename pure ASCII
    try:
        filename.encode('ascii')
        is_ascii = True
    except UnicodeEncodeError:
        is_ascii = False
    
    if is_ascii:
        # ASCII filename - gunakan adb pull standar (lebih cepat dan reliable)
        # IMPORTANT: jangan pipe stdout/stderr karena output progress adb pull
        # bisa overflow pipe buffer (4-64KB) dan menyebabkan adb hang!
        
        cmd = ["pull", remote_path, temp_local_path]
        start_time = time.time()
        last_update = start_time
        
        proc = subprocess.Popen(
            [ADB_PATH] + cmd,
            stdout=None,
            stderr=None,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        
        # Monitor progress via file size
        while proc.poll() is None:
            now = time.time()
            if os.path.exists(temp_local_path):
                current_size = os.path.getsize(temp_local_path)
                elapsed = now - start_time
                speed_mbps = (current_size / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                if now - last_update >= PROGRESS_UPDATE_INTERVAL:
                    if total_size > 0:
                        folder_percent = (current_size / item_size * 100) if item_size > 0 else 0
                        overall_percent = min(99.9, (total_transferred + current_size) / total_size * 100)
                        draw_folder_progress(
                            folder_percent,
                            overall_percent,
                            folder_name,
                            file_idx,
                            total_files_in_folder,
                            total_transferred + current_size,
                            total_size,
                            speed_mbps,
                        )
                    last_update = now
            time.sleep(0.05)
        
        if proc.returncode == 0 and os.path.exists(temp_local_path):
            transferred = os.path.getsize(temp_local_path)
        else:
            # Pull gagal - fallback: copy ke temp di device, pull dari sana
            clear_line()
            print(f"\n[WARN] Pull gagal, fallback copy+cp: {local_filename}")
            
            temp_on_device = f"/data/local/tmp/backup_tmp_{int(time.time() * 1000)}.bin"
            shell_cp = f"cp \"{remote_path}\" \"{temp_on_device}\" && echo 'CP_OK'"
            
            cp_stdout, cp_stderr, cp_rc = adb_run(["shell", shell_cp], timeout=30)
            if cp_rc != 0 or (cp_stdout and 'CP_OK' not in cp_stdout):
                print(f"       Copy ke temp device gagal: {cp_stderr[:200]}")
                return False, 0
            
            # Pull dari temp
            proc = subprocess.Popen(
                [ADB_PATH, "pull", temp_on_device, temp_local_path],
                stdout=None,
                stderr=None,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            proc.wait(timeout=120)
            
            # Clean temp
            adb_run(["shell", f"rm -f \"{temp_on_device}\""], timeout=10)
            
            if proc.returncode == 0 and os.path.exists(temp_local_path):
                transferred = os.path.getsize(temp_local_path)
            else:
                print(f"       Pull dari temp juga gagal")
                return False, 0
    else:
        # Non-ASCII filename (Unicode/emoji) - SKIP silently
        # File akan di-skip dan dilaporkan di summary akhir
        return False, 0

    # Validasi hasil transfer
    if not os.path.exists(temp_local_path):
        clear_line()
        print(f"\n[ERROR] Gagal: {local_filename}")
        print(f"       Alasan: File tidak berhasil di-download")
        return False, 0

    actual_size = os.path.getsize(temp_local_path)
    
    # Validasi ukuran dengan toleransi untuk file besar
    if item_size > 0:
        size_diff = abs(actual_size - item_size)
        size_diff_percent = (size_diff / item_size * 100) if item_size > 0 else 0
        
        # Kriteria validasi:
        # 1. Jika download terlalu kecil (< 50% dari expected) → definitely error (download incomplete)
        # 2. Jika selisih > 1% → reject (1% tolerance untuk metadata/rounding)
        size_ratio = (actual_size / item_size) if item_size > 0 else 0
        
        if size_ratio < 0.5:
            # File downloaded incomplete (< 50% dari size yang diharapkan)
            clear_line()
            print(
                f"\n[ERROR] Download incomplete {local_filename}:"
            )
            print(f"       Diharapkan: {format_size(item_size)} ({item_size:,} bytes)")
            print(f"       Didapat   : {format_size(actual_size)} ({actual_size:,} bytes)")
            print(f"       Hanya {size_ratio*100:.1f}% dari file yang didownload")
            try:
                os.remove(temp_local_path)
            except:
                pass
            return False, 0
        
        if size_diff_percent > 1.0:
            # Selisih > 1%
            clear_line()
            print(
                f"\n[WARN] Ukuran tidak sesuai {local_filename}:"
            )
            print(f"       Diharapkan: {format_size(item_size)} ({item_size:,} bytes)")
            print(f"       Didapat   : {format_size(actual_size)} ({actual_size:,} bytes)")
            print(f"       Selisih   : {size_diff:,} bytes ({size_diff_percent:.2f}%)")
            try:
                os.remove(temp_local_path)
            except:
                pass
            return False, 0
    
    # Simpan file ke lokasi final
    try:
        if os.path.exists(local_path):
            os.remove(local_path)
        os.replace(temp_local_path, local_path)
    except Exception as e:
        clear_line()
        print(f"\n[ERROR] Gagal menyimpan {local_filename}: {e}")
        try:
            os.remove(temp_local_path)
        except:
            pass
        return False, 0
    
    final_transferred = total_transferred + actual_size
    final_percent = (
        min(100.0, (final_transferred / total_size) * 100)
        if total_size > 0
        else 100
    )
    draw_folder_progress(
        100,
        final_percent,
        folder_name,
        file_idx,
        total_files_in_folder,
        final_transferred,
        total_size,
        0,
    )
    print()
    return True, actual_size


def group_by_folder(media_files):
    folders = {}
    for item in media_files:
        folder = os.path.dirname(item["path"])
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(item)
    return folders


def print_folder_summary(folders):
    print(f"\n{'=' * 60}")
    print("  FOLDER MEDIA YANG DITEMUKAN")
    print(f"{'=' * 60}")
    sorted_folders = sorted(folders.items(), key=lambda x: len(x[1]), reverse=True)
    for idx, (folder, files) in enumerate(sorted_folders, 1):
        total_size = sum(f["size"] for f in files if f["size"] is not None)
        display_folder = folder.replace(DEVICE_MOUNT_POINT + "/", "/")
        print(
            f"  {idx:2d}. [{len(files):3d} file] {format_size(total_size):>10s}  {display_folder}"
        )
    print(f"{'=' * 60}")
    print(f"  Total folder: {len(sorted_folders)}")
    print(f"{'=' * 60}")


def select_folders(folders_dict):
    sorted_folders = sorted(folders_dict.items(), key=lambda x: len(x[1]), reverse=True)
    print(f"\n{'=' * 60}")
    print("  PILIH FOLDER UNTUK BACKUP")
    print(f"{'=' * 60}")
    for idx, (folder, files) in enumerate(sorted_folders, 1):
        total_size = sum(f["size"] for f in files if f["size"] is not None)
        display_folder = folder.replace(DEVICE_MOUNT_POINT + "/", "/")
        print(
            f"  {idx:2d}. [{len(files):3d} file] {format_size(total_size):>10s}  {display_folder}"
        )
    print(f"  0.   Kembali (semua folder)")
    print(f"{'=' * 60}")
    while True:
        choice = input(
            "\n  Masukkan nomor folder (pisah dengan koma, contoh: 1,3,5) atau '0' untuk semua: "
        ).strip()
        if choice == "0":
            return folders_dict
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            selected = {}
            for i in indices:
                if 1 <= i <= len(sorted_folders):
                    folder, files = sorted_folders[i - 1]
                    selected[folder] = files
                else:
                    print(f"  Nomor {i} tidak valid. Coba lagi.")
                    raise ValueError
            return selected
        except ValueError:
            print("  Input tidak valid. Contoh: 1,3,5 atau 0")


def run_backup(device_id):
    print(f"\n{'=' * 60}")
    print(f"  Device    : {device_id}")
    print(f"  Backup To : {PC_BACKUP_DIR}")
    print(f"{'=' * 60}")

    all_media = adb_list_files_recursive()
    if not all_media:
        print("\n[TIDAK ADA FILE] Tidak ditemukan file media di HP.")
        return

    existing = get_existing_files(PC_BACKUP_DIR)
    cleaned = clean_zero_byte_files(PC_BACKUP_DIR)
    if cleaned > 0:
        print(f"\n[CLEANUP] Menghapus {cleaned} file 0 byte dari backup sebelumnya.")
    existing_paths = safe_names.get_existing_paths(PC_BACKUP_DIR)
    new_files = filter_new_files_by_path(all_media, PC_BACKUP_DIR, existing_paths)
    dup_count = len(all_media) - len(new_files)
    total_new_size = sum(f["size"] for f in new_files if f["size"] is not None)

    all_folders = group_by_folder(all_media)
    new_folders = group_by_folder(new_files)

    print_folder_summary(new_folders)

    print(f"\n{'=' * 60}")
    print("  RINGKASAN BACKUP")
    print(f"{'=' * 60}")
    print(f"  Total file media di HP   : {len(all_media)}")
    print(f"  File baru (belum backup) : {len(new_files)}")
    print(f"  File duplikat            : {dup_count}")
    print(f"  Total ukuran baru        : {format_size(total_new_size)}")
    print(f"  Lokasi backup            : {PC_BACKUP_DIR}")
    print(f"  Folder dengan media baru : {len(new_folders)}")
    print(f"{'=' * 60}")

    if not new_files:
        print("\n[TIDAK ADA FILE BARU] Semua file sudah tercadangkan.")
        return

    print(f"\n{'=' * 60}")
    print("  MODE TRANSFER")
    print(f"{'=' * 60}")
    print(f"  C. COPY  - Salin file (tetap ada di HP)")
    print(f"  M. MOVE  - Pindah file (dihapus dari HP setelah backup)")
    print(f"{'=' * 60}")
    while True:
        mode_choice = input("\n  Pilih mode [C/M]: ").strip().upper()
        if mode_choice in ("C", "M"):
            copy_mode = "move" if mode_choice == "M" else "copy"
            break
        print("  Input tidak valid. Pilih C atau M.")

    mode_label = "PINDAH (MOVE)" if copy_mode == "move" else "SALIN (COPY)"
    print(f"\n[MODE] {mode_label}")

    print("\n[PILIHAN]")
    print("  A. Backup SEMUA folder")
    print("  B. Pilih folder tertentu")
    print("  C. Batalkan")
    while True:
        choice = input("\n  Pilih [A/B/C]: ").strip().upper()
        if choice == "A":
            break
        elif choice == "B":
            selected = select_folders(new_folders)
            if selected is None:
                return
            new_folders = selected
            new_files = []
            for files in new_folders.values():
                new_files.extend(files)
            if not new_files:
                print("\n[TIDAK ADA FILE] Tidak ada file yang dipilih.")
                return
            break
        elif choice == "C":
            print("\n[ BATAL ] Backup dibatalkan.")
            return
        else:
            print("  Input tidak valid. Pilih A, B, atau C.")

    total_new_size = sum(f["size"] for f in new_files if f["size"] is not None)
    print(
        f"\n[START] Memulai {mode_label.lower()} {len(new_files)} file dari {len(new_folders)} folder..."
    )
    print(f"       Total ukuran: {format_size(total_new_size)}")
    os.makedirs(PC_BACKUP_DIR, exist_ok=True)

    success = 0
    failed = 0
    skipped = 0
    skipped_unicode = 0  # Counter untuk file Unicode/emoji yang di-skip
    total_transferred = 0
    used_paths = set()

    sorted_folders = sorted(new_folders.items(), key=lambda x: x[0])

    for folder_idx, (folder_path, folder_files) in enumerate(sorted_folders, 1):
        folder_name = folder_path.replace(DEVICE_MOUNT_POINT + "/", "").replace(
            DEVICE_MOUNT_POINT, ""
        )
        if not folder_name:
            folder_name = "/"

        print(f"\n[{folder_idx}/{len(sorted_folders)}] Folder: {folder_name}")
        print(
            f"       File: {len(folder_files)} | Ukuran: {format_size(sum(f['size'] for f in folder_files if f['size'] is not None))}"
        )

        folder_transferred = 0
        folder_total = sum(f["size"] for f in folder_files if f["size"] is not None)

        for file_idx_in_folder, item in enumerate(folder_files, 1):
            filename = item["name"]
            remote_path = item["path"]
            rel_path = os.path.relpath(remote_path, DEVICE_MOUNT_POINT)
            original_local_path = os.path.join(PC_BACKUP_DIR, rel_path)
            local_path, _ = safe_names.resolve_safe_destination_path(
                original_local_path,
                existing_paths=existing_paths,
                used_paths=used_paths,
            )

            dst_dir = os.path.dirname(local_path)
            os.makedirs(dst_dir, exist_ok=True)

            # Cek jika file sudah ada dan ukurannya sama
            if os.path.exists(local_path):
                existing_size = os.path.getsize(local_path)
                if item["size"] is not None and existing_size == item["size"]:
                    skipped += 1
                    folder_transferred += existing_size
                    total_transferred += existing_size
                    continue

            if (
                safe_names.norm_path(local_path) in existing_paths
                or safe_names.norm_path(local_path) in used_paths
                or os.path.exists(f"{local_path}.tmp")
            ):
                skipped += 1
                folder_transferred += item["size"] if item["size"] else 0
                total_transferred += item["size"] if item["size"] else 0
                folder_percent = (file_idx_in_folder / len(folder_files)) * 100
                overall_percent = (
                    min(
                        100.0,
                        (total_transferred + folder_transferred) / total_new_size * 100,
                    )
                    if total_new_size > 0
                    else 0
                )
                draw_folder_progress(
                    folder_percent,
                    overall_percent,
                    folder_name,
                    file_idx_in_folder,
                    len(folder_files),
                    total_transferred,
                    folder_total,
                    0,
                )
                print()
                continue

            ok, transferred = adb_pull_file_with_progress(
                remote_path,
                local_path,
                item["size"],
                total_transferred + folder_transferred,
                total_new_size,
                (folder_name, len(folder_files), file_idx_in_folder),
            )
            if ok:
                used_paths.add(safe_names.norm_path(local_path))
                folder_transferred += transferred
                total_transferred += transferred
                success += 1
                if copy_mode == "move":
                    e_remote = escape_adb_shell(remote_path)
                    _, _, delete_ok = adb_run(
                        ["shell", f'rm "{e_remote}"'], timeout=10
                    )
                    if delete_ok != 0:
                        print(f"\n[WARN] Gagal hapus dari HP: {filename}")
            else:
                # Check if it's Unicode/emoji skip (transferred = 0 and non-ASCII)
                try:
                    filename.encode('ascii')
                    is_ascii = True
                except UnicodeEncodeError:
                    is_ascii = False
                
                if not is_ascii:
                    skipped_unicode += 1
                else:
                    failed += 1

        print()

    draw_folder_progress(
        100,
        100,
        "SELESAI",
        len(sorted_folders),
        len(sorted_folders),
        total_transferred,
        total_new_size,
        0,
    )
    print()

    print(f"\n{'=' * 60}")
    print("  LAPORAN BACKUP")
    print(f"{'=' * 60}")
    print(f"  Mode         : {mode_label}")
    print(f"  Berhasil     : {success}")
    print(f"  Gagal        : {failed}")
    print(f"  Dilewati     : {skipped}")
    print(f"  Unicode/Emoji: {skipped_unicode}")
    print(f"  Total        : {len(new_files)}")
    print(
        f"  Ukuran       : {format_size(total_transferred)} / {format_size(total_new_size)}"
    )
    print(f"{'=' * 60}")

    if failed == 0 and skipped_unicode == 0:
        print("\n[SUKSES] Semua file berhasil dicadangkan!")
    else:
        if skipped_unicode > 0:
            print(f"\n[INFO] {skipped_unicode} file Unicode/emoji di-skip (fitur tidak aktif)")
        if failed > 0:
            print(f"[WARN] {failed} file gagal dicadangkan.")


def main():
    enable_ansi_colors()

    print(f"{'=' * 60}")
    print("  CLI Automated Media Backup Tool (ADB Version)")
    print("  Python Version - Zero Dependency (butuh adb)")
    print(f"{'=' * 60}")
    print(f"  Device Root  : {DEVICE_MOUNT_POINT}")
    print(f"  Backup To    : {PC_BACKUP_DIR}")
    print(f"  Extensions   : {', '.join(VALID_EXTENSIONS)}")
    print(f"  Scan Paths   : {len(SCAN_PATHS)} lokasi")
    print(f"  Mode Default : {COPY_MODE.upper()}")
    print(f"{'=' * 60}\n")

    if not os.path.exists(PC_BACKUP_DIR):
        print(f"[INFO] Direktori backup akan dibuat: {PC_BACKUP_DIR}")

    adb_path = ensure_adb()
    if adb_path is None:
        print("[ERROR] Gagal menginstal ADB secara otomatis.")
        print("       Silakan download manual dari:")
        print("       https://developer.android.com/studio/releases/platform-tools")
        print(f"       Ekstrak ke: {ADB_DIR}")
        input("       Tekan Enter untuk keluar...")
        sys.exit(1)
    print(f"[ADB] ADB siap: {adb_path}\n")

    try:
        while True:
            device = wait_for_device()
            if device:
                run_backup(device)
            print("\n[IDLE] Menunggu device terhubung kembali...")
            print("       Cabut kabel untuk keluar dari program.\n")
    except KeyboardInterrupt:
        print("\n\n[EXIT] Program dihentikan oleh user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
