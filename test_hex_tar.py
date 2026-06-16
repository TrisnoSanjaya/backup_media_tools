#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test hex-escaped filename approach untuk tar streaming"""

import subprocess
import io
import tarfile
import os

adb_path = "C:\\adb\\adb.exe"

# Dari find sebelumnya, actual filename:
actual_filename = "IMG20240903_001232_IPHONE_14_PROMAX✺𝓔𝓷𝓭𝓪𝓜𝓮𝓭𝓲𝓪✺.jpg"
parent_dir = "/sdcard/DCIM/Camera"

print(f"Actual filename: {actual_filename}")
print(f"UTF-8 bytes: {actual_filename.encode('utf-8').hex()}\n")

# === APPROACH 1: printf dengan hex escapes (ASCII-safe) ===
print("=== APPROACH 1: printf hex -> temp file -> tar ===")
fname_bytes = actual_filename.encode('utf-8')
hex_escapes = ''.join(f'\\x{b:02x}' for b in fname_bytes)

# Step 1: Write filename to temp file with echo -ne + hex escapes
write_cmd = f"echo -ne '{hex_escapes}' > /data/local/tmp/backup_fname.txt"
print(f"Write cmd: {write_cmd}")

result = subprocess.run(
    [adb_path, "exec-out", write_cmd],
    capture_output=True,
    timeout=30
)
print(f"Write exit: {result.returncode}, stderr: {result.stderr.decode('utf-8', errors='replace')[:100]}")

# Verify filename was written correctly
verify_cmd = "cat /data/local/tmp/backup_fname.txt"
result = subprocess.run(
    [adb_path, "exec-out", verify_cmd],
    capture_output=True,
    timeout=30
)
print(f"Filename from temp: {result.stdout}")
print(f"Matches original: {result.stdout.decode('utf-8', errors='replace').strip() == actual_filename}")

# Step 2: Tar using --files-from
escaped_parent = parent_dir.replace("'", "'\\''")
tar_cmd = f"cd '{escaped_parent}' && tar -cf - --files-from=/data/local/tmp/backup_fname.txt"
print(f"\nTar cmd: {tar_cmd}")

result = subprocess.run(
    [adb_path, "exec-out", tar_cmd],
    capture_output=True,
    timeout=60
)

print(f"Tar exit: {result.returncode}")
print(f"Tar stdout: {len(result.stdout)} bytes")
print(f"Tar stderr: {result.stderr.decode('utf-8', errors='replace')[:200]}")

if len(result.stdout) > 512:
    try:
        tar_stream = io.BytesIO(result.stdout)
        with tarfile.open(fileobj=tar_stream, mode='r') as tar:
            members = tar.getmembers()
            print(f"Members: {len(members)}")
            for m in members:
                print(f"  - {m.name} (size: {m.size:,} bytes)")
            
            if members:
                member = members[0]
                data = tar.extractfile(member)
                if data:
                    content = data.read()
                    print(f"Extracted: {len(content):,} bytes")
                    if content[:2] == b'\xff\xd8':
                        print("[SUCCESS] Valid JPEG!")
                        with open("test_hex_tar.jpg", "wb") as f:
                            f.write(content)
                    else:
                        print(f"Signature: {content[:4]}")
    except Exception as e:
        print(f"Extract error: {e}")
else:
    print(f"[FAIL] Tar output too small")

# Cleanup temp
subprocess.run([adb_path, "exec-out", "rm -f /data/local/tmp/backup_fname.txt"], capture_output=True)
