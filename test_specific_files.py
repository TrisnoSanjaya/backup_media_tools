#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test untuk tar streaming debug - gunakan file yang sudah ketahuan"""

import subprocess
import os
import sys

adb_path = "C:\\adb\\adb.exe" if os.path.exists("C:\\adb\\adb.exe") else None
if not adb_path:
    for path_env in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path_env, "adb.exe")
        if os.path.exists(candidate):
            adb_path = candidate
            break

if not adb_path:
    print("[ERROR] ADB tidak ditemukan")
    sys.exit(1)

print(f"[ADB] {adb_path}\n")

# File yang diketahui gagal
test_files = [
    "/sdcard/DCIM/Camera/IMG20240903_001232_IPHONE_14_PROMAX_EndaMedia.jpg",
    "/sdcard/DCIM/Camera/trashed_1782204794_By_Seputar_gcam20_Apr_19_09_Iphone_16_Stabilizer_V9_Auto.jpg",
]

for remote_file in test_files:
    print(f"[TEST] File: {remote_file}")
    
    # Cek file exists
    result = subprocess.run(
        [adb_path, "ls", remote_file],
        capture_output=True,
        text=True,
        timeout=10
    )
    print(f"  ls exit code: {result.returncode}")
    if result.stdout:
        print(f"  ls output: {result.stdout.strip()[:100]}")
    if result.stderr:
        print(f"  ls stderr: {result.stderr.strip()[:100]}")
    
    if result.returncode != 0:
        print("  File tidak ditemukan, lanjut...\n")
        continue
    
    # Test adb pull langsung
    print(f"  Testing adb pull langsung...")
    result = subprocess.run(
        [adb_path, "pull", remote_file, "test_pull.tmp"],
        capture_output=True,
        text=True,
        timeout=30
    )
    print(f"  pull exit code: {result.returncode}")
    if result.stderr:
        print(f"  pull stderr: {result.stderr.strip()[:200]}")
    if os.path.exists("test_pull.tmp"):
        size = os.path.getsize("test_pull.tmp")
        print(f"  pull result size: {size} bytes")
        os.remove("test_pull.tmp")
    
    # Test tar
    print(f"  Testing tar streaming...")
    parent_dir = os.path.dirname(remote_file)
    filename = os.path.basename(remote_file)
    
    escaped_parent = parent_dir.replace("'", "'\\''")
    escaped_filename = filename.replace("'", "'\\''")
    
    shell_cmd = f"cd '{escaped_parent}' && tar -cf - '{escaped_filename}'"
    print(f"  cmd: tar -cf - '{escaped_filename}'")
    
    result = subprocess.run(
        [adb_path, "shell", shell_cmd],
        capture_output=True,
        timeout=30
    )
    
    print(f"  tar exit code: {result.returncode}")
    print(f"  tar stdout size: {len(result.stdout)} bytes")
    if result.stderr:
        stderr_str = result.stderr.decode('utf-8', errors='replace')
        print(f"  tar stderr: {stderr_str[:200]}")
    
    if result.returncode == 0 and len(result.stdout) > 512:
        print(f"  [SUCCESS] Tar output valid")
    else:
        print(f"  [FAIL] Tar output invalid")
    
    print()
