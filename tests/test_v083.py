"""v0.8.3 regressions: visible row focus, no English KNULLI names."""
from pathlib import Path
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import backend, core, bundle_engine, gui
from test_v05 import FakeADB

class TestKoreanDisplay(unittest.TestCase):
    def _english_xml(self, a):
        key='/userdata/roms/gba/gamelist.xml'
        doc=core.parse_xml(a.files[key])
        core.find_entry(doc,'./마더 3.gba').find('name').text='Mother 3'
        a.files[key]=core.xml_bytes(doc)

    def test_auto_sync_preserves_rom_and_every_other_xml_field(self):
        a=FakeADB();self._english_xml(a)
        root='/userdata/roms/gba/gamelist.xml'
        before=core.parse_xml(a.files[root]);item_before=core.find_entry(before,'./마더 3.gba')
        old_image=item_before.findtext('image');old_desc=item_before.findtext('desc')
        old_rom=a.files['/userdata/roms/gba/마더 3.gba']
        rows=backend.catalogue(a,{'remote_root':'/userdata/roms'})
        m=next(x for x in rows if x.stem=='마더 3')
        self.assertEqual(m.metadata['name'],'Mother 3')
        with tempfile.TemporaryDirectory() as td:
            count=backend.sync_korean_names(a,{'remote_root':'/userdata/roms'},rows,work=Path(td))
            self.assertEqual(count,1)
            self.assertTrue(list((Path(td)/'xml_backups').glob('*.xml')))
            self.assertEqual(backend.sync_korean_names(a,{'remote_root':'/userdata/roms'},rows,work=Path(td)),0)
        after=core.find_entry(core.parse_xml(a.files[root]),'./마더 3.gba')
        self.assertEqual(after.findtext('name'),'마더 3')
        self.assertEqual(after.findtext('image'),old_image)
        self.assertEqual(after.findtext('desc'),old_desc)
        self.assertEqual(a.files['/userdata/roms/gba/마더 3.gba'],old_rom)
        self.assertTrue(any('.bak' in x for x in a.files))

    def test_safe_apply_syncs_name_even_without_media(self):
        a=FakeADB();self._english_xml(a)
        item=next(x for x in backend.catalogue(a,{'remote_root':'/userdata/roms'}) if x.stem=='마더 3')
        with tempfile.TemporaryDirectory() as td:
            got=bundle_engine.safe_apply(a,item,{'name':'Mother 3','metadata':{},'media':{},'_config':{}},['image'],work=Path(td))
        self.assertTrue(got['updated'])
        self.assertEqual(core.find_entry(core.parse_xml(a.files['/userdata/roms/gba/gamelist.xml']),'./마더 3.gba').findtext('name'),'마더 3')

    def test_does_not_override_custom_korean_title_or_protected_zip(self):
        a=FakeADB()
        a.files['/userdata/roms/neogeo/mslug.zip']=b'ROMSET'
        a.files['/userdata/roms/neogeo/gamelist.xml']=b'<gameList><game><path>./mslug.zip</path><name>Metal Slug</name></game></gameList>'
        rows=backend.catalogue(a,{'remote_root':'/userdata/roms'})
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(backend.sync_korean_names(a,{'remote_root':'/userdata/roms'},rows,work=Path(td)),0)
        self.assertEqual(core.find_entry(core.parse_xml(a.files['/userdata/roms/neogeo/gamelist.xml']),'./mslug.zip').findtext('name'),'Metal Slug')
        self.assertEqual(core.find_entry(core.parse_xml(a.files['/userdata/roms/gba/gamelist.xml']),'./젤다의 전설 & 검.gba').findtext('name'),'젤다 게임')

    def test_backup_failure_does_not_replace_original_xml(self):
        a=FakeADB();self._english_xml(a)
        key='/userdata/roms/gba/gamelist.xml';before=a.files[key]
        rows=backend.catalogue(a,{'remote_root':'/userdata/roms'})
        def fail_copy(command,timeout=60):
            if command.startswith('cp '):raise RuntimeError('simulate read-only backup failure')
            return ''
        with tempfile.TemporaryDirectory() as td,patch.object(a,'shell',side_effect=fail_copy):
            with self.assertRaises(RuntimeError):
                backend.sync_korean_names(a,{'remote_root':'/userdata/roms'},rows,work=Path(td))
        self.assertEqual(a.files[key],before)

@unittest.skipUnless(os.name=='nt' or bool(os.environ.get('DISPLAY')),'GUI requires a display')
class TestSelection(unittest.TestCase):
    def test_focus_marker_and_tag_survive_editor_focus(self):
        app=gui.App(auto_setup=False)
        try:
            a=backend.RomItem('/userdata/roms/gba/마더 3.gba','gba/마더 3.gba','gba','마더 3')
            b=backend.RomItem('/userdata/roms/gba/마더 1+2.gba','gba/마더 1+2.gba','gba','마더 1+2')
            app._paint([a,b]);app.update_idletasks()
            first=app.current
            self.assertTrue(app.tree.set(first,'check').startswith('▸'))
            self.assertIn('active_row',app.tree.item(first,'tags'))
            app.english_entry.focus_set();app.update_idletasks()
            self.assertIn('active_row',app.tree.item(first,'tags'))
            other=next(x for x in (a.rel,b.rel) if x!=first)
            app.tree.selection_set(other);app.select_row()
            self.assertTrue(app.tree.set(other,'check').startswith('▸'))
            self.assertFalse(app.tree.set(first,'check').startswith('▸'))
            self.assertIn('active_row',app.tree.item(other,'tags'))
            self.assertNotIn('active_row',app.tree.item(first,'tags'))
        finally:app.destroy()

if __name__=='__main__':unittest.main()
