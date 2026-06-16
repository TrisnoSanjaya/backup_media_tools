#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test: Verify Unicode files are skipped silently
"""

import subprocess
import os

# Create test folder dengan mix ASCII dan Unicode files
test_dir = r"C:\Users\TrisnoSanjaya\Documents\Code\New folder\test_backup_skip"
os.makedirs(test_dir, exist_ok=True)

# Create dummy files
files = [
    "ascii_file_1.jpg",
    "ascii_file_2.mp4",
    "unicode_file_✺𝓔𝓷𝓭𝓪𝓜𝓮𝓭𝓲𝓪✺.jpg",
]

for fname in files:
    fpath = os.path.join(test_dir, fname)
    # Create small dummy file
    with open(fpath, 'wb') as f:
        f.write(b'\xff\xd8' + b'\x00' * 1000 + b'\xff\xd9')  # JPEG-like
    print(f"Created: {fname}")

print(f"\nTest files created in: {test_dir}")
print("\nTo test backup tool with Unicode skip:")
print("1. Copy test files to device /sdcard/test_unicode/")
print("2. Run backup tool and select that folder")
print("3. Verify summary shows 'Unicode/Emoji: 1' with no progress output for that file")
