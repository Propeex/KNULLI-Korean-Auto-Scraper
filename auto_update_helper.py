"""Independent Windows-friendly update installer (copied outside the app).

This script runs only after the original launcher has exited. The staged
release is checked again, installed with per-file rollback, and relaunched.
It never touches user_data settings, ROMs, or app-created scrape data.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
import uuid


PRESERVE_EXISTING = frozenset({"aliases.json", "artwork.xml"})
MANDATORY = frozenset({
    "GUI_실행.pyw", "gui.py", "app_version.py",
    "auto_update.py", "auto_update_helper.py",
})
HASH = re.compile(r"[0-9a-f]{64}\Z")
TAG = re.compile(r"v\d+\.\d+\.\d+-beta\.[1-9]\d*\Z")


def _valid_relative(path: str) -> bool:
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        return False
    parts = path.split("/")
    if any(x in ("", ".", "..") or ":" in x for x in parts):
        return False
    if len(parts) == 1:
        return path.endswith(".py") or path in {
            "GUI_실행.pyw", "GUI_실행.vbs", "README.md", "README_한국어.txt",
            "aliases.json", "artwork.xml", "config.example.json", "테스트_실행.bat",
        }
    return (len(parts) == 2 and parts[0] == "docs"
            and path in {"docs/KNOWN_ISSUES.md", "docs/DECISIONS.md"})


def _load_manifest(stage: Path) -> dict[str, str]:
    info = json.loads((stage / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(info, dict) or not TAG.fullmatch(info.get("tag", "")):
        raise ValueError("Invalid update manifest tag")
    files = info.get("files")
    if not isinstance(files, dict) or not MANDATORY.issubset(files):
        raise ValueError("Incomplete update manifest")
    for rel, digest in files.items():
        if not _valid_relative(rel) or not isinstance(digest, str) or not HASH.fullmatch(digest):
            raise ValueError("Unsafe update manifest entry")
        source = stage / "payload" / PurePosixPath(rel)
        if source.is_symlink() or not source.is_file():
            raise ValueError("Missing or linked update payload: " + rel)
        if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
            raise ValueError("Staged update payload hash mismatch: " + rel)
    return files


def _check_target(install: Path) -> None:
    if install.is_symlink() or not install.is_dir():
        raise ValueError("Invalid installed application directory")
    if not ((install / "GUI_실행.pyw").is_file()
            and (install / "gui.py").is_file()):
        raise ValueError("Target does not look like the installed KNULLI application")


def apply_update(stage: Path, install: Path) -> int:
    """Apply verified app modules; rollback code files if replacement fails.

    Returns the number of updated files. A small temporary rollback directory
    contains only application code, never gamelist.xml or scraped media.
    """
    stage = Path(stage).resolve()
    install = Path(install).resolve()
    _check_target(install)
    files = _load_manifest(stage)
    rollback = stage / "rollback"
    rollback.mkdir(exist_ok=True)
    updates = []
    for rel in sorted(files):
        source = stage / "payload" / PurePosixPath(rel)
        dest = install / PurePosixPath(rel)
        if dest.parent.is_symlink() or dest.is_symlink():
            raise ValueError("Refusing to overwrite a symbolic link")
        if rel in PRESERVE_EXISTING and dest.exists():
            continue
        if dest.exists() and not dest.is_file():
            raise ValueError("Refusing to overwrite a non-file")
        if dest.is_file():
            previous = rollback / PurePosixPath(rel)
            previous.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, previous)
        updates.append((rel, source, dest, dest.is_file()))
    changed = []
    try:
        for rel, source, dest, existed in updates:
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".knulli-update-" + uuid.uuid4().hex + ".tmp")
            try:
                shutil.copyfile(source, tmp)
                if hashlib.sha256(tmp.read_bytes()).hexdigest() != files[rel]:
                    raise ValueError("Update file verification failed: " + rel)
                os.replace(tmp, dest)
                changed.append((rel, dest, existed))
            finally:
                if tmp.exists():
                    tmp.unlink()
        return len(changed)
    except Exception:
        restore_errors = []
        for rel, dest, existed in reversed(changed):
            try:
                if existed:
                    previous = rollback / PurePosixPath(rel)
                    temp_restore = dest.with_name(dest.name + ".knulli-restore-" + uuid.uuid4().hex)
                    shutil.copyfile(previous, temp_restore)
                    os.replace(temp_restore, dest)
                else:
                    dest.unlink(missing_ok=True)
            except Exception as exc:
                restore_errors.append(f"{rel}: {exc}")
        if restore_errors:
            raise RuntimeError(
                "Update failed and automatic code rollback was incomplete: "
                + "; ".join(restore_errors)
            )
        raise


def wait_for_parent_exit(pid: int, timeout: float = 120.0) -> None:
    """Wait for the original Windows GUI to exit before modifying app files."""
    if pid <= 0 or pid == os.getpid():
        raise ValueError("Invalid parent process ID")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.WaitForSingleObject.restype = wintypes.DWORD
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        SYNCHRONIZE = 0x00100000
        WAIT_OBJECT_0 = 0
        handle = kernel.OpenProcess(SYNCHRONIZE, False, pid)
        if not handle:
            # The original launcher may have quit before the helper opened it.
            error = ctypes.get_last_error()
            if error in (87, 1168):  # invalid process ID / not found
                return
            raise RuntimeError(f"Cannot wait for original GUI process: {error}")
        try:
            millis = min(int(timeout * 1000), 0xFFFFFFFE)
            state = kernel.WaitForSingleObject(handle, millis)
            if state != WAIT_OBJECT_0:
                raise TimeoutError(f"Original GUI did not exit for update (wait={state})")
        finally:
            kernel.CloseHandle(handle)
        return

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        except PermissionError as exc:
            raise RuntimeError("Cannot inspect original GUI process") from exc
        time.sleep(0.15)
    raise TimeoutError("Original GUI did not exit for update")


def _log(stage: Path, text: str) -> None:
    # Keep the log outside the application folder; it survives upgrades.
    try:
        path = stage.parent / "auto_update.log"
        from datetime import datetime
        with path.open("a", encoding="utf-8") as stream:
            stream.write(f"{datetime.now().isoformat(timespec='seconds')}: {text}\n")
    except OSError:
        pass


def _restart(python_exe: str, install: Path, skip_update: bool) -> None:
    env = os.environ.copy()
    if skip_update:
        env["KNULLI_SKIP_UPDATE_ONCE"] = "1"
    else:
        env.pop("KNULLI_SKIP_UPDATE_ONCE", None)
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    subprocess.Popen(
        [python_exe, str(install / "GUI_실행.pyw")],
        cwd=str(install), env=env, close_fds=True, creationflags=flags,
    )


def main(args: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if args is None else args)
    if len(arguments) != 4:
        return 2
    stage = Path(arguments[0]).resolve()
    install = Path(arguments[1]).resolve()
    try:
        pid = int(arguments[2])
    except ValueError:
        return 2
    executable = arguments[3]
    success = False
    try:
        wait_for_parent_exit(pid)
        count = apply_update(stage, install)
        _log(stage, f"Auto update applied: {count} application files; {install}")
        success = True
    except Exception as exc:
        _log(stage, f"Auto update failed: {type(exc).__name__}: {exc}")
    finally:
        try:
            # Even when update fails, resume the existing app without retrying
            # immediately; a later normal launch will try again.
            _restart(executable, install, skip_update=not success)
        except Exception as exc:
            _log(stage, f"Failed to restart application: {exc}")
        if success:
            try:
                shutil.rmtree(stage)
            except OSError:
                pass
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
