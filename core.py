#!/usr/bin/env python3
# KNULLI Korean ROM Auto Scraper v0.3.1 - stdlib only, no server restarts or OS changes.
from __future__ import annotations
import argparse
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
# ScreenScraper numeric IDs: incomplete by design; unknown folders are skipped instead of misclassified.
SYSTEM_IDS = {
    'nes':3, 'snes':4, 'gb':9, 'gbc':10, 'gba':12, 'n64':14, 'nds':15,
    'megadrive':1, 'mastersystem':2, 'gamegear':21, 'pcengine':31,
    'psx':57, 'psp':61, 'saturn':22, 'dreamcast':23, 'sega32x':19,
    'segacd':20, 'mame':75, 'fbneo':75, 'neogeo':142, 'atari2600':26,
    'atari7800':27, 'ngp':25, 'ngpc':82, 'wswan':45, 'wswanc':46, 'ports':0,  # Native PortMaster launchers
}
ROM_EXT = {'.nes','.fds','.sfc','.smc','.gb','.gbc','.gba','.nds','.n64','.z64','.v64',
           '.md','.gen','.bin','.sms','.gg','.pce','.zip','.7z','.chd','.iso','.cue',
           '.pbp','.cso','.cdi','.gdi','.32x','.a26','.a78','.ngp','.ngc','.ws','.wsc','.sh'}
# Disc containers/archives can't be assumed to match hash catalog; for them search names only.
NO_HASH = {'.zip','.7z','.chd','.iso','.cue','.pbp','.cso','.cdi','.gdi'}
EXT_MATCH = {
    '.nes':{'nes'}, '.sfc':{'snes'},'.smc':{'snes'}, '.gba':{'gba'},'.gb':{'gb'},'.gbc':{'gbc'},
    '.nds':{'nds'},'.n64':{'n64'},'.z64':{'n64'},'.v64':{'n64'},'.pce':{'pcengine'},
    '.sms':{'mastersystem'},'.gg':{'gamegear'},'.a26':{'atari2600'},'.a78':{'atari7800'},
    '.ngp':{'ngp'},'.ngc':{'ngpc'},'.ws':{'wswan'},'.wsc':{'wswanc'},
}


def sq(s: str) -> str:
    if '\n' in s or '\r' in s or '\x00' in s:
        raise ValueError('unsupported newline/NUL in path')
    return "'" + s.replace("'", "'\\''") + "'"


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKC', s).casefold()
    s = re.sub(r'\([^)]*(?:k|kor|한글|korean|j|u|e|usa|japan)[^)]*\)', ' ', s, flags=re.I)
    s = re.sub(r'\[[^]]*\]', ' ', s)
    return re.sub(r'[^\w가-힣]+', ' ', s).strip()


def safe_rel(remote: str, root: str) -> PurePosixPath | None:
    root = root.rstrip('/')
    if not remote.startswith(root + '/') or '\n' in remote or '\r' in remote:
        return None
    rel = PurePosixPath(remote[len(root)+1:])
    if len(rel.parts) < 2 or '..' in rel.parts or rel.name in ('', '.', '..'):
        return None
    return rel


