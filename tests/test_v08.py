"""v0.8 offline regression suite. UI tests require an X server on Linux."""
from __future__ import annotations
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import csv
import os
import tempfile
import unittest
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

import backend
import credential_store
import core
import gui
import learned_titles
import user_data
from test_v05 import FakeADB


class TestPersistentStorage(unittest.TestCase):
    def test_title_data_belongs_to_user_and_csv_is_editable(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'KNULLI_USER_DATA_DIR':td}):
            titles={}
            learned_titles.learn(titles,'gba','마더 3','Mother 3')
            user_data.save_titles(titles)
            self.assertTrue((Path(td)/'learned_titles.json').is_file())
            self.assertTrue((Path(td)/'title_map.csv').is_file())
            with (Path(td)/'title_map.csv').open(encoding='utf-8-sig',newline='') as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]['english'],'Mother 3')
            with (Path(td)/'title_map.csv').open('w',encoding='utf-8-sig',newline='') as f:
                f.write('system,korean,english,source,updated\ngba,마더 3,MOTHER III,user,2030-01-01\n')
            os.utime(Path(td)/'title_map.csv',(1893456000,1893456000))
            self.assertEqual(learned_titles.lookup(user_data.load_titles(),'gba','마더 3'),'MOTHER III')

    def test_settings_never_contain_password(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'KNULLI_USER_DATA_DIR':td}),\
                patch.object(credential_store,'write',return_value=True) as store,\
                patch.object(credential_store,'read',return_value={'user':'secretuser','password':'secretpassword'}):
            backend.save_config({'screenscraper_account':{'user':'secretuser','password':'secretpassword'},
                                 'knulli_scraper':{'image_source':'ss'}})
            self.assertNotIn('secretpassword',(Path(td)/'settings.json').read_text(encoding='utf-8'))
            self.assertEqual(store.call_count,1)
            self.assertEqual(backend.load_config()['screenscraper_account']['password'],'secretpassword')

    def test_manual_english_override_separate_from_app(self):
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'KNULLI_USER_DATA_DIR':td}):
            backend.save_overrides({'gba/마더 3.gba':'Mother 3'})
            self.assertEqual(backend.load_overrides()['gba/마더 3.gba'],'Mother 3')
            self.assertTrue((Path(td)/'manual_titles.json').exists())


class TestFocusedRefresh(unittest.TestCase):
    def test_one_game_updated_without_full_scan(self):
        adb=FakeADB()
        original=backend.catalogue(adb,{'remote_root':'/userdata/roms'})
        one=next(x for x in original if x.stem=='마더 3')
        refreshed=backend.refresh_item(adb,{'remote_root':'/userdata/roms'},one)
        self.assertTrue(refreshed.has_data)
        self.assertEqual(refreshed.metadata.get('desc'),'기존 설명 보존')
        self.assertEqual(refreshed.stem,'마더 3')


@unittest.skipUnless(os.name=='nt' or bool(os.environ.get('DISPLAY')),'GUI requires a display')
class TestGUI(unittest.TestCase):
    def setUp(self):
        self.app=gui.App(auto_setup=False)
        self.app.update_idletasks()
        self.a=backend.RomItem('/userdata/roms/gba/마더 3.gba','gba/마더 3.gba','gba','마더 3',
                               metadata={'desc':'옛 설명'},status='데이터 있음')
        self.b=backend.RomItem('/userdata/roms/neogeo/mslug.zip','neogeo/mslug.zip','neogeo','메탈슬러그',
                               metadata={'name':'메탈슬러그'},status='데이터 없음')
        self.c=backend.RomItem('/userdata/roms/nes/젤다의 전설.nes','nes/젤다의 전설.nes','nes','젤다의 전설',
                               metadata={'name':'젤다의 전설'},status='데이터 없음')
        self.app._paint([self.a,self.b,self.c])
        self.app.update_idletasks()

    def tearDown(self):
        self.app.destroy()

    def test_three_columns_and_protected_rom_uses_display_name(self):
        self.assertEqual(tuple(self.app.tree['columns']),('check','system','name','status'))
        self.assertEqual(self.app.tree.set(self.b.rel,'name'),'메탈슬러그')
        self.assertEqual(self.app.tree.set(self.a.rel,'name'),'마더 3')
        self.assertEqual(self.app.btn_go.cget('text'),'작업 시작')
        self.assertEqual(self.app.tree.set(self.b.rel,'system'),'Neo Geo')

    def test_data_missing_selects_only_truly_empty(self):
        self.app.bulk('missing')
        self.assertEqual(self.app.checked,{self.b.rel,self.c.rel})
        self.app.bulk('all')
        self.assertEqual(len(self.app.checked),3)

    def test_double_click_toggles_once_even_check_cell(self):
        rid=self.b.rel
        x,y,w,h=self.app.tree.bbox(rid,'#1')
        e=SimpleNamespace(x=x+w//2,y=y+h//2)
        self.app.click_row(e)
        self.app.click_row(e)
        self.app.double_click_row(e)
        self.assertEqual(self.app.checked,{rid})
        self.assertIsNone(self.app.pending_check)
        self.app.space_toggle(None)
        self.assertNotIn(rid,self.app.checked)

    def test_ready_result_is_readable_during_work_editors_locked(self):
        self.app._busy(True)
        complete=backend.RomItem(self.a.remote,self.a.rel,self.a.system,'마더 3',
                                 metadata={'desc':'새로 내려받은 설명','genre':'RPG'},status='적용 완료')
        self.app._update_one(complete)
        self.app.tree.selection_set(self.a.rel)
        self.app.select_row()
        self.assertEqual(self.app.description.get('1.0','end-1c'),'새로 내려받은 설명')
        self.assertEqual(str(self.app.name_entry.cget('state')),'disabled')
        self.assertEqual(self.app.detail_metadata['genre'].cget('text'),'RPG')
        self.app._busy(False)
        self.assertEqual(str(self.app.name_entry.cget('state')),'normal')


if __name__=='__main__':unittest.main()
