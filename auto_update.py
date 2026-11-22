"""Automatic GitHub beta update discovery and verified staging.

Runs *before* the GUI starts, using only the Windows PC's Internet.
No dialog and no interaction with the KNULLI device or ADB server.
The running application is never modified: a separate helper applies the
verified update after the original process has exited.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

from app_version import GITHUB_REPOSITORY, VERSION_TAG
from user_data import data_dir


BETA_TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)-beta\.([1-9]\d*)\Z")
API_RELEASES = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases?per_page=100"
MAX_API_BYTES = 2 * 1024 * 1024
MAX_ZIP_BYTES = 40 * 1024 * 1024
MAX_EXTRACT_BYTES = 80 * 1024 * 1024
MAX_FILES = 150
PRESERVE_EXISTING = frozenset({"aliases.json", "artwork.xml"})
MANDATORY = frozenset({
    "GUI_실행.pyw", "gui.py", "app_version.py",
    "auto_update.py", "auto_update_helper.py",
})


@dataclass(frozen=True)
class Release:
    tag: str
    zip_url: str
    checksum_url: str
    zip_digest: str | None = None


def beta_key(tag: str) -> tuple[int, int, int, int]:
    match = BETA_TAG.fullmatch(tag)
    if not match:
        raise ValueError(f"Invalid beta release tag: {tag!r}")
    return tuple(int(n) for n in match.groups())


def _read_https(url: str, max_bytes: int, timeout: float = 5) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"api.github.com", "github.com"}:
        raise ValueError("Untrusted automatic update source")
    req = urllib.request.Request(url, headers={
        "User-Agent": "KNULLI-Korean-Auto-Scraper-Updater",
        "Accept": "application/vnd.github+json" if parsed.hostname == "api.github.com"
                  else "application/octet-stream",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("Automatic update response exceeds size limit")
        return data


def choose_newest_beta(releases: list, current_tag: str = VERSION_TAG) -> Release | None:
    """Use GitHub release *list*: /releases/latest excludes prereleases."""
    current_key = beta_key(current_tag)
    found = []
    for row in releases:
        if not isinstance(row, dict) or row.get("draft") or row.get("prerelease") is not True:
            continue
        tag = row.get("tag_name")
        if not isinstance(tag, str) or not BETA_TAG.fullmatch(tag):
            continue
        key = beta_key(tag)
        if key <= current_key:
            continue
        names = {
            f"KNULLI-Korean-Auto-Scraper-{tag}-Windows.zip",
            f"KNULLI-Korean-Auto-Scraper-{tag}-Windows.zip.sha256",
        }
        assets = {
            a.get("name"): a
            for a in row.get("assets", [])
            if isinstance(a, dict) and a.get("name") in names
        }
        if len(assets) != 2:
            continue
        archive = assets[f"KNULLI-Korean-Auto-Scraper-{tag}-Windows.zip"]
        checks = assets[f"KNULLI-Korean-Auto-Scraper-{tag}-Windows.zip.sha256"]
        url = archive.get("browser_download_url")
        checksum_url = checks.get("browser_download_url")
        if not all(isinstance(s, str) for s in (url, checksum_url)):
            continue
        valid_prefix = f"https://github.com/{GITHUB_REPOSITORY}/releases/download/{tag}/"
        if url != valid_prefix + f"KNULLI-Korean-Auto-Scraper-{tag}-Windows.zip":
            continue
        if checksum_url != url + ".sha256":
            continue
        digest = archive.get("digest")
        if digest is not None and (not isinstance(digest, str) or
                                   not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest)):
            continue
        found.append((key, Release(tag, url, checksum_url, digest)))
    return max(found, key=lambda item: item[0])[1] if found else None


def discover(current_tag: str = VERSION_TAG) -> Release | None:
    records = json.loads(_read_https(API_RELEASES, MAX_API_BYTES).decode("utf-8"))
    if not isinstance(records, list):
        raise ValueError("Invalid GitHub releases API response")
    return choose_newest_beta(records, current_tag)


def _safe_member(name: str, prefix: str) -> str | None:
    """Require the *exact* one-directory packaged layout and trusted file types."""
    if not name.startswith(prefix + "/") or "\\" in name:
        raise ValueError("Unexpected archive root")
    rel = name[len(prefix) + 1:]
    if not rel or name.endswith("/"):
        return None
    parts = rel.split("/")
    if any(p in ("", ".", "..") or ":" in p or "\x00" in p for p in parts):
        raise ValueError("Unsafe archive file path")
    if len(parts) == 1:
        allowed = (rel.endswith(".py") or rel in {
            "GUI_실행.pyw", "GUI_실행.vbs",
            "README.md", "README_한국어.txt", "aliases.json",
            "artwork.xml", "config.example.json", "테스트_실행.bat",
        })
    else:
        allowed = len(parts) == 2 and parts[0] == "docs" and rel in {
            "docs/KNOWN_ISSUES.md", "docs/DECISIONS.md",
        }
    if not allowed:
        raise ValueError("Archive contains unexpected app file: " + rel)
    return rel


def _embedded_version(py_source: bytes) -> str:
    tree = ast.parse(py_source.decode("utf-8"), filename="app_version.py")
    for node in tree.body:
        if (isinstance(node, ast.Assign) and
                any(isinstance(t, ast.Name) and t.id == "VERSION_TAG" for t in node.targets)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            return node.value.value
    raise ValueError("Archive has no valid VERSION_TAG")


def verify_archive(data: bytes, tag: str) -> dict[str, bytes]:
    """Read the complete allow-listed ZIP into memory only after hash validation.

    Reject Zip Slip, symlinks, duplicate members, unexpected app files,
    oversized/bomb-like archives and a version that differs from its tag.
    """
    result: dict[str, bytes] = {}
    prefix = f"KNULLI-Korean-Auto-Scraper-{tag}"
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > MAX_FILES:
            raise ValueError("Too many files in update archive")
        for entry in entries:
            if entry.is_dir():
                _safe_member(entry.filename, prefix)
                continue
            rel = _safe_member(entry.filename, prefix)
            if rel is None:
                continue
            if rel in result:
                raise ValueError("Duplicate update archive member")
            mode = (entry.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError("Symlink in update archive is forbidden")
            if entry.file_size > MAX_EXTRACT_BYTES:
                raise ValueError("Oversized update member")
            total += entry.file_size
            if total > MAX_EXTRACT_BYTES:
                raise ValueError("Update archive exceeds extraction size limit")
            result[rel] = archive.read(entry)
    if not MANDATORY.issubset(result):
        raise ValueError("Update archive lacks required startup modules")
    if _embedded_version(result["app_version.py"]) != tag:
        raise ValueError("Release tag and application version do not match")
    return result


def stage_release(release: Release, base: Path | None = None) -> Path:
    archive = _read_https(release.zip_url, MAX_ZIP_BYTES, timeout=15)
    checksum = _read_https(release.checksum_url, 512, timeout=8).decode("ascii")
    expected_filename = f"KNULLI-Korean-Auto-Scraper-{release.tag}-Windows.zip"
    match = re.fullmatch(r"([0-9a-fA-F]{64})  " + re.escape(expected_filename) + r"\s*", checksum)
    if not match:
        raise ValueError("Invalid release SHA-256 checksum file")
    digest = hashlib.sha256(archive).hexdigest()
    if digest.lower() != match.group(1).lower():
        raise ValueError("Release ZIP SHA-256 does not match checksum")
    if release.zip_digest and digest != release.zip_digest.split(":", 1)[1].lower():
        raise ValueError("Release ZIP SHA-256 does not match GitHub digest")
    members = verify_archive(archive, release.tag)
    root = Path(base or data_dir())
    root.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="knulli_autoupdate_", dir=root))
    try:
        payload = stage / "payload"
        payload.mkdir()
        hashes = {}
        for rel, contents in members.items():
            dest = payload / PurePosixPath(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(contents)
            hashes[rel] = hashlib.sha256(contents).hexdigest()
        (stage / "manifest.json").write_text(json.dumps({
            "tag": release.tag, "files": hashes,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.copy2(payload / "auto_update_helper.py", stage / "update_worker.py")
        return stage
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def log_error(exc: Exception | str) -> None:
    try:
        path = data_dir() / "auto_update.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        from datetime import datetime
        with path.open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now().isoformat(timespec='seconds')}: {exc}\n")
    except Exception:
        pass  # Update failure must never prevent the app from starting.


def _acquire_update_lock() -> Path | None:
    """Avoid two independently started GUIs installing over each other."""
    home = data_dir()
    home.mkdir(parents=True, exist_ok=True)
    lock = home / "auto_update.lock"
    for _ in range(2):
        try:
            fd = os.open(str(lock), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 15 * 60:
                    lock.unlink()
                    continue
            except FileNotFoundError:
                continue
            return None
        with os.fdopen(fd, "w", encoding="ascii") as out:
            out.write(str(os.getpid()))
        return lock
    return None


def _release_update_lock(lock: Path | None) -> None:
    if lock is None:
        return
    try:
        if lock.read_text(encoding="ascii") == str(os.getpid()):
            lock.unlink()
    except OSError:
        pass


def try_launch_update(install_dir: Path, current_tag: str = VERSION_TAG) -> bool:
    """Return True only after a checked update is assigned to its own process.

    Offline/timeouts/invalid releases must not prevent the existing GUI from
    starting. An update lock avoids simultaneous installers on the same PC.
    """
    if os.environ.pop("KNULLI_SKIP_UPDATE_ONCE", None) == "1":
        return False
    stage = None
    lock = None
    launched = False
    try:
        lock = _acquire_update_lock()
        if lock is None:
            return False
        release = discover(current_tag)
        if not release:
            return False
        stage = stage_release(release)
        worker = stage / "update_worker.py"
        command = [sys.executable, str(worker), str(stage),
                   str(Path(install_dir).resolve()), str(os.getpid()), sys.executable]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        subprocess.Popen(command, cwd=str(stage), close_fds=True, creationflags=flags)
        launched = True
        return True
    except Exception as exc:
        log_error(exc)
        if stage:
            shutil.rmtree(stage, ignore_errors=True)
        return False
    finally:
        if not launched:
            _release_update_lock(lock)