def json_write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Adb:
    def __init__(self, binary=None, serial=None):
        if not binary:
            for p in [HERE / 'adb.exe', HERE / 'platform-tools' / 'adb.exe',
                      HERE.parent / 'knulli_auto_scraper' / 'adb.exe',
                      HERE.parent / 'knulli_auto_scraper_v06' / 'platform-tools' / 'adb.exe',
                      HERE.parent / 'knulli_auto_scraper_v05' / 'adb.exe',
                      HERE.parent / 'knulli_auto_scraper_v06' / 'adb.exe',
                      Path.home() / 'Desktop' / 'knulli_auto_scraper_v06' / 'platform-tools' / 'adb.exe',
                      Path.home() / 'Desktop' / 'knulli_auto_scraper_v06' / 'adb.exe',
                      Path.cwd() / 'adb.exe',
                      Path.home() / 'Desktop' / 'knulli_auto_scraper' / 'adb.exe']:
                if p.is_file():
                    binary = str(p)
                    break
        self.binary = binary or shutil.which('adb')
        if not self.binary:
            raise RuntimeError('adb.exe not found: put adb.exe and accompanying DLLs beside this program, or set ADB_PATH')
        self.serial = serial

    def call(self, args, timeout=60, ok=True) -> bytes:
        cmd = [self.binary] + (['-s',self.serial] if self.serial else []) + list(args)
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
                               creationflags=(0x08000000 if os.name=="nt" else 0))
        except FileNotFoundError as e:
            raise RuntimeError('ADB executable or DLL not found: '+str(self.binary)) from e
        except subprocess.TimeoutExpired as e:
            raise RuntimeError('ADB timeout during '+str(args[:1])) from e
        if ok and p.returncode != 0:
            msg = p.stderr.decode('utf-8','replace').strip() or p.stdout.decode('utf-8','replace').strip()
            raise RuntimeError('ADB '+args[0]+' failed: '+msg[:300])
        return p.stdout

    def connect(self):
        # Doesn't call 'start-server', 'kill-server', 'reconnect' or modify USB internet tunnel.
        lines = self.call(['devices'],timeout=12).decode('utf-8','replace').splitlines()
        ready = [x.split()[0] for x in lines[1:] if len(x.split())>=2 and x.split()[1]=='device']
        if len(ready)!=1:
            raise RuntimeError('Expected one authorized ADB device, found '+str(len(ready)))
        self.serial = ready[0]
        return self.serial

    def shell(self, command: str, timeout=60) -> str:
        # Explicitly use 'shell', not 'exec-out': that transport reported 'closed' on this KNULLI.
        return self.call(['shell',command],timeout=timeout).decode('utf-8','replace').replace('\r\n','\n').strip()

    def exists(self, remote):
        return self.shell('if [ -f '+sq(remote)+' ]; then echo YES; fi')=='YES'

    def exists_many(self, paths):
        """Batch read-only media existence checks to reduce ADB round trips."""
        results={}
        for start in range(0,len(paths),40):
            batch=list(paths[start:start+40])
            cmd='; '.join('if [ -f '+sq(p)+' ]; then printf 1; else printf 0; fi' for p in batch)
            try:
                bits=self.shell(cmd,timeout=35).replace('\n','').replace('\r','')
                if len(bits)!=len(batch) or any(c not in '01' for c in bits):raise ValueError('short response')
                results.update({p:bit=='1' for p,bit in zip(batch,bits)})
            except Exception:
                # Never mislabel media as nonexistent after a transient USB failure.
                for p in batch:results[p]=self.exists(p)
        return results

    @staticmethod
    def _parse_hex_listing(text: str, root: str) -> list[str]:
        """Decode remote path bytes after ASCII-only `od -tx1` transport.

        Some KNULLI/Windows ADB shell configurations replace non-ASCII
        pathname characters with question marks in the shell listing output.
        Hex encoding the *remote bytes before transmission* preserves Korean
        names even within nested ROM folders. NUL-separated data also avoids
        `ls` quoting and filenames containing whitespace/ampersands.
        """
        words = text.split()
        if not words:
            return []
        if not all(re.fullmatch(r'[0-9a-fA-F]{2}', w) for w in words):
            raise RuntimeError('non-hex output from device ROM listing')
        raw = bytes.fromhex(''.join(words))
        if raw and not raw.endswith(b'\x00'):
            raise RuntimeError('truncated ROM listing returned by ADB')
        found=[]
        for encoded in raw.split(b'\x00'):
            if not encoded:
                continue
            try:
                path=encoded.decode('utf-8', errors='strict')
            except UnicodeDecodeError as exc:
                raise RuntimeError('device returned non-UTF-8 pathname; no paths were modified') from exc
            if path.startswith(root.rstrip('/') + '/') and '\n' not in path and '\r' not in path:
                found.append(path)
        return list(dict.fromkeys(found))

    @staticmethod
    def _listing_script(system_roots: list[str]) -> str:
        """Run all path discovery on device; send ASCII hex over ADB.

        The original implementation sent raw nested `find` output back to
        Windows. On some installations its Korean folder components became
        literal '?' characters, causing `stat` to report no such file.
        File discovery works with original byte strings on the device, then
        encodes those bytes *before* ADB can mangle shell stdout.
        """
        dirs=' '.join(sq(path) for path in system_roots)
        return ('(for d in ' + dirs + '; do '
                '[ -d "$d" ] || continue; '
                # Never recurse into PortMaster game-data directories.
                'case "$d" in */ports) '
                'for p in "$d"/*.sh; do [ -f "$p" ] && printf "%s\\000" "$p"; done; '
                'continue ;; esac; '
                'for p in "$d"/*; do '
                'if [ -f "$p" ]; then printf "%s\\000" "$p"; '
                'elif [ -d "$p" ]; then '
                'case "$p" in */images|*/videos|*/media|*/manuals) ;; '
                '*) find "$p" -type f -print0 2>/dev/null ;; esac; '
                'fi; '
                'done; done) | od -An -v -tx1')

    def listing(self, root: str) -> list[str]:
        """Enumerate ROMs with Unicode-safe, NUL-delimited hex transport.

        Uses only `adb shell` (no `exec-out`, server reset, or OS changes).
        Falls back to scanning individual system folders if one big ADB shell
        response fails. Invalid or truncated output must never turn into a
        plausible but broken path, so it is rejected instead of applying data.
        """
        base=root.rstrip('/')
        system_roots=[base+'/'+name for name in sorted(SYSTEM_IDS)]
        errors=[]
        try:
            output=self.shell(self._listing_script(system_roots),timeout=180)
            result=self._parse_hex_listing(output,base)
            if result:
                return result
            errors.append('batch scan returned no files')
        except Exception as exc:
            errors.append('batch scan: '+str(exc)[:160])

        # Smaller per-system fallback for USB/ADB command length and output limits.
        result=[]
        for directory in system_roots:
            try:
                output=self.shell(self._listing_script([directory]),timeout=45)
                result.extend(self._parse_hex_listing(output,base))
            except Exception as exc:
                errors.append(directory+': '+str(exc)[:120])
        if result:
            return list(dict.fromkeys(result))
        # A device may have valid system folders but no ROMs at all.
        # Treat genuine empty discovery as empty, not a transport error.
        if errors == ['batch scan returned no files']:
            return []
        raise RuntimeError('ROM listing produced no valid paths; no files changed. '
                           + '; '.join(errors[:4]))

    @staticmethod
    def _encoded_remote_path(remote: str) -> str:
        """Create ASCII-only shell expression that resolves to exact UTF-8 path.

        Safe for Korean path components on Windows ADB command-line transports.
        Each byte is represented by POSIX `printf %b` octal escape; no path
        content is ever interpreted as a shell script.
        """
        sq(remote)  # reject NUL/newline before creating a shell argument
        octals=''.join('\\0%03o' % b for b in remote.encode('utf-8'))
        return "\"$(printf '%b' " + sq(octals) + ")\""

    def stat_size(self, remote):
        """Ask for the exact file size without a lossy Unicode path argument."""
        cmd='stat -c %s '+self._encoded_remote_path(remote)
        out=self.shell(cmd,timeout=25)
        if not re.fullmatch(r'[0-9]+',out):
            raise RuntimeError('ROM 파일 크기를 확인하지 못했습니다 (경로/ADB 문제): '+remote)
        return int(out)

    def sha1(self, remote):
        out=self.shell('sha1sum '+sq(remote),timeout=900)
        m=re.match(r'^([0-9a-fA-F]{40})\b',out)
        if not m: raise RuntimeError('sha1sum unavailable')
        return m.group(1).lower()

    def gba_internal_name(self, remote):
        cmd=('dd if='+sq(remote)+' bs=1 skip=160 count=12 2>/dev/null | od -An -tx1')
        output=self.shell(cmd,timeout=30)
        octets=re.findall(r'\b[0-9a-fA-F]{2}\b',output)
        if len(octets)<12: return None
        title=bytes(int(i,16) for i in octets[:12]).decode('ascii','ignore').strip('\x00 ')
        return title if len(title)>=4 and re.fullmatch(r'[\w\- ]+',title) else None

    def pull(self, remote, local: Path):
        local.parent.mkdir(parents=True,exist_ok=True)
        self.call(['pull',remote,str(local)],timeout=120)

    def upload(self, local: Path, remote: str):
        # ADB push -> temporary remote name -> atomic rename; does not overwrite ROMs.
        remote_dir=remote.rsplit('/',1)[0]
        self.shell('mkdir -p '+sq(remote_dir),timeout=30)
        stage=remote+'.knulli-autoscraper.part'
        try:
            self.call(['push',str(local),stage],timeout=180)
            self.shell('mv '+sq(stage)+' '+sq(remote),timeout=30)
        except Exception:
            try: self.shell('rm -f '+sq(stage),timeout=20)
            except Exception: pass
            raise




