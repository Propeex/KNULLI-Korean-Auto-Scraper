"""Find and remove gamelist entries whose ROM files no longer exist.

Scanning is read-only; removal is an explicit, confirmed action in the GUI.
Only XML-linked, unshared media in managed media folders can be deleted.
Never scans image filenames to guess ownership and never deletes ROM files.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath
import tempfile
import xml.etree.ElementTree as ET

import backend
import core
import manager


MEDIA_TAGS = manager.MEDIA
MEDIA_FOLDERS = frozenset({'images', 'videos', 'media', 'manuals', 'covers', 'screenshots'})
MEDIA_EXT = {
    'image': {'.png', '.jpg', '.jpeg', '.webp'},
    'thumbnail': {'.png', '.jpg', '.jpeg', '.webp'},
    'marquee': {'.png', '.jpg', '.jpeg', '.webp'},
    'fanart': {'.png', '.jpg', '.jpeg', '.webp'},
    'titleshot': {'.png', '.jpg', '.jpeg', '.webp'},
    'wheel': {'.png', '.jpg', '.jpeg', '.webp'},
    'mix': {'.png', '.jpg', '.jpeg', '.webp'},
    'boxart': {'.png', '.jpg', '.jpeg', '.webp'},
    'boxback': {'.png', '.jpg', '.jpeg', '.webp'},
    'video': {'.mp4', '.mkv', '.avi'},
    'manual': {'.pdf'},
}


@dataclass
class SystemCleanup:
    system: str
    original: bytes
    paths: tuple[str, ...] = ()
    media: tuple[str, ...] = ()


@dataclass
class CleanupPlan:
    root: str
    snapshots: dict[str, bytes] = field(default_factory=dict)
    systems: list[SystemCleanup] = field(default_factory=list)

    @property
    def game_count(self) -> int:
        return sum(len(s.paths) for s in self.systems)

    @property
    def media_count(self) -> int:
        return len({p for s in self.systems for p in s.media})

    def examples(self, limit: int = 6) -> list[str]:
        return [f'{s.system}: {p}' for s in self.systems for p in s.paths][:limit]


def _valid_root(root: str) -> str:
    root = root.rstrip('/')
    if not root.startswith('/') or '..' in root.split('/') or not root:
        raise ValueError('Invalid KNULLI ROM root')
    core.sq(root)
    return root


def _game_path(root: str, system: str, text: str | None) -> str | None:
    """Resolve a <game><path>; ignore ambiguous or unsafe references."""
    if not text or text != text.strip() or any(c in text for c in ('\\', '\x00', '\r', '\n')):
        return None
    if '..' in text.split('/'):
        return None
    base = root + '/' + system
    if text.startswith('./'):
        path = base + '/' + text[2:]
    elif text.startswith(base + '/'):
        path = text
    elif not text.startswith('/'):
        # Some EmulationStation gamelists omit the leading ./.
        path = base + '/' + text
    else:
        return None
    posix = PurePosixPath(path)
    if system == 'ports':
        # Only actual PortMaster launcher XML entries are eligible. Never
        # treat package directories or PortMaster management tools as games.
        from portmaster import is_game_launcher
        if not is_game_launcher('ports/' + posix.name) or len(posix.parts) != len(PurePosixPath(base).parts)+1:
            return None
    if not posix.suffix or posix.name in ('.', '..'):
        return None
    if not posix.as_posix().startswith(base + '/'):
        return None
    return posix.as_posix()


def _media_path(root: str, system: str, tag: str, text: str | None) -> str | None:
    if tag not in MEDIA_EXT or not text or text != text.strip():
        return None
    path = backend.remote_media_path(root, system, text)
    if not path or '\r' in path or '\n' in path:
        return None
    parts = PurePosixPath(path).parts
    # The path must stay inside this system and a known media subfolder.
    base = PurePosixPath(root + '/' + system).parts
    if parts[:len(base)] != base or len(parts) < len(base) + 2:
        return None
    if not set(x.lower() for x in parts[len(base):-1]).intersection(MEDIA_FOLDERS):
        return None
    if PurePosixPath(path).suffix.lower() not in MEDIA_EXT[tag]:
        return None
    return path


def _reference_path(root: str, system: str, tag: str, text: str | None) -> str | None:
    """Also recognize explicit links to another system's media for share safety."""
    local = _media_path(root, system, tag, text)
    if local:
        return local
    if not text or not text.startswith(root + '/') or '..' in text.split('/'):
        return None
    parts = PurePosixPath(text).parts
    root_parts = PurePosixPath(root).parts
    if len(parts) <= len(root_parts) or parts[:len(root_parts)] != root_parts:
        return None
    target_system = parts[len(root_parts)]
    if target_system not in core.SYSTEM_IDS:
        return None
    return _media_path(root, target_system, tag, text)


