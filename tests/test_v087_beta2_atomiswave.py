"""Regression: Atomiswave .7z files were omitted because system ID was absent."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import backend
import core
import legacy_bridge as legacy
import manager
from test_v05 import FakeADB, PNG


ROOT = '/userdata/roms'
ROM = ROOT + '/atomiswave/북두의 권.7z'
REL = 'atomiswave/북두의 권.7z'


class TestAtomiswaveRecognition(unittest.TestCase):
    def test_atomiswave_platform_and_archive_extensions_enabled(self):
        self.assertEqual(core.SYSTEM_IDS['atomiswave'], 53)
        self.assertEqual(legacy.PLATFORMS['atomiswave'], 'atomiswave')
        self.assertIn('.7z',core.ROM_EXT)
        self.assertIn('.7z',core.NO_HASH)
        self.assertNotIn('atomiswave',manager.SINGLE_FILE.get('.7z',set()))

    def test_catalogue_includes_nested_unicode_7z_without_modifying_rom(self):
        a = FakeADB()
        a.files[ROM] = b'7Z_ARCHIVE_PAYLOAD'
        a.files[ROOT+'/atomiswave/subfolder/메탈 슬러그.7Z'] = b'ANOTHER_7Z'
        a.files[ROOT+'/atomiswave/gamelist.xml'] = (
            '<gameList><game><path>./북두의 권.7z</path>'
            '<name>북두의 권 (사용자 지정)</name><desc>기존 한글 설명</desc>'
            '</game></gameList>'
        ).encode('utf-8')
        before = dict(a.files)
        items = backend.catalogue(a, {'remote_root':ROOT})
        games = {item.rel:item for item in items}
        self.assertIn(REL,games)
        self.assertIn('atomiswave/subfolder/메탈 슬러그.7Z', games)
        item = games[REL]
        self.assertEqual(item.system,'atomiswave')
        self.assertEqual(item.display,'북두의 권 (사용자 지정)')
        self.assertEqual(item.metadata['desc'],'기존 한글 설명')
        self.assertEqual(item.status,'데이터 있음')
        self.assertEqual(a.files,before)
        self.assertEqual(a.uploaded,[])

    def test_skyscraper_receives_atomiswave_platform_and_archive_kept(self):
        a = FakeADB()
        a.files[ROM]=b'ARCHIVE_WITHOUT_EXTRACTION'
        a.files[ROOT+'/atomiswave/gamelist.xml']=(
            b'<gameList><game><path>./'
            + '북두의 권'.encode('utf-8')
            + b'.7z</path><name>Fist of the North Star</name></game></gameList>'
        )
        before=a.files[ROM]
        item=next(item for item in backend.catalogue(a,{'remote_root':ROOT})
                  if item.rel==REL)

        class FakeEngine:
            def __init__(self):
                self.platforms=[]
                self.input_suffix=[]
            def scrape(self,stage,platform,local_rom,terms):
                self.platforms.append(platform)
                self.input_suffix.append(local_rom.suffix)
                media=stage/'preview.png'
                media.write_bytes(PNG)
                return media,'Fist of the North Star','test'
        engine=FakeEngine()
        with tempfile.TemporaryDirectory() as td, patch.object(backend,'HERE',Path(td)):
            report=backend.process_selected(
                a, {'remote_root':ROOT,'use_wikidata':False},
                [item], {'atomiswave/북두의 권.7z':'Fist of the North Star'},
                engine=engine
            )
            self.assertFalse((Path(td)/'work'/'xml_backups').exists())
        self.assertEqual(report[0]['status'],'applied')
        self.assertEqual(engine.platforms,['atomiswave'])
        self.assertEqual(engine.input_suffix,['.7z'])
        self.assertEqual(a.files[ROM],before)
        self.assertFalse(any('.knulli-autoscraper-' in remote for remote in a.files))
        doc=core.parse_xml(a.files[ROOT+'/atomiswave/gamelist.xml'])
        entry=core.find_entry(doc,'./북두의 권.7z')
        self.assertEqual(entry.findtext('name'),'Fist of the North Star')
        self.assertTrue((entry.findtext('image') or '').startswith('./images/'))

    def test_archive_filename_rename_refused_but_xml_display_name_editable(self):
        with self.assertRaisesRegex(ValueError,'보호'):
            manager.validate_name('북두의 권.7z','북두의 권 2.7z','atomiswave')
        import xml.etree.ElementTree as ET
        xml=ET.fromstring('<gameList><game><path>./fight.7z</path>'
                          '<name>Original</name></game></gameList>')
        entry=core.find_entry(xml,'./fight.7z')
        entry.find('name').text='사용자 한글 제목'
        self.assertEqual(core.find_entry(xml,'./fight.7z').findtext('name'),
                         '사용자 한글 제목')

    def test_non_atomiswave_dat_lst_are_not_treated_as_roms(self):
        class Device:
            def listing(self,root):
                return [ROOT+'/atomiswave/one.7z',
                        ROOT+'/atomiswave/two.ZIP',
                        ROOT+'/atomiswave/three.LST',
                        ROOT+'/atomiswave/four.dat',
                        ROOT+'/gba/misleading.dat',
                        ROOT+'/psx/notgame.lst',
                        ROOT+'/atomiswave/images/ignored.7z']
        result=core.collect_roms(Device(),ROOT)
        found={str(rel) for _,rel,_ in result}
        self.assertEqual(found,{
            'atomiswave/one.7z','atomiswave/two.ZIP',
            'atomiswave/three.LST','atomiswave/four.dat',
        })

    @unittest.skipUnless(os.name=='posix','POSIX remote shell simulation')
    def test_real_shell_detects_atomiswave_nested_korean_7z(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'roms'
            item=root/'atomiswave'/'한글 폴더'/'북두의 권.7z'
            item.parent.mkdir(parents=True)
            item.write_bytes(b'7zip contents')
            class Shell(core.Adb):
                def __init__(self):
                    self.commands=[]
                def shell(self,command,timeout=60):
                    self.commands.append(command)
                    p=subprocess.run(['sh','-c',command],capture_output=True,
                                     timeout=timeout)
                    if p.returncode:
                        raise RuntimeError(p.stderr.decode('utf-8','replace'))
                    return p.stdout.decode('utf-8','replace').strip()
            device=Shell()
            filenames=device.listing(str(root))
            self.assertIn(str(item),filenames)
            roms=core.collect_roms(device,str(root))
            self.assertIn(str(item),[remote for remote,_,_ in roms])
            self.assertTrue(all(cmd.isascii() for cmd in device.commands))


if __name__=='__main__':
    unittest.main()
