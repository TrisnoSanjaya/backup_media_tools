# Backup Media Tools

CLI tool untuk backup foto/video dari HP Android via ADB. Otomatis scan folder media di `/sdcard`, deteksi file baru, dan transfer ke PC.

## Fitur

-   Scan recursive folder DCIM, Download, Pictures, Movies, Telegram, WhatsApp, dll.
-   Dedup otomatis — hanya backup file yang belum ada di folder tujuan
-   Dua mode: **COPY** (file tetap di HP) / **MOVE** (file dihapus dari HP setelah backup)
-   Progress bar realtime dengan estimasi waktu dan kecepatan transfer
-   Validasi ukuran file setelah transfer (toleransi < 1%)
-   Fallback otomatis jika `adb pull` gagal (copy + pull via temp di device)
-   Filter ekstensi: `.jpg, .jpeg, .png, .gif, .bmp, .tiff, .webp, .mp4, .mov, .mkv, .avi, .wmv, .flv, .webm, .3gp`

## Persyaratan

-   Python 3.8+
-   ADB (Android Debug Bridge) — otomatis diunduh jika belum ada
-   USB Debugging aktif di HP Android

## Cara Pakai

```bash
python backup_tool_adb.py
```

Tool akan:
1.  Cek ketersediaan ADB (download otomatis bila perlu)
2.  Tunggu HP terhubung via USB
3.  Scan semua file media di HP
4.  Tampilkan daftar folder dan file baru
5.  Minta pilihan mode COPY/MOVE
6.  Transfer file dengan progress bar
7.  Tampilkan laporan akhir

## Opsional: Rich Display

Jika `rich` terinstall, tampilan CLI jadi lebih berwarna dengan panel, tabel, dan progress bar yang lebih informatif:

```bash
pip install rich
```

Tanpa `rich` pun tool tetap berjalan normal dengan fallback ANSI.
