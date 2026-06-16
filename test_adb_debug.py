#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Debug script untuk test adb pull dengan berbagai filename"""

import subprocess
import os

def get_adb_path():
    """Find adb executable"""
    adb_exe = "adb.exe"
    try:
        result = subprocess.run([adb_exe, "version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            return adb_exe
    except:
        pass
    return None

def test_adb_connection():
    """Test jika device terhubung"""
    adb = get_adb_path()
    if not adb:
        print("[ERROR] ADB tidak ditemukan")
        return False
    
    result = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=10)
    print("Device list:")
    print(result.stdout)
    
    lines = [l.strip() for l in result.stdout.split('\n') if l.strip() and not l.startswith('List')]
    for line in lines:
        if 'device' in line and 'offline' not in line.lower():
            return True
    
    print("[ERROR] Tidak ada device terhubung")
    return False

def list_files_in_dcim():
    """List files di /sdcard/DCIM/Camera"""
    adb = get_adb_path()
    if not adb:
        return
    
    print("\n=== Files in /sdcard/DCIM/Camera ===")
    result = subprocess.run(
        [adb, "ls", "/sdcard/DCIM/Camera"],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0:
        print(result.stdout[:1000])  # First 1000 chars
    else:
        print(f"[ERROR] ls failed: {result.stderr[:500]}")

def test_pull(remote_path):
    """Test adb pull dengan specific path"""
    adb = get_adb_path()
    if not adb:
        return
    
    print(f"\n=== Test Pull: {remote_path} ===")
    
    # Verify file exists
    result = subprocess.run(
        [adb, "ls", "-la", remote_path],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode != 0:
        print(f"[ERROR] File tidak ditemukan atau ls gagal")
        print(f"stderr: {result.stderr[:300]}")
        return False
    
    print(f"[OK] File exists: {result.stdout[:200]}")
    
    # Try pull
    temp_file = "/tmp/test_pull_output.bin"
    if os.path.exists(temp_file):
        os.remove(temp_file)
    
    print(f"[INFO] Pulling ke: {temp_file}")
    result = subprocess.run(
        [adb, "pull", remote_path, temp_file],
        stdout=None,
        stderr=None,
        timeout=60
    )
    
    if result.returncode == 0 and os.path.exists(temp_file):
        size = os.path.getsize(temp_file)
        print(f"[OK] Pull success! Size: {size} bytes")
        os.remove(temp_file)
        return True
    else:
        print(f"[ERROR] Pull failed with exit code: {result.returncode}")
        if os.path.exists(temp_file):
            size = os.path.getsize(temp_file)
            print(f"       Partial file: {size} bytes")
            os.remove(temp_file)
        return False

if __name__ == "__main__":
    print("=== ADB Debug Script ===\n")
    
    if not test_adb_connection():
        exit(1)
    
    # List files first
    list_files_in_dcim()
    
    # Test dengan beberapa file
    test_paths = [
        "/sdcard/DCIM/Camera/IMG20240903_001232_IPHONE_14_PROMAX_EndaMedia.jpg",
        "/sdcard/DCIM/Camera/IMG20240903_101548_IPHONE_14_PROMAX_EndaMedia.jpg",
    ]
    
    for path in test_paths:
        test_pull(path)
    
    print("\n=== Debug Complete ===")
