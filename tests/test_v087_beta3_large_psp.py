"""Regression for multi-gigabyte PSP ROMs: never transfer full ISO/CSO/PBP for name lookup."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import backend
import bundle_engine
import core
import legacy_bridge as legacy
import rom_staging
from test_v05 import FakeADB, PNG


ROOT='/userdata/roms'
ROM=ROOT+'/psp/몬스터 헌터 포터블 3rd.iso'
REL='psp/몬스터 헌터 포터블 3rd.iso'
LARGE=2*1024*1024*1024


class FakeLargeAdb(FakeADB):
    def __init__(self):
        super().__init__()
        self.files[ROM]=b'ROM_ORIGINAL_UNMODIFIED'
        self.full_rom_pull_calls=0
    def stat_size(self,path):
        return LARGE if path==ROM else super().stat_size(path)
    def pull(self,remote,local):
        if remote==ROM:
            self.full_rom_pull_calls+=1
            raise AssertionError('Large PSP disc must not be pulled via ADB')
        return super().pull(remote,local)


class TestRomStaging(unittest.TestCase):
    def test_large_psp_disc_uses_tiny_local_filename_carrier(self):
        adb=FakeLargeAdb()
        for ext in ('iso','cso','pbp','chd','ISO'):
            with tempfile.TemporaryDirectory() as td:
                destination=Path(td)/('한글 게임.'+ext)
                result=rom_staging.prepare(adb,ROM,destination,LARGE,256)
                self.assertTrue(result)
                self.assertEqual(destination.read_bytes(),rom_staging.placeholder_for(ROM))
                self.assertLess(destination.stat().st_size,8192)
        self.assertEqual(adb.full_rom_pull_calls,0)
        self.assertEqual(adb.files[ROM],b'ROM_ORIGINAL_UNMODIFIED')

    def test_name_only_placeholder_is_unique_per_game_path(self):
        first=rom_staging.placeholder_for(ROOT+'/psp/Game One.iso')
        second=rom_staging.placeholder_for(ROOT+'/psp/Game Two.iso')
        self.assertNotEqual(first,second)
        self.assertEqual(len(first),4096)
        self.assertNotIn(b'ROM_ORIGINAL_UNMODIFIED',first)
        self.assertTrue(first.startswith(rom_staging.PLACEHOLDER_PREFIX))

    def test_normal_size_disc_still_uses_real_rom_hash_lookup(self):
        adb=FakeADB()
        remote=ROOT+'/psp/small.iso'
        adb.files[remote]=b'REAL_ROM_BYTES'
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'small.iso'
            name_only=rom_staging.prepare(adb,remote,target,len(adb.files[remote]),256)
            self.assertFalse(name_only)
            self.assertEqual(target.read_bytes(),adb.files[remote])
            self.assertIn(remote,adb.pulled)

    def test_invalid_archive_is_not_faked(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,'rom_too_large'):
                rom_staging.prepare(FakeLargeAdb(),ROM,Path(td)/'huge.7z',LARGE,256)
            self.assertFalse((Path(td)/'huge.7z').exists())

    def test_limit_still_bounds_full_rom_download(self):
        adb=FakeLargeAdb()
        with tempfile.TemporaryDirectory() as td:
            self.assertTrue(rom_staging.prepare(adb,ROM,Path(td)/'name.iso',LARGE,1))
        self.assertEqual(adb.full_rom_pull_calls,0)


class TestForcedNameQueries(unittest.TestCase):
    def test_large_disc_never_runs_hash_first_skyscraper_pass(self):
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td)
            (stage/'roms').mkdir()
            local=stage/'roms'/'몬스터 헌터 포터블 3rd.iso'
            local.write_bytes(rom_staging.placeholder_for(ROM))
            engine=bundle_engine.DetailedEngine('Skyscraper.exe',stage/'config.ini')
            commands=[]
            def run(args):
                commands.append([str(x) for x in args])
                if '-g' in args:
                    (stage/'export'/'gamelist.xml').write_text(
                        '<gameList><game><name>Monster Hunter Portable 3rd</name>'
                        '<desc>A PSP hunting game</desc></game></gameList>',encoding='utf-8')
                return True,''
            with mock.patch.object(engine,'_run',side_effect=run):
                found,reason=engine.scrape_detail(
                    stage,'psp',local,['Monster Hunter Portable 3rd'],['desc'],
                    name_only=True)
            self.assertEqual(found['metadata']['desc'],'A PSP hunting game')
            search_commands=[args for args in commands if '-s' in args]
            self.assertEqual(len(search_commands),1)
            self.assertIn('--query',search_commands[0])
            self.assertIn('romnom=Monster+Hunter+Portable+3rd',search_commands[0])
            self.assertEqual([args for args in commands if '-g' in args].__len__(),1)

    def test_name_only_with_no_query_aborts_without_running_skyscraper(self):
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td)
            (stage/'roms').mkdir()
            local=stage/'roms'/'something.iso'
            local.write_bytes(rom_staging.placeholder_for(ROM))
            engine=bundle_engine.DetailedEngine('Skyscraper.exe',stage/'config.ini')
            with mock.patch.object(engine,'_run') as run:
                found,reason=engine.scrape_detail(stage,'psp',local,[],['desc'],name_only=True)
            self.assertIsNone(found)
            self.assertIn('검색어',reason)
            run.assert_not_called()

    def test_old_engine_also_forces_romnom_if_name_only(self):
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td)
            (stage/'roms').mkdir()
            local=stage/'roms'/'game.iso'
            local.write_bytes(rom_staging.placeholder_for(ROM))
            eng=legacy.SkyscraperEngine('Skyscraper.exe',stage/'config.ini')
            commands=[]
            def run(args):
                commands.append([str(x) for x in args])
                return False,'not found'
            with mock.patch.object(eng,'_run',side_effect=run):
                image,title,reason=eng.scrape(
                    stage,'psp',local,['Monster Hunter Portable 3rd'],name_only=True)
            self.assertIsNone(image)
            self.assertEqual(len(commands),1)
            self.assertIn('--query',commands[0])
            self.assertIn('romnom=Monster+Hunter+Portable+3rd',commands[0])


class TestLargePspWorkflow(unittest.TestCase):
    def test_gui_scraper_uses_name_only_and_keeps_original_rom(self):
        adb=FakeLargeAdb()
        rom_bytes=adb.files[ROM]
        class Engine:
            def __init__(self):
                self.requests=[]
            def scrape_detail(self,stage,platform,romfile,terms,wanted,name_only=False):
                self.requests.append((platform,name_only,romfile.stat().st_size,terms))
                self.assertions = True
                assert name_only
                assert platform=='psp'
                assert romfile.read_bytes()==rom_staging.placeholder_for(ROM)
                assert 'Monster Hunter Portable 3rd' in terms
                image=stage/'game.png'
                image.write_bytes(PNG)
                return {'name':'Monster Hunter Portable 3rd',
                        'metadata':{},'media':{'image':image}},'match'
        engine=Engine()
        item=backend.RomItem(ROM,REL,'psp','몬스터 헌터 포터블 3rd')
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(backend,'HERE',Path(td)):
            result=bundle_engine.process_selected(
                adb,{'remote_root':ROOT,'scrape_fields':['image'],'use_wikidata':False},
                [item],{REL:'Monster Hunter Portable 3rd'},engine=engine)
            self.assertFalse((Path(td)/'work'/'xml_backups').exists())
        self.assertEqual(result[0]['status'],'applied')
        self.assertEqual(result[0]['lookup'],'name_only')
        self.assertEqual(adb.full_rom_pull_calls,0)
        self.assertEqual(adb.files[ROM],rom_bytes)
        self.assertEqual(engine.requests[0][0:3],('psp',True,len(rom_staging.placeholder_for(ROM))))
        xml=core.parse_xml(adb.files[ROOT+'/psp/gamelist.xml'])
        entry=core.find_entry(xml,'./몬스터 헌터 포터블 3rd.iso')
        self.assertEqual(entry.findtext('name'),'몬스터 헌터 포터블 3rd')
        self.assertTrue((entry.findtext('image') or '').startswith('./images/'))

    def test_legacy_backend_also_skips_full_rom_pull(self):
        adb=FakeLargeAdb()
        class Engine:
            def __init__(self): self.name_only=None
            def scrape(self,stage,platform,romfile,terms,name_only=False):
                self.name_only=name_only
                assert romfile.read_bytes()==rom_staging.placeholder_for(ROM)
                image=stage/'art.png'
                image.write_bytes(PNG)
                return image,'Monster Hunter Portable 3rd','name match'
        eng=Engine()
        item=backend.RomItem(ROM,REL,'psp','몬스터 헌터 포터블 3rd')
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(backend,'HERE',Path(td)):
            report=backend.process_selected(
                adb,{'remote_root':ROOT,'use_wikidata':False},
                [item],{REL:'Monster Hunter Portable 3rd'},engine=eng)
        self.assertEqual(report[0]['status'],'applied')
        self.assertTrue(eng.name_only)
        self.assertEqual(adb.full_rom_pull_calls,0)


if __name__=='__main__':
    unittest.main()
