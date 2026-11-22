"""Conservative offline PortMaster metadata scraper for KNULLI.

Only top-level /userdata/roms/ports/*.sh launchers are games. A trusted local
port.json/gameinfo.xml and existing local cover/screenshot may fill absent
EmulationStation gamelist.xml metadata. NEVER modify launchers, port data,
licenses, save files, or images. No device network or permanent XML backups.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import PurePosixPath
import re
import xml.etree.ElementTree as ET

import core
import manager

PORT_SYSTEM = 'ports'
FIELDS = frozenset({'name','desc','genre','developer','publisher','releasedate','players','rating'})
IMAGE_SUFFIX = frozenset({'.png','.jpg','.jpeg','.webp'})
MAX_MANIFEST = 128 * 1024

# Not games: PortMaster itself and tooling/installers in the Ports menu.
CONTROL_NAMES = frozenset({
    'portmaster.sh', 'install.portmaster.sh', 'install.full.portmaster.sh',
    'install portmaster.sh', 'portmaster scraper.sh',
    'portmaster scraper (rescan all).sh',
})
SKIP_PREFIXES = ('install.', 'install ', 'uninstall.', 'uninstall ')


def is_game_launcher(relative: str) -> bool:
    path = PurePosixPath(relative)
    if len(path.parts) != 2 or path.parts[0].lower() != PORT_SYSTEM:
        return False
    name = path.name.casefold()
    return (path.suffix.lower() == '.sh'
            and not name.startswith(('.', '_'))
            and name not in CONTROL_NAMES
            and not name.startswith(SKIP_PREFIXES))


def _clean_field(value: object, length: int = 10000) -> str:
    if not isinstance(value, str):
        return ''
    value = value.strip()
    return value if len(value) <= length and '\x00' not in value else ''


def _read_small(adb, remote: str) -> bytes:
    """Read small UTF-8 manifests through ADB ASCII hex (Korean path safe)."""
    size = adb.stat_size(remote)
    if not 0 < size <= MAX_MANIFEST:
        raise ValueError('PortMaster manifest exceeds supported size')
    encoded = core.Adb._encoded_remote_path(remote)
    text = adb.shell('od -An -v -tx1 ' + encoded, timeout=40)
    words = text.split()
    if not all(re.fullmatch('[0-9a-fA-F]{2}', w) for w in words):
        raise ValueError('Invalid hex response when reading PortMaster metadata')
    data = bytes.fromhex(''.join(words))
    if len(data) != size:
        raise RuntimeError('PortMaster metadata read truncated over USB ADB')
    return data


def _metadata_paths(adb, ports_root: str) -> list[str]:
    """Enumerate only shallow metadata/artwork; never scan large game data."""
    quoted = core.sq(ports_root)
    patterns = [
        '"$d"/*/port.json', '"$d"/*/*.port.json',
        '"$d"/*.port.json', '"$d"/*/gameinfo.xml',
        '"$d"/*/cover.png', '"$d"/*/cover.jpg', '"$d"/*/cover.jpeg',
        '"$d"/*/screenshot.png', '"$d"/*/screenshot.jpg',
    ]
    script = ('(d=' + quoted + '; for p in ' + ' '.join(patterns) + '; do '
              '[ -f "$p" ] && [ ! -L "$p" ] && printf "%s\\000" "$p"; '
              'done) | od -An -v -tx1')
    raw = adb.shell(script, timeout=90)
    return core.Adb._parse_hex_listing(raw, ports_root)


@dataclass
class PortInfo:
    relative_launcher: str
    metadata: dict[str,str] = field(default_factory=dict)
    image: str = ''
    source: str = ''


def _launcher_from_path(text: str, ports_root: str) -> str | None:
    if not isinstance(text,str) or not text.strip() or '\x00' in text:
        return None
    text = text.strip().replace('\\','/')
    if text.startswith('./'):
        text = text[2:]
    elif text.startswith(ports_root + '/'):
        text = text[len(ports_root)+1:]
    elif text.startswith('ports/'):
        # GUI catalogue entries are relative to the ROM root.
        text = text[len('ports/'):]
    if '/' in text or text in ('.','..'):
        return None
    rel = 'ports/' + text
    return text if is_game_launcher(rel) else None


def _media_candidate(ports_root: str, text: str | None) -> str | None:
    if not text or '\x00' in text or '\\' in text or '\r' in text or '\n' in text:
        return None
    if '..' in text.split('/'):
        return None
    if text.startswith('./'):
        remote = ports_root + '/' + text[2:]
    elif text.startswith(ports_root + '/'):
        remote = text
    else:
        return None
    parts = PurePosixPath(remote)
    base = PurePosixPath(ports_root).parts
    if (parts.parts[:len(base)] != base or len(parts.parts) < len(base)+2
            or parts.suffix.lower() not in IMAGE_SUFFIX):
        return None
    return remote


def _read_json(adb, path: str) -> dict:
    value = json.loads(_read_small(adb,path).decode('utf-8-sig'))
    return value if isinstance(value,dict) else {}


def _read_gameinfo(adb, path: str) -> dict[str,str]:
    root = core.parse_xml(_read_small(adb,path))
    games = root.findall('game')
    if len(games) != 1:
        return {}
    result = {}
    for key in FIELDS | {'path','image','thumbnail'}:
        val = _clean_field(games[0].findtext(key))
        if val:
            result[key] = val
    return result


def _metadata_from_json(obj: dict) -> dict[str,str]:
    attr = obj.get('attr',{})
    if not isinstance(attr,dict):
        return {}
    result = {}
    for src,dest in [('title','name'),('desc','desc'),('developer','developer'),
                     ('publisher','publisher'),('releasedate','releasedate'),
                     ('players','players'),('rating','rating')]:
        val = _clean_field(attr.get(src))
        if val:
            result[dest] = val
    genre = attr.get('genres')
    if isinstance(genre,list):
        genre = ', '.join(_clean_field(v,100) for v in genre if _clean_field(v,100))
    genre = _clean_field(genre)
    if genre:
        result['genre'] = genre
    return result


def load_ports(adb, root: str, launchers: list[str]) -> dict[str,PortInfo]:
    """Resolve authoritative manifest items -> launcher mapping, no fuzzy matches.

    PortMaster files may have different names from their launcher. We accept
    a manifest only if its explicit items or gameinfo path matches a real,
    top-level launcher. Unknown scripts are preserved but not scraped.
    """
    ports_root = root.rstrip('/')+'/ports'
    available = set()
    for path in launchers:
        target = _launcher_from_path(path, ports_root)
        if target:
            available.add(target)
    if not available:
        return {}

    listing = _metadata_paths(adb,ports_root)
    manifests = sorted(p for p in listing if p.endswith('.port.json') or p.endswith('/port.json'))
    gameinfos = sorted(p for p in listing if p.endswith('/gameinfo.xml'))
    images = {p for p in listing if PurePosixPath(p).suffix.lower() in IMAGE_SUFFIX}
    by_folder = {}
    for info in gameinfos:
        by_folder.setdefault(str(PurePosixPath(info).parent),{})['xml']=info
    for manifest in manifests:
        by_folder.setdefault(str(PurePosixPath(manifest).parent),{})['json']=manifest

    found = {}
    # Match by package content, not folder/filename similarity.
    for folder, files in sorted(by_folder.items()):
        if len(found) >= len(available):
            break
        obj = {}
        attrs = {}
        xml_fields = {}
        if 'json' in files:
            try:
                obj = _read_json(adb,files['json'])
                attrs = _metadata_from_json(obj)
            except (ValueError, UnicodeError):
                # Malformed PortMaster package metadata is not trusted.
                pass
        if 'xml' in files:
            try:
                xml_fields = _read_gameinfo(adb,files['xml'])
            except (ValueError, ET.ParseError, UnicodeError):
                # Invalid gameinfo.xml: fall back to a valid port.json.
                pass

        declared = set()
        for item in obj.get('items',[]) if isinstance(obj.get('items'),list) else []:
            launch = _launcher_from_path(item,ports_root)
            if launch:
                declared.add(launch)
        xml_launch = _launcher_from_path(xml_fields.get('path',''),ports_root)
        # If both metadata sources explicitly name different launchers,
        # do not guess which installed game to modify.
        if xml_launch and declared and xml_launch not in declared:
            continue
        matched = (declared & available)
        if xml_launch and xml_launch in available:
            matched.add(xml_launch)
        if len(matched) != 1:
            # Do not guess for mismatched/multiple launchers.
            continue
        target = next(iter(matched))
        if target in found:
            # Multiple sources matching one script: keep first, avoid overwrites.
            continue

        merged = dict(attrs)
        merged.update({k:v for k,v in xml_fields.items() if k in FIELDS})
        image = _media_candidate(ports_root,xml_fields.get('image'))
        if image not in images:
            image = _media_candidate(ports_root,xml_fields.get('thumbnail'))
        if image not in images:
            image = None
        if not image:
            # Trusted files in exactly the manifest's parent directory.
            for name in ('cover.png','cover.jpg','cover.jpeg',
                         'screenshot.png','screenshot.jpg'):
                candidate = folder + '/' + name
                if candidate in images:
                    image = candidate
                    break
        if not merged and not image:
            continue
        relative = './'+target
        found[target] = PortInfo(relative,merged,image or '',
                                 'gameinfo.xml' if xml_fields else 'port.json')
    return found


def apply_one(adb, item, config: dict, catalog: dict[str,PortInfo],
              selection: list[str]) -> dict:
    """Fill only missing XML fields and link to existing PortMaster artwork.

    Never alter port .sh scripts or game data; never upload/copy images.
    This respects the user's no XML backup policy.
    """
    if item.system != PORT_SYSTEM or not is_game_launcher(item.rel):
        raise ValueError('Not a PortMaster game launcher')
    target = PurePosixPath(item.rel).name
    info = catalog.get(target)
    if info is None:
        return {'status':'unmatched','note':'PortMaster의 port.json/gameinfo.xml 정보가 없습니다.'}
    root=config.get('remote_root','/userdata/roms').rstrip('/')
    sysdir = root + '/ports'
    original, xml = manager._read_xml(adb,sysdir)
    rel = info.relative_launcher
    entry = core.find_entry(xml, rel)
    if entry is None:
        entry = ET.SubElement(xml,'game')
        ET.SubElement(entry,'path').text=rel
    changed = []
    # name is important even though it is not a user-visible scraper toggle;
    # never overwrite an explicitly customized non-stem name.
    original_name = (entry.findtext('name') or '').strip()
    expected_stem = PurePosixPath(target).stem
    if (info.metadata.get('name') and
            (not original_name or original_name.casefold()==expected_stem.casefold())):
        new_name=info.metadata['name']
        if new_name!=original_name:
            node=entry.find('name')
            if node is None:node=ET.SubElement(entry,'name')
            node.text=new_name
            changed.append('name')

    for key in sorted(FIELDS-{'name'}):
        if key not in selection:
            continue
        value=info.metadata.get(key,'')
        if not value or (entry.findtext(key) or '').strip():
            continue
        node=entry.find(key)
        if node is None:node=ET.SubElement(entry,key)
        node.text=value
        changed.append(key)
    if info.image and ('image' in selection or 'thumbnail' in selection):
        image_path='./'+info.image[len(sysdir)+1:]
        for key in ('image','thumbnail'):
            if key not in selection or (entry.findtext(key) or '').strip():
                continue
            node=entry.find(key)
            if node is None:node=ET.SubElement(entry,key)
            node.text=image_path
            changed.append(key)

    updated=core.xml_bytes(xml)
    if not changed or updated==original:
        return {'status':'unchanged','fields':[], 'note':'이미 게임 정보가 설정되어 있습니다.'}
    manager._check_unmodified(adb,sysdir,original)
    manager._write_xml(adb,sysdir,updated)
    return {'status':'applied','fields':changed,'matched_title':info.metadata.get('name',expected_stem)}
