import shlex
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import backend
import core
import manager
import bundle_engine
import setup_platform_tools

PNG=b'\x89PNG\r\n\x1a\n'+b'fakeimagepayload'

class FakeADB:
    def __init__(self):
        self.files={
            '/userdata/roms/gba/마더 3.gba':b'ROM',
            '/userdata/roms/gba/젤다 & 검.gba':b'ZELDA',
            '/userdata/roms/gba/images/마더 3-image.png':PNG,
            '/userdata/roms/gba/images/마더 3-wheel.png':PNG,
            '/userdata/roms/gba/gamelist.xml':('''<?xml version="1.0"?><gameList>
              <game><path>./마더 3.gba</path><name>마더 3</name>
              <image>./images/마더 3-image.png</image>
              <thumbnail>./images/마더 3-image.png</thumbnail>
              <marquee>./images/마더 3-wheel.png</marquee>
              <desc>기존 설명</desc></game>
              <game><path>./젤다 &amp; 검.gba</path><name>젤다 &amp; 검</name></game>
              </gameList>''').encode('utf-8')
        }
        self.uploads=[]
        self.fail_xml=False
    def shell(self,cmd,timeout=60):
        parts=shlex.split(cmd)
        if parts[:2]==['if','[']:
            return 'YES' if any(x in cmd for x in []) else (
                'YES' if parts[2]=='-e' and parts[3] in self.files else '')
        if parts and parts[0]=='cp':
            self.files[parts[2]]=self.files[parts[1]]
        if parts and parts[0]=='mv':
            self.files[parts[2]]=self.files.pop(parts[1])
        return ''
    def exists(self,path):return path in self.files
    def pull(self,remote,local):local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(self.files[remote])
    def upload(self,source,remote):
        if remote.endswith('gamelist.xml') and self.fail_xml:raise RuntimeError('simulated upload fail')
        self.uploads.append(remote);self.files[remote]=source.read_bytes()
    def stat_size(self,path):return len(self.files[path])
    def gba_internal_name(self,path):return None

