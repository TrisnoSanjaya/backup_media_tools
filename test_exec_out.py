#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test adb exec-out untuk tar streaming"""

import subprocess
import os
import io
import tarfile

adb_path = "C:\\adb\\adb.exe"

remote_file = "/sdcard/DCIM/Camera/IMG20240903_001232_IPHONE_14_PROMAX_EndaMedia.jpg"

parent_dir = os.path.dirname(remote_file)
filename = os.path.basename(remote_file)

escaped_parent = parent_dir.replace("'", "'\\''")
escaped_filename = filename.replace("'", "'\\''")

# PENTING: gunakan exec-out untuk binary, bukan shell
shell_cmd = f"cd '{escaped_parent}' && tar -cf - '{escaped_filename}'"

print(f"Testing adb exec-out...")
print(f"Cmd: {shell_cmd}\n")

result = subprocess.run(
    [adb_path, "exec-out", shell_cmd],
    capture_output=True,
    timeout=30
)

print(f"Exit code: {result.returncode}")
print(f"Stdout size: {len(result.stdout)} bytes")
print(f"Stderr size: {len(result.stderr)} bytes")

if result.stderr:
    print(f"Stderr: {result.stderr.decode('utf-8', errors='replace')[:200]}")

# Try extract
if result.returncode == 0 and len(result.stdout) > 512:
    print("\n[EXTRACT]")
    try:
        tar_stream = io.BytesIO(result.stdout)
        with tarfile.open(fileobj=tar_stream, mode='r') as tar:
            members = tar.getmembers()
            print(f"Members: {len(members)}")
            for m in members:
                print(f"  - {m.name} (size: {m.size:,} bytes)")
            
            if members:
                member = members[0]
                file_data = tar.extractfile(member)
                if file_data:
                    content = file_data.read()
                    print(f"  Extracted: {len(content):,} bytes")
                    if content[:2] == b'\xff\xd8':
                        print("  [SUCCESS] Valid JPEG!")
                        # Save ke file untuk verifikasi visual
                        with open("test_extract.jpg", "wb") as f:
                            f.write(content)
                        print(f"  Saved to: test_extract.jpg")
                    else:
                        print(f"  Signature: {content[:4].hex()}")
    except Exception as e:
        print(f"Extract error: {e}")
else:
    print("[FAIL] Output too small or error")