# Leave substantial headroom for short ADB shell command limits on KNULLI.
MAX_EXISTENCE_SHELL_LENGTH = 1000


def _path_states(adb, paths: list[str]) -> dict[str, bool]:
    """Check exact ROM paths without exceeding ADB shell command length.

    Each Unicode path is encoded once and assigned to a shell variable; the
    previous version expanded the octal-encoded path twice for every check.
    A length-budgeted batch is sent only when all checks fit. If ADB still
    refuses a batch for length, retry with smaller batches. Never interpret
    an ADB error or shortened reply as 'ROM missing'.
    """
    unique = list(dict.fromkeys(paths))
    states: dict[str, bool] = {}

    def statement(path: str) -> str:
        encoded = core.Adb._encoded_remote_path(path)
        return ('p=' + encoded + '; if [ -e "$p" ] || [ -L "$p" ]; '
                'then printf 1; else printf 0; fi')

    def verify(batch: list[tuple[str, str]]) -> None:
        cmd = '; '.join(snippet for _, snippet in batch)
        try:
            reply = adb.shell(cmd, timeout=70).replace('\r', '').replace('\n', '')
        except Exception as exc:
            if len(batch) > 1 and 'too long' in str(exc).lower():
                midpoint = len(batch) // 2
                verify(batch[:midpoint])
                verify(batch[midpoint:])
                return
            raise RuntimeError(
                'ADB ROM 파일 존재 확인 실패(안전상 자료 삭제 중단): ' + str(exc)
            ) from exc
        if len(reply) != len(batch) or any(bit not in '01' for bit in reply):
            raise RuntimeError(
                'ADB ROM 검사 응답이 불완전합니다. 안전을 위해 자료 정리를 중단합니다.'
            )
        for (path, _), bit in zip(batch, reply):
            states[path] = bit == '1'

    batch: list[tuple[str, str]] = []
    total = 0
    for path in unique:
        snippet = statement(path)
        added = len(snippet) + (2 if batch else 0)
        if batch and total + added > MAX_EXISTENCE_SHELL_LENGTH:
            verify(batch)
            batch = []
            total = 0
            added = len(snippet)
        # A single very long pathname is still checked individually. If the
        # device refuses it, verify() raises rather than guessing 'missing'.
        batch.append((path, snippet))
        total += added
    if batch:
        verify(batch)
    return states


def _read_available_xml(adb, root: str) -> dict[str, bytes]:
    system_list = sorted(core.SYSTEM_IDS)
    remote = {sys: root + '/' + sys + '/gamelist.xml' for sys in system_list}
    # These paths are ASCII-only; use a single batch instead of one ADB trip per system.
    if hasattr(adb, 'exists_many'):
        xml_exists = adb.exists_many(list(remote.values()))
    else:
        xml_exists = {path: adb.exists(path) for path in remote.values()}
    with tempfile.TemporaryDirectory(prefix='knulli_orphan_scan_') as td:
        result = {}
        for system, path in remote.items():
            if not xml_exists.get(path, False):
                continue
            dest = Path(td) / (system + '.xml')
            adb.pull(path, dest)
            data = dest.read_bytes()
            # Invalid XML is never treated as empty: abort rather than deleting.
            core.parse_xml(data)
            result[system] = data
    return result


