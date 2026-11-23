"""Read-only PS1 multi-disc grouping and explicitly approved KNULLI M3U creation.

The actual disc images and save data are NEVER moved, renamed or deleted.
An existing valid M3U is the canonical game. Otherwise a complete set of
Disc 1..N is represented once in our catalogue until the user explicitly
selects "멀티디스크 묶기" to write a small playlist.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
from pathlib import Path, PurePosixPath
import re
import tempfile
import uuid
import xml.etree.ElementTree as ET

import core
import manager

PSX = "psx"
DISC_EXT = frozenset({".chd", ".cue", ".iso", ".pbp", ".ccd"})
PLAYLIST_MAX_BYTES = 16384
DISC = re.compile(
    r"(?i)(?:[\(\[\{]\s*)?(?:disc|disk|cd|디스크)\s*[-_. ]*([1-9])\s*[\)\]\}]?"
)
STRIP = " \t._-"
BAD_NAME = re.compile(r'[/\\\x00-\x1f<>:"|?*]')


@dataclass(frozen=True)
class PlaylistPlan:
    remote: str
    title: str
    tracks: tuple[str, ...]
    # Representative disc path displayed temporarily until M3U is created.
    lead: str

    @property
    def rel(self) -> str:
        return "psx/" + self.remote.split("/psx/", 1)[1]

    def text(self) -> str:
        folder = PurePosixPath(self.remote).parent
        entries = [str(PurePosixPath(p).relative_to(folder)) for p in self.tracks]
        return "\n".join(entries) + "\n"


def disc_identity(name: str) -> tuple[str, int] | None:
    """Strict explicit Disc/CD number recognition, preserving region/revision tags."""
    stem = PurePosixPath(name).stem
    matches = list(DISC.finditer(stem))
    if len(matches) != 1:
        return None
    part = matches[0]
    base = (stem[:part.start()] + " " + stem[part.end():]).strip(STRIP)
    base = re.sub(r"\s+", " ", base).strip(STRIP)
    if not base or BAD_NAME.search(base) or len(base.encode("utf-8")) > 210:
        return None
    return base, int(part.group(1))


def clean_title(name: str) -> str:
    found = disc_identity(name)
    return found[0] if found else PurePosixPath(name).stem


def _is_disc(rom: tuple) -> bool:
    remote, rel, sys = rom
    return sys == PSX and rel.suffix.lower() in DISC_EXT


def plans_for(roms: list[tuple], root: str) -> list[PlaylistPlan]:
    """Find unambiguous 2+ disc sets in the same folder with contiguous numbers."""
    groups: dict[tuple, dict[int, list[tuple]]] = {}
    for record in roms:
        if not _is_disc(record):
            continue
        remote, rel, _ = record
        found = disc_identity(rel.name)
        if not found:
            continue
        title, number = found
        key = (str(PurePosixPath(remote).parent), title.casefold())
        groups.setdefault(key, {}).setdefault(number, []).append(record)
    existing = {p for p, _, _ in roms}
    plans = []
    for (folder, _), discs in sorted(groups.items()):
        numbers = sorted(discs)
        if len(numbers) < 2 or numbers != list(range(1, len(numbers) + 1)):
            continue
        if any(len(choices) != 1 for choices in discs.values()):
            continue  # do not mix cue/chd variants or ambiguous same-number discs
        tracks = tuple(discs[n][0][0] for n in numbers)
        title = disc_identity(discs[1][0][1].name)[0]
        playlist = folder + "/" + title + ".m3u"
        if playlist in existing:
            continue
        plans.append(PlaylistPlan(playlist, title, tracks, tracks[0]))
    return plans


def _playlist_refs(adb, playlist: str, remote_files: set[str], root: str) -> set[str]:
    """Resolve an existing M3U only if every relative reference is safe/existing."""
    try:
        size = adb.stat_size(playlist)
        if not 0 < size <= PLAYLIST_MAX_BYTES:
            return set()
        # First read with an ASCII-only shell command: Windows ADB may lose
        # Korean path bytes when 'adb pull' passes a Unicode argument.
        data = None
        try:
            response = adb.shell(
                "od -An -v -tx1 " + core.Adb._encoded_remote_path(playlist),
                timeout=30,
            )
            words = response.split()
            if words and all(re.fullmatch(r"[0-9a-fA-F]{2}", w) for w in words):
                data = bytes.fromhex("".join(words))
        except (RuntimeError, ValueError, OSError):
            pass
        if data is None:
            with tempfile.TemporaryDirectory(prefix="knulli_m3u_read_") as td:
                local = Path(td) / "playlist.m3u"
                adb.pull(playlist, local)
                data = local.read_bytes()
        if len(data) != size:
            return set()
        raw = data.decode("utf-8-sig")
        base = PurePosixPath(playlist).parent
        tracks = []
        for line in raw.splitlines():
            item = line.strip()
            if not item or item.startswith("#"):
                continue
            if ("\\" in item or "\x00" in item or "\r" in item
                    or item.startswith("/") or ".." in item.split("/")):
                return set()
            parts = PurePosixPath(item).parts
            if any(p in (".", "..", "") for p in parts):
                return set()
            remote = str(base.joinpath(*parts))
            if not remote.startswith(root.rstrip("/") + "/psx/"):
                return set()
            if remote not in remote_files:
                return set()
            if PurePosixPath(remote).suffix.lower() not in DISC_EXT:
                return set()
            tracks.append(remote)
        return set(tracks) if len(tracks) >= 2 and len(set(tracks)) == len(tracks) else set()
    except (RuntimeError, ValueError, UnicodeError, OSError):
        return set()


def group_catalogue(adb, roms: list[tuple], root: str) -> tuple[list[tuple], dict[str, PlaylistPlan]]:
    """Return one visible row per multi-disc title; no writes during scan.

    Existing M3U hides only files it references correctly. A missing M3U
    produces a temporary representative Disc 1 and an explicit create plan.
    """
    root = root.rstrip("/")
    psx_root = root + "/psx/"
    all_files = {p for p, _, _ in roms}
    all_playlists = [p for p, rel, sys in roms if sys == PSX and rel.suffix.lower() == ".m3u"]
    hidden = set()
    for playlist in all_playlists:
        if not playlist.startswith(psx_root):
            continue
        hidden.update(_playlist_refs(adb, playlist, all_files, root))
    candidates = {}
    for plan in plans_for(roms, root):
        if any(p in hidden for p in plan.tracks):
            continue
        if plan.remote in all_files:
            continue
        candidates[plan.lead] = plan
        hidden.update(plan.tracks[1:])
    return [r for r in roms if r[0] not in hidden], candidates


def _copy_existing_disc_metadata(adb, plan: PlaylistPlan, root: str) -> None:
    """Copy Disc 1 metadata to a new playlist entry, without deleting old XML.

    Does not make a backup, matching the user's explicit no-scrape-backup
    requirement. Errors propagate; no existing game entries are removed.
    """
    sysdir = root.rstrip("/") + "/psx"
    original, xml = manager._read_xml(adb, sysdir)
    disc_rel = "./" + plan.lead[len(sysdir) + 1:]
    playlist_rel = "./" + plan.remote[len(sysdir) + 1:]
    if core.find_entry(xml, playlist_rel) is not None:
        return
    prior = core.find_entry(xml, disc_rel)
    if prior is None:
        return
    new = copy.deepcopy(prior)
    path = new.find("path")
    if path is None:
        path = ET.SubElement(new, "path")
    path.text = playlist_rel
    # Prefer title without Disc 1, unless the user provided a custom title.
    name = new.find("name")
    old_name = (name.text or "").strip() if name is not None else ""
    if not old_name or old_name == PurePosixPath(plan.lead).stem:
        if name is None:
            name = ET.SubElement(new, "name")
        name.text = plan.title
    xml.append(new)
    manager._check_unmodified(adb, sysdir, original)
    manager._write_xml(adb, sysdir, core.xml_bytes(xml))


def create_one(adb, plan: PlaylistPlan, root: str) -> str:
    """Create one playlist with exclusive remote creation; NEVER overwrite files."""
    root = root.rstrip("/")
    if not plan.remote.startswith(root + "/psx/") or len(plan.tracks) < 2:
        raise ValueError("Invalid PS1 multi-disc playlist plan")
    if PurePosixPath(plan.remote).suffix.lower() != ".m3u":
        raise ValueError("Invalid PS1 M3U extension")
    folder = PurePosixPath(plan.remote).parent
    if any(PurePosixPath(track).parent != folder for track in plan.tracks):
        raise ValueError("Only same-folder PS1 disc sets can be auto-created")
    if adb.exists(plan.remote):
        return "exists"
    for track in plan.tracks:
        if not adb.exists(track):
            raise RuntimeError("디스크 파일이 변경되어 M3U 생성을 중단했습니다: " + track)
    with tempfile.TemporaryDirectory(prefix="knulli_m3u_create_") as td:
        local = Path(td) / "playlist.m3u"
        local.write_bytes(plan.text().encode("utf-8"))
        # Stage under PSX root with ASCII-only remote name, so Korean target
        # names are carried exclusively through the encoded ASCII shell command.
        stage = root + "/psx/.knulli-m3u-" + uuid.uuid4().hex + ".tmp"
        adb.upload(local, stage)
        source = core.Adb._encoded_remote_path(stage)
        target = core.Adb._encoded_remote_path(plan.remote)
        cmd = ("p=" + target + "; s=" + source + "; "
               "if [ -e \"$p\" ] || [ -L \"$p\" ]; then printf EXISTS; "
               "elif (set -C; cat \"$s\" > \"$p\") 2>/dev/null; "
               "then printf CREATED; else printf FAILED; fi; "
               "rm -f \"$s\"")
        try:
            result = adb.shell(cmd, timeout=30).strip()
        finally:
            # Safe to attempt cleanup even if ADB failed mid-command.
            try:
                adb.shell("rm -f " + core.Adb._encoded_remote_path(stage), timeout=15)
            except Exception:
                pass
        if result == "EXISTS":
            return "exists"
        if result != "CREATED":
            raise RuntimeError("M3U 파일 생성이 실패했습니다(기존 파일은 보존).")
    _copy_existing_disc_metadata(adb, plan, root)
    return "created"


def create_many(adb, root: str, plans: list[PlaylistPlan]) -> dict:
    created = []
    warnings = []
    for plan in plans:
        try:
            status = create_one(adb, plan, root)
            if status == "created":
                created.append(plan.remote)
            elif status == "exists":
                warnings.append(plan.remote + ": 이미 존재해 덮어쓰지 않았습니다")
        except Exception as exc:
            warnings.append(plan.remote + ": " + str(exc)[:190])
    return {"created": created, "warnings": warnings}
