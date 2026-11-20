"""v0.8.2 regressions: status column, neutral UI and safe English auto-save."""
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gui
import backend


def gray(hexrgb):
    s=hexrgb.lstrip('#')
    return len(s)==6 and s[:2].lower()==s[2:4].lower()==s[4:].lower()


class TestPresentationHelpers(unittest.TestCase):
    def test_monochrome_palette(self):
        for key in ('BG','CARD','INPUT','ALT','ACTIVE','CHECKED','LINE','BLUE'):
            self.assertTrue(gray(getattr(gui,key)),key)

    def test_status_labels(self):
        for status,expected in (
            ('적용 완료','✓ 작업 성공'),('데이터 있음','● 데이터 있음'),
            ('검색 실패','✕ 검색 실패'),('오류','✕ 작업 실패'),
            ('데이터 없음','○ 데이터 없음'),('진행 중','… 작업 중')):
            item=backend.RomItem('/root/x.gba','gba/x.gba','gba','x',status=status)
            self.assertEqual(gui.App._status_text(item),expected)


@unittest.skipUnless(os.name=='nt' or bool(os.environ.get('DISPLAY')),'GUI requires a display')
class TestNeutralGUI(unittest.TestCase):
    def setUp(self):
        self.app=gui.App(auto_setup=False)
        self.app.geometry('1200x760')
        self.games=[
            backend.RomItem('/userdata/roms/gba/마더 3.gba','gba/마더 3.gba','gba','마더 3',
                            metadata={'desc':'이미 설명 있음'},status='데이터 있음'),
            backend.RomItem('/userdata/roms/gba/메트로이드 퓨전.gba','gba/메트로이드 퓨전.gba','gba',
                            '메트로이드 퓨전',status='적용 완료'),
            backend.RomItem('/userdata/roms/neogeo/mslug.zip','neogeo/mslug.zip','neogeo',
                            '메탈슬러그',status='검색 실패')]
        self.app._paint(self.games)
        self.app.update_idletasks()

    def tearDown(self):
        self.app.destroy()

    def test_four_columns_and_state_in_last_column(self):
        self.assertEqual(tuple(self.app.tree['columns']),('check','system','name','status'))
        self.assertEqual(self.app.tree.heading('status')['text'],'상태')
        self.assertEqual(self.app.tree.set(self.games[0].rel,'status'),'● 데이터 있음')
        self.assertEqual(self.app.tree.set(self.games[1].rel,'status'),'✓ 작업 성공')
        self.assertEqual(self.app.tree.set(self.games[2].rel,'status'),'✕ 검색 실패')

    def test_no_alternating_shading_and_focus_visible(self):
        first,second,third=(g.rel for g in self.games)
        self.assertEqual(self.app.tree.tag_configure('checked_row')['background'],gui.CARD)
        self.assertIn('active_row',self.app.tree.item(first,'tags'))
        self.assertNotIn('stripe_row',self.app.tree.item(second,'tags'))
        self.app.tree.selection_set(second)
        self.app.select_row()
        self.assertIn('active_row',self.app.tree.item(second,'tags'))
        self.assertNotIn('active_row',self.app.tree.item(first,'tags'))

    def test_compact_english_field_autosave_without_button(self):
        self.assertFalse(hasattr(self.app,'btn_english'))
        self.assertEqual(self.app.english_entry.cget('width'),26)
        records=[]
        with patch.object(backend,'save_overrides',side_effect=lambda o:records.append(dict(o))):
            self.app.english_var.set('Mother 3')
            self.assertIsNotNone(self.app._english_timer)
            self.app._flush_english_pending()
            self.assertEqual(records[-1][self.games[0].rel],'Mother 3')
            self.assertIsNone(self.app._english_pending)
            self.app.english_var.set('Mother III')
            self.app._english_commit_event()
            self.assertEqual(records[-1][self.games[0].rel],'Mother III')
            self.assertTrue(self.app.english_entry.bind('<FocusOut>'))

    def test_save_previous_game_on_selection_switch(self):
        first,second=self.games[:2]
        with patch.object(backend,'save_overrides',side_effect=lambda o:None):
            self.app.english_var.set('Mother 3')
            self.app.tree.selection_set(second.rel)
            self.app.select_row()
            self.assertEqual(self.app.overrides[first.rel],'Mother 3')
            self.assertNotIn(second.rel,self.app.overrides)
            self.app.english_var.set('Metroid Fusion')
            self.app._flush_english_pending()
            self.assertEqual(self.app.overrides[second.rel],'Metroid Fusion')

    def test_complete_item_updates_state_without_rescan(self):
        game=self.games[0]
        replacement=backend.RomItem(game.remote,game.rel,game.system,game.display,
                                    metadata={'desc':'업데이트'},status='적용 완료')
        self.app._update_one(replacement)
        self.assertEqual(self.app.tree.set(game.rel,'status'),'✓ 작업 성공')

if __name__=='__main__':unittest.main()
