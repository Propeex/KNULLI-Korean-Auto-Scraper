"""Build the Windows source distribution for a verified GitHub prerelease.

Usage: python3 scripts/package_release.py
Requires release/request.json, creates dist/*.zip and *.sha256.
Only allow-listed project sources and docs are included.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_version import VERSION_TAG
REQUEST = ROOT / "release" / "request.json"
DIST = ROOT / "dist"
VERSION_PATTERN = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)-beta\.([1-9]\d*)\Z")

EXTRA_FILES = [
    "GUI_실행.pyw",
    "GUI_실행.vbs",
    "README.md",
    "README_한국어.txt",
    "aliases.json",
    "artwork.xml",
    "config.example.json",
    "테스트_실행.bat",
]
DOC_FILES = [
    "docs/KNOWN_ISSUES.md",
    "docs/DECISIONS.md",
]


def load_request() -> str:
    obj = json.loads(REQUEST.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("Release request must be a JSON object")
    version = obj.get("version")
    if not isinstance(version, str) or not VERSION_PATTERN.fullmatch(version):
        raise ValueError("Only numbered beta tags are permitted before explicit stable approval")
    if obj.get("prerelease") is not True:
        raise ValueError("All releases must be marked prerelease until stable approval")
    if version != VERSION_TAG:
        raise ValueError("GUI application version and release request are inconsistent")
    return version


def build() -> tuple[Path, Path]:
    version = load_request()
    scripts = sorted(p.name for p in ROOT.glob("*.py") if p.is_file())
    if not scripts:
        raise RuntimeError("No Python application modules found")
    members = [ROOT / p for p in scripts + EXTRA_FILES + DOC_FILES]
    missing = [str(p.relative_to(ROOT)) for p in members if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing distribution file(s): " + ", ".join(missing))
    # Prevent accidental inclusion of any secret-bearing runtime folders.
    assert not any(p.name in {"config.json", ".env"} for p in members)
    DIST.mkdir(exist_ok=True)
    archive = DIST / f"KNULLI-Korean-Auto-Scraper-{version}-Windows.zip"
    folder = f"KNULLI-Korean-Auto-Scraper-{version}"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in members:
            entry = (Path(folder) / p.relative_to(ROOT)).as_posix()
            z.write(p, arcname=entry)
    with zipfile.ZipFile(archive) as z:
        broken = z.testzip()
        if broken:
            raise RuntimeError(f"ZIP CRC verification failed: {broken}")
        if not any(name.endswith("/GUI_실행.pyw") for name in z.namelist()):
            raise RuntimeError("GUI launcher missing in release")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    checkfile = DIST / (archive.name + ".sha256")
    checkfile.write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    print(f"Built {archive.name} ({archive.stat().st_size} bytes, SHA256 {digest})")
    return archive, checkfile


if __name__ == "__main__":
    try:
        build()
    except Exception as exc:
        print(f"Packaging failed: {exc}", file=sys.stderr)
        sys.exit(1)
