"""System-scoped Korean -> English result memory. Never learn from failed guesses."""
from pathlib import Path
from datetime import datetime, timezone
import core


def key(system, stem):
    return str(system).lower() + '::' + core.norm(stem)


def load(path):
    try:
        import json
        d=json.loads(Path(path).read_text(encoding='utf-8'))
        return d if isinstance(d,dict) else {}
    except (ValueError,OSError):
        return {}


def lookup(db, system, stem):
    item=db.get(key(system,stem),{})
    result=item.get('english','') if isinstance(item,dict) else ''
    return result if isinstance(result,str) and len(result)<160 else ''


def learn(db,system,stem,english,source='verified_scrape'):
    english=str(english).strip()
    if not english or len(english)>150 or not any(c.isascii() and c.isalpha() for c in english):
        return False
    db[key(system,stem)]={'korean':stem,'english':english,'system':system,
                          'source':source, 'updated':datetime.now(timezone.utc).isoformat()}
    return True


def migrate(db,system,old_stem,new_stem):
    old=key(system,old_stem)
    if old in db:
        entry=dict(db.pop(old))
        entry['korean']=new_stem
        db[key(system,new_stem)]=entry
