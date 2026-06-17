#!/usr/bin/env python3
"""Debug GCam photo files - find embedded images inside EXIF."""
import os
import struct
from PIL import Image
from io import BytesIO

orig_dir = 'C:/Users/TrisnoSanjaya/Backup_Media_HP/DCIM/Camera'
test_dir = 'C:/Users/TrisnoSanjaya/Backup_Media_HP/Recovered/test'
os.makedirs(test_dir, exist_ok=True)

FFD8 = bytes([255, 216])
FFD9 = bytes([255, 217])
FFDB = bytes([255, 219])
FFDA = bytes([255, 218])
FFC0 = bytes([255, 192])
FFC4 = bytes([255, 196])
FFE0 = bytes([255, 224])
FFE1 = bytes([255, 225])
FF00 = bytes([255, 0])

# Pick one file to deep-analyze
fname = 'By_Sepu_ar_Gcam12_May_17_02_iPhone_16_Stabilizer_V14_Auto_MP_(1) (2).jpg'
fpath = os.path.join(orig_dir, fname)

with open(fpath, 'rb') as f:
    data = f.read()

print("=== Strategy 1: PIL directly on full file ===")
try:
    with Image.open(fpath) as img:
        img.load()
        print(f"  Size: {img.size}")
except Exception as e:
    print(f"  Failed: {e}")

# Strategy 3: Parse EXIF, find thumbnail + embedded image
exif_offset = 6
exif_len = struct.unpack('>H', data[4:6])[0]
exif_data = data[exif_offset:exif_offset + exif_len]

print(f"\n=== EXIF Structure ===")
print(f"EXIF data: {exif_len:,} bytes")

if exif_data[:2] == b'II':
    endian = '<'
    print("Endian: Little-endian (II)")
elif exif_data[:2] == b'MM':
    endian = '>'
    print("Endian: Big-endian (MM)")
else:
    print(f"Unknown TIFF header: {exif_data[:4].hex()}")
    exit()

tiff_offset = 8
ifd_offset = struct.unpack(endian + 'I', exif_data[4:8])[0]
print(f"IFD0 offset: {ifd_offset}")

if ifd_offset >= len(exif_data) or ifd_offset < 8:
    print(f"IFD offset out of range, trying absolute offset...")
    ifd_offset = struct.unpack(endian + 'I', data[10:14])[0]
    print(f"  Absolute IFD offset: {ifd_offset}")
    if ifd_offset < len(data):
        ifd_data = data[ifd_offset:]
    else:
        ifd_data = exif_data
else:
    ifd_data = exif_data[ifd_offset:]

num_entries = struct.unpack(endian + 'H', ifd_data[:2])[0]
print(f"IFD0 entries: {num_entries}")

thumb_offset = None
thumb_length = None
exif_ifd_offset = None
maker_note_offset = None
img_width = None
img_height = None

tag_names = {
    0x010F: 'Make', 0x0110: 'Model', 0x0112: 'Orientation',
    0x8769: 'ExifIFD', 0x8825: 'GPS_IFD',
    0x927C: 'MakerNote', 0x010E: 'ImageDescription',
    0x0201: 'ThumbnailOffset', 0x0202: 'ThumbnailLength',
    0xA002: 'PixelXDimension', 0xA003: 'PixelYDimension',
    0x0100: 'ImageWidth', 0x0101: 'ImageLength',
    0x0117: 'StripOffsets', 0x0119: 'StripByteCounts',
    0x0102: 'PixelXDimension_IFD0',
    0x0103: 'PixelYDimension_IFD0',
    0x011A: 'XResolution', 0x011B: 'YResolution',
    0x0131: 'Software', 0x0132: 'DateTime',
}