def inspect(adb, config: dict) -> CleanupPlan:
    """Discover orphaned XML records; does not write/delete anything."""
    root = _valid_root(config.get('remote_root', '/userdata/roms'))
    docs = _read_available_xml(adb, root)
    plan = CleanupPlan(root=root, snapshots=docs)
    candidates = {}
    for system, data in docs.items():
        xml = core.parse_xml(data)
        for entry in xml.findall('game'):
            rom = _game_path(root, system, entry.findtext('path'))
            if rom:
                candidates.setdefault(rom, []).append((system, entry))
    if not candidates:
        return plan
    existing = _path_states(adb, list(candidates))
    missing = {path for path, present in existing.items() if not present}
    if not missing:
        return plan

    # Collect references from entries that remain, including folder thumbnails.
    used_media = set()
    for system, data in docs.items():
        xml = core.parse_xml(data)
        for node in xml:
            if node.tag == 'game':
                rom = _game_path(root, system, node.findtext('path'))
                if rom in missing:
                    continue
            for child in node.iter():
                if child.tag in MEDIA_TAGS:
                    media = _reference_path(root, system, child.tag, child.text)
                    if media:
                        used_media.add(media)

    by_system = {}
    for rom in missing:
        for system, _ in candidates[rom]:
            by_system.setdefault(system, set()).add(rom)

    for system, paths in sorted(by_system.items()):
        media = set()
        xml = core.parse_xml(docs[system])
        for node in xml.findall('game'):
            rom = _game_path(root, system, node.findtext('path'))
            if rom not in paths:
                continue
            for child in node:
                if child.tag in MEDIA_TAGS:
                    remote = _media_path(root, system, child.tag, child.text)
                    if remote and remote not in used_media and remote not in candidates:
                        media.add(remote)
        plan.systems.append(SystemCleanup(
            system=system, original=docs[system],
            paths=tuple(sorted(paths)), media=tuple(sorted(media))
        ))
    return plan


def apply(adb, plan: CleanupPlan, work: Path) -> dict:
    """Apply an approved plan with revalidation and NO persistent backups.

    Media are removed only *after* XML is successfully updated. A failed media
    removal is reported without removing other unrelated files.
    """
    if not plan.game_count:
        return {'removed_games': 0, 'removed_media': 0, 'warnings': []}
    # All XMLs must be unchanged, including references in other systems.
    current = _read_available_xml(adb, plan.root)
    if current != plan.snapshots:
        raise RuntimeError('게임 목록이 변경되었습니다. 다시 조회한 뒤 정리하세요.')
    gone = [path for sysplan in plan.systems for path in sysplan.paths]
    if any(_path_states(adb, gone).values()):
        raise RuntimeError('삭제된 ROM 중 다시 발견된 파일이 있습니다. 다시 조회하세요.')

    work = Path(work)
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    report = {'removed_games': 0, 'removed_media': 0, 'warnings': [],
              'systems': []}
    for sysplan in plan.systems:
        sysdir = plan.root + '/' + sysplan.system
        xml = core.parse_xml(sysplan.original)
        removed = 0
        target = set(sysplan.paths)
        for node in list(xml.findall('game')):
            if _game_path(plan.root, sysplan.system, node.findtext('path')) in target:
                xml.remove(node)
                removed += 1
        if not removed:
            continue
        # Only remove XML entries, never source ROM files.
        manager._check_unmodified(adb, sysdir, sysplan.original)
        manager._write_xml(adb, sysdir, core.xml_bytes(xml))
        report['removed_games'] += removed
        report['systems'].append(sysplan.system)
        for remote in sysplan.media:
            # Re-check that the target is a controlled media path and not a directory.
            if not any(_media_path(plan.root, sysplan.system, tag, remote) == remote
                       for tag in MEDIA_TAGS):
                report['warnings'].append('unsafe media reference skipped: ' + remote)
                continue
            expr = core.Adb._encoded_remote_path(remote)
            cmd = ('if [ -d ' + expr + ' ]; then printf SKIP; '
                   'elif [ -f ' + expr + ' ] || [ -L ' + expr + ' ]; then '
                   'rm -f ' + expr + ' && printf DELETED; '
                   'else printf ABSENT; fi')
            try:
                result = adb.shell(cmd, timeout=50).strip()
                if result == 'DELETED':
                    report['removed_media'] += 1
                elif result not in ('SKIP', 'ABSENT'):
                    raise RuntimeError('unexpected delete response: ' + result[:80])
                elif result == 'SKIP':
                    report['warnings'].append('directory not deleted: ' + remote)
            except Exception as exc:
                report['warnings'].append('media deletion failed: ' + remote + ': ' + str(exc)[:100])
    # Report is local only; no credentials or ROM contents included.
    core.json_write(work / 'last_cleanup.json', report)
    return report
