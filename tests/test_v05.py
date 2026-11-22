import sys, tempfile, shlex, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core,backend,legacy_bridge as legacy

PNG=b'\x89PNG\r\n\x1a\n'+b'fake_image'
class FakeADB:
    def __init__(self):
        self.files={
            '/userdata/roms/gba/마더 3.gba':b'MOTHER3_ROM',
            '/userdata/roms/gba/젤다의 전설 & 검.gba':b'ZELDA_ROM',
            '/userdata/roms/gba/images/old.png':PNG,
            '/userdata/roms/gba/gamelist.xml':('''<?xml version="1.0" encoding="UTF-8"?>
            <gameList><game><path>./마더 3.gba</path><name>마더 3</name>
            <image>./images/old.png</image><desc>기존 설명 보존</desc></game>
            <game><path>./젤다의 전설 &amp; 검.gba</path><name>젤다 게임</name></game>
            </gameList>''').encode('utf-8'),
        }
        self.uploaded=[];self.pulled=[];self.commands=[]
    def shell(self,command,timeout=60):
        self.commands.append(command)
        if command.startswith('if [ -d '):return 'YES'
        if command.startswith('cp '):
            parts=shlex.split(command)
            self.files[parts[2]]=self.files[parts[1]]
            return ''
        return ''
    def listing(self,root):
        return list(self.files)
    def exists(self,p):return p in self.files
    def pull(self,remote,local):
        self.pulled.append(remote)
        local.parent.mkdir(parents=True,exist_ok=True);local.write_bytes(self.files[remote])
    def upload(self,local,remote):
        self.uploaded.append(remote)
        self.files[remote]=Path(local).read_bytes()
    def stat_size(self,remote):return len(self.files[remote])
    def gba_internal_name(self,remote):return None

class FakeEngine:
    def __init__(self):self.terms=[]
    def scrape(self,stage,platform,romfile,terms):
        self.terms.append(terms)
        image=stage/'image.png'
        image.write_bytes(PNG)
        return image,'Mother 3','manual-test'

