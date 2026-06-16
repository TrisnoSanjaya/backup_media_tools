# CLI Automated Media Backup Tool

Modern backup tool untuk Android devices via ADB dengan progress bar real-time dan Unicode support.

## 🎯 Features

- **Zero Python Dependency** - hanya butuh ADB executable
- **Rich Progress UI** - modern progress bar dengan speed & ETA
- **Unicode/Emoji Support** - handle complex filenames via hex escape + tar streaming
- **Dual Pull Strategy** - ASCII files via adb pull (cepat), Unicode via tar exec-out
- **Incremental Backup** - skip files yang sudah di-backup
- **File Renaming** - auto-sanitize invalid Windows characters
- **Copy/Move Modes** - backup atau pindah file dari HP
- **Folder Selection** - pilih folder tertentu atau backup semua
- **Real-time Stats** - speed (MB/s), transferred, total size, ETA
- **Stack-based Scanning** - safe & scalable untuk banyak folder

## 📋 Requirements

- Python 3.8+
- Android Device dengan USB Debugging aktif
- ADB (auto-download jika belum ada)
- Optional: `rich` library untuk modern UI

## 🚀 Quick Start

### 1. Clone & Setup
```bash
cd backup_media_tools
pip install -r requirements.txt  # optional, hanya untuk rich
```

### 2. Run Backup
```bash
# Via ADB (recommended)
python backup_tool_adb.py

# Via Menu Wrapper
python media_backup.py
```

### 3. First Run
- Koneksi HP via USB cable
- Aktifkan "File Transfer" atau "USB Debugging" mode
- Program akan auto-detect device
- Pilih folder atau backup semua

## 📦 File Structure

```
backup_media_tools/
├── backup_tool_adb.py         # Main ADB backup tool (optimized)
├── backup_tool.py             # USB drive backup tool
├── media_backup.py            # Menu wrapper/CLI
├── safe_names.py              # Filename sanitization
├── requirements.txt           # Python dependencies
├── OPTIMIZATIONS.md           # Optimization details
└── README.md                  # This file
```

## ⚙️ Configuration

Edit constants di `backup_tool_adb.py`:

```python
PC_BACKUP_DIR = os.path.join(os.path.expanduser("~"), "Backup_Media_HP")
DEVICE_MOUNT_POINT = "/sdcard"
VALID_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp",
    ".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm", ".3gp",
)
SCAN_PATHS = [
    "/sdcard/DCIM",
    "/sdcard/Download",
    "/sdcard/Pictures",
    ...
]
```

## 🔍 How It Works

### Phase 1: Scan
- Stack-based recursive scan semua media folders
- Extract filename, size, path dari device
- Build file list untuk filtering

### Phase 2: Filter
- Cache existing backup paths untuk O(1) lookup
- Hitung file baru vs duplikat
- Display folder summary

### Phase 3: Mode & Folder Selection
- Pilih COPY (tetap di HP) atau MOVE (hapus dari HP)
- Pilih semua folder atau folder tertentu
- Konfirmasi sebelum start

### Phase 4: Transfer
- Loop per folder, per file
- Detect filename type (ASCII vs Unicode)
- Pull via optimized method
- Update progress real-time
- Delete dari HP jika MOVE mode
- Display final report

## 📊 Performance

Optimizations implemented:

| Optimization | Impact |
|--------------|--------|
| Stack-based scanning | Safer, faster untuk banyak folder |
| Path caching | 10x faster filtering |
| Dual pull strategy | 2-3x faster untuk ASCII files |
| Rich progress UI | Better UX, accurate ETA |
| Code refactoring | Cleaner, maintainable codebase |

## 🛠️ Development

### Running Tests
```bash
python -m py_compile backup_tool_adb.py
python -m py_compile backup_tool.py
python -m py_compile safe_names.py
```

### Code Style
- PEP 8 compliant
- Type hints where applicable
- Docstrings untuk semua functions
- Error handling dengan try/except

## 🐛 Troubleshooting

### Device tidak terdeteksi
```bash
# Check ADB connection
adb devices

# Aktifkan USB Debugging di HP
Settings > Developer Options > USB Debugging = ON

# Jalankan ulang program
python backup_tool_adb.py
```

### Unicode/Emoji files di-skip
- Files dengan filename Unicode/emoji di-skip di fallback mode
- Install `rich` untuk full support via tar streaming
- Atau rename file di HP untuk ASCII-only

### Progress bar tidak muncul
- Install `rich`: `pip install rich`
- Atau gunakan fallback ANSI progress bar (default)

## 📝 License

MIT License - feel free to use dan modify

## 🤝 Contributing

Suggestions welcome! Test dan report issues.

---

**Last Updated:** 2026-06-16  
**Version:** 2.0 (Optimized)
