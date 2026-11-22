"""Conservative transactional KNULLI gamelist/ROM changes over the existing ADB connection.

Never changes emulator config or restarts/stops ADB. No rename of archives,
disc playlists, cue-based systems, or ambiguous multi-file ROM sets.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path, PurePosixPath
import re
import tempfile
import xml.etree.ElementTree as ET

import core

MEDIA = ('image','thumbnail','marquee','fanart','video','manual','boxback','titleshot','wheel','mix','boxart')
TEXT = ('desc','rating','genre','releasedate','developer','publisher','players','name')
# A conservative allow list. Zip/fbneo/neo geo archives and multi-part CD images
# can rely on their fixed ROM/archive name and are intentionally excluded.
SINGLE_FILE = {
    '.nes':{'nes'}, '.sfc':{'snes'}, '.smc':{'snes'},
    '.gba':{'gba'}, '.gb':{'gb'}, '.gbc':{'gbc'},
    '.n64':{'n64'}, '.z64':{'n64'}, '.v64':{'n64'},
    '.nds':{'nds'}, '.gg':{'gamegear'}, '.sms':{'mastersystem'},
    '.pce':{'pcengine'}, '.a26':{'atari2600'}, '.a78':{'atari7800'},
    '.ngp':{'ngp'}, '.ngc':{'ngpc'}, '.ws':{'wswan'}, '.wsc':{'wswanc'},
}


def validate_name(old_name: str, proposed: str, system: str):
    new=(proposed or '').strip()
    if new != proposed or not new or new in ('.','..'):
        raise ValueError('파일명 앞뒤 공백과 빈 파일명은 허용하지 않습니다.')
    if any(c in new for c in '/\\\x00\r\n<>:"|?*') or any(ord(c)<32 for c in new):
        raise ValueError('파일명에 사용할 수 없는 문자입니다.')
    if new.endswith(('.', ' ')) or len(new.encode('utf-8'))>240:
        raise ValueError('파일명 끝의 공백/점 또는 너무 긴 이름은 허용하지 않습니다.')
    before=PurePosixPath(old_name)
    after=PurePosixPath(new)
    if before.suffix.lower()!=after.suffix.lower() or not before.suffix:
        raise ValueError('확장자는 변경할 수 없습니다. 파일명만 수정하세요.')
    if system not in SINGLE_FILE.get(before.suffix.lower(),set()):
        raise ValueError('이 게임기는 묶음 ROM/특수 파일일 수 있어 이름 변경을 보호합니다.')
    if old_name == new:
        raise ValueError('기존 파일명과 동일합니다.')
    return new


def complete_filename(old_name:str,stem:str):
    """GUI edits only the visible stem, never the extension."""
    suffix=PurePosixPath(old_name).suffix
    return stem+suffix


def media_rename_suggestion(old_stem: str, new_stem: str, basename: str):
    # Only rename a media filename clearly tied to the ROM stem. Hash-named
    # `auto-*` media remain unchanged and XML references remain valid.
    if basename == old_stem:
        return new_stem
    if basename.startswith(old_stem) and len(basename)>len(old_stem) and basename[len(old_stem)] in '.- _':
        return new_stem + basename[len(old_stem):]
    return None


def _relative_for_item(item):
    return './'+PurePosixPath(*PurePosixPath(item.rel).parts[1:]).as_posix()


def _safe_media_path(root, system, path):
    from backend import remote_media_path
    return remote_media_path(root,system,path)


def plan_rename(item, new_name, xml_root, root='/userdata/roms', rename_display=True):
    new_name=validate_name(PurePosixPath(item.rel).name,new_name,item.system)
    old=PurePosixPath(item.remote)
    new_remote=str(old.parent/new_name)
    before_rel=_relative_for_item(item)
    after_rel='./'+PurePosixPath(*PurePosixPath(item.rel).parts[1:-1],new_name).as_posix()
    existing=core.find_entry(xml_root,before_rel)
    if core.find_entry(xml_root,after_rel) is not None:
        raise ValueError('변경할 ROM 이름이 이미 gamelist.xml에 있습니다.')
    moves=[]
    if existing is not None:
        for key in MEDIA:
            text=(existing.findtext(key) or '').strip()
            source=_safe_media_path(root,item.system,text)
            if not source:
                continue
            src_path=PurePosixPath(source)
            next_name=media_rename_suggestion(old.stem,PurePosixPath(new_name).stem,src_path.name)
            if next_name is None:
                continue
            # Do not rename a resource shared by any other game entry.
            shared=False
            for other in xml_root.findall('game'):
                if other is existing:continue
                for other_tag in MEDIA:
                    if _safe_media_path(root,item.system,(other.findtext(other_tag) or '').strip())==source:
                        shared=True;break
                if shared:break
            if shared:continue
            dest=str(src_path.with_name(next_name))
            if source!=dest:
                # Relative path follows the original gamelist style.
                sys_root=root.rstrip('/')+'/'+item.system
                new_xml=('./'+dest[len(sys_root)+1:]) if text.startswith('./') else dest
                moves.append((key,source,dest,new_xml))
    return {'old_remote':item.remote,'new_remote':new_remote,'old_rel':before_rel,
            'new_rel':after_rel,'old_name':old.name,'new_name':new_name,
            'moves':moves,'display_name':bool(rename_display)}


def _write_xml(adb, sysdir: str, changed: bytes) -> None:
    """Replace gamelist.xml via ADB's temporary upload, without backups.

    The currently read XML remains in memory until the caller returns; no
    persistent XML copy is written locally or on the handheld.
    """
    remote_xml = sysdir + '/gamelist.xml'
    with tempfile.TemporaryDirectory(prefix='knulli_xml_write_') as td:
        path = Path(td) / 'gamelist.xml'
        path.write_bytes(changed)
        adb.upload(path, remote_xml)


def _read_xml(adb,sysdir):
    remote=sysdir+'/gamelist.xml'
    with tempfile.TemporaryDirectory(prefix='knulli_xml_read_') as td:
        if not adb.exists(remote):return None,core.parse_xml(None)
        dest=Path(td)/'gamelist.xml'
        adb.pull(remote,dest)
        data=dest.read_bytes()
    return data,core.parse_xml(data)


def _check_unmodified(adb,sysdir,expected):
    actual,_=_read_xml(adb,sysdir)
    if actual!=expected:
        raise RuntimeError('기기 gamelist.xml이 변경되어 작업을 중단했습니다.')


def rename_rom(adb,item,new_name,root='/userdata/roms',work:Path|None=None,rename_display=True):
    """Moves a single-file ROM and any unshared stem-named referenced media.

    If an operation fails, known file moves are reversed where possible.
    No persistent XML backups are created; an operational rename journal may
    remain to diagnose failed rollback (it is not a copy of scraped data).
    """
    work=Path(work or Path(__file__).resolve().parent/'work')
    sysdir=root.rstrip('/')+'/'+item.system
    initial,xml=_read_xml(adb,sysdir)
    plan=plan_rename(item,new_name,xml,root,rename_display)
    if not adb.exists(plan['old_remote']):raise RuntimeError('원본 ROM이 없습니다.')
    if adb.shell('if [ -e '+core.sq(plan['new_remote'])+' ]; then echo YES; fi')=='YES':
        raise RuntimeError('변경할 이름의 파일이 기기에 이미 있습니다.')
    actual_moves=[]
    for key,src,dest,text in plan['moves']:
        if adb.exists(src):
            if adb.shell('if [ -e '+core.sq(dest)+' ]; then echo YES; fi')=='YES':
                raise RuntimeError('자원 파일명이 충돌합니다: '+dest)
            actual_moves.append((key,src,dest,text))
    entry=core.find_entry(xml,plan['old_rel'])
    if entry is None:
        entry=ET.SubElement(xml,'game')
        ET.SubElement(entry,'path').text=plan['old_rel']
    entry.find('path').text=plan['new_rel']
    if rename_display:
        child=entry.find('name')
        if child is None:child=ET.SubElement(entry,'name')
        child.text=PurePosixPath(new_name).stem
    for key,src,dest,new_xml in actual_moves:
        entry.find(key).text=new_xml
    updated=core.xml_bytes(xml)
    _check_unmodified(adb,sysdir,initial)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    plan['moves']=[(key,src,dest) for key,src,dest,_ in actual_moves]
    jpath=work/'rename_journal'/('rename_'+stamp+'.json')
    core.json_write(jpath,{**plan,'stage':'prepared'})
    moved=[]
    try:
        move_targets=[(plan['old_remote'],plan['new_remote'])]+[(src,dest) for _,src,dest in plan['moves']]
        for src,dest in dict.fromkeys(move_targets):
            adb.shell('mv '+core.sq(src)+' '+core.sq(dest))
            moved.append((src,dest))
            core.json_write(jpath,{**plan,'stage':'moving','moved':moved})
        _write_xml(adb,sysdir,updated)
        core.json_write(jpath,{**plan,'stage':'done','moved':moved})
        return plan
    except Exception as e:
        failures=[]
        for src,dest in reversed(moved):
            try:adb.shell('mv '+core.sq(dest)+' '+core.sq(src))
            except Exception as err:failures.append(str(err))
        if failures:
            core.json_write(jpath,{**plan,'stage':'ROLLBACK_FAILED','moved':moved,'errors':failures})
            raise RuntimeError('이름 변경 실패 후 복구도 일부 실패했습니다. 연결 확인 후 rename_journal 확인: '+str(e)) from e
        core.json_write(jpath,{**plan,'stage':'rolled_back','reason':str(e)})
        raise


def update_metadata(adb,item,edits:dict,root='/userdata/roms',work:Path|None=None):
    work=Path(work or Path(__file__).resolve().parent/'work')
    sysdir=root.rstrip('/')+'/'+item.system
    original,xml=_read_xml(adb,sysdir)
    entry=core.find_entry(xml,_relative_for_item(item))
    if entry is None:
        entry=ET.SubElement(xml,'game');ET.SubElement(entry,'path').text=_relative_for_item(item)
    for key,value in edits.items():
        if key not in TEXT:raise ValueError('허용되지 않는 메타데이터 필드: '+key)
        value=str(value).strip()
        if len(value)>10000:raise ValueError('메타데이터가 너무 깁니다.')
        if key=='rating' and value:
            try: number=float(value)
            except ValueError:raise ValueError('평점은 0~1 사이의 숫자여야 합니다.')
            if not 0<=number<=1:raise ValueError('평점은 0~1 사이의 숫자여야 합니다.')
        child=entry.find(key)
        if child is None:child=ET.SubElement(entry,key)
        child.text=value
    changed=core.xml_bytes(xml)
    if changed==original:return False
    _check_unmodified(adb,sysdir,original)
    _write_xml(adb,sysdir,changed)
    return True