for i in range(num_entries):
    entry_offset = 2 + i * 12
    if entry_offset + 12 > len(ifd_data):
        break
    tag = struct.unpack(endian + 'H', ifd_data[entry_offset:entry_offset+2])[0]
    type_field = struct.unpack(endian + 'H', ifd_data[entry_offset+2:entry_offset+4])[0]
    count = struct.unpack(endian + 'I', ifd_data[entry_offset+4:entry_offset+8])[0]
    value = struct.unpack(endian + 'I', ifd_data[entry_offset+8:entry_offset+12])[0]
    
    type_sizes = {1:1, 2:1, 3:2, 4:4, 5:8, 7:1, 9:4, 10:8}
    data_size = type_sizes.get(type_field, 1) * count
    
    name = tag_names.get(tag, f'0x{tag:04X}')
    
    if tag == 0x0201:
        thumb_offset = value
    elif tag == 0x0202:
        thumb_length = value
    elif tag == 0x8769:
        exif_ifd_offset = value
    elif tag == 0x927C:
        maker_note_offset = value
    elif tag in (0xA002, 0x0102, 0x0100):
        img_width = value if data_size <= 4 else None
    elif tag in (0xA003, 0x0103, 0x0101):
        img_height = value if data_size <= 4 else None
    
    val_str = f"offset={value}" if data_size > 4 else str(value)
    print(f"  {name} (0x{tag:04X}): tag={tag}, type={type_field}, count={count}, {val_str}")

print(f"\nImage dimensions from EXIF: {img_width}x{img_height}")

# Try to find thumbnail
if thumb_offset and thumb_length:
    thumb_data = None
    for base_offset, base_name in [(thumb_offset, "absolute"), (exif_offset + thumb_offset, "EXIF-relative")]:
        try:
            if base_offset + thumb_length <= len(data):
                td = data[base_offset:base_offset + thumb_length]
                with Image.open(BytesIO(td)) as img:
                    img.load()
                    print(f"\n  Thumbnail ({base_name} offset): {img.size}")
                    thumb_data = td
                    break
        except:
            pass
    
    if thumb_data:
        out = os.path.join(test_dir, f"thumb_{fname}")
        with open(out, 'wb') as f:
            f.write(thumb_data)
        print(f"   Saved: {out}")

# Strategy 5: Raw image data after EXIF
print(f"\n=== Strategy 5: Raw image data after EXIF ===")
after_exif = data[exif_offset + exif_len:]
print(f"Data after EXIF: {len(after_exif):,} bytes")
print(f"FF 00 pairs: {after_exif.count(FF00)}")
print(f"FF D9 occurrences: {after_exif.count(FFD9)}")
print(f"FF D8 occurrences: {after_exif.count(FFD8)}")
print(f"FF DA occurrences: {after_exif.count(FFDA)}")

if after_exif.count(FF00) > 100 and after_exif.count(FFD8) == 0:
    print("\n  Data after EXIF looks like valid JPEG entropy-coded data!")

# Look for DQT markers in the file
print(f"\n=== Searching for JPEG markers in file ===")
for marker_name, marker_bytes in [('DQT/FFDB', FFDB), ('SOF0/FFC0', FFC0),
                                    ('DHT/FFC4', FFC4), ('APP0/JFIF', FFE0)]:
    positions = []
    pos = 0
    while True:
        idx = data.find(marker_bytes, pos)
        if idx < 0:
            break
        positions.append(idx)
        pos = idx + 2
    if positions:
        print(f"  {marker_name}: {positions}")
    else:
        print(f"  {marker_name}: NOT FOUND")

# Check MakerNote
if maker_note_offset:
    mn_start = maker_note_offset
    # MakerNote offset could be from start of EXIF or start of file
    for base, label in [(exif_offset, "EXIF"), (0, "FILE")]:
        maker_note_data = data[base + mn_start:]
        print(f"\n=== MakerNote ({label} offset) ===")
        print(f"  Size: {len(maker_note_data):,} bytes")
        print(f"  First bytes: {maker_note_data[:32].hex()}")
        
        # Check for embedded JPEG
        ffd8_pos = maker_note_data.find(FFD8)
        if ffd8_pos >= 0:
            ffd9_pos = maker_note_data.find(FFD9, ffd8_pos + 2)
            if ffd9_pos >= 0:
                embedded = maker_note_data[ffd8_pos:ffd9_pos+2]
                print(f"  Embedded JPEG at {ffd8_pos}: {len(embedded):,} bytes")
                try:
                    with Image.open(BytesIO(embedded)) as img:
                        img.load()
                        print(f"  MakerNote image: {img.size}")
                        out = os.path.join(test_dir, f"mn_{label}_{fname}")
                        with open(out, 'wb') as f:
                            f.write(embedded)
                        print(f"  Saved: {out}")
                except Exception as e:
                    print(f"  PIL: {e}")
            else:
                print(f"  FFD8 at {ffd8_pos} but no FFD9 found")
        
        # Check for DQT/SOF/DHT in MakerNote
        for marker_name, marker_bytes in [('DQT', FFDB), ('SOF0', FFC0),
                                            ('DHT', FFC4), ('SOS', FFDA)]:
            mk_pos = maker_note_data.find(marker_bytes)
            if mk_pos >= 0:
                print(f"  {marker_name} at maker_note offset {mk_pos}")
        break  # Only try first base

