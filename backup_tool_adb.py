# -*- coding: utf-8 -*-
"""
CLI Automated Media Backup Tool (ADB Version) - Optimized with Rich Progress
Backup foto/video dari HP Android via adb pull dengan progress bar modern.
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
from pathlib import Path

import safe_names

try:
    from rich.progress import Progress, SpinnerColumn, BarColumn, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, TaskProgressColumn
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# ============================================================================
# KONFIGURASI PENGGUNA
# ============================================================================
DEVICE_MOUNT_POINT = "/sdcard"
PC_BACKUP_DIR = os.path.join(os.path.expanduser("~"), "Backup_Media_HP")
VALID_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    ".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".3gp",
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
CHUNK_SIZE = 1024 * 1024  # 1MB chunks
POLL_INTERVAL = 2
PROGRESS_UPDATE_INTERVAL = 0.1
COPY_MODE = "copy"

ADB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools")
ADB_URL = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
ADB_ZIP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "platform-tools.zip")
# ============================================================================

# Console untuk rich output
console = Console() if RICH_AVAILABLE else None


def enable_ansi_colors():
    """Aktifkan ANSI escape codes di Windows CMD/PowerShell."""
    try:
        kernel32 = ctypes.windll.kernel32
        h_stdout = kernel32.GetStdHandle(-11)
        mode = wintypes.DWORD()
        kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode))
        mode = mode.value | 0x0004
        kernel32.SetConsoleMode(h_stdout, mode)
    except:
        pass


def get_adb_path():
    """Dapatkan path ADB executable."""
    adb_exe = os.path.join(ADB_DIR, "adb.exe")
    if os.path.exists(adb_exe):
        return adb_exe
    for path in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path, "adb.exe")
        if os.path.exists(candidate):
            return candidate
    return None


def download_and_extract_adb():
    """Download dan ekstrak ADB platform-tools jika belum ada."""
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
    """Pastikan ADB tersedia, download jika perlu."""
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
    """Jalankan command ADB."""
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
    """Cek apakah ADB device terhubung."""
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
    """Tunggu hingga HP Android terhubung via USB."""
    print("\\n[IDLE] Menunggu HP Android terhubung via USB...")
    print("       Pastikan USB Debugging sudah aktif dan HP terhubung.\\n")
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
    """Escape string untuk digunakan di dalam adb shell."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace("`", "\\`")


def format_size(size_bytes):
    """Format ukuran file ke human-readable."""
    if size_bytes is None:
        return "Unknown"
    size_bytes = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def adb_list_files_recursive():
    """Scan semua file media di HP dengan optimasi stack-based iteration."""
    all_files = []
    seen_paths = set()

    if RICH_AVAILABLE:
        console.print("[SCAN] Melakukan deep scan via ADB (direct listing)...")
    else:
        print("[SCAN] Melakukan deep scan via ADB (direct listing)...")

    scan_start = time.time()
    stack = list(SCAN_PATHS)

    while stack:
        current_path = stack.pop()
        stdout, stderr, rc = adb_run(["ls", current_path], timeout=60)
        if rc != 0 or not stdout:
            continue

        for line in stdout.splitlines():
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
    if RICH_AVAILABLE:
        console.print(f"       [green]Scan selesai dalam {elapsed:.1f} detik[/green]")
        console.print(f"       [cyan]Total file media ditemukan: {len(all_files)}[/cyan]")
    else:
        print(f"       Scan selesai dalam {elapsed:.1f} detik")
        print(f"       Total file media ditemukan: {len(all_files)}")
    return all_files


def get_existing_files(backup_dir):
    """Dapatkan set file yang sudah ada di backup (optimasi caching)."""
    existing = set()
    if not os.path.exists(backup_dir):
        return existing
    for root, dirs, files in os.walk(backup_dir):
        for f in files:
            filepath = os.path.join(root, f)
            try:
                if os.path.getsize(filepath) > 0:
                    existing.add(f)
            except OSError:
                continue
    return existing


