#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test tar streaming dan extract content untuk verifikasi"""

import subprocess
import os
import io
import tarfile

adb_path = "C:\\adb\\adb.exe"

remote_file = "/sdcard/DCIM/Camera/IMG20240903_001232_IPHONE_14_PROMAX_EndaMedia.jpg"

# Test tar
parent_dir = os.path.dirname(remote_file)
filename = os.path.basename(remote_file)

escaped_parent = parent_dir.replace("'", "'\\''")
escaped_filename = filename.replace("'", "'\\''")

shell_cmd = f"cd '{escaped_parent}' && tar -cf - '{escaped_filename}'"
print(f"Shell cmd: {shell_cmd}")

result = subprocess.run(
    [adb_path, "shell", shell_cmd],
    capture_output=True,
    timeout=30
)

print(f"Exit code: {result.returncode}")
print(f"Stdout size: {len(result.stdout)} bytes")

# Coba extract
print("\n[EXTRACT] Mencoba extract tar...")
try:
    tar_stream = io.BytesIO(result.stdout)
    with tarfile.open(fileobj=tar_stream, mode='r') as tar:
        members = tar.getmembers()
        print(f"Members in tar: {len(members)}")
        for m in members:
            print(f"  - {m.name} (size: {m.size} bytes, type: {m.type})")
        
        if members:
            member = members[0]
            file_data = tar.extractfile(member)
            if file_data:
                content = file_data.read()
                print(f"  Extracted: {len(content)} bytes")
                print(f"  First 20 bytes: {content[:20].hex()}")
                # Check if it looks like a real JPEG
                if content[:2] == b'\xff\xd8':
                    print("  File signature: JPEG (valid image file)")
                else:
                    print(f"  File signature: {content[:4]}")
                    print(f"  Content preview: {content[:100]}")
except Exception as e:
    print(f"Extract error: {e}")

# Bandingkan dengan ukuran dari ls
print("\n[COMPARE] Ukuran dari ls:")
result = subprocess.run(
    [adb_path, "ls", remote_file],
    capture_output=True,
    text=True,
    timeout=10
)
print(f"ls output: {result.stdout}")
