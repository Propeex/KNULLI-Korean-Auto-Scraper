import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import backend
import bundle_engine
import core
import learned_titles
import manager
import scrape_options
import setup_platform_tools
import setup_engine
from test_v05 import FakeADB


class TestInstaller(unittest.TestCase):
    def as_zip(self, entries):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:
            for name,payload in entries.items():z.writestr(name,payload)
        return data.getvalue()

    def test_top_level_directory_is_valid_not_malicious(self):
        # Regression: v0.6 rejected a perfectly normal platform-tools/ directory.
        zipbytes=self.as_zip({'platform-tools/':b'',
                              'platform-tools/adb.exe':b'exe',
                              'platform-tools/AdbWinApi.dll':b'dll',
                              'platform-tools/AdbWinUsbApi.dll':b'dll2'})
        with tempfile.TemporaryDirectory() as td,patch.object(setup_platform_tools,'HERE',Path(td)),\
                patch.object(setup_platform_tools.urllib.request,'urlopen',return_value=io.BytesIO(zipbytes)):
            installed=setup_platform_tools.setup()
            self.assertTrue(Path(installed).is_file())
            self.assertEqual(Path(td,'platform-tools','AdbWinApi.dll').read_bytes(),b'dll')

    def test_zip_traversal_is_rejected(self):
        zipbytes=self.as_zip({'platform-tools/../evil.exe':b'evil', 'platform-tools/adb.exe':b'ok'})
        with tempfile.TemporaryDirectory() as td,patch.object(setup_platform_tools,'HERE',Path(td)),\
                patch.object(setup_platform_tools.urllib.request,'urlopen',return_value=io.BytesIO(zipbytes)):
            with self.assertRaises(RuntimeError):setup_platform_tools.setup()
            self.assertFalse(Path(td,'evil.exe').exists())

    def test_skyscraper_bootstrap_auto_install(self):
        zipbytes=self.as_zip({'Skyscraper_3.6.12_unsupported_win_version/Skyscraper.exe':b'placeholder'})
        with tempfile.TemporaryDirectory() as td, patch.object(setup_engine,'HERE',Path(td)),\
                patch.object(setup_engine.urllib.request,'urlopen',return_value=io.BytesIO(zipbytes)):
            p=setup_engine.setup()
            self.assertTrue(Path(p).is_file())
            # Reusing existing file should not require internet.
            with patch.object(setup_engine.urllib.request,'urlopen',side_effect=AssertionError('download again')):
                self.assertEqual(setup_engine.setup(),p)


class TestBehavior(unittest.TestCase):
    def test_stem_only_rename_keeps_original_extension(self):
        self.assertEqual(manager.complete_filename('마더 3.gba','마더 III'),'마더 III.gba')
        self.assertEqual(manager.validate_name('마더 3.gba','마더 III.gba','gba'),'마더 III.gba')
        with self.assertRaises(ValueError): manager.validate_name('마더 3.gba','마더 III.sfc','gba')

    def test_learning_is_system_scoped_and_persistent(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'titles.json';d={}
            self.assertTrue(learned_titles.learn(d,'gba','마더 3','Mother 3'))
            core.json_write(path,d)
            self.assertEqual(learned_titles.lookup(learned_titles.load(path),'gba','마더 3'),'Mother 3')
            self.assertEqual(learned_titles.lookup(d,'snes','마더 3'),'')
            learned_titles.migrate(d,'gba','마더 3','마더 III')
            self.assertEqual(learned_titles.lookup(d,'gba','마더 III'),'Mother 3')

    def test_non_success_never_learns(self):
        self.assertFalse(learned_titles.learn({},'gba','마더 3',''))
        self.assertFalse(learned_titles.learn({},'gba','마더 3','????'))

    def test_actual_data_includes_text_metadata(self):
        d=backend.RomItem('/userdata/roms/gba/x.gba','gba/x.gba','gba','x',metadata={'desc':'기존 설명'})
        self.assertTrue(d.has_data)
        m=backend.RomItem('/userdata/roms/gba/y.gba','gba/y.gba','gba','y',resource_paths={'image':'/foo'})
        self.assertFalse(m.has_data)
        m.existing_resources.add('image')
        self.assertTrue(m.has_data)

    def test_batched_file_existence(self):
        obj=object.__new__(core.Adb)
        commands=[]
        def fake_shell(cmd,timeout=60):
            commands.append(cmd)
            return '101'
        obj.shell=fake_shell
        got=obj.exists_many(['/a','/b','/c'])
        self.assertEqual(got,{'/a':True,'/b':False,'/c':True})
        self.assertEqual(len(commands),1)

    def test_scrape_options_match_knulli_basic_structure(self):
        config={'knulli_scraper':{'image_source':'mixrbv2','box_source':'box-2D','logo_source':'wheel',
                                  'rating':True,'video':False,'desc':True,'players':True}}
        wanted=scrape_options.selection(config)
        self.assertIn('image',wanted)
        self.assertIn('thumbnail',wanted)
        self.assertIn('marquee',wanted)
        self.assertNotIn('video',wanted)
        self.assertEqual(scrape_options.options(config)['overwrite_names'],False)
        self.assertEqual(scrape_options.options(config)['preferred_region'],'')
        self.assertNotIn('padtokey',wanted)
        self.assertIn(b'cover',scrape_options.recipe(config))

    def test_media_overwrite_controls(self):
        a=FakeADB()
        items=backend.catalogue(a,{'remote_root':'/userdata/roms'})
        item=next(i for i in items if i.stem=='마더 3')
        with tempfile.TemporaryDirectory() as td:
            new=Path(td)/'new.png';new.write_bytes(b'\x89PNG\r\n\x1a\n' + b'payloadpng'*3)
            found={'media':{'image':new},'metadata':{'desc':'영어 새 설명'},
                   '_config':{'knulli_scraper':{'overwrite_medias':False,'overwrite_descriptions':False}}}
            original=dict(a.files)
            result=bundle_engine.safe_apply(a,item,found,['image','desc'],work=Path(td))
            self.assertFalse(result['updated'])
            self.assertEqual(a.files,original)


if __name__=='__main__':unittest.main()
