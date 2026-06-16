# -*- coding: utf-8 -*-
"""
CLI Automated Media Backup Tool
Python 3.8+ | Zero Dependency | Windows 10/11
"""

import os
import sys
import time
import shutil
import ctypes
import safe_names
from ctypes import wintypes

# ============================================================================
# KONFIGURASI PENGGUNA
# ============================================================================
TARGET_DRIVE_NAME = "Internal Storage"  # Kata kunci untuk mengenali drive HP
MANUAL_PATH = None  # Path manual lengkap (misal: "E:\\" atau None untuk auto-detect)
PC_BACKUP_DIR = r"D:\Backup_Media_HP"   # Lokasi absolut direktori backup di PC
VALID_EXTENSIONS = (
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp',
    '.mp4', '.mov', '.mkv', '.avi', '.wmv', '.flv', '.webm', '.3gp'
)
CHUNK_SIZE = 1024 * 1024  # 1MB per chunk
POLL_INTERVAL = 2  # detik
PROGRESS_BAR_WIDTH = 30
PROGRESS_UPDATE_INTERVAL = 0.1  # detik
# ============================================================================


def enable_ansi_colors():
    """Aktifkan ANSI escape codes di Windows CMD/PowerShell."""
    kernel32 = ctypes.windll.kernel32
    h_stdout = kernel32.GetStdHandle(-11)
    mode = wintypes.DWORD()
    kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode))
    mode = mode.value | 0x0004
    kernel32.SetConsoleMode(h_stdout, mode)


def get_drive_letters():
    """Mendapatkan semua drive letter yang tersedia."""
    drives = []
    for letter in (chr(c) for c in range(ord('A'), ord('Z') + 1)):
        drive = f"{letter}:\\"
        if os.path.exists(drive):
            drives.append(drive)
    return drives


def detect_hp_drive():
    """
    Mendeteksi drive HP berdasarkan MANUAL_PATH atau auto-detect by TARGET_DRIVE_NAME.
    Prioritas: MANUAL_PATH > auto-detect.
    """
    if MANUAL_PATH is not None:
        if os.path.exists(MANUAL_PATH):
            return MANUAL_PATH
        else:
            print(f"[WARN] MANUAL_PATH '{MANUAL_PATH}' tidak ditemukan!")
    
    drives = get_drive_letters()
    for drive in drives:
        try:
            for entry in os.listdir(drive):
                if TARGET_DRIVE_NAME.lower() in entry.lower():
                    return drive
        except (PermissionError, OSError):
            continue
    return None


def prompt_manual_path():
    """Meminta user memasukkan path HP secara manual."""
    print("\n" + "="*60)
    print("  INPUT PATH MANUAL")
    print("="*60)
    print("  Masukkan path lengkap ke storage HP.")
    print("  Contoh untuk drive letter  : E:\\")
    print("  Contoh untuk MTP           : This PC\\NamaHP\\Internal storage")
    print("  Atau cek di File Explorer > klik kanan > Properties > Location")
    print("-"*60)
    while True:
        path = input("  Path: ").strip().strip('"').strip("'")
        if not path:
            print("  [ERROR] Path tidak boleh kosong.")
            continue
        if os.path.exists(path):
            print(f"  [OK] Path valid: {path}")
            return path
        else:
            print(f"  [WARN] Path tidak ditemukan: {path}")
            retry = input("  Coba lagi? (y/n): ").strip().lower()
            if retry != 'y':
                return None


def wait_for_hp():
    """Menunggu HP terhubung (polling mode) dengan opsi manual input."""
    print("[IDLE] Menunggu HP terhubung via kabel USB...")
    print("       Pastikan mode koneksi diatur ke 'File Transfer / MTP'")
    print("       Tekan 'M' + Enter untuk input path manual kapan saja.\n")
    
    while True:
        drive = detect_hp_drive()
        if drive:
            print(f"[FOUND] Drive HP terdeteksi: {drive}")
            return drive
        
        try:
            choice = input("[IDLE] Belum terdeteksi. Tekan 'M' untuk manual, atau Enter untuk cek lagi: ").strip().upper()
            if choice == 'M':
                manual = prompt_manual_path()
                if manual:
                    return manual
        except EOFError:
            pass
        
        time.sleep(POLL_INTERVAL)


