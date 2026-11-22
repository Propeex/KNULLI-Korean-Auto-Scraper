#!/usr/bin/env python3
"""KNULLI ADB -> Skyscraper CLI -> KNULLI. No custom ScreenScraper API credentials.

Dry-run by default. Writes ONLY ./images/auto-* and gamelist.xml (with backup), never ROMs.
"""
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
import xml.etree.ElementTree as ET

import core

HERE = Path(__file__).resolve().parent
# Explicit platform names supported by tested Skyscraper versions; unsupported systems skipped.
# This map can be extended later without changing the application.
PLATFORMS = {
    'nes':'nes','snes':'snes','gb':'gb','gbc':'gbc','gba':'gba',
    'n64':'n64','nds':'nds','megadrive':'megadrive','mastersystem':'mastersystem',
    'gamegear':'gamegear','pcengine':'pcengine','psx':'psx','psp':'psp',
    'saturn':'saturn','dreamcast':'dreamcast','sega32x':'sega32x',
    'segacd':'segacd','mame':'mame','fbneo':'fba','neogeo':'neogeo','atomiswave':'atomiswave',
    'atari2600':'atari2600','atari7800':'atari7800','ngp':'ngp','ngpc':'ngpc',
    'wswan':'wonderswan','wswanc':'wonderswanc',
}
# Ambiguous names on certain legacy Skyscraper builds may need a platform override.


def find_engine(explicit=''):
    possible=[]
    if explicit:
        p=Path(explicit).expanduser()
        possible.append(p if p.is_absolute() else HERE / p)
    possible += [HERE/'Skyscraper.exe', HERE/'skyscraper.exe',
                 HERE/'skyscraper'/'Skyscraper.exe', HERE/'skyscraper'/'skyscraper.exe',
                 HERE/'Skyscraper'/'Skyscraper.exe']
    base=HERE/'skyscraper'
    if base.is_dir():
        possible += list(base.rglob('Skyscraper.exe'))+list(base.rglob('skyscraper.exe'))
    # Reuse engine from the user's prior v0.4 installation without copying binaries.
    for sibling in (HERE.parent/'knulli_auto_scraper_v05', Path.home()/'Desktop'/'knulli_auto_scraper_v05',
                    HERE.parent/'knulli_auto_scraper_v04', Path.home()/'Desktop'/'knulli_auto_scraper_v04',
                    HERE.parent/'knulli_auto_scraper_v06', Path.home()/'Desktop'/'knulli_auto_scraper_v06'):
        if (sibling/'skyscraper').is_dir():
            possible += list((sibling/'skyscraper').rglob('Skyscraper.exe'))
    for p in possible:
        if p.is_file(): return str(p.resolve())
    for candidate in ('Skyscraper.exe','skyscraper.exe','Skyscraper','skyscraper'):
        found=shutil.which(candidate)
        if found:return found
    raise RuntimeError('Skyscraper.exe not found. Install the official upstream Windows release beside this file '
                       'or set skyscraper_path in config.json. Developer ID is NOT required.')


def engine_ini(config, work):
    """Write a program-private INI; never print credentials in subprocess arguments."""
    ss=config.get('screenscraper_account',{})
    user=(ss.get('user') or '').strip()
    passwd=ss.get('password') or ''
    # API supports anonymous use; credentials can optionally be supplied once locally.
    work.mkdir(parents=True,exist_ok=True)
    path=work/'skyscraper_config.ini'
    if '\n' in user+passwd or '\r' in user+passwd or '"' in user+passwd:
        raise ValueError('ScreenScraper account contains characters unsafe for Skyscraper config.ini')
    content='[main]\n'  # standard default values; no forced output changes
    if user or passwd:
        if not (user and passwd):
            raise ValueError('To use a ScreenScraper account, provide both user and password; or leave both empty')
        content+='\n[screenscraper]\nuserCreds="'+user+':'+passwd+'"\n'
    path.write_text(content,encoding='utf-8')
    return path


def text_score(a,b):
    aa=core.norm(a);bb=core.norm(b)
    if not aa or not bb:return 0
    return SequenceMatcher(None,aa,bb).ratio()