def parse_xml(data):
    if not data:
        return ET.Element('gameList')
    parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True,insert_pis=True))
    root=ET.fromstring(data,parser=parser)
    if root.tag!='gameList':raise ValueError('unexpected gamelist.xml format')
    return root


def xml_bytes(root):
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def find_entry(root, relative):
    relative=relative.replace('\\','/')
    for g in root.findall('game'):
        p=(g.findtext('path') or '').replace('\\','/')
        if p.lstrip('./')==relative.lstrip('./'):
            return g
    return None


def apply_entry(root, relative, title, img):
    entry=find_entry(root,relative)
    if entry is None:
        entry=ET.SubElement(root,'game')
        ET.SubElement(entry,'path').text=relative
    if entry.find('name') is None:
        ET.SubElement(entry,'name').text=title
    img_element=entry.find('image')
    if img_element is not None and (img_element.text or '').strip():
        return False
    if img_element is None:img_element=ET.SubElement(entry,'image')
    img_element.text=img
    return True


def load_aliases(path):
    if not path.is_file():return {}
    source=json.loads(path.read_text(encoding='utf-8'))
    return {norm(k):[str(v)] if isinstance(v,str) else list(v) for k,v in source.items()}


def candidates_for(stem, aliases, internal=None):
    result=[]
    for s in aliases.get(norm(stem),[]): result.append(s)
    if internal:result.append(internal)
    result.append(stem)
    # Entries with Latin title prefixes may contain a region tag or translation marker.
    cleaned=re.sub(r'\s*(?:\([^)]*\)|\[[^]]*\])\s*',' ',stem).strip()
    if cleaned and cleaned!=stem:result.append(cleaned)
    seen=set();out=[]
    for x in result:
        n=norm(x)
        if n and n not in seen:seen.add(n);out.append(x)
    return out


