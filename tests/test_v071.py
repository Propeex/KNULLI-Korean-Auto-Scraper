"""Regression: arcade ROM filenames remain fixed; localized display titles are editable."""
import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import backend, core, manager
from test_v06 import FakeADB

class TestDisplayNameForArchives(unittest.TestCase):
    def test_neogeo_archive_has_editable_korean_display_name_without_renaming_rom(self):
        adb=FakeADB()
        rom='/userdata/roms/neogeo/mslug.zip'
        xml='/userdata/roms/neogeo/gamelist.xml'
        adb.files[rom]=b'PK\x03\x04not_a_real_rom'
        adb.files[xml]=b'<gameList><game><path>./mslug.zip</path><name>Metal Slug</name><image>./images/mslug.png</image></game></gameList>'
        adb.files['/userdata/roms/neogeo/images/mslug.png']=b'fakeimage'
        item=backend.RomItem(rom,'neogeo/mslug.zip','neogeo','mslug')
        with tempfile.TemporaryDirectory() as temp:
            did_change=manager.update_metadata(adb,item,{'name':'메탈슬러그'},work=Path(temp))
            self.assertTrue(did_change)
            doc=core.parse_xml(adb.files[xml])
            game=doc.find('game')
            self.assertEqual(game.findtext('name'),'메탈슬러그')
            self.assertEqual(game.findtext('path'),'./mslug.zip')
            self.assertEqual(game.findtext('image'),'./images/mslug.png')
            self.assertIn(rom,adb.files)
            self.assertEqual(adb.files[rom],b'PK\x03\x04not_a_real_rom')
            self.assertTrue(list((Path(temp)/'xml_backups').glob('neogeo_*.xml')))
            self.assertTrue(any('.bak' in key for key in adb.files))
            with self.assertRaises(ValueError):
                manager.validate_name('mslug.zip','메탈슬러그.zip','neogeo')

if __name__=='__main__':unittest.main()
