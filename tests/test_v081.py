"""Dark theme, selection emphasis and whole-detail scroll regressions."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gui
import backend
import tkinter as tk


@unittest.skipUnless(__import__('os').name=='nt' or __import__('os').environ.get('DISPLAY'),
                     'A display is required')
class TestDarkUI(unittest.TestCase):
    def setUp(self):
        self.app=gui.App(auto_setup=False)
        self.app.geometry('1100x670')
        self.games=[
            backend.RomItem('/userdata/roms/gba/마더 3.gba','gba/마더 3.gba','gba','마더 3',
                            metadata={'desc':'마더 시리즈의 세 번째 작품'},status='데이터 있음'),
            backend.RomItem('/userdata/roms/neogeo/mslug.zip','neogeo/mslug.zip','neogeo','메탈슬러그',
                            metadata={'name':'메탈슬러그'},status='데이터 없음'),
        ]
        self.app._paint(self.games)
        self.app.update_idletasks()

    def tearDown(self):
        self.app.destroy()

    def test_dark_colors_extend_to_text_and_canvas(self):
        self.assertEqual(self.app.cget('background'),gui.BG)
        self.assertEqual(self.app.detail_canvas.cget('background'),gui.CARD)
        self.assertEqual(self.app.description.cget('background'),gui.INPUT)
        self.assertEqual(gui.ttk.Style(self.app).lookup('Treeview','background'),gui.CARD)

    def test_current_row_stays_shaded_when_editing_and_switches_with_selection(self):
        one,two=(x.rel for x in self.games)
        self.assertIn('active_row',self.app.tree.item(one,'tags'))
        self.app.english_entry.focus_set()
        self.app.update_idletasks()
        self.assertIn('active_row',self.app.tree.item(one,'tags'))
        self.app.tree.selection_set(two)
        self.app.select_row()
        self.assertNotIn('active_row',self.app.tree.item(one,'tags'))
        self.assertIn('active_row',self.app.tree.item(two,'tags'))
        self.app._toggle(one)
        self.assertIn('checked_row',self.app.tree.item(one,'tags'))
        self.assertIn('active_row',self.app.tree.item(two,'tags'))

    def test_mouse_wheel_over_text_and_image_scrolls_parent(self):
        self.app.update_idletasks()
        canvas=self.app.detail_canvas
        self.assertGreater(float(canvas.yview()[1])-float(canvas.yview()[0]),0)
        self.assertLess(float(canvas.yview()[1]),1, 'detail must actually need scrolling')
        canvas.yview_moveto(0)
        self.app.description.event_generate('<MouseWheel>',delta=-120)
        self.app.update_idletasks()
        first=canvas.yview()[0]
        self.assertGreater(first,0,'wheel over description did not scroll detail pane')
        self.app.image_label.event_generate('<MouseWheel>',delta=-120)
        self.app.update_idletasks()
        self.assertGreater(canvas.yview()[0],first,'wheel over preview did not scroll detail pane')
        self.app.description.event_generate('<MouseWheel>',delta=120)
        self.app.update_idletasks()
        self.assertLess(canvas.yview()[0],1)

if __name__=='__main__':unittest.main()