def normalized_candidates(stem, aliases, gba_title=None, wiki=None):
    # Alias dictionary has precedence; do not take arbitrary literal Korean translation.
    names=list(aliases.get(core.norm(stem),[]))
    if gba_title:names.append(gba_title)
    if re.search(r'[A-Za-z]',stem):
        names.append(re.sub(r'\([^)]*\)|\[[^]]*\]',' ',stem).strip())
    if wiki:names.extend(wiki)
    unique=[];seen=set()
    for s in names:
        n=core.norm(s)
        if n and n not in seen and re.search('[A-Za-z]',s):
            seen.add(n);unique.append(s)
    return unique[:8]


def safe_media(stage, exported_xml):
    """Read Skyscraper XML; allow only a real media file inside this job's temp dir."""
    xml_path=stage/'export'/'gamelist.xml'
    if not xml_path.is_file():return None,None
    root=core.parse_xml(xml_path.read_bytes())
    entries=root.findall('game')
    if len(entries)!=1:return None,None
    entry=entries[0]
    image=(entry.findtext('image') or '').strip()
    name=(entry.findtext('name') or '').strip()
    if not image or '\x00' in image:return None,name
    # Skyscraper may write absolute paths or relative paths based on input directory.
    rel=Path(image.replace('\\','/'))
    possibilities = ([rel] if rel.is_absolute() else [
        stage/'export'/rel,stage/'roms'/rel,stage/'export'/'media'/rel,
        stage/'export'/'media'/rel.name])
    stage_root=stage.resolve()
    for candidate in possibilities:
        resolved=candidate.resolve()
        if resolved.is_relative_to(stage_root) and resolved.is_file() and resolved.suffix.lower() in ('.png','.jpg','.jpeg'):
            if resolved.stat().st_size<=12*1024*1024:
                return resolved,name
    return None,name


class SkyscraperEngine:
    def __init__(self, executable, ini, timeout=240):
        self.executable=executable
        self.ini=ini
        self.timeout=int(timeout)
    def _run(self,args):
        command=[self.executable]+[str(x) for x in args]
        try:
            done=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                timeout=self.timeout,cwd=str(Path(self.executable).resolve().parent),
                                env={**os.environ,'NO_COLOR':'1'},
                                creationflags=(0x08000000 if os.name=='nt' else 0))
        except (OSError,subprocess.TimeoutExpired) as e:
            return False,str(e)[:160]
        output=(done.stdout+done.stderr).decode('utf-8','replace')
        return done.returncode==0,output[-1200:]
    def scrape(self,stage,platform,romfile,terms):
        # First let Skyscraper inspect the real ROM hash. Then try known names if needed.
        # Query override is officially documented; never assume a translated title is correct.
        base=['-p',platform,'-i',stage/'roms','-c',self.ini, '-a', HERE/'artwork.xml', '-t','1']
        out=stage/'export'
        out.mkdir(exist_ok=True)
        attempts=[None]+terms[:6]
        last='no media generated'
        for idx,term in enumerate(attempts):
            if idx:
                # Clear generated XML from the prior attempt; underlying cache remains managed by Skyscraper.
                (out/'gamelist.xml').unlink(missing_ok=True)
            params=base+['-s','screenscraper','-m','85']
            if term:
                # Old Windows Skyscraper builds understand romnom= overrides.
                from urllib.parse import quote_plus
                params+=['--query','romnom='+quote_plus(term)]
            params.append(romfile)
            scraped,msg=self._run(params)
            if not scraped:
                last='scrape CLI: '+msg[-240:]
                continue
            generated,msg2=self._run(base+['-g',out,'-o',out/'media',
                                           '--flags','unattend',romfile])
            if not generated:
                last='gamelist CLI: '+msg2[-240:]
                continue
            media,title=safe_media(stage,out/'gamelist.xml')
            if not media:
                last='no image in generated gamelist'
                continue
            # Without independent title evidence, do not push a potentially wrong ROM image.
            if term:
                if text_score(term,title)<0.78:
                    last='title mismatch; skipped'
                    continue
                return media,title,'title:'+term
            # A hash-based result is not independently verifiable from the generated XML.
            # Require title alignment with trusted aliases, ROM header, or Latin stem.
            if terms and max(text_score(x,title) for x in terms)>=0.78:
                return media,title,'hash_or_title_verified'
            last='unverified hash/name result; skipped'
        return None,None,last


