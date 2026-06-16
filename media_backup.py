# -*- coding: utf-8 -*-
"""Unified CLI for media backup via ADB."""

import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import backup_tool_adb

DIVIDER = "=" * 60


def print_header():
    print(f"\n{DIVIDER}")
    print("  MEDIA BACKUP - ADB")
    print(f"{DIVIDER}")
    print(f"  Folder backup    : {backup_tool_adb.PC_BACKUP_DIR}")
    print(f"  ADB siap         : {bool(backup_tool_adb.get_adb_path())}")
    print(f"{DIVIDER}\n")


def input_text(prompt, default=None, strip_quotes=True):
    default_text = f" [{default}]" if default else ""
    value = input(f"{prompt}{default_text}: ").strip()
    if not value and default is not None:
        value = default
    if strip_quotes:
        value = value.strip('"').strip("'")
    return value


def configure_backup_dir():
    print(f"\nFolder backup saat ini: {backup_tool_adb.PC_BACKUP_DIR}")
    new_dir = input_text("Masukkan folder backup baru, Enter untuk batal")
    if not new_dir:
        print("  [BATAL] Folder backup tidak diubah.")
        return

    new_dir = os.path.expandvars(os.path.expanduser(new_dir))
    backup_tool_adb.PC_BACKUP_DIR = new_dir
    print(f"  [OK] Folder backup diubah ke: {new_dir}")


def show_settings():
    while True:
        print(f"\n{DIVIDER}")
        print("  PENGATURAN")
        print(f"{DIVIDER}")
        print("  1. Ubah folder backup")
        print("  2. Cek ADB")
        print("  0. Kembali")
        print(f"{DIVIDER}")

        choice = input_text("Pilih menu [0-2]").lower()
        if choice == "1":
            configure_backup_dir()
        elif choice == "2":
            adb_path = backup_tool_adb.get_adb_path()
            if adb_path:
                print(f"  [OK] ADB ditemukan: {adb_path}")
            else:
                print("  [WARN] ADB belum ditemukan. Mode ADB akan mencoba install otomatis saat dipakai.")
        elif choice == "0":
            return
        else:
            print("  [ERROR] Pilihan tidak valid.")


def show_help():
    print(f"\n{DIVIDER}")
    print("  BANTUAN")
    print(f"{DIVIDER}")
    print("  Mode ADB:")
    print("    - Aktifkan USB debugging di HP.")
    print("    - Program akan memakai adb untuk pull file dari folder media.")
    print("    - Cocok untuk backup tanpa MTP.")
    print()
    print("  Rename otomatis:")
    print("    - Mengubah nama file Unicode/emoji menjadi ASCII-safe.")
    print("    - Jika nama tujuan sudah ada, otomatis tambah (1), (2), dst.")
    print(f"{DIVIDER}")


def run_adb_backup():
    print(f"\n{DIVIDER}")
    print("  MODE BACKUP: ADB")
    print(f"{DIVIDER}")
    try:
        adb_path = backup_tool_adb.ensure_adb()
        if adb_path is None:
            print("  [ERROR] ADB tidak tersedia.")
            input("  Tekan Enter untuk kembali ke menu...")
            return

        print(f"  [ADB] ADB siap: {adb_path}")
        device = backup_tool_adb.wait_for_device()
        if device:
            backup_tool_adb.run_backup(device)
    except KeyboardInterrupt:
        print("\n\n[EXIT] Backup ADB dibatalkan.")


def main():
    while True:
        print_header()
        print("  1. Backup via ADB")
        print("  2. Pengaturan")
        print("  3. Bantuan")
        print("  0. Keluar")
        print(f"{DIVIDER}")

        choice = input_text("Pilih menu [0-3]").lower()
        if choice == "1":
            run_adb_backup()
        elif choice == "2":
            show_settings()
        elif choice == "3":
            show_help()
        elif choice == "0":
            print("\n[EXIT] Program selesai.")
            return 0
        else:
            print("  [ERROR] Pilihan tidak valid.")

        if choice != "0":
            input("\nTekan Enter untuk kembali ke menu...")


if __name__ == "__main__":
    raise SystemExit(main())
