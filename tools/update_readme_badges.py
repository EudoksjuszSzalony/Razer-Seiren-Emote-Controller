#!/usr/bin/env python3
"""Mirror official Shields.io SVG badge renders into this repository.

Use the GitHub releases API for the current version and total asset downloads.
GitHub Actions refreshes the SVGs periodically; README views do not depend
on either Shields.io availability or GitHub Camo cache state. Stdlib only.
"""
from __future__ import annotations

import argparse
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


def shields_url(label: str, message: str, color: str, *, style: str = "flat-square",
                logo: str | None = None) -> str:
    """Official Shields.io static badge API, preserving native badge styling."""
    from urllib.parse import quote, urlencode

    def component(text: str) -> str:
        # Shields uses -- for literal hyphens; URL encoding handles spaces.
        return quote(text.replace("-", "--").replace("_", "__"), safe="")

    path = "-".join(component(part) for part in (label, message, color))
    opts = {"style": style}
    if logo:
        opts.update(logo=logo, logoColor="white")
    return "https://img.shields.io/badge/" + path + "?" + urlencode(opts)


def shields_svg(label: str, message: str, color: str, *,
                style: str = "flat-square", logo: str | None = None) -> str:
    """Retrieve an actual Shields.io-rendered SVG, validating it before saving.

    Download failures do not overwrite existing, working local badge files.
    """
    from xml.etree import ElementTree as ET
    import time

    url = shields_url(label, message, color, style=style, logo=logo)
    last_error = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "SeirenEmoteController-readme-badge-mirror",
                "Accept": "image/svg+xml",
            })
            with urllib.request.urlopen(request, timeout=25) as response:
                payload = response.read(100001)
                if len(payload) > 100000:
                    raise ValueError("Shields SVG exceeded maximum expected size")
                svg = payload.decode("utf-8")
            root = ET.fromstring(svg)
            if root.tag != "{http://www.w3.org/2000/svg}svg":
                raise ValueError("Shields response is not an SVG")
            # Error badges may be valid SVGs; validate the actual expected text.
            contents = " ".join(root.itertext()).casefold()
            if label.casefold() not in contents or message.casefold() not in contents:
                raise ValueError("Shields response has unexpected text (possible error badge)")
            if any(elem.tag.rsplit("}", 1)[-1].lower() in ("script", "foreignobject")
                   for elem in root.iter()):
                raise ValueError("Unsupported active content in badge")
            return svg if svg.endswith("\n") else svg + "\n"
        except (OSError, UnicodeError, ValueError, ET.ParseError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Could not verify Shields.io badge {label!r}: {last_error}")


def generate(version: str, downloads: int, out: Path = BASE) -> None:
    """Mirror real Shields.io badge designs using authenticated GitHub stats.

    Download all seven files successfully before overwriting any old assets.
    This keeps README functional if Shields.io has a temporary outage.
    """
    if downloads < 0:
        raise ValueError("Download count must not be negative")
    definitions = {
        "downloads.svg": ("downloads", f"{downloads:,}", "brightgreen", "flat-square", None),
        "release.svg": ("latest release", version, "blue", "flat-square", None),
        "python.svg": ("no python required", "installer", "2ea44f", "flat-square", "windows"),
        "platform.svg": ("platform", "windows", "0078D6", "flat-square", "windows"),
        "license.svg": ("license", "GPL-3.0", "brightgreen", "flat-square", None),
        "status.svg": ("status", "stable", "brightgreen", "flat-square", None),
        "download-windows.svg": ("download", "windows installer", "2ea44f", "for-the-badge", "windows"),
    }
    rendered = {}
    for filename, (label, message, color, style, logo) in definitions.items():
        rendered[filename] = shields_svg(label, message, color, style=style, logo=logo)
    out.mkdir(parents=True, exist_ok=True)
    for filename, svg in rendered.items():
        path = out / filename
        if not path.is_file() or path.read_text(encoding="utf-8") != svg:
            temporary = path.with_suffix(".svg.tmp")
            temporary.write_text(svg, encoding="utf-8")
            temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", help="Use this release (offline/test mode)")
    parser.add_argument("--downloads", type=int, help="Use this download count (offline/test mode)")
    args = parser.parse_args()
    if (args.version is None) != (args.downloads is None):
        parser.error("--version and --downloads must be supplied together")
    version, downloads = (args.version, args.downloads) if args.version is not None else release_stats()
    generate(version, downloads)
    print(f"Mirrored 7 verified Shields.io SVGs: latest {version}, {downloads} release-asset download events")


if __name__ == "__main__":
    main()
