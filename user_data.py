"""User-owned data, kept outside the application folder across upgrades.

Account secret lives in Windows Credential Manager, not JSON/CSV.
"""
from __future__ import annotations
import csv
import os
from pathlib import Path
import json


def data_dir() -> Path:
    override=os.environ.get('KNULLI_USER_DATA_DIR')
    if override:
        return Path(override).expanduser()
    if os.name=='nt':
        # Users can copy / edit the title map without entering the application folder.
        home=Path(os.environ.get('USERPROFILE',str(Path.home())))
        return home/'Documents'/'KNULLI Auto Scraper Data'
    return Path.home()/'Documents'/'KNULLI Auto Scraper Data'


def settings_path(): return data_dir()/'settings.json'
def overrides_path(): return data_dir()/'manual_titles.json'
def learned_path(): return data_dir()/'learned_titles.json'
def title_csv_path(): return data_dir()/'title_map.csv'


def export_title_csv(db:dict, path:Path|None=None):
    path=Path(path or title_csv_path())
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['system','korean','english','source','updated'])
        w.writeheader()
        for row in sorted(db.values(),key=lambda x:(str(x.get('system','')),str(x.get('korean','')))):
            if isinstance(row,dict):w.writerow({k:row.get(k,'') for k in w.fieldnames})
    tmp.replace(path)


def import_title_csv(path:Path|None=None):
    """CSV can also be edited by the user outside this program."""
    from learned_titles import key
    path=Path(path or title_csv_path())
    db={}
    if not path.exists():return db
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            system=(row.get('system') or '').strip(); korean=(row.get('korean') or '').strip()
            english=(row.get('english') or '').strip()
            if system and korean and english:
                db[key(system,korean)]={'system':system,'korean':korean,'english':english,
                                          'source':row.get('source','csv'),'updated':row.get('updated','')}
    return db


def load_titles():
    from learned_titles import load
    p=learned_path()
    db=load(p)
    # First run after upgrade: silently import prior successful mappings.
    if not db and not p.exists():
        here=Path(__file__).resolve().parent
        candidate_dirs=[here.parent/'knulli_auto_scraper_v071',
                        here.parent/'knulli_auto_scraper_v07',
                        here.parent/'knulli_auto_scraper_v06',
                        Path.home()/'Desktop'/'knulli_auto_scraper_v071',
                        Path.home()/'Desktop'/'knulli_auto_scraper_v07']
        for old in candidate_dirs:
            old_map=old/'work'/'learned_titles.json'
            if old_map.is_file():
                db=load(old_map)
                if db:
                    save_titles(db)
                    break
    csvp=title_csv_path()
    # Prefer freshly edited CSV when present; users can reuse it independently.
    if csvp.is_file() and (not p.exists() or csvp.stat().st_mtime>p.stat().st_mtime):
        db.update(import_title_csv(csvp))
    return db


def save_titles(db):
    from core import json_write
    json_write(learned_path(),db)
    export_title_csv(db)
