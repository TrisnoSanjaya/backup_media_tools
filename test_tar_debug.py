#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick test untuk tar streaming debug"""

import subprocess
import os
import sys

# Cek ADB tersedia
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

print(f"[ADB] {adb_path}")

# Test adb devices
print("\n[CHECK] Device...")
result = subprocess.run(
    [adb_path, "devices"],
    capture_output=True,
    text=True
)
print(result.stdout)

if "device" not in result.stdout or "offline" in result.stdout:
    print("[ERROR] Device tidak tersedia")
    sys.exit(1)

# Test tar command availability di device
print("\n[TEST] Tar availability di device...")
result = subprocess.run(
    [adb_path, "shell", "which tar"],
    capture_output=True,
    text=True
)
print(f"Tar path: {result.stdout.strip() if result.stdout else 'NOT FOUND'}")
print(f"Exit code: {result.returncode}")

# List file dengan non-ASCII dari device
print("\n[SCAN] Mencari file dengan non-ASCII di /sdcard...")
result = subprocess.run(
    [adb_path, "shell", "find /sdcard/DCIM/Camera -type f -name '*nda*' 2>/dev/null | head -1"],
    capture_output=True,
    text=True,
    timeout=10
)
remote_file = result.stdout.strip()
print(f"Found: {remote_file}")

if not remote_file:
    print("[ERROR] Tidak menemukan file test")
    sys.exit(1)

# Test tar untuk file itu
print(f"\n[TEST] Tar streaming untuk: {remote_file}")
parent_dir = os.path.dirname(remote_file)
filename = os.path.basename(remote_file)

print(f"Parent: {parent_dir}")
print(f"Filename: {filename}")

# Escape single quotes
escaped_parent = parent_dir.replace("'", "'\\''")
escaped_filename = filename.replace("'", "'\\''")

shell_cmd = f"cd '{escaped_parent}' && tar -cf - '{escaped_filename}'"
print(f"Shell cmd: {shell_cmd}\n")

# Run tar via adb shell
result = subprocess.run(
    [adb_path, "shell", shell_cmd],
    capture_output=True,
    timeout=30
)

print(f"Exit code: {result.returncode}")
print(f"Stdout size: {len(result.stdout)} bytes")
print(f"Stderr size: {len(result.stderr)} bytes")

if result.stderr:
    print(f"Stderr: {result.stderr.decode('utf-8', errors='replace')[:300]}")

if result.returncode == 0 and len(result.stdout) > 512:
    print(f"[SUCCESS] Tar output valid ({len(result.stdout)} bytes)")
else:
    print(f"[FAIL] Tar output invalid")
    if result.stderr:
        print(f"Error detail: {result.stderr.decode('utf-8', errors='replace')}")
