# -*- coding: utf-8 -*-
"""Safe filename helpers for backup destinations."""

import os
import re
import unicodedata

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}

WINDOWS_INVALID_FILENAME_CHARS = set('<>:"/\\|?*') | {chr(i) for i in range(32)}
SAFE_SEPARATOR_RE = re.compile(r"[\s._-]+")
ASCII_RE = re.compile(r"[^A-Za-z0-9._-]")


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKD", value or "")


def strip_accents(value: str) -> str:
    return "".join(ch for ch in normalize_text(value) if not unicodedata.combining(ch))


def sanitize_name_part(value: str, fallback: str = "unnamed") -> str:
    value = strip_accents(value or "")
    chars = []
    for ch in value:
        if ch in WINDOWS_INVALID_FILENAME_CHARS or ord(ch) > 127:
            chars.append("_")
        elif ch in {" ", ".", "-", "_"}:
            chars.append("_")
        else:
            chars.append(ch)

    name = SAFE_SEPARATOR_RE.sub("_", "".join(chars)).strip("._- ")
    if not name:
        return fallback
    if name.upper() in WINDOWS_RESERVED_NAMES:
        return f"{name}_"
    return name


def sanitize_extension(ext: str) -> str:
    ext = strip_accents(ext or "").strip()
    ext = "".join("_" if (ch in WINDOWS_INVALID_FILENAME_CHARS or ord(ch) > 127) else ch for ch in ext)
    ext = ASCII_RE.sub("_", ext).strip("._- ")
    if not ext:
        return ""
    ext = ext.lower()
    return ext if ext.startswith(".") else f".{ext}"


def safe_filename(filename: str, used_names=None, max_stem_length: int = 180) -> tuple[str, bool]:
    used_names_lower = {str(name).lower() for name in (used_names or set())}
    original = filename or "unnamed"
    stem, ext = os.path.splitext(original)
    safe_stem = sanitize_name_part(stem)
    safe_ext = sanitize_extension(ext)

    if len(safe_stem) > max_stem_length:
        safe_stem = safe_stem[:max_stem_length].rstrip("._- ") or "unnamed"

    candidate = f"{safe_stem}{safe_ext}"
    counter = 1

    while candidate.lower() in used_names_lower:
        suffix = f" ({counter})"
        available = max(1, max_stem_length - len(suffix) - len(safe_ext))
        safe_stem_part = safe_stem[:available].rstrip("._- ") or "unnamed"
        candidate = f"{safe_stem_part}{suffix}{safe_ext}"
        counter += 1

    return candidate, candidate != original


def should_rename_filename(filename: str) -> bool:
    return any(ord(ch) > 127 or ch in WINDOWS_INVALID_FILENAME_CHARS for ch in filename or "")


def norm_path(path: str) -> str:
    return os.path.normcase(os.path.normpath(os.path.abspath(path)))


def get_existing_paths(root: str) -> set[str]:
    existing = set()
    if not os.path.exists(root):
        return existing
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.getsize(filepath) > 0:
                existing.add(norm_path(filepath))
    return existing


def _names_in_same_dir(path_set, directory: str) -> set[str]:
    directory = norm_path(directory)
    names = set()
    for path in path_set or set():
        normalized = norm_path(path)
        if norm_path(os.path.dirname(normalized)) == directory:
            names.add(os.path.basename(normalized))
    return names


def resolve_safe_destination_path(dst_path: str, existing_paths=None, used_paths=None, enabled: bool = True) -> tuple[str, bool]:
    if not enabled:
        return dst_path, False

    dst_dir = os.path.dirname(dst_path)
    filename = os.path.basename(dst_path)
    used_names = set()
    used_names.update(_names_in_same_dir(existing_paths, dst_dir))
    used_names.update(_names_in_same_dir(used_paths, dst_dir))

    safe_name, renamed = safe_filename(filename, used_names)
    return os.path.join(dst_dir, safe_name), renamed