def wikidata_title(korean_stem, cache):
    """Optional best-effort exact Korean label -> English label, not fuzzy translation."""
    key=norm(korean_stem)
    if not key or not re.search('[가-힣]',key):return []
    if key in cache:return cache[key]
    search={'action':'wbsearchentities','search':korean_stem,'language':'ko',
            'type':'item','limit':5,'format':'json'}
    url='https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode(search)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'KnulliKoreanAutoScraper/0.3 (personal tool)'}),timeout=12) as r:
            data=json.load(r)
        exact=[v for v in data.get('search',[]) if norm(v.get('label',''))==key]
        # Ambiguous Korean labels must never be auto-converted.
        if len(exact)!=1:cache[key]=[];return []
        item=exact[0].get('id','')
        q={'action':'wbgetentities','ids':item,'props':'labels|aliases','languages':'en|ja','format':'json'}
        with urllib.request.urlopen(urllib.request.Request('https://www.wikidata.org/w/api.php?'+urllib.parse.urlencode(q),headers={'User-Agent':'KnulliKoreanAutoScraper/0.3 (personal tool)'}),timeout=12) as r:
            entity=json.load(r).get('entities',{}).get(item,{})
        labels=entity.get('labels',{})
        name=labels.get('en',{}).get('value') or labels.get('ja',{}).get('value')
        cache[key]=[name] if name else []
    except Exception:
        cache[key]=[]
    return cache[key]


def collect_roms(adb, root):
    result=[]
    for remote in adb.listing(root):
        rel=safe_rel(remote,root)
        if not rel or rel.suffix.lower() not in ROM_EXT or rel.parts[0].lower() not in SYSTEM_IDS:continue
        if rel.parts[0].lower()=='ports':
            from portmaster import is_game_launcher
            if not is_game_launcher(rel.as_posix()):continue
        elif rel.suffix.lower()=='.sh':
            continue
        if any(x.lower() in ('images','videos','manuals','media') for x in rel.parts[1:-1]):continue
        # A system directory is authoritative for ambiguous image extensions. Do not guess on .zip/.chd.
        system=rel.parts[0].lower()
        allowed=EXT_MATCH.get(rel.suffix.lower())
        if allowed is not None and system not in allowed:continue
        if rel.suffix.lower()=='.bin' and system in ('psx','saturn','segacd','dreamcast'):continue
        result.append((remote,rel,system))
    return sorted(set(result),key=lambda x:str(x[1]))