def scan_media(drive_path):
    """
    Deep scan seluruh folder di drive_path untuk file media.
    Mengembalikan list dict: {'path': str, 'size': int}
    """
    media_files = []
    print(f"[SCAN] Melakukan deep scan di {drive_path} ...")
    scan_start = time.time()
    
    for root, dirs, files in os.walk(drive_path):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext in VALID_EXTENSIONS:
                full_path = os.path.join(root, filename)
                try:
                    size = os.path.getsize(full_path)
                    media_files.append({'path': full_path, 'size': size})
                except OSError:
                    continue
    
    elapsed = time.time() - scan_start
    print(f"       Scan selesai dalam {elapsed:.1f} detik")
    print(f"       Total file media ditemukan: {len(media_files)}")
    return media_files


def get_existing_files(backup_dir):
    """Mendapatkan set nama file yang sudah ada di direktori backup."""
    existing = set()
    if not os.path.exists(backup_dir):
        return existing
    for root, dirs, files in os.walk(backup_dir):
        for f in files:
            existing.add(f)
    return existing


def filter_new_files(media_files, existing_files):
    """Filter file yang belum ada di backup (incremental)."""
    new_files = []
    for item in media_files:
        filename = os.path.basename(item['path'])
        if filename not in existing_files:
            new_files.append(item)
    return new_files


def filter_new_files_by_path(media_files, backup_dir, existing_paths, base_path):
    """Filter file berdasarkan path tujuan backup."""
    new_files = []
    for item in media_files:
        rel_path = os.path.relpath(item['path'], base_path)
        dst_path = os.path.join(backup_dir, rel_path)
        if safe_names.norm_path(dst_path) not in existing_paths:
            new_files.append(item)
    return new_files


