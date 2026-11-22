"""KNULLI v0.5 GUI backend. No writes to ROMs, no ADB server restart.

GUI queries a read-only catalogue; user chooses jobs. The only device writes are
new image files and an atomically replaced gamelist.xml with two backups.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
from typing import Callable
import xml.etree.ElementTree as ET

import core
import user_data
import credential_store
import legacy_bridge as legacy

HERE = Path(__file__).resolve().parent
RESOURCES = ('image', 'thumbnail', 'marquee', 'fanart', 'video', 'manual', 'boxback', 'titleshot', 'wheel', 'mix', 'boxart')
METADATA = ('name','desc','genre','developer','publisher','releasedate','rating','players','image','thumbnail','marquee','fanart','video','manual','boxback','titleshot','wheel','mix','boxart')

@dataclass
class RomItem:
    remote: str
    rel: str
    system: str
    display: str
    metadata: dict = field(default_factory=dict)
    resource_paths: dict = field(default_factory=dict)
    image_exists: bool = False
    existing_resources: set = field(default_factory=set)
    xml_problem: str = ''
    status: str = ''
    details: str = ''

    @property
    def stem(self):
        return PurePosixPath(self.rel).stem

    @property
    def has_image_path(self):
        return bool(self.resource_paths.get('image'))

    @property
    def has_data(self):
        # ROM filename/name alone are not scraped data. Broken XML media paths
        # also do not count as resources.
        return bool(self.existing_resources or any((self.metadata.get(k) or '').strip()
                    for k in ('desc','rating','genre','releasedate','developer','publisher','players')))


def remote_media_path(root: str, system: str, text: str) -> str | None:
    if not text or '\x00' in text or '\\' in text or '\n' in text:
        return None
    path=PurePosixPath(text)
    if '..' in path.parts: return None
    system_root=root.rstrip('/')+'/'+system
    if path.is_absolute():
        result=path.as_posix()
        return result if result.startswith(system_root+'/') else None
    return system_root+'/'+path.as_posix().removeprefix('./')


def catalogue(adb: core.Adb, config: dict, update: Callable[[str],None]|None=None) -> list[RomItem]:
    root=config.get('remote_root','/userdata/roms').rstrip('/')
    if not root.startswith('/') or '..' in root.split('/'):
        raise ValueError('Invalid remote root')
    if adb.shell('if [ -d '+core.sq(root)+' ]; then echo YES; fi')!='YES':
        raise RuntimeError('ROM root not found: '+root)
    files=core.collect_roms(adb,root)
    # A valid, reachable KNULLI ROM root can contain zero games. The orphan
    # cleanup feature must still be able to inspect existing gamelist.xml files.
    report=load_json(HERE/'work'/'last_report.json',[])
    recent={r.get('rom'):r for r in report if isinstance(r,dict) and r.get('rom')} if isinstance(report,list) else {}
    with tempfile.TemporaryDirectory(prefix='knulli_catalog_') as td:
        tmp=Path(td);by_system={};result=[]
        for count,(remote,rel,system) in enumerate(files,1):
            if update:update(f'{count}/{len(files)}  {rel}')
            if system not in by_system:
                xml_remote=root+'/'+system+'/gamelist.xml'
                try:
                    if adb.exists(xml_remote):
                        target=tmp/(system+'.xml')
                        adb.pull(xml_remote,target)
                        parsed=core.parse_xml(target.read_bytes())
                        by_system[system]=(parsed,'')
                    else:by_system[system]=(ET.Element('gameList'),'')
                except Exception as e:
                    by_system[system]=(None,'XML 읽기 실패: '+str(e)[:130])
            doc,problem=by_system[system]
            item=RomItem(remote,rel.as_posix(),system,rel.stem,xml_problem=problem)
            if doc is not None:
                local_path='./'+PurePosixPath(*rel.parts[1:]).as_posix()
                entry=core.find_entry(doc,local_path)
                if entry is not None:
                    item.metadata={name:(entry.findtext(name) or '').strip() for name in METADATA}
                    item.display=item.metadata.get('name') or rel.stem
                    for k in RESOURCES:
                        rp=remote_media_path(root,system,item.metadata.get(k,''))
                        if rp:item.resource_paths[k]=rp
            # All actual media existence checks are batched below (less USB traffic).
            result.append(item)
        paths=list(dict.fromkeys(p for item in result for p in item.resource_paths.values()))
        if hasattr(adb,'exists_many'):
            existence=adb.exists_many(paths)
        else:
            existence={p:adb.exists(p) for p in paths}
        for item in result:
            item.existing_resources={k for k,path in item.resource_paths.items() if existence.get(path,False)}
            item.image_exists='image' in item.existing_resources
            if item.xml_problem:item.status='XML 오류'
            elif item.has_data:item.status='데이터 있음'
            elif item.resource_paths:item.status='자원 경로만 있음'
            else:item.status='데이터 없음'
            previous=recent.get(item.rel,{})
            if previous.get('status') in ('unmatched','invalid_media'):
                item.status='검색 실패';item.details=previous.get('note','')
            elif previous.get('status')=='error':
                item.status='오류';item.details=previous.get('note','')
        return result


def load_json(path:Path, fallback):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (ValueError,OSError):return fallback


def _previous_installations():
    """Known old release folders; upgrade never needs a manual file copy."""
    guesses = [HERE.parent / 'knulli_auto_scraper_v05',
               Path.home() / 'Desktop' / 'knulli_auto_scraper_v05',
               HERE.parent / 'knulli_auto_scraper_v071', Path.home() / 'Desktop' / 'knulli_auto_scraper_v071',
               HERE.parent / 'knulli_auto_scraper_v07', Path.home() / 'Desktop' / 'knulli_auto_scraper_v07',
               HERE.parent / 'knulli_auto_scraper_v06',
               Path.home() / 'Desktop' / 'knulli_auto_scraper_v06',
               HERE.parent / 'knulli_auto_scraper_v04',
               Path.home() / 'Desktop' / 'knulli_auto_scraper_v04']
    return list(dict.fromkeys(p for p in guesses if p != HERE))


def load_config():
    """Keep settings and account separately from the replaceable install folder."""
    path=user_data.settings_path()
    if not path.exists():
        config=load_json(HERE/'config.example.json',{})
        for old in [HERE]+_previous_installations():
            other=load_json(old/'config.json',{})
            if isinstance(other,dict) and other:
                for key in ('knulli_scraper','scrape_fields','use_wikidata',
                            'max_rom_transfer_mb','engine_timeout_seconds'):
                    if key in other:config[key]=other[key]
                legacy_account=other.get('screenscraper_account',{})
                if legacy_account.get('user') and legacy_account.get('password'):
                    if credential_store.write(legacy_account):
                        config['screenscraper_account']={'user':'','password':''}
                    else:config['screenscraper_account']=legacy_account
                break
        # Preserve an already-installed Windows Credential Manager entry.
        if not (config.get('screenscraper_account') or {}).get('user'):
            credential=credential_store.read()
            if credential:config['screenscraper_account']=credential
        save_config(config)
    config=load_json(path,{})
    # On Windows Credential Manager is the sole source of secret material.
    account=credential_store.read()
    if account:config['screenscraper_account']=account
    else:config.setdefault('screenscraper_account',{'user':'','password':''})
    return config


def save_config(cfg:dict):
    saved=dict(cfg)
    account=saved.pop('screenscraper_account',{})
    # Do not store secrets in user-visible JSON on Windows.
    if credential_store.write(account):
        pass
    elif account.get('password'):
        # Non-Windows for development only: keep secret in process memory.
        pass
    core.json_write(user_data.settings_path(),saved)


def load_overrides():
    destination=user_data.overrides_path()
    if not destination.exists():
        for old in _previous_installations():
            source=old/'work'/'manual_titles.json'
            if source.is_file():
                old_data=load_json(source,{})
                if isinstance(old_data,dict):
                    core.json_write(destination,old_data)
                    break
    return load_json(destination,{})


def save_overrides(d):
    core.json_write(user_data.overrides_path(),d)


def fetch_resource(adb,item:RomItem,key='image') -> Path | None:
    remote=item.resource_paths.get(key)
    if not remote:return None
    ext=PurePosixPath(remote).suffix.lower()
    if ext not in ('.png','.jpg','.jpeg','.gif','.webp','.mp4','.avi','.mkv','.pdf'):
        return None
    path=HERE/'work'/'preview'/(hashlib.sha256(remote.encode('utf-8')).hexdigest()[:24]+ext)
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.stat().st_size>0:return path
    if not adb.exists(remote):return None
    adb.pull(remote,path)
    return path


def apply_image_element(root:ET.Element, rel_xml:str, filename:str, image_rel:str):
    entry=core.find_entry(root,rel_xml)
    if entry is None:
        entry=ET.SubElement(root,'game')
        ET.SubElement(entry,'path').text=rel_xml
    current_name=entry.find('name')
    if current_name is None:
        ET.SubElement(entry,'name').text=filename
    elif re.search('[가-힣]',filename) and not re.search('[가-힣]',current_name.text or ''):
        # Keep customized Korean titles; restore Korean when a previous scrape wrote English.
        current_name.text=filename
    image=entry.find('image')
    if image is None:image=ET.SubElement(entry,'image')
    previous=image.text
    image.text=image_rel
    return previous


def _device_apply(adb,root_dir, item, media:Path, suffix:str, work:Path):
    sysdir=root_dir+'/'+item.system
    rel_parts=PurePosixPath(item.rel).parts
    local_path='./'+PurePosixPath(*rel_parts[1:]).as_posix()
    xml_remote=sysdir+'/gamelist.xml'
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    image_name='auto-'+hashlib.sha256(item.rel.encode('utf-8')).hexdigest()[:16]+'-'+stamp+suffix
    image_rel='./images/'+image_name
    with tempfile.TemporaryDirectory(prefix='knulli_apply_') as td:
        tmp=Path(td)
        original=None
        if adb.exists(xml_remote):
            file=tmp/'gamelist.xml';adb.pull(xml_remote,file)
            original=file.read_bytes()
        tree=core.parse_xml(original)
        apply_image_element(tree,local_path,item.stem,image_rel)
        changed=core.xml_bytes(tree)
        if changed == original:
            return '이미 동일한 이미지 경로입니다'
        # Re-read before overwriting in case another program changed gamelist.xml.
        if adb.exists(xml_remote):
            second=tmp/'recheck.xml';adb.pull(xml_remote,second)
            if second.read_bytes()!=original:raise RuntimeError('gamelist.xml changed while preparing; aborted')
        elif original is not None:
            raise RuntimeError('gamelist.xml disappeared; aborted')
        # New image filename: re-scraping never destroys the old image.
        remote_image=sysdir+'/images/'+image_name
        adb.upload(media,remote_image)
        backup_dir=work/'xml_backups'
        backup_dir.mkdir(parents=True,exist_ok=True)
        if original is not None:
            local_backup=backup_dir/(item.system+'_'+stamp+'.xml')
            local_backup.write_bytes(original)
            remote_backup=xml_remote+'.knulli-autoscraper-'+stamp+'.bak'
            adb.shell('cp '+core.sq(xml_remote)+' '+core.sq(remote_backup))
            if not adb.exists(remote_backup):raise RuntimeError('Backup not confirmed; XML write aborted')
        local_xml=tmp/'updated.xml';local_xml.write_bytes(changed)
        adb.upload(local_xml,xml_remote)
        return image_rel


def process_selected(adb,config,items:list[RomItem], overrides:dict,
                     progress:Callable[[int,int,RomItem,str,str],None]|None=None,
                     engine=None) -> list[dict]:
    """Only caller-selected games processed; existing image never causes a skip."""
    root_dir=config.get('remote_root','/userdata/roms').rstrip('/')
    work=HERE/'work';work.mkdir(parents=True,exist_ok=True)
    if engine is None:
        exe=legacy.find_engine(config.get('skyscraper_path',''))
        ini=legacy.engine_ini(config,work)
        engine=legacy.SkyscraperEngine(exe,ini,config.get('engine_timeout_seconds',240))
    aliases=core.load_aliases(HERE/'aliases.json')
    wiki_cache=load_json(work/'wikidata_titles_cache.json',{})
    report=[]
    for i,item in enumerate(items,1):
        row={'rom':item.rel,'system':item.system,'status':'working'}
        report.append(row)
        if progress:progress(i,len(items),item,'진행 중','')
        try:
            if item.xml_problem:
                raise RuntimeError('기존 gamelist.xml 오류로 안전하게 건너뜀: '+item.xml_problem)
            platform=legacy.PLATFORMS.get(item.system)
            if not platform:
                row['status']='unsupported_platform';continue
            size=adb.stat_size(item.remote)
            if size > int(config.get('max_rom_transfer_mb',256))*1024*1024:
                row['status']='rom_too_large';continue
            with tempfile.TemporaryDirectory(prefix='knulli_rom_') as td:
                stage=Path(td);(stage/'roms').mkdir()
                local_rom=stage/'roms'/PurePosixPath(item.rel).name
                adb.pull(item.remote,local_rom)
                if local_rom.stat().st_size!=size:raise RuntimeError('ROM byte count mismatch; no writes')
                manual=(overrides.get(item.rel) or '').strip()
                internal=None
                if item.system=='gba':
                    try:internal=adb.gba_internal_name(item.remote)
                    except Exception:pass
                wiki=[]
                if config.get('use_wikidata',True) and not manual and not aliases.get(core.norm(item.stem)) and re.search(r'[가-힣]',item.stem):
                    wiki=core.wikidata_title(item.stem,wiki_cache)
                candidates=legacy.normalized_candidates(item.stem,aliases,internal,wiki)
                if manual:
                    candidates=[manual]+[s for s in candidates if core.norm(s)!=core.norm(manual)]
                row['candidates']=candidates
                result=engine.scrape(stage,platform,local_rom,candidates)
                media,title,reason=result
                if media is None:
                    row['status']='unmatched';row['note']=reason;continue
                data=media.read_bytes()
                ext=legacy.image_extension(data)
                if not ext:
                    row['status']='invalid_media';continue
                row['matched_title']=title;row['reason']=reason
                rel=_device_apply(adb,root_dir,item,media,ext,work)
                row['image']=rel;row['status']='applied'
                item.resource_paths['image']=root_dir+'/'+item.system+'/'+rel.removeprefix('./')
                item.image_exists=True;item.metadata['image']=rel
        except Exception as e:
            row['status']='error';row['note']=str(e)[:400]
        finally:
            if progress:progress(i,len(items),item,row['status'],row.get('note',''))
            core.json_write(work/'last_report.json',report)
    core.json_write(work/'wikidata_titles_cache.json',wiki_cache)
    return report


def sync_korean_names(adb, config:dict, items:list[RomItem], work:Path|None=None) -> int:
    """Align KNULLI's <name> with a Korean ROM stem for renameable single-file games.

    Runs once after discovery, grouped by system. Never touches ROM files or
    protected archive names. Every changed XML is backed up on PC and device.
    Only an existing non-Korean <name> is overwritten. Customized Korean
    names and image/desc/etc are preserved.
    """
    from manager import SINGLE_FILE, _read_xml, _check_unmodified, _backup_and_write
    import re
    root=config.get('remote_root','/userdata/roms').rstrip('/')
    work=Path(work or HERE/'work')
    systems={}
    for item in items:
        if item.xml_problem or not re.search(r'[가-힣]',item.stem):
            continue
        if item.system not in SINGLE_FILE.get(PurePosixPath(item.rel).suffix.lower(),set()):
            continue
        # Only existing, mismatched XML names require repair.
        if not item.metadata.get('name') or re.search(r'[가-힣]',item.metadata['name']):
            continue
        systems.setdefault(item.system,[]).append(item)
    total=0
    for system,group in systems.items():
        sysdir=root+'/'+system
        original,xml=_read_xml(adb,sysdir)
        if original is None:
            continue
        changed=[]
        for item in group:
            rel='./'+PurePosixPath(*PurePosixPath(item.rel).parts[1:]).as_posix()
            entry=core.find_entry(xml,rel)
            if entry is None:continue
            node=entry.find('name')
            if node is None or re.search(r'[가-힣]',node.text or ''):continue
            node.text=item.stem
            changed.append(item)
        if not changed:continue
        updated=core.xml_bytes(xml)
        if updated==original:continue
        _check_unmodified(adb,sysdir,original)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        _backup_and_write(adb,sysdir,original,updated,work,stamp)
        for item in changed:
            item.metadata['name']=item.stem
            item.display=item.stem
        total+=len(changed)
    return total


def refresh_item(adb:core.Adb, config:dict, previous:RomItem) -> RomItem:
    """Refresh one finished ROM, without re-scanning the whole device.

    Invoked by the work thread after each ROM is applied, then sent to GUI.
    """
    from dataclasses import replace
    root=config.get('remote_root','/userdata/roms').rstrip('/')
    item=replace(previous,metadata={},resource_paths={},existing_resources=set(),image_exists=False,
                 xml_problem='',details='',status='')
    remote=root+'/'+item.system+'/gamelist.xml'
    if adb.exists(remote):
        with tempfile.TemporaryDirectory(prefix='knulli_one_') as td:
            local=Path(td)/'gamelist.xml';adb.pull(remote,local)
            doc=core.parse_xml(local.read_bytes())
        rel='./'+PurePosixPath(*PurePosixPath(item.rel).parts[1:]).as_posix()
        node=core.find_entry(doc,rel)
        if node is not None:
            item.metadata={k:(node.findtext(k) or '').strip() for k in METADATA}
            item.display=item.metadata.get('name') or item.stem
            for k in RESOURCES:
                p=remote_media_path(root,item.system,item.metadata.get(k,''))
                if p:item.resource_paths[k]=p
    if item.resource_paths:
        paths=list(item.resource_paths.values())
        checks=(adb.exists_many(paths) if hasattr(adb,'exists_many')
                else {p:adb.exists(p) for p in paths})
        item.existing_resources={k for k,p in item.resource_paths.items() if checks.get(p,False)}
        item.image_exists='image' in item.existing_resources
    item.status='데이터 있음' if item.has_data else '데이터 없음'
    return item