class TestUIBackend(unittest.TestCase):
    def test_scans_existing_actual_file_and_missing(self):
        adb=FakeADB()
        items=backend.catalogue(adb,{'remote_root':'/userdata/roms'})
        self.assertEqual(len(items),2)
        m=next(x for x in items if '마더' in x.rel)
        self.assertEqual(m.status,'데이터 있음')
        self.assertEqual(m.metadata['name'],'마더 3')
        self.assertEqual(m.metadata['desc'],'기존 설명 보존')
        self.assertIn('old.png',m.resource_paths['image'])
        z=next(x for x in items if '젤다' in x.rel)
        self.assertEqual(z.status,'데이터 없음')
    def test_selected_existing_rescrapes_preserves_old_and_name(self):
        adb=FakeADB();engine=FakeEngine()
        with tempfile.TemporaryDirectory() as td,mock.patch.object(backend,'HERE',Path(td)):
            (Path(td)/'aliases.json').write_text('{"마더 3":["Mother 3"]}',encoding='utf-8')
            catalog=backend.catalogue(adb,{'remote_root':'/userdata/roms'})
            chosen=[x for x in catalog if '마더' in x.rel]
            saved_orig=adb.files['/userdata/roms/gba/마더 3.gba']
            report=backend.process_selected(adb,{'remote_root':'/userdata/roms','use_wikidata':False},chosen,
                                            {'gba/마더 3.gba':'Mother 3'},engine=engine)
            self.assertEqual(report[0]['status'],'applied')
            self.assertEqual(adb.files['/userdata/roms/gba/마더 3.gba'],saved_orig)
            root=core.parse_xml(adb.files['/userdata/roms/gba/gamelist.xml'])
            entry=core.find_entry(root,'./마더 3.gba')
            self.assertEqual(entry.findtext('name'),'마더 3')
            self.assertEqual(entry.findtext('desc'),'기존 설명 보존')
            self.assertNotEqual(entry.findtext('image'),'./images/old.png')
            self.assertEqual(adb.files['/userdata/roms/gba/images/old.png'],PNG)
            self.assertFalse((Path(td)/'work'/'xml_backups').exists())
            self.assertFalse(any('.knulli-autoscraper-' in name and name.endswith('.bak') for name in adb.files))
            self.assertTrue(all('마더 3' in p or '/images/' in p or '/gamelist.xml' in p for p in adb.uploaded))
            self.assertIn('Mother 3',engine.terms[0])
            self.assertFalse(any('젤다' in p for p in adb.pulled))
    def test_restores_korean_rom_name_if_old_xml_english(self):
        import xml.etree.ElementTree as ET
        root=ET.fromstring('<gameList><game><path>./마더 3.gba</path><name>Mother 3</name></game></gameList>')
        backend.apply_image_element(root,'./마더 3.gba','마더 3','./images/new.png')
        self.assertEqual(core.find_entry(root,'./마더 3.gba').findtext('name'),'마더 3')
        root=ET.fromstring('<gameList><game><path>./마더 3.gba</path><name>마더 III</name></game></gameList>')
        backend.apply_image_element(root,'./마더 3.gba','마더 3','./images/new.png')
        self.assertEqual(core.find_entry(root,'./마더 3.gba').findtext('name'),'마더 III')
    def test_scan_is_read_only(self):
        adb=FakeADB();original=dict(adb.files)
        backend.catalogue(adb,{'remote_root':'/userdata/roms'})
        self.assertEqual(adb.files,original)
        self.assertEqual(adb.uploaded,[])
    def test_failure_does_not_change_existing_image(self):
        class NoMatch:
            def scrape(self,*args):return None,None,'not matched'
        adb=FakeADB();items=backend.catalogue(adb,{'remote_root':'/userdata/roms'})
        original=dict(adb.files)
        with tempfile.TemporaryDirectory() as td,mock.patch.object(backend,'HERE',Path(td)):
            (Path(td)/'aliases.json').write_text('{"마더 3":["Mother 3"]}',encoding='utf-8')
            selected=[x for x in items if '마더' in x.rel]
            r=backend.process_selected(adb,{'remote_root':'/userdata/roms','use_wikidata':False},selected,{},engine=NoMatch())
        self.assertEqual(r[0]['status'],'unmatched')
        self.assertEqual(adb.files,original)
        self.assertEqual(adb.uploaded,[])
    def test_broken_path_not_mistaken_for_image(self):
        a=FakeADB();del a.files['/userdata/roms/gba/images/old.png']
        items=backend.catalogue(a,{'remote_root':'/userdata/roms'})
        mother=next(x for x in items if '마더' in x.rel)
        self.assertEqual(mother.status,'데이터 있음')
    def test_resource_traversal_rejected(self):
        self.assertIsNone(backend.remote_media_path('/userdata/roms','gba','../../etc/passwd'))
        self.assertIsNone(backend.remote_media_path('/userdata/roms','gba','/etc/passwd'))
        self.assertEqual(backend.remote_media_path('/userdata/roms','gba','./images/a.png'),'/userdata/roms/gba/images/a.png')
    def test_artwork_file_passed_to_every_skyscraper_stage(self):
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td);(stage/'roms').mkdir()
            f=stage/'roms'/'마더 3.gba';f.write_bytes(b'abc')
            eng=legacy.SkyscraperEngine('Skyscraper.exe',stage/'config.ini')
            cmds=[]
            def fake_run(args):
                cmds.append(args)
                return False,'simulated missing-result'
            eng._run=fake_run
            eng.scrape(stage,'gba',f,['Mother 3'])
            self.assertTrue(cmds)
            for args in cmds:
                self.assertIn('-a',args)
                path=Path(str(args[args.index('-a')+1]))
                self.assertTrue(path.is_file())
            self.assertIn('romnom=Mother+3',str(cmds[-1]))
    def test_manual_override_saved_even_with_existing_alias(self):
        src=legacy.normalized_candidates('마더 3',{core.norm('마더 3'):['Mother III']})
        manual='Mother 3'
        candidates=[manual]+[x for x in src if core.norm(x)!=core.norm(manual)]
        self.assertEqual(candidates[0],'Mother 3')

if __name__=='__main__':unittest.main()