# Check data after EXIF for markers with stripped FF
print(f"\n=== Check for markers with potentially stripped FF ===")
search_area = data[exif_offset + exif_len:]
for mk_name, mk_byte in [('DB (DQT)', b'\xdb'), ('C0 (SOF)', b'\xc0'),
                          ('C4 (DHT)', b'\xc4'), ('DA (SOS)', b'\xda')]:
    # Count single marker bytes (potential stripped FF markers)
    count = 0
    skip_until = 0
    for i in range(1, len(search_area)):
        if i < skip_until:
            continue
        if search_area[i] == mk_byte[0]:
            if search_area[i-1] != 0xFF:
                # Skip FF 00 stuffing
                if i >= 2 and search_area[i-2:i] == bytes([255, 0]):
                    continue
                count += 1
    if count > 0:
        print(f"  {mk_name}: {count} occurrences after non-FF")
    else:
        print(f"  {mk_name}: 0")

# Final attempt: reconstruct from scratch
# If we can find DQT + SOF + DHT anywhere, use them + the entropy data
print(f"\n=== Final attempt: reconstruct JPEG ===")
# Collect all DQT segments
dqt_blocks = []
pos = 0
while True:
    idx = data.find(FFDB, pos)
    if idx < 0:
        break
    length = struct.unpack('>H', data[idx+2:idx+4])[0]
    dqt_blocks.append(data[idx:idx+2+length])
    pos = idx + 2 + length

# Collect all DHT segments
dht_blocks = []
pos = 0
while True:
    idx = data.find(FFC4, pos)
    if idx < 0:
        break
    length = struct.unpack('>H', data[idx+2:idx+4])[0]
    dht_blocks.append(data[idx:idx+2+length])
    pos = idx + 2 + length

# Collect SOF segment
sof_block = None
pos = 0
while True:
    idx = data.find(FFC0, pos)
    if idx < 0:
        break
    length = struct.unpack('>H', data[idx+2:idx+4])[0]
    sof_block = data[idx:idx+2+length]
    break

# Collect SOS segment
sos_block = None
pos = 0
while True:
    idx = data.find(FFDA, pos)
    if idx < 0:
        break
    length = struct.unpack('>H', data[idx+2:idx+4])[0]
    sos_block = data[idx:idx+2+length]
    break

print(f"DQT blocks: {len(dqt_blocks)}")
print(f"DHT blocks: {len(dht_blocks)}")
print(f"SOF block: {'found' if sof_block else 'NOT FOUND'}")
print(f"SOS block: {'found' if sos_block else 'NOT FOUND'}")

if dqt_blocks and dht_blocks and sof_block and sos_block:
    # Rebuild JPEG
    reconstructed = bytearray()
    reconstructed.extend(FFD8)  # SOI
    # Apple EXIF from original
    reconstructed.extend(data[2:exif_offset + exif_len])
    # JFIF APP0 (optional but helpful)
    jfif = bytes([255, 224, 0, 16, 74, 70, 73, 70, 0, 1, 1, 0, 0, 1, 0, 1, 0, 0])
    reconstructed.extend(jfif)
    # DQT blocks
    for block in dqt_blocks:
        reconstructed.extend(block)
    # SOF
    reconstructed.extend(sof_block)
    # DHT blocks
    for block in dht_blocks:
        reconstructed.extend(block)
    # SOS
    reconstructed.extend(sos_block)
    # Entropy data (everything after EXIF)
    reconstructed.extend(after_exif)
    # EOI
    reconstructed.extend(FFD9)
    
    out_path = os.path.join(test_dir, f"reconstructed_{fname}")
    with open(out_path, 'wb') as f:
        f.write(bytes(reconstructed))
    print(f"\nReconstructed JPEG: {len(reconstructed):,} bytes -> {out_path}")
    
    try:
        with Image.open(out_path) as img:
            img.load()
            print(f"  Size: {img.size}")
    except Exception as e:
        print(f"  PIL: {e}")
else:
    print("Not enough markers found for reconstruction")
    print("The FF bytes were stripped from marker prefixes")
    print("This is NOT recoverable - need to re-backup from phone")
