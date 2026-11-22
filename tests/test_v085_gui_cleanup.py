"""GUI safety checks: cleanup is never executed without the user's consent."""
from pathlib import Path
import sys
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gui
import orphan_cleanup as oc


class TestCleanupDialog(unittest.TestCase):
    def setUp(self):
        self.app = gui.App(auto_setup=False)
        self.app.withdraw()
        self.plan = oc.CleanupPlan(
            root='/userdata/roms',
            systems=[oc.SystemCleanup('gba',b'<gameList/>',
                                      paths=('/userdata/roms/gba/missing.gba',),
                                      media=('/userdata/roms/gba/images/missing.png',))]
        )

    def tearDown(self):
        self.app.destroy()

    def test_decline_does_not_start_cleanup(self):
        with patch('gui.messagebox.askyesno', return_value=False) as confirm, \
             patch.object(self.app, '_thread') as launch:
            self.app._offer_cleanup(self.plan)
        confirm.assert_called_once()
        launch.assert_not_called()
        self.assertFalse(self.app.busy)

    def test_accept_starts_background_cleanup(self):
        self.app.adb=object()
        with patch('gui.messagebox.askyesno', return_value=True), \
             patch('gui.orphan_cleanup.apply',return_value={
                 'removed_games':1,'removed_media':1,'warnings':[],
                 'systems':['gba'],'backups':['backup.xml']}) as apply, \
             patch.object(self.app, '_thread',side_effect=lambda fn:fn()):
            self.app._offer_cleanup(self.plan)
        apply.assert_called_once()
        event,data=self.app.q.get_nowait()
        self.assertEqual(event,'cleanup-done')
        self.assertEqual(data['removed_games'],1)

    def test_empty_game_list_clears_stale_editor(self):
        self.app.name_var.set('previous game')
        self.app.description.configure(state='normal')
        self.app.description.insert('1.0','previous description')
        self.app._paint([])
        self.assertEqual(self.app.current,None)
        self.assertEqual(self.app.name_var.get(),'')
        self.assertEqual(self.app.description.get('1.0','end-1c'),'')
        self.assertEqual(str(self.app.name_entry.cget('state')),'disabled')


if __name__=='__main__':
    unittest.main()
