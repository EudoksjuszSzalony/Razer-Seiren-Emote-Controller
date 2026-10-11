"""Safe user-selected media import and low-cost directory change detection."""
from __future__ import annotations

import filecmp
from pathlib import Path
import re
import shutil

from PIL import Image

IMPORT_SUFFIXES = frozenset(('.png', '.gif'))
LIBRARY_SUFFIXES = frozenset(('.png', '.gif', '.webp', '.bmp', '.jpg', '.jpeg'))


def media_signature(folder: Path):
    """Metadata only; no image decodes until a directory entry changes."""
    try:
        rows = []
        for p in Path(folder).iterdir():
            if p.is_file() and p.suffix.lower() in LIBRARY_SUFFIXES:
                stat = p.stat()
                rows.append((p.name, stat.st_size, stat.st_mtime_ns))
        return tuple(sorted(rows))
    except (FileNotFoundError, PermissionError, OSError):
        return ()


def import_user_media(sources, destination: Path):
    """Copy verified PNG/GIF files. Never overwrite other users' media."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    added = 0
    skipped = 0
    for src in (Path(p) for p in sources):
        if src.suffix.lower() not in IMPORT_SUFFIXES or not src.is_file():
            skipped += 1
            continue
        try:
            if not 0 < src.stat().st_size <= 25_000_000:
                skipped += 1
                continue
            with Image.open(src) as image:
                if image.format not in ('GIF', 'PNG'):
                    skipped += 1
                    continue
                image.verify()
            stem = re.sub(r'[^\w. -]', '_', src.stem, flags=re.UNICODE).strip(' .')[:64] or 'emote'
            suffix = src.suffix.lower()
            candidate = destination / (stem + suffix)
            number = 2
            while candidate.exists():
                if filecmp.cmp(src, candidate, shallow=False):
                    skipped += 1
                    break
                candidate = destination / f'{stem}_{number}{suffix}'
                number += 1
            else:
                shutil.copy2(src, candidate)
                added += 1
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
            skipped += 1
    return added, skipped
