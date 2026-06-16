#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan backup directory untuk identify corrupt vs valid files
"""

import os
from pathlib import Path

def check_jpeg_integrity(filepath):
    """Check if JPEG file has proper start and end markers"""
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
        
        if len(data) < 4:
            return False, "File too small"
        
        # JPEG should start with FFD8
        if data[:2] != b'\xff\xd8':
            return False, "Missing JPEG start marker"
        
        # JPEG should end with FFD9
        if data[-2:] != b'\xff\xd9':
            return False, "Missing JPEG end marker"
        
        return True, "OK"
    except Exception as e:
        return False, str(e)

def check_mp4_integrity(filepath):
    """Check if MP4 file has proper structure"""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(32)
        
        if len(header) < 8:
            return False, "File too small"
        
        # MP4 should have 'ftyp' atom
        if b'ftyp' in header[:24]:
            return True, "OK"
        
        return False, "Missing ftyp atom"
    except Exception as e:
        return False, str(e)

def scan_directory(root_dir):
    """Scan backup directory and report integrity"""
    root_path = Path(root_dir)
    
    results = {
        'jpeg_ok': [],
        'jpeg_corrupt': [],
        'mp4_ok': [],
        'mp4_corrupt': [],
        'other': []
    }
    
    for filepath in root_path.rglob('*'):
        if not filepath.is_file():
            continue
        
        ext = filepath.suffix.lower()
        rel_path = filepath.relative_to(root_path)
        
        if ext in ['.jpg', '.jpeg']:
            ok, msg = check_jpeg_integrity(filepath)
            if ok:
                results['jpeg_ok'].append((rel_path, filepath.stat().st_size))
            else:
                results['jpeg_corrupt'].append((rel_path, filepath.stat().st_size, msg))
        
        elif ext in ['.mp4', '.mov', '.mkv', '.avi']:
            ok, msg = check_mp4_integrity(filepath)
            if ok:
                results['mp4_ok'].append((rel_path, filepath.stat().st_size))
            else:
                results['mp4_corrupt'].append((rel_path, filepath.stat().st_size, msg))
        
        else:
            results['other'].append((rel_path, ext))
    
    return results

def main():
    backup_dir = r"C:\Users\TrisnoSanjaya\Backup_Media_HP"
    
    print("=" * 70)
    print("BACKUP INTEGRITY SCANNER")
    print("=" * 70)
    print(f"Scanning: {backup_dir}\n")
    
    if not os.path.exists(backup_dir):
        print(f"[ERROR] Directory not found: {backup_dir}")
        return
    
    results = scan_directory(backup_dir)
    
    # Summary
    total_jpeg = len(results['jpeg_ok']) + len(results['jpeg_corrupt'])
    total_mp4 = len(results['mp4_ok']) + len(results['mp4_corrupt'])
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"JPEG files:")
    print(f"  Valid   : {len(results['jpeg_ok'])}/{total_jpeg}")
    print(f"  Corrupt : {len(results['jpeg_corrupt'])}/{total_jpeg}")
    print(f"\nVideo files:")
    print(f"  Valid   : {len(results['mp4_ok'])}/{total_mp4}")
    print(f"  Corrupt : {len(results['mp4_corrupt'])}/{total_mp4}")
    print(f"\nOther files: {len(results['other'])}")
    
    # Detailed corrupt list
    if results['jpeg_corrupt']:
        print("\n" + "=" * 70)
        print("CORRUPT JPEG FILES")
        print("=" * 70)
        for path, size, msg in results['jpeg_corrupt'][:20]:  # Show first 20
            size_mb = size / (1024 * 1024)
            print(f"  [{size_mb:6.1f} MB] {path}")
            print(f"              -> {msg}")
        
        if len(results['jpeg_corrupt']) > 20:
            print(f"  ... and {len(results['jpeg_corrupt']) - 20} more")
    
    if results['mp4_corrupt']:
        print("\n" + "=" * 70)
        print("CORRUPT VIDEO FILES")
        print("=" * 70)
        for path, size, msg in results['mp4_corrupt'][:10]:
            size_mb = size / (1024 * 1024)
            print(f"  [{size_mb:6.1f} MB] {path}")
            print(f"              -> {msg}")
        
        if len(results['mp4_corrupt']) > 10:
            print(f"  ... and {len(results['mp4_corrupt']) - 10} more")
    
    # Sample valid files
    if results['jpeg_ok']:
        print("\n" + "=" * 70)
        print("SAMPLE VALID JPEG FILES")
        print("=" * 70)
        for path, size in results['jpeg_ok'][:5]:
            size_mb = size / (1024 * 1024)
            print(f"  [{size_mb:6.1f} MB] {path}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
