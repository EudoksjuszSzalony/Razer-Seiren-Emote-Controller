"""Recover 8x8 GIFs from an installed Streamer Companion app's LOCAL cache.

No network requests and no bundled Razer artwork. The user's cache must already
contain a module with 8x8 GIF data URIs. This is best-effort and version-specific.
"""
from __future__ import annotations

import base64
import io
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from PIL import Image

APP_DIR = Path(os.getenv('LOCALAPPDATA') or Path.home() / '.local' / 'share') / 'SeirenEmoteController'
EMOTES_DIR = APP_DIR / 'Emotes'
DATA_URI = re.compile(rb'data:image/gif;base64,([a-zA-Z0-9+/=]+)')


def cache_candidates(root: Path | None = None):
    if root is not None:
        yield Path(root)
        return
    for key in ('LOCALAPPDATA', 'APPDATA'):
        base = os.getenv(key)
        if not base:
            continue
        for suffix in ('Razer/RzAppEngine', 'RzAppEngine', 'Razer/RazerAppEngine'):
            path = Path(base) / suffix / 'User Data' / 'Default' / 'Service Worker' / 'CacheStorage'
            if path.is_dir():
                yield path


def extract_gifs(blob: bytes) -> list[bytes]:
    """Read GIF data URIs and ignore 100x100 browser previews."""
    results = []
    seen = set()
    for match in DATA_URI.finditer(blob):
        try:
            payload = base64.b64decode(match.group(1), validate=True)
            if not payload.startswith((b'GIF89a', b'GIF87a')) or len(payload) > 300_000:
                continue
            with Image.open(io.BytesIO(payload)) as im:
                if im.format != 'GIF' or im.size != (8, 8):
                    continue
                im.verify()
            if payload not in seen:
                results.append(payload)
                seen.add(payload)
        except (ValueError, OSError, base64.binascii.Error):
            continue
    return results


def import_from_cache(cache_root: Path | None = None, destination: Path = EMOTES_DIR) -> int:
    """Use the largest complete cache module; never publish/exfiltrate assets."""
    best = []
    searched = False
    for base in cache_candidates(cache_root):
        if not base.exists():
            continue
        searched = True
        if base.is_file():
            files = [base]
        else:
            files = (p for p in base.rglob('*') if p.is_file())
        for path in files:
            try:
                if not 50 < path.stat().st_size < 2_000_000:
                    continue
                data = path.read_bytes()
                if b'data:image/gif;base64,' not in data:
                    continue
                items = extract_gifs(data)
                if len(items) > len(best):
                    best = items
            except (OSError, PermissionError):
                continue
    if not searched:
        raise FileNotFoundError('Streamer Companion cache was not found. Please select its folder manually.')
    if not best:
        raise RuntimeError('No 8x8 emotes were found in this cache. Run Streamer Companion first, then try again.')

    manifest_file = Path(__file__).resolve().with_name('emote_manifest.json')
    known = json.loads(manifest_file.read_text(encoding='utf-8')) if manifest_file.exists() else {}
    destination.mkdir(parents=True, exist_ok=True)
    for i, gif in enumerate(best):
        name = known.get(hashlib.sha256(gif).hexdigest(), f'Emote_{i:03d}')
        name = re.sub(r'[^a-zA-Z0-9_+\-]', '_', name)[:60]
        target = destination / f'{i:03d}_{name}.gif'
        if target.is_file() and target.read_bytes() == gif:
            continue  # Avoid rewriting unchanged cache files.
        with tempfile.NamedTemporaryFile(dir=destination, delete=False, suffix='.tmp') as temp:
            temp.write(gif)
            temp_path = Path(temp.name)
        temp_path.replace(target)
    return len(best)


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--cache-dir', type=Path, help='Path to a RzAppEngine CacheStorage folder')
    p.add_argument('--out', type=Path, default=EMOTES_DIR)
    args = p.parse_args()
    print(f'Imported {import_from_cache(args.cache_dir, args.out)} emotes into {args.out}')