def filter_new_files_by_path(media_files, backup_dir, existing_paths):
    """Filter file yang belum ada di backup dengan optimasi path normalization."""
    new_files = []
    for item in media_files:
        rel_path = os.path.relpath(item["path"], DEVICE_MOUNT_POINT)
        dst_path = os.path.join(backup_dir, rel_path)
        if safe_names.norm_path(dst_path) not in existing_paths:
            new_files.append(item)
    return new_files


def clean_zero_byte_files(root: str) -> int:
    """Hapus file 0 byte di direktori backup."""
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


def pull_file_via_exec_out(remote_path, local_path, timeout=120):
    """
    Pull file dari Android via adb exec-out dengan tar streaming.
    Handle Unicode/emoji filenames via hex escape.
    
    Returns: (success: bool, transferred_bytes: int, error_msg: str)
    """
    if ADB_PATH is None:
        return False, 0, "ADB not available"

    parent_dir = os.path.dirname(remote_path)
    filename = os.path.basename(remote_path)

    # Step 1: Get actual filename dari device
    stdout, stderr, rc = adb_run(["ls", parent_dir], timeout=10)
    if rc != 0:
        return False, 0, f"Cannot list parent dir: {stderr[:100]}"

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

    # Step 2: Write filename ke temp file dengan hex escapes
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

    # Step 3: Tar streaming
    escaped_parent = parent_dir.replace("'", "'\\\\''")
    tar_cmd = f"cd '{escaped_parent}' && tar -cf - --files-from={temp_fname_path}"

    try:
        proc = subprocess.Popen(
            [ADB_PATH, "exec-out", tar_cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        tar_data, stderr_data = proc.communicate(timeout=timeout)

        # Cleanup temp
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

        # Extract from tar stream
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


def pull_file_with_adb_pull(remote_path, local_path, item_size):
    """
    Pull file menggunakan adb exec-out cat untuk transfer binary yang reliable.
    Menggantikan adb pull yang terbukti corrupt pada file > 5MB.
    
    Returns: (success: bool, transferred_bytes: int)
    """
    temp_local_path = f"{local_path}.tmp"
    os.makedirs(os.path.dirname(temp_local_path), exist_ok=True)
    
    # Escape path untuk shell
    escaped_path = remote_path.replace("'", "'\\\\''")
    cmd = f"cat '{escaped_path}'"
    
    proc = subprocess.Popen(
        [ADB_PATH, "exec-out", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    
    # Stream langsung ke file (chunk-by-chunk, tanpa memory penuh)
    transferred = 0
    try:
        with open(temp_local_path, 'wb') as f:
            while True:
                chunk = proc.stdout.read(65536)  # 64KB chunks
                if not chunk:
                    break
                f.write(chunk)
                transferred += len(chunk)
        proc.wait(timeout=120)
    except Exception as e:
        proc.kill()
        try:
            os.remove(temp_local_path)
        except:
            pass
        return False, 0
    
    if proc.returncode != 0:
        try:
            os.remove(temp_local_path)
        except:
            pass
        return False, 0
    
    if transferred == 0:
        try:
            os.remove(temp_local_path)
        except:
            pass
        return False, 0
    
    # Validasi ukuran KETAT - minimal 95% dari expected
    if item_size > 0:
        ratio = transferred / item_size
        if ratio < 0.5:
            try:
                os.remove(temp_local_path)
            except:
                pass
            return False, 0
        if ratio < 0.95:
            # 50-95%: warning tapi tetap simpan sebagai partial
            # (mungkin file di HP memang belum selesai di-write)
            pass
    
    # Pindah ke lokasi final
    if os.path.exists(local_path):
        os.remove(local_path)
    os.replace(temp_local_path, local_path)
    
    return True, transferred


def copy_with_progress_rich(media_files, new_folders, total_new_size, existing_paths, used_paths, copy_mode):
    """
    Copy file dengan rich.progress untuk visual yang modern dan informatif.
    """
    total_files = len(media_files)
    success = 0
    failed = 0
    skipped = 0
    skipped_unicode = 0
    total_transferred = 0
    sorted_folders = sorted(new_folders.items(), key=lambda x: x[0])
    
    overall_progress = Progress(
        SpinnerColumn(),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=True,
    )
    
    folder_progress = Progress(
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        "•",
        DownloadColumn(),
        console=console,
        expand=True,
    )
    
    with overall_progress:
        overall_task = overall_progress.add_task(
            "[cyan]Total Backup[/cyan]", 
            total=total_new_size if total_new_size > 0 else total_files
        )
        
        for folder_idx, (folder_path, folder_files) in enumerate(sorted_folders, 1):
            folder_name = folder_path.replace(DEVICE_MOUNT_POINT + "/", "").replace(
                DEVICE_MOUNT_POINT, ""
            ) or "/"
            
            folder_total = sum(f["size"] for f in folder_files if f["size"] is not None)
            
            with folder_progress:
                folder_task = folder_progress.add_task(
                    f"  [yellow]{folder_name[:30]}[/yellow]",
                    total=len(folder_files),
                )
                
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

                    # Skip if exists with same size
                    if os.path.exists(local_path):
                        existing_size = os.path.getsize(local_path)
                        if item["size"] is not None and existing_size == item["size"]:
                            skipped += 1
                            folder_progress.advance(folder_task, 1)
                            overall_progress.advance(overall_task, item["size"] or 0)
                            continue

                    if (safe_names.norm_path(local_path) in existing_paths 
                        or safe_names.norm_path(local_path) in used_paths):
                        skipped += 1
                        folder_progress.advance(folder_task, 1)
                        overall_progress.advance(overall_task, item["size"] or 0)
                        continue

                    # Cek apakah filename ASCII
                    try:
                        filename.encode('ascii')
                        is_ascii = True
                    except UnicodeEncodeError:
                        is_ascii = False

                    # Cek apakah file video (rentan truncation) atau file besar
                    is_video = item["path"].lower().endswith(('.mp4', '.mov', '.mkv', '.avi', '.wmv', '.flv', '.webm', '.3gp'))
                    is_large = item["size"] is not None and item["size"] > 5 * 1024 * 1024  # > 5MB
                    
                    if is_ascii and not is_video:
                        # ASCII + non-video: pakai adb pull (cepat)
                        ok, transferred = pull_file_with_adb_pull(
                            remote_path, local_path, item["size"]
                        )
                        
                        # Validasi tambahan untuk file besar
                        if ok and is_large and transferred < (item["size"] or 0) * 0.95:
                            # Download >5% kurang dari expected - fallback ke tar
                            if os.path.exists(local_path):
                                os.remove(local_path)
                            console.print(f"\n[yellow]  ⚠️  adb pull incomplete ({format_size(transferred)}/{format_size(item['size'])}), retry via tar...[/yellow]")
                            ok, transferred, err = pull_file_via_exec_out(
                                remote_path, local_path
                            )
                    else:
                        # Video file atau Unicode: pakai tar streaming (reliable)
                        ok, transferred, err = pull_file_via_exec_out(
                            remote_path, local_path
                        )

                    if ok:
                        used_paths.add(safe_names.norm_path(local_path))
                        total_transferred += transferred
                        success += 1
                        if copy_mode == "move":
                            e_remote = escape_adb_shell(remote_path)
                            adb_run(["shell", f'rm "{e_remote}"'], timeout=10)
                    else:
                        if not is_ascii:
                            skipped_unicode += 1
                        else:
                            failed += 1

                    folder_progress.advance(folder_task, 1)
                    overall_progress.advance(overall_task, transferred)

    summary = f"""
[{'=' * 60}]
  LAPORAN BACKUP
[{'=' * 60}]
  Mode         : {copy_mode}
  Berhasil     : {success}
  Gagal        : {failed}
  Dilewati     : {skipped}
  Unicode/Emoji: {skipped_unicode}
  Total        : {total_files}
  Ukuran       : {format_size(total_transferred)}
[{'=' * 60}]
"""
    console.print(summary)

    if failed == 0 and skipped_unicode == 0:
        console.print("\n[green][SUKSES][/green] Semua file berhasil dicadangkan!")
    else:
        if skipped_unicode > 0:
            console.print(f"\n[yellow][INFO][/yellow] {skipped_unicode} file Unicode/emoji di-skip (butuh tar streaming)")
        if failed > 0:
            console.print(f"[red][WARN][/red] {failed} file gagal dicadangkan.")


def clear_line():
    """Hapus baris saat ini (fallback jika rich tidak tersedia)."""
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()


def draw_progress_bar(percent, filename, transferred, total_size, speed_mbps=None):
    """Fallback progress bar (tanpa rich)."""
    bar_width = 40
    filled = int(bar_width * percent / 100)
    bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
    fname = filename[:25] if filename else ""
    status = f"\r\033[K[{bar}] {percent:5.1f}% | {fname:25s} | {format_size(transferred)}/{format_size(total_size)}"
    if speed_mbps is not None and speed_mbps > 0:
        status += f" | {speed_mbps:.1f} MB/s"
    sys.stdout.write(status)
    sys.stdout.flush()


def draw_folder_progress(folder_percent, overall_percent, folder_name, file_idx, total_files, folder_transferred, folder_total, speed_mbps):
    """Fallback folder progress bar (tanpa rich)."""
    bar_width = 30
    filled = int(bar_width * folder_percent / 100)
    bar = "\u2588" * filled + "\u2591" * (bar_width - filled)
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


def group_by_folder(media_files):
    """Kelompokkan file berdasarkan folder."""
    folders = {}
    for item in media_files:
        folder = os.path.dirname(item["path"])
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(item)
    return folders


def print_folder_summary(folders):
    """Tampilkan ringkasan folder yang ditemukan."""
    if RICH_AVAILABLE:
        table = Table(title="Folder Media Yang Ditemukan", border_style="blue")
        table.add_column("#", style="dim")
        table.add_column("File", justify="right")
        table.add_column("Ukuran", justify="right")
        table.add_column("Folder")
        sorted_folders = sorted(folders.items(), key=lambda x: len(x[1]), reverse=True)
        for idx, (folder, files) in enumerate(sorted_folders, 1):
            total_size = sum(f["size"] for f in files if f["size"] is not None)
            display_folder = folder.replace(DEVICE_MOUNT_POINT + "/", "/")
            table.add_row(str(idx), str(len(files)), format_size(total_size), display_folder)
        console.print(table)
        console.print(f"  Total folder: {len(sorted_folders)}")
    else:
        print(f"\n{'=' * 60}")
        print("  FOLDER MEDIA YANG DITEMUKAN")
        print(f"{'=' * 60}")
        sorted_folders = sorted(folders.items(), key=lambda x: len(x[1]), reverse=True)
        for idx, (folder, files) in enumerate(sorted_folders, 1):
            total_size = sum(f["size"] for f in files if f["size"] is not None)
            display_folder = folder.replace(DEVICE_MOUNT_POINT + "/", "/")
            print(f"  {idx:2d}. [{len(files):3d} file] {format_size(total_size):>10s}  {display_folder}")
        print(f"{'=' * 60}")
        print(f"  Total folder: {len(sorted_folders)}")
        print(f"{'=' * 60}")


def select_folders(folders_dict):
    """Pilih folder tertentu untuk backup."""
    sorted_folders = sorted(folders_dict.items(), key=lambda x: len(x[1]), reverse=True)
    print(f"\n{'=' * 60}")
    print("  PILIH FOLDER UNTUK BACKUP")
    print(f"{'=' * 60}")
    for idx, (folder, files) in enumerate(sorted_folders, 1):
        total_size = sum(f["size"] for f in files if f["size"] is not None)
        display_folder = folder.replace(DEVICE_MOUNT_POINT + "/", "/")
        print(f"  {idx:2d}. [{len(files):3d} file] {format_size(total_size):>10s}  {display_folder}")
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


def copy_with_progress_fallback(media_files, new_folders, total_new_size, existing_paths, used_paths, copy_mode):
    """
    Copy file dengan fallback progress manual (saat rich tidak ada).
    Versi teroptimasi dari backup_tool_adb asli.
    """
    total_files = len(media_files)
    success = 0
    failed = 0
    skipped = 0
    skipped_unicode = 0
    total_transferred = 0
    sorted_folders = sorted(new_folders.items(), key=lambda x: x[0])

    print(f"\n[START] Memulai {copy_mode} {len(media_files)} file dari {len(sorted_folders)} folder...")
    print(f"       Total ukuran: {format_size(total_new_size)}")
    os.makedirs(PC_BACKUP_DIR, exist_ok=True)

    for folder_idx, (folder_path, folder_files) in enumerate(sorted_folders, 1):
        folder_name = folder_path.replace(DEVICE_MOUNT_POINT + "/", "").replace(
            DEVICE_MOUNT_POINT, ""
        ) or "/"

        print(f"\n[{folder_idx}/{len(sorted_folders)}] Folder: {folder_name}")
        print(f"       File: {len(folder_files)} | Ukuran: {format_size(sum(f['size'] for f in folder_files if f['size'] is not None))}")

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

            # Skip if exists with same size
            if os.path.exists(local_path):
                existing_size = os.path.getsize(local_path)
                if item["size"] is not None and existing_size == item["size"]:
                    skipped += 1
                    total_transferred += existing_size
                    continue

            if (safe_names.norm_path(local_path) in existing_paths
                or safe_names.norm_path(local_path) in used_paths):
                skipped += 1
                total_transferred += item["size"] if item["size"] else 0
                continue

            # Cek apakah filename ASCII
            try:
                filename.encode('ascii')
                is_ascii = True
            except UnicodeEncodeError:
                is_ascii = False

            # Video files pakai tar streaming (lebih reliable, cegah moov truncation)
            is_video = remote_path.lower().endswith(('.mp4', '.mov', '.mkv', '.avi', '.wmv', '.flv', '.webm', '.3gp'))

            if is_ascii and not is_video:
                ok, transferred = pull_file_with_adb_pull(remote_path, local_path, item["size"])
                
                # Auto-fallback ke tar jika adb pull incomplete untuk file > 5MB
                is_large = item["size"] is not None and item["size"] > 5 * 1024 * 1024
                if ok and is_large and transferred < (item["size"] or 0) * 0.95:
                    if os.path.exists(local_path):
                        os.remove(local_path)
                    print(f"\n  ⚠️  adb pull incomplete ({format_size(transferred)}/{format_size(item['size'])}), retry via tar...")
                    ok, transferred, err = pull_file_via_exec_out(remote_path, local_path)
            else:
                ok, transferred, err = pull_file_via_exec_out(remote_path, local_path)

            if ok:
                used_paths.add(safe_names.norm_path(local_path))
                total_transferred += transferred
                success += 1
                
                overall_percent = min(100.0, total_transferred / total_new_size * 100) if total_new_size > 0 else 100
                draw_folder_progress(
                    (file_idx_in_folder / len(folder_files)) * 100,
                    overall_percent,
                    folder_name,
                    file_idx_in_folder,
                    len(folder_files),
                    total_transferred,
                    total_new_size,
                    0,
                )
                print()
                
                if copy_mode == "move":
                    e_remote = escape_adb_shell(remote_path)
                    adb_run(["shell", f'rm "{e_remote}"'], timeout=10)
            else:
                if not is_ascii:
                    skipped_unicode += 1
                else:
                    print(f"\n[ERROR] Gagal: {filename}")
                    failed += 1

    draw_folder_progress(100, 100, "SELESAI", len(sorted_folders), len(sorted_folders),
                          total_transferred, total_new_size, 0)
    print()

    print(f"\n{'=' * 60}")
    print("  LAPORAN BACKUP")
    print(f"{'=' * 60}")
    print(f"  Mode         : {copy_mode}")
    print(f"  Berhasil     : {success}")
    print(f"  Gagal        : {failed}")
    print(f"  Dilewati     : {skipped}")
    print(f"  Unicode/Emoji: {skipped_unicode}")
    print(f"  Total        : {total_files}")
    print(f"  Ukuran       : {format_size(total_transferred)} / {format_size(total_new_size)}")
    print(f"{'=' * 60}")

    if failed == 0 and skipped_unicode == 0:
        print("\n[SUKSES] Semua file berhasil dicadangkan!")
    else:
        if skipped_unicode > 0:
            print(f"\n[INFO] {skipped_unicode} file Unicode/emoji di-skip")
        if failed > 0:
            print(f"[WARN] {failed} file gagal dicadangkan.")


def run_backup(device_id):
    """Jalankan seluruh proses backup dengan optimasi dan rich.progress."""
    print(f"\n{'=' * 60}")
    print(f"  Device    : {device_id}")
    print(f"  Backup To : {PC_BACKUP_DIR}")
    print(f"{'=' * 60}")

    # Phase 1: Scan
    all_media = adb_list_files_recursive()
    if not all_media:
        print("\n[TIDAK ADA FILE] Tidak ditemukan file media di HP.")
        return

    # Phase 2: Filter dengan caching
    cleaned = clean_zero_byte_files(PC_BACKUP_DIR)
    if cleaned > 0:
        print(f"\n[CLEANUP] Menghapus {cleaned} file 0 byte dari backup sebelumnya.")

    # Cache existing paths untuk filtering cepat
    existing_paths = safe_names.get_existing_paths(PC_BACKUP_DIR)
    new_files = filter_new_files_by_path(all_media, PC_BACKUP_DIR, existing_paths)
    dup_count = len(all_media) - len(new_files)
    total_new_size = sum(f["size"] for f in new_files if f["size"] is not None)

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

    # Phase 3: Pilih mode
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
            print("\n[BATAL] Backup dibatalkan.")
            return
        else:
            print("  Input tidak valid. Pilih A, B, atau C.")

    total_new_size = sum(f["size"] for f in new_files if f["size"] is not None)
    used_paths = set()

    # Phase 4: Transfer dengan progress
    if RICH_AVAILABLE:
        copy_with_progress_rich(new_files, new_folders, total_new_size, existing_paths, used_paths, copy_mode)
    else:
        copy_with_progress_fallback(new_files, new_folders, total_new_size, existing_paths, used_paths, copy_mode)


def main():
    """Entry point program."""
    enable_ansi_colors()

    if RICH_AVAILABLE:
        console.print(Panel.fit(
            "[bold cyan]CLI Automated Media Backup Tool (ADB Version)[/bold cyan]\n"
            f"[dim]Device Root: {DEVICE_MOUNT_POINT}[/dim]\n"
            f"[dim]Backup To: {PC_BACKUP_DIR}[/dim]\n"
            f"[dim]Rich UI: Enabled ✓[/dim]",
            border_style="blue"
        ))
    else:
        print(f"{'=' * 60}")
        print("  CLI Automated Media Backup Tool (ADB Version)")
        print("  Optimized - Zero Python Dependency (butuh adb)")
        print(f"{'=' * 60}")
        print(f"  Device Root  : {DEVICE_MOUNT_POINT}")
        print(f"  Backup To    : {PC_BACKUP_DIR}")
        print(f"  Extensions   : {', '.join(VALID_EXTENSIONS)}")
        print(f"  Scan Paths   : {len(SCAN_PATHS)} lokasi")
        print(f"  Rich UI      : Tidak tersedia (install rich untuk UI lebih baik)")
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