def image_extension(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):return '.png'
    if data.startswith(b'\xff\xd8\xff'):return '.jpg'
    return None


def read_original(adb,remote,temp):
    if not adb.exists(remote):return None
    local=temp/('xml_'+hashlib.sha1(remote.encode()).hexdigest()[:12]+'.xml')
    adb.pull(remote,local)
    return local.read_bytes()


def inspect_and_apply(adb,engine,config,apply=False):
    root=config.get('remote_root','/userdata/roms').rstrip('/')
    if not root.startswith('/') or '..' in root.split('/'):
        raise ValueError('unsafe remote ROM root')
    if adb.shell('if [ -d '+core.sq(root)+' ]; then echo YES; fi')!='YES':
        raise RuntimeError('ROM root missing: '+root)
    files=core.collect_roms(adb,root)
    print('ROM files found:',len(files),flush=True)
    if not files:raise RuntimeError('0 ROM files found; no changes made')
    work=HERE/'work';work.mkdir(exist_ok=True)
    aliases=core.load_aliases(HERE/'aliases.json')
    wiki_cache_path=work/'wikidata_titles_cache.json'
    try:wiki_cache=json.loads(wiki_cache_path.read_text(encoding='utf-8'))
    except (OSError,ValueError):wiki_cache={}
    report=[];states={};stamp=datetime.now().strftime('%Y%m%d_%H%M%S')
    with tempfile.TemporaryDirectory(prefix='knulli_bridge_') as tmp:
        tmp=Path(tmp)
        for i,(remote,rel,system) in enumerate(files,1):
            rec={'rom':rel.as_posix(),'system':system,'status':'inspect'};report.append(rec)
            print(f'[{i}/{len(files)}] {rel}',flush=True)
            folder=rel.parts[0];remote_xml=root+'/'+folder+'/gamelist.xml'
            if system not in states:
                orig=read_original(adb,remote_xml,tmp)
                try:xml=core.parse_xml(orig)
                except (ET.ParseError,ValueError):xml=None
                states[system]={'path':remote_xml,'orig':orig,'root':xml,'pending':[]}
            state=states[system]
            if state['root'] is None:rec['status']='invalid_xml';continue
            rel_xml='./'+PurePosixPath(*rel.parts[1:]).as_posix()
            entry=core.find_entry(state['root'],rel_xml)
            if entry is not None and (entry.findtext('image') or '').strip():
                rec['status']='existing_image';continue
            if not apply:rec['status']='check_only';continue
            platform=PLATFORMS.get(system)
            if not platform:rec['status']='unsupported_platform';continue
            if engine is None:rec['status']='engine_missing';continue
            # ROMs are pulled only if missing media; original remains untouched.
            try:
                size=adb.stat_size(remote)
                max_mb=int(config.get('max_rom_transfer_mb',256))
                if size>max_mb*1024*1024:
                    rec['status']='rom_too_large';continue
                localdir=tmp/('case_'+hashlib.sha1(str(rel).encode()).hexdigest()[:14]);
                (localdir/'roms').mkdir(parents=True)
                # We may need a physical copy for Skyscraper checksum-based lookup.
                local_rom=localdir/'roms'/rel.name
                adb.pull(remote,local_rom)
                if local_rom.stat().st_size!=size:raise RuntimeError('ROM byte count differs after ADB pull')
                gba_title=None
                if system=='gba':
                    try:gba_title=adb.gba_internal_name(remote)
                    except Exception:pass
                wiki=[]
                if (not aliases.get(core.norm(rel.stem)) and
                    bool(config.get('use_wikidata',True)) and re.search('[가-힣]',rel.stem)):
                    wiki=core.wikidata_title(rel.stem,wiki_cache)
                terms=normalized_candidates(rel.stem,aliases,gba_title,wiki)
                rec['candidates']=terms
                media,exported_title,reason=engine.scrape(localdir,platform,local_rom,terms)
                if not media:
                    rec['status']='unmatched';rec['note']=reason;continue
                data=media.read_bytes();ext=image_extension(data)
                if not ext:
                    rec['status']='invalid_media';continue
                new_name='auto-'+hashlib.sha256(str(rel).encode('utf-8')).hexdigest()[:24]+ext
                image_rel='./images/'+new_name
                local_img=tmp/new_name
                local_img.write_bytes(data)
                rec['matched_title']=exported_title
                rec['reason']=reason
                rec['status']='staged'
                state['pending'].append((rec,rel_xml,local_img,image_rel))
            except Exception as e:
                rec['status']='error';rec['error']=str(e)[:240]
        if apply:
            for system,state in states.items():
                if not state['pending']:continue
                path=state['path']
                current=read_original(adb,path,tmp)
                if current!=state['orig']:
                    for rec,*_ in state['pending']:rec['status']='xml_changed_abort'
                    continue
                prepared=[]
                for rec,rel_xml,local_img,imgrel in state['pending']:
                    remote_img=root+'/'+system+'/'+imgrel.removeprefix('./')
                    try:
                        if not adb.exists(remote_img):
                            adb.upload(local_img,remote_img)
                        prepared.append((rec,rel_xml,imgrel))
                    except Exception as e:
                        rec['status']='upload_error';rec['error']=str(e)[:200]
                if not prepared:continue
                rootxml=core.parse_xml(state['orig'])
                for rec,rel_xml,imgrel in prepared:
                    original_title=PurePosixPath(rel_xml).stem
                    if not core.apply_entry(rootxml,rel_xml,original_title,imgrel):
                        rec['status']='existing_image'
                new_bytes=core.xml_bytes(rootxml)
                if new_bytes==state['orig']:continue
                try:
                    if state['orig'] is not None:
                        backups=work/'xml_backups';backups.mkdir(exist_ok=True)
                        backup=backups/(stamp+'_'+hashlib.sha256(path.encode()).hexdigest()[:12]+'.xml')
                        backup.write_bytes(state['orig'])
                        adb.shell('cp '+core.sq(path)+' '+core.sq(path+'.knulli-autoscraper-'+stamp+'.bak'))
                    local_xml=tmp/('install_'+hashlib.sha1(path.encode()).hexdigest()[:10]+'.xml')
                    local_xml.write_bytes(new_bytes)
                    adb.upload(local_xml,path)
                    for rec,_,_ in prepared:
                        if rec['status']=='staged':rec['status']='applied'
                    print('APPLIED:',path,flush=True)
                except Exception as e:
                    for rec,_,_ in prepared:
                        if rec['status']=='staged':rec['status']='xml_write_error';rec['error']=str(e)[:200]
    core.json_write(wiki_cache_path,wiki_cache)
    core.json_write(work/'last_report.json',report)
    print('SUMMARY:',dict(Counter(r['status'] for r in report)))
    print('REPORT:',work/'last_report.json')
    if apply:print('No KNULLI reboot performed. Game list refresh may be required.')
    return report


def main():
    arg=argparse.ArgumentParser(description='KNULLI ADB + Skyscraper CLI v0.4')
    arg.add_argument('--apply',action='store_true',help='Download/upload changes; default is inspect only')
    arg.add_argument('--config',default=str(HERE/'config.json'))
    args=arg.parse_args()
    cfg=Path(args.config)
    if not cfg.exists():
        shutil.copy2(HERE/'config.example.json',cfg)
        print('Created config.json (no developer ID needed).')
    config=json.loads(cfg.read_text(encoding='utf-8'))
    adb=core.Adb(os.environ.get('ADB_PATH') or config.get('adb_path'))
    print('CONNECTED:',adb.connect(),flush=True)
    engine=None
    if args.apply:
        path=find_engine(config.get('skyscraper_path',''))
        ini=engine_ini(config,HERE/'work')
        engine=SkyscraperEngine(path,ini,config.get('engine_timeout_seconds',240))
        print('SKYSCRAPER:',path,flush=True)
    inspect_and_apply(adb,engine,config,args.apply)

if __name__=='__main__':
    try:main()
    except (Exception,KeyboardInterrupt) as e:
        print('ERROR:',e,file=sys.stderr)
        sys.exit(1)