class TestChanges(unittest.TestCase):
    def _item(self):
        return backend.RomItem('/userdata/roms/gba/마더 3.gba','gba/마더 3.gba','gba','마더 3')
    def _entry(self,db,path):
        return core.find_entry(core.parse_xml(db.files['/userdata/roms/gba/gamelist.xml']),path)
    def test_rename_rom_and_both_media_references(self):
        db=FakeADB();item=self._item()
        with tempfile.TemporaryDirectory() as tmp:
            plan=manager.rename_rom(db,item,'마더 III.gba',work=Path(tmp))
            self.assertIn('/userdata/roms/gba/마더 III.gba',db.files)
            self.assertNotIn(item.remote,db.files)
            self.assertIn('/userdata/roms/gba/images/마더 III-image.png',db.files)
            entry=self._entry(db,'./마더 III.gba')
            self.assertEqual(entry.findtext('name'),'마더 III')
            self.assertEqual(entry.findtext('thumbnail'),'./images/마더 III-image.png')
            self.assertEqual(entry.findtext('image'),'./images/마더 III-image.png')
            self.assertEqual(entry.findtext('desc'),'기존 설명')
            self.assertTrue(list((Path(tmp)/'rename_journal').glob('*.json')))
            self.assertFalse((Path(tmp)/'xml_backups').exists())
            self.assertEqual(len({x[1:3] for x in plan['moves']}),2)
    def test_rename_does_not_modify_hash_named_media(self):
        db=FakeADB();item=self._item()
        root=core.parse_xml(db.files['/userdata/roms/gba/gamelist.xml'])
        core.find_entry(root,'./마더 3.gba').find('image').text='./images/auto-9a8b.png'
        plan=manager.plan_rename(item,'마더 III.gba',root)
        self.assertFalse(any(x[0]=='image' for x in plan['moves']))
    def test_disallow_arcade_and_disc_and_extension_change(self):
        for name,sys in [('mslug.zip','neogeo'),('disc.cue','psx'),('multi.chd','psx')]:
            with self.assertRaises(ValueError):manager.validate_name(name,'edited'+Path(name).suffix,sys)
        with self.assertRaises(ValueError):manager.validate_name('마더 3.gba','마더 3.sfc','gba')
    def test_rename_target_collision_safe(self):
        db=FakeADB(); db.files['/userdata/roms/gba/마더 III.gba']=b'OTHER'
        old=dict(db.files)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                manager.rename_rom(db,self._item(),'마더 III.gba',work=Path(tmp))
        self.assertEqual(db.files,old)
    def test_rename_xml_failed_rolls_back_files(self):
        db=FakeADB();db.fail_xml=True
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):manager.rename_rom(db,self._item(),'마더 III.gba',work=Path(tmp))
        self.assertIn('/userdata/roms/gba/마더 3.gba',db.files)
        self.assertIn('/userdata/roms/gba/images/마더 3-image.png',db.files)
    def test_update_metadata_preserves_rom_and_other_entry(self):
        db=FakeADB();old=db.files['/userdata/roms/gba/마더 3.gba']
        with tempfile.TemporaryDirectory() as tmp:
            manager.update_metadata(db,self._item(),{'desc':'새로운 설명','rating':'0.85','name':'마더 3'},work=Path(tmp))
        self.assertEqual(db.files['/userdata/roms/gba/마더 3.gba'],old)
        self.assertEqual(self._entry(db,'./마더 3.gba').findtext('rating'),'0.85')
        self.assertEqual(self._entry(db,'./젤다 & 검.gba').findtext('name'),'젤다 & 검')
    def test_scrape_multiple_resources_with_selection_and_backup(self):
        db=FakeADB();item=self._item()
        with tempfile.TemporaryDirectory() as tmp:
            pic=Path(tmp)/'image.png';pic.write_bytes(PNG)
            box=Path(tmp)/'box.png';box.write_bytes(PNG)
            result=bundle_engine.safe_apply(db,item,{
                'name':'Mother 3',
                'metadata':{'desc':'스크랩 설명','rating':'0.95','genre':'Role-Playing'},
                'media':{'image':pic,'thumbnail':box}
            },['thumbnail','rating','genre'],work=Path(tmp))
            entry=self._entry(db,'./마더 3.gba')
            self.assertEqual(entry.findtext('image'),'./images/마더 3-image.png')
            self.assertEqual(entry.findtext('desc'),'기존 설명')
            self.assertEqual(entry.findtext('name'),'마더 3')
            self.assertIn('-thumbnail.',entry.findtext('thumbnail'))
            self.assertEqual(entry.findtext('rating'),'0.95')
            self.assertEqual(entry.findtext('genre'),'Role-Playing')
            self.assertEqual(set(result['fields']),{'thumbnail','rating','genre'})
            self.assertFalse(any('.knulli-autoscraper-' in k and k.endswith('.bak') for k in db.files))
    def test_unavailable_media_not_selected(self):
        config={'scrape_fields':['image','manual','fanart','boxback','video','desc']}
        self.assertEqual(bundle_engine.chosen(config),['image','video','desc'])
    def test_platform_install_detection_from_adb_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'adb.exe';path.write_bytes(b'fake')
            self.assertEqual(setup_platform_tools.existing_adb({'adb_path':str(path)}),str(path))

if __name__=='__main__':unittest.main()

class TestSkyscraperXML(unittest.TestCase):
    def test_generated_metadata_and_multiple_images(self):
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td);(stage/'roms').mkdir()
            rom=stage/'roms'/'마더 3.gba';rom.write_bytes(b'rom')
            engine=bundle_engine.DetailedEngine('Skyscraper.exe',stage/'config.ini')
            calls=[]
            def generator(args):
                calls.append(args)
                if '-g' in args:
                    out=stage/'export';(out/'media').mkdir(parents=True,exist_ok=True)
                    (out/'media'/'image.png').write_bytes(PNG)
                    (out/'media'/'cover.png').write_bytes(PNG)
                    (out/'gamelist.xml').write_text('''<gameList><game>
                      <name>Mother 3</name><desc>A game</desc><rating>0.87</rating>
                      <image>./media/image.png</image><thumbnail>./media/cover.png</thumbnail>
                      </game></gameList>''',encoding='utf-8')
                return True,'ok'
            engine._run=generator
            results,reason=engine.scrape_detail(stage,'gba',rom,['Mother 3'],
                                                 ['image','thumbnail','desc','rating'])
            self.assertEqual(results['metadata']['desc'],'A game')
            self.assertIn('thumbnail',results['media'])
            self.assertEqual(results['media']['image'].read_bytes(),PNG)
            self.assertTrue(calls)
            self.assertTrue(all('-a' in a for a in calls))
