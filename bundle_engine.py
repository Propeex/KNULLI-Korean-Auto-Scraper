"""Selected Skyscraper resources and metadata -> safe KNULLI gamelist patch.

Use a single temporary per-ROM staging area. Generated metadata is the source of
truth: unavailable resources are reported as missing, never invented.
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import tempfile
import xml.etree.ElementTree as ET

import core
import backend
import scrape_options
import learned_titles
import user_data
import legacy_bridge as legacy
import portmaster
import rom_staging
import multidisc

MEDIA_TAGS=('image','thumbnail','marquee','fanart','video','manual','boxback')
TEXT_TAGS=('desc','rating','releasedate','genre','developer','publisher','players')
FIELD_DEFAULT=['image','thumbnail','marquee','desc','rating','releasedate','genre','developer','publisher','players']
FIELD_LABEL={
    'image':'대표 이미지 / 스크린샷 합성',
    'thumbnail':'게임 박스 / 표지 (Cover)',
    'marquee':'게임 로고 (Wheel)',
    'video':'게임 플레이 영상',
    'desc':'게임 설명','rating':'커뮤니티 평점','releasedate':'출시일',
    'genre':'장르','developer':'개발사','publisher':'배급사','players':'지원 인원',
    'manual':'게임 매뉴얼 (현재 구버전 엔진 미지원)',
    'fanart':'팬아트 (현재 구버전 엔진 미지원)',
    'boxback':'박스 뒷면 (현재 구버전 엔진 미지원)',
}
# The bundled Windows 3.6.12 build predates Skyscraper 3.12 manual and
# 3.18 fanart/backcover additions. Don't promise downloaded data it cannot supply.
LEGACY_UNAVAILABLE={'manual','fanart','boxback'}
MAX_MEDIA_BYTES={'image':18_000_000,'thumbnail':18_000_000,'marquee':18_000_000,
                 'fanart':20_000_000,'boxback':20_000_000,
                 'video':180_000_000,'manual':80_000_000}
SUPPORTED_SUFFIX={
    'image':{'.png','.jpg','.jpeg','.webp'},'thumbnail':{'.png','.jpg','.jpeg','.webp'},
    'marquee':{'.png','.jpg','.jpeg','.webp'},'fanart':{'.png','.jpg','.jpeg','.webp'},
    'boxback':{'.png','.jpg','.jpeg','.webp'},'video':{'.mp4','.mkv','.avi'},'manual':{'.pdf'},
}

def chosen(config):
    if config.get('knulli_scraper') is not None:
        return scrape_options.selection(config)
    raw=config.get('scrape_fields',FIELD_DEFAULT)
    if not isinstance(raw,list):return list(FIELD_DEFAULT)
    return [x for x in raw if x in FIELD_LABEL and x not in LEGACY_UNAVAILABLE]


def export_path(stage:Path, xml_path:Path, raw:str, key:str):
    if not raw or '\x00' in raw:return None
    p=Path(raw.replace('\\','/'))
    attempts=[p] if p.is_absolute() else [xml_path.parent/p,stage/'roms'/p,
                  xml_path.parent/'media'/p,xml_path.parent/'media'/p.name]
    for attempt in attempts:
        try:out=attempt.resolve(strict=True)
        except (OSError,RuntimeError):continue
        if not out.is_file() or not out.is_relative_to(stage.resolve()):continue
        if out.suffix.lower() not in SUPPORTED_SUFFIX[key]:continue
        if out.stat().st_size>MAX_MEDIA_BYTES[key] or out.stat().st_size<16:continue
        return out
    return None


class DetailedEngine(legacy.SkyscraperEngine):
    def scrape_detail(self, stage:Path,platform,romfile,terms, wanted, name_only=False):
        base=['-p',platform,'-i',stage/'roms','-c',self.ini,
              '-a',getattr(self,'artwork_path',legacy.HERE/'artwork.xml'),'-t','1']
        region=getattr(self,'region','')
        if region:base.extend(['--region',region])
        out=stage/'export';out.mkdir(exist_ok=True)
        last='검색 결과가 없거나 유효한 데이터를 찾지 못했습니다.'
        # For a large disc we have only a synthetic filename carrier.
        # NEVER hash-search that fake file. Force --query romnom each time.
        attempts=list(terms[:6]) if name_only else [None]+list(terms[:6])
        if name_only and not attempts:
            return None,'대용량 디스크 이름 검색어가 없어 안전하게 건너뜁니다.'
        for term in attempts:
            (out/'gamelist.xml').unlink(missing_ok=True)
            param=base+['-s','screenscraper','-m','85']
            if term:
                from urllib.parse import quote_plus
                param+=['--query','romnom='+quote_plus(term)]
            param.append(romfile)
            success,msg=self._run(param)
            if not success:
                last='검색: '+msg[-300:];continue
            ok,msg2=self._run(base+['-g',out,'-o',out/'media',
                                       '--flags','unattend',romfile])
            if not ok:
                last='결과 생성: '+msg2[-300:];continue
            xml_file=out/'gamelist.xml'
            if not xml_file.is_file():
                last='gamelist.xml 내보내기 실패';continue
            try:
                tree=core.parse_xml(xml_file.read_bytes())
                games=tree.findall('game')
                if len(games)!=1:raise ValueError('한 게임의 XML이 아닙니다')
                entry=games[0]
                title=(entry.findtext('name') or '').strip()
            except Exception as exc:
                last='결과 XML 문제: '+str(exc);continue
            if term and legacy.text_score(term,title)<0.78:
                last='영문 검색어와 반환 게임명이 다름: '+title;continue
            if not term and (not terms or max(legacy.text_score(x,title) for x in terms)<0.78):
                last='게임명 검증 실패: '+title;continue
            found={};files={}
            for key in wanted:
                if key in TEXT_TAGS:
                    val=(entry.findtext(key) or '').strip()
                    if val:found[key]=val
                elif key in MEDIA_TAGS:
                    value=(entry.findtext(key) or '').strip()
                    p=export_path(stage,xml_file,value,key) if value else None
                    if p:files[key]=p
            if not found and not files:
                last='선택한 자원이 결과에 없음 (검색명: '+title+')';continue
            return {'name':title,'metadata':found,'media':files,'source':'manual title' if term else 'hash/title'},last
        return None,last


def engine_config(config,work,selection):
    path=legacy.engine_ini(config,work)
    # Actual media output and downloading is handled by upstream Skyscraper;
    # toggles only request capabilities that exist in Windows v3.6.12.
    content=path.read_text(encoding='utf-8')
    content=content.replace('[main]\n','[main]\nvideos="'+('true' if 'video' in selection else 'false')+'"\n',1)
    path.write_text(content,encoding='utf-8')
    return path


def safe_apply(adb,item,found,selected,root='/userdata/roms',work=None):
    """Atomic gamelist upload after new media files are uploaded with unique names.

    Existing paths and fields not selected remain unchanged. No
    persistent scraper-data XML backups are created.
    """
    work=Path(work or backend.HERE/'work')
    sysdir=root.rstrip('/')+'/'+item.system
    remote_xml=sysdir+'/gamelist.xml'
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    from manager import _read_xml, _check_unmodified
    original,xml=_read_xml(adb,sysdir)
    rel='./'+PurePosixPath(*PurePosixPath(item.rel).parts[1:]).as_posix()
    entry=core.find_entry(xml,rel)
    if entry is None:
        entry=ET.SubElement(xml,'game');ET.SubElement(entry,'path').text=rel
        ET.SubElement(entry,'name').text=PurePosixPath(item.rel).stem
    # English Skyscraper search titles are NEVER used for KNULLI display.
    # For Korean single-file ROMs, the filename (without extension) owns <name>.
    # Protected archives keep the user's custom <name> / display name.
    from manager import SINGLE_FILE
    prefs=scrape_options.options(found.get('_config',{}))
    touched=False
    applied_fields=[]
    renameable=item.system in SINGLE_FILE.get(PurePosixPath(item.rel).suffix.lower(),set())
    if renameable and re.search(r'[가-힣]',item.stem):
        name=entry.find('name')
        if name is None:name=ET.SubElement(entry,'name')
        if name.text!=item.stem and not re.search(r'[가-힣]',name.text or ''):
            name.text=item.stem
            touched=True
            applied_fields.append('name')
    for key,val in found.get('metadata',{}).items():
        if key not in selected or key not in TEXT_TAGS:continue
        if key=='desc' and not prefs['overwrite_descriptions'] and (entry.findtext(key) or '').strip():continue
        if len(val)>10000:continue
        target=entry.find(key)
        if target is not None and (target.text or '')==val:continue
        if target is None:target=ET.SubElement(entry,key)
        target.text=val
        touched=True;applied_fields.append(key)
    uploads=[]
    for key,source in found.get('media',{}).items():
        if key not in selected or key not in MEDIA_TAGS:continue
        if not prefs['overwrite_medias'] and (entry.findtext(key) or '').strip():
            old_path=backend.remote_media_path(root,item.system,(entry.findtext(key) or '').strip())
            if old_path and adb.exists(old_path):continue
            # A stale XML path does not count as an existing media file.

        suffix=source.suffix.lower()
        new_name='auto-'+hashlib.sha256(item.rel.encode()).hexdigest()[:16]+'-'+stamp+'-'+key+suffix
        folder='videos' if key=='video' else ('manuals' if key=='manual' else 'images')
        path='./'+folder+'/'+new_name
        dest=sysdir+'/'+folder+'/'+new_name
        uploads.append((source,dest))
        touched=True;applied_fields.append(key)
        node=entry.find(key)
        if node is None:node=ET.SubElement(entry,key)
        node.text=path
    if not touched:return {'fields':[],'updated':False}
    updated=core.xml_bytes(xml)
    if updated==original:return {'fields':[],'updated':False}
    _check_unmodified(adb,sysdir,original)
    # First upload fresh uniquely named resources; old referenced resources are untouched.
    for local,remote in uploads:adb.upload(local,remote)
    # Concurrency guard following media transfer.
    _check_unmodified(adb,sysdir,original)
    from manager import _write_xml
    _write_xml(adb,sysdir,updated)
    return {'fields':applied_fields,'updated':True}


def process_selected(adb,config,items,overrides,progress=None, engine=None):
    # ScreenScraper credentials are passed through a short-lived private INI.
    # They are never left in the installed program folder after a normal run.
    with tempfile.TemporaryDirectory(prefix='knulli_auth_') as secret_dir:
        return _process_selected(adb,config,items,overrides,progress,engine,Path(secret_dir))


def _process_selected(adb,config,items,overrides,progress=None, engine=None,secret_dir=None):
    selection=chosen(config)
    work=backend.HERE/'work';work.mkdir(exist_ok=True)
    if engine is None and any(item.system!='ports' for item in items):
        exe=legacy.find_engine(config.get('skyscraper_path',''))
        ini=engine_config(config,secret_dir or work,selection)
        engine=DetailedEngine(exe,ini,config.get('engine_timeout_seconds',240))
        artwork_path=work/'artwork_selected.xml'
        artwork_path.write_bytes(scrape_options.recipe(config))
        engine.artwork_path=artwork_path
        engine.region=scrape_options.options(config).get('preferred_region','')
    aliases=core.load_aliases(backend.HERE/'aliases.json')
    learned=user_data.load_titles()
    wiki_cache=backend.load_json(work/'wikidata_titles_cache.json',{})
    report=[]
    # PortMaster already ships local manifests and artwork; no ScreenScraper
    # search, launcher transfer, or handheld Internet is necessary.
    ports=[item for item in items if item.system=='ports']
    port_catalog={}
    port_error=''
    if ports:
        try:
            port_catalog=portmaster.load_ports(
                adb,config.get('remote_root','/userdata/roms'),
                [item.rel for item in ports])
        except Exception as exc:
            port_error=str(exc)[:250]
    for i,item in enumerate(items,1):
        rec={'rom':item.rel,'system':item.system,'status':'working'};report.append(rec)
        if progress:progress(i,len(items),item,'진행 중','')
        try:
            if item.xml_problem:raise RuntimeError('기존 XML 읽기 실패: '+item.xml_problem)
            if item.system=='ports':
                if port_error:
                    raise RuntimeError('PortMaster 정보 확인 실패: '+port_error)
                applied=portmaster.apply_one(adb,item,config,port_catalog,selection)
                rec.update(applied)
                continue
            platform=legacy.PLATFORMS.get(item.system)
            if not platform:rec['status']='unsupported_platform';continue
            size=adb.stat_size(item.remote)
            with tempfile.TemporaryDirectory(prefix='knulli_rom_') as tmp:
                stage=Path(tmp);(stage/'roms').mkdir()
                local=stage/'roms'/PurePosixPath(item.rel).name
                name_only=rom_staging.prepare(
                    adb,item.remote,local,size,
                    int(config.get('max_rom_transfer_mb',256))) or item.rel.lower().endswith('.m3u')
                rec['lookup']='name_only' if name_only else 'hash_or_name'
                manual=(overrides.get(item.rel) or '').strip()
                learned_term=learned_titles.lookup(learned,item.system,item.stem)
                internal=adb.gba_internal_name(item.remote) if item.system=='gba' else None
                wiki=[]
                if config.get('use_wikidata',True) and not manual and not aliases.get(core.norm(item.stem)) and re.search('[가-힣]',item.stem):
                    wiki=core.wikidata_title(item.stem,wiki_cache)
                source_stem=multidisc.clean_title(item.stem) if item.system=='psx' else item.stem
                terms=legacy.normalized_candidates(source_stem,aliases,internal,wiki)
                prior=manual or learned_term
                if prior:terms=[prior]+[s for s in terms if core.norm(s)!=core.norm(prior)]
                rec['candidates']=terms
                if name_only:
                    result,reason=engine.scrape_detail(
                        stage,platform,local,terms,selection,name_only=True)
                else:
                    result,reason=engine.scrape_detail(stage,platform,local,terms,selection)
                if result is None:
                    rec['status']='unmatched';rec['note']=reason;continue
                result['_config']=config
                applied=safe_apply(adb,item,result,selection,config.get('remote_root','/userdata/roms'),work)
                rec['status']='applied' if applied['updated'] else 'unchanged'
                rec['matched_title']=result['name']
                if learned_titles.learn(learned,item.system,item.stem,result['name']):
                    user_data.save_titles(learned)
                rec['fields']=applied['fields']
                rec['unavailable']=[x for x in selection if x not in applied['fields']]
        except ValueError as exc:
            if str(exc).startswith('rom_too_large:'):
                rec['status']='rom_too_large'
                rec['note']=str(exc).removeprefix('rom_too_large:').strip()[:400]
            else:
                rec['status']='error';rec['note']=str(exc)[:400]
        except Exception as exc:
            rec['status']='error';rec['note']=str(exc)[:400]
        finally:
            if progress:progress(i,len(items),item,rec['status'],rec.get('note',''))
            core.json_write(work/'last_report.json',report)
    core.json_write(work/'wikidata_titles_cache.json',wiki_cache)
    return report
