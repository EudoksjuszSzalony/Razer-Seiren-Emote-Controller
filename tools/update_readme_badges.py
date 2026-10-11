#!/usr/bin/env python3
"""Generate repository-hosted GitHub README badges, without Shields.io.

Use the GitHub releases API for the current version and total asset downloads.
GitHub Actions refreshes the SVGs periodically; README views need no external
badge provider. Stdlib only: no dependency on PIL, fonts or SVG packages.
"""
from __future__ import annotations

import argparse
from html import escape
import json
import os
from pathlib import Path
import urllib.request

REPOSITORY = "EudoksjuszSzalony/Razer-Seiren-Emote-Controller"
BASE = Path(__file__).resolve().parent.parent / "docs" / "badges"


def api_get(url: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "SeirenEmoteController-readme-badges",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
        return json.load(response)


def release_stats() -> tuple[str, int]:
    """Count published release-asset download events across all pages."""
    all_releases = []
    page = 1
    while True:
        batch = api_get(f"https://api.github.com/repos/{REPOSITORY}/releases?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise ValueError("GitHub releases API returned unexpected data")
        all_releases.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        if page > 100:
            raise ValueError("Too many pages of releases")
    published = [r for r in all_releases if not r.get("draft") and not r.get("prerelease")]
    latest = api_get(f"https://api.github.com/repos/{REPOSITORY}/releases/latest")
    if not isinstance(latest, dict) or not latest.get("tag_name"):
        raise ValueError("No published stable release available")
    total = sum(int(asset.get("download_count", 0))
                for release in published for asset in release.get("assets", []))
    return str(latest["tag_name"]), total


def badge(left: str, right: str, color: str) -> str:
    """Self-contained flat-square SVG with the familiar two-panel badge look."""
    left_width = max(55, int(len(left) * 7.1 + 20))
    right_width = max(38, int(len(right) * 7.1 + 20))
    width = left_width + right_width
    # textLength ensures browser font differences do not crop text.
    left_len, right_len = left_width - 20, right_width - 20
    left_s, right_s = escape(left), escape(right)
    title = escape(f"{left}: {right}")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="24" viewBox="0 0 {width} 24" role="img" aria-label="{title}">
<title>{title}</title>
<rect width="{width}" height="24" rx="4" fill="#32383e"/>
<path d="M{left_width},0 H{width - 4} Q{width},0 {width},4 V20 Q{width},24 {width - 4},24 H{left_width} Z" fill="{color}"/>
<g fill="#fff" font-family="Verdana, DejaVu Sans, Arial, sans-serif" font-size="11" font-weight="600" text-anchor="middle">
<text x="{left_width / 2:g}" y="16" textLength="{left_len}" lengthAdjust="spacingAndGlyphs">{left_s}</text>
<text x="{left_width + right_width / 2:g}" y="16" textLength="{right_len}" lengthAdjust="spacingAndGlyphs">{right_s}</text>
</g></svg>
"""


def generate(version: str, downloads: int, out: Path = BASE) -> None:
    if downloads < 0:
        raise ValueError("Download count must not be negative")
    out.mkdir(parents=True, exist_ok=True)
    definitions = {
        "downloads.svg": ("downloads", f"{downloads:,}", "#15803d"),
        "release.svg": ("latest release", version, "#2563eb"),
        "python.svg": ("Python", "not required", "#16a34a"),
        "platform.svg": ("platform", "Windows", "#0078d4"),
        "license.svg": ("license", "GPL-3.0", "#16a34a"),
        "status.svg": ("status", "stable", "#16a34a"),
        "download-windows.svg": ("Download", "Windows Installer", "#16a34a"),
    }
    for name, (left, right, color) in definitions.items():
        path = out / name
        svg = badge(left, right, color)
        if not path.exists() or path.read_text(encoding="utf-8") != svg:
            path.write_text(svg, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Use this release (offline/test mode)")
    parser.add_argument("--downloads", type=int, help="Use this download count (offline/test mode)")
    args = parser.parse_args()
    if (args.version is None) != (args.downloads is None):
        parser.error("--version and --downloads must be supplied together")
    version, downloads = (args.version, args.downloads) if args.version is not None else release_stats()
    generate(version, downloads)
    print(f"Updated SVG badges: latest {version}, {downloads} release-asset download events")


if __name__ == "__main__":
    main()