def format_size(size_bytes):
    """Format ukuran file ke human-readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def draw_progress_bar(percent, filename, transferred, total_size, speed_mbps):
    """Gambar progress bar dengan ANSI codes."""
    filled = int(PROGRESS_BAR_WIDTH * percent / 100)
    bar = '█' * filled + '░' * (PROGRESS_BAR_WIDTH - filled)
    fname = filename[:25]
    status = (
        f"\r\033[K[{bar}] {percent:3.0f}% | "
        f"{fname:25s} | "
        f"{format_size(transferred)}/{format_size(total_size)} | "
        f"{speed_mbps:.1f} MB/s"
    )
    sys.stdout.write(status)
    sys.stdout.flush()


def copy_with_progress(src, dst, filename, total_size):
    """
    Copy file dengan chunk-based streaming dan progress bar real-time.
    Menggunakan os.open untuk kontrol penuh atas file descriptor.
    """
    src_fd = os.open(src, os.O_RDONLY | os.O_BINARY)
    dst_fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_BINARY, 0o644)
    
    transferred = 0
    start_time = time.time()
    last_update = start_time
    speed_mbps = 0.0
    
    try:
        while True:
            chunk = os.read(src_fd, CHUNK_SIZE)
            if not chunk:
                break
            os.write(dst_fd, chunk)
            transferred += len(chunk)
            
            now = time.time()
            elapsed = now - start_time
            if elapsed > 0:
                speed_mbps = (transferred / (1024 * 1024)) / elapsed
            
            if now - last_update >= PROGRESS_UPDATE_INTERVAL:
                percent = min(100.0, (transferred / total_size) * 100)
                draw_progress_bar(percent, filename, transferred, total_size, speed_mbps)
                last_update = now
        
        os.close(dst_fd)
        dst_fd = None
        
        actual_size = os.path.getsize(dst) if os.path.exists(dst) else 0
        if actual_size != total_size:
            raise ValueError(f"Ukuran file tidak sesuai: diharapkan {total_size}, dapat {actual_size}")
        
        percent = 100.0
        draw_progress_bar(percent, filename, total_size, total_size, speed_mbps)
        print()
        return True
    except Exception as e:
        print(f"\n[ERROR] Gagal menyalin {filename}: {e}")
        if os.path.exists(dst) and os.path.getsize(dst) == 0:
            try:
                os.remove(dst)
            except:
                pass
        return False
    finally:
        if dst_fd is not None:
            try:
                os.close(dst_fd)
            except:
                pass
        os.close(src_fd)


def group_by_folder_usb(media_files):
    folders = {}
    for item in media_files:
        folder = os.path.dirname(item['path'])
        if folder not in folders:
            folders[folder] = []
        folders[folder].append(item)
    return folders


def draw_folder_progress_usb(folder_percent, overall_percent, folder_name, file_idx, total_files, folder_transferred, folder_total, speed_mbps):
    bar_width = 30
    filled = int(bar_width * folder_percent / 100)
    bar = '█' * filled + '░' * (bar_width - filled)
    
    display_folder = folder_name[:25] if len(folder_name) > 25 else folder_name
    status = (
        f"\r\033[K[{bar}] {folder_percent:5.1f}% | "
        f"{display_folder:25s} | "
        f"{file_idx}/{total_files} | "
        f"{format_size(folder_transferred)}/{format_size(folder_total)} | "
        f"Total: {overall_percent:5.1f}%"
    )
    if speed_mbps is not None and speed_mbps > 0:
        status += f" | {speed_mbps:.1f} MB/s"
    sys.stdout.write(status)
    sys.stdout.flush()


def clean_zero_byte_files(root: str) -> int:
    """Hapus file 0 byte di direktori backup untuk mengatasi file corrupt."""
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


def run_backup(drive_path):
    """Jalankan seluruh proses backup: scan, summary, transfer."""
    print(f"\n{'='*60}")
    print(f"  Drive sumber : {drive_path}")
    print(f"  Drive tujuan : {PC_BACKUP_DIR}")
    print(f"{'='*60}")
    
    # Phase 1: Scan
    all_media = scan_media(drive_path)
    if not all_media:
        print("\n[TIDAK ADA FILE] Tidak ditemukan file media di HP.")
        return
    
    # Phase 2: Filter & Summary
    existing = get_existing_files(PC_BACKUP_DIR)
    existing_paths = safe_names.get_existing_paths(PC_BACKUP_DIR)
    cleaned = clean_zero_byte_files(PC_BACKUP_DIR)
    if cleaned > 0:
        print(f"\n[CLEANUP] Menghapus {cleaned} file 0 byte dari backup sebelumnya.")
        existing_paths = safe_names.get_existing_paths(PC_BACKUP_DIR)
    new_files = filter_new_files_by_path(all_media, PC_BACKUP_DIR, existing_paths, drive_path)
    dup_count = len(all_media) - len(new_files)
    total_new_size = sum(f['size'] for f in new_files)
    
    all_folders = group_by_folder_usb(all_media)
    new_folders = group_by_folder_usb(new_files)
    
    print(f"\n{'='*60}")
    print("  RINGKASAN BACKUP")
    print(f"{'='*60}")
    print(f"  Total file media di HP   : {len(all_media)}")
    print(f"  File baru (belum backup) : {len(new_files)}")
    print(f"  File duplikat            : {dup_count}")
    print(f"  Total ukuran baru        : {format_size(total_new_size)}")
    print(f"  Lokasi backup            : {PC_BACKUP_DIR}")
    print(f"  Folder ditemukan         : {len(new_folders)}")
    print(f"{'='*60}")
    
    if not new_files:
        print("\n[TIDAK ADA FILE BARU] Semua file sudah tercadangkan.")
        return
    
    # Phase 3: Transfer with folder progress
    print(f"\n[START] Memulai transfer {len(new_files)} file dari {len(new_folders)} folder...")
    os.makedirs(PC_BACKUP_DIR, exist_ok=True)
    
    success = 0
    failed = 0
    skipped = 0
    total_transferred = 0
    used_paths = set()
    
    sorted_folders = sorted(new_folders.items(), key=lambda x: x[0])
    
    for folder_idx, (folder_path, folder_files) in enumerate(sorted_folders, 1):
        folder_name = folder_path.replace(drive_path, '').lstrip('\\').lstrip('/') or '/'
        if not folder_name:
            folder_name = '/'
        
        print(f"\n[{folder_idx}/{len(sorted_folders)}] Folder: {folder_name}")
        print(f"       File: {len(folder_files)} | Ukuran: {format_size(sum(f['size'] for f in folder_files))}")
        
        folder_transferred = 0
        folder_total = sum(f['size'] for f in folder_files)
        
        for file_idx_in_folder, item in enumerate(folder_files, 1):
            filename = os.path.basename(item['path'])
            rel_path = os.path.relpath(item['path'], drive_path)
            original_dst_path = os.path.join(PC_BACKUP_DIR, rel_path)
            dst_path, _ = safe_names.resolve_safe_destination_path(
                original_dst_path,
                existing_paths=existing_paths,
                used_paths=used_paths,
            )
            
            dst_dir = os.path.dirname(dst_path)
            os.makedirs(dst_dir, exist_ok=True)
            
            if safe_names.norm_path(dst_path) in existing_paths or safe_names.norm_path(dst_path) in used_paths or os.path.exists(dst_path):
                skipped += 1
                folder_transferred += item['size'] if item['size'] else 0
                total_transferred += item['size'] if item['size'] else 0
                folder_percent = (file_idx_in_folder / len(folder_files)) * 100
                overall_percent = min(100.0, (total_transferred + folder_transferred) / total_new_size * 100) if total_new_size > 0 else 0
                draw_folder_progress_usb(folder_percent, overall_percent, folder_name, file_idx_in_folder, len(folder_files),
                                       total_transferred, total_new_size, 0)
                print()
                continue
            
            src_fd = os.open(item['path'], os.O_RDONLY | os.O_BINARY)
            dst_fd = os.open(dst_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_BINARY, 0o644)
            
            transferred = 0
            start_time = time.time()
            last_update = start_time
            speed_mbps = 0.0
            
            try:
                while True:
                    chunk = os.read(src_fd, CHUNK_SIZE)
                    if not chunk:
                        break
                    os.write(dst_fd, chunk)
                    transferred += len(chunk)
                    
                    now = time.time()
                    elapsed = now - start_time
                    if elapsed > 0:
                        speed_mbps = (transferred / (1024 * 1024)) / elapsed
                    
                    if now - last_update >= PROGRESS_UPDATE_INTERVAL:
                        folder_percent = min(100.0, (transferred / item['size']) * 100) if item['size'] else 0
                        overall_percent = min(99.9, (total_transferred + folder_transferred + transferred) / total_new_size * 100) if total_new_size > 0 else 0
                        draw_folder_progress_usb(folder_percent, overall_percent, folder_name, file_idx_in_folder, len(folder_files),
                                               total_transferred + folder_transferred + transferred, total_new_size, speed_mbps)
                        last_update = now
                
                os.close(dst_fd)
                dst_fd = None
                
                actual_size = os.path.getsize(dst_path) if os.path.exists(dst_path) else 0
                if actual_size != item['size']:
                    raise ValueError(f"Ukuran file tidak sesuai: diharapkan {item['size']}, dapat {actual_size}")
                
                used_paths.add(safe_names.norm_path(dst_path))
                folder_transferred += transferred
                total_transferred += transferred
                success += 1
                draw_folder_progress_usb(100, min(100.0, total_transferred / total_new_size * 100) if total_new_size > 0 else 100, 
                                       folder_name, file_idx_in_folder, len(folder_files),
                                       total_transferred, total_new_size, 0)
                print()
            except Exception as e:
                print(f"\n[ERROR] Gagal menyalin {filename}: {e}")
                failed += 1
                try:
                    if os.path.exists(dst_path):
                        os.remove(dst_path)
                except:
                    pass
            finally:
                if dst_fd is not None:
                    try:
                        os.close(dst_fd)
                    except:
                        pass
                os.close(src_fd)
    
    draw_folder_progress_usb(100, 100, "SELESAI", len(sorted_folders), len(sorted_folders), total_transferred, total_new_size, 0)
    print()
    
    # Laporan akhir
    print(f"\n{'='*60}")
    print("  LAPORAN BACKUP")
    print(f"{'='*60}")
    print(f"  Berhasil  : {success}")
    print(f"  Gagal     : {failed}")
    print(f"  Dilewati   : {skipped}")
    print(f"  Total     : {len(new_files)}")
    print(f"  Ukuran    : {format_size(total_transferred)} / {format_size(total_new_size)}")
    print(f"{'='*60}")
    
    if failed == 0:
        print("\n[SUKSES] Semua file berhasil dicadangkan!")
    else:
        print(f"\n[WARN] {failed} file gagal dicadangkan.")


def main():
    enable_ansi_colors()
    
    print(f"{'='*60}")
    print("  CLI Automated Media Backup Tool")
    print("  Python Version - Zero Dependency")
    print(f"{'='*60}")
    print(f"  Target Drive : {TARGET_DRIVE_NAME}")
    print(f"  Backup To    : {PC_BACKUP_DIR}")
    print(f"  Extensions   : {', '.join(VALID_EXTENSIONS)}")
    print(f"{'='*60}\n")
    
    if not os.path.exists(PC_BACKUP_DIR):
        print(f"[INFO] Direktori backup akan dibuat: {PC_BACKUP_DIR}")
    
    try:
        while True:
            drive = wait_for_hp()
            if drive:
                run_backup(drive)
            print("\n[IDLE] Menunggu HP terhubung kembali...")
            print("       Cabut kabel untuk keluar dari program.\n")
    except KeyboardInterrupt:
        print("\n\n[EXIT] Program dihentikan oleh user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
