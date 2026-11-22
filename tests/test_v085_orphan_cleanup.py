"""Regression tests for cleanup of removed ROMs (v0.8.5)."""
from pathlib import Path
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core
import orphan_cleanup as oc


ROOT = '/userdata/roms'
SYS = ROOT + '/gba'


def xml(*games):
    root = ET.Element('gameList')
    for path, media, title in games:
        game = ET.SubElement(root, 'game')
        ET.SubElement(game, 'path').text = path
        ET.SubElement(game, 'name').text = title
        for key, value in media.items():
            ET.SubElement(game, key).text = value
    return core.xml_bytes(root)


class FakeAdb:
    def __init__(self, documents):
        self.docs = dict(documents)
        self.backups = {}
        self.commands = []
        self.uploads = 0

    def exists_many(self, paths):
        return {p: p in self.docs or p in self.backups for p in paths}

    def exists(self, path):
        return path in self.docs or path in self.backups

    def pull(self, remote, dest):
        Path(dest).write_bytes(self.docs[remote])

    def upload(self, source, remote):
        self.docs[remote] = Path(source).read_bytes()
        self.uploads += 1

    def shell(self, command, timeout=60):
        self.commands.append(command)
        if command.startswith('cp '):
            _, source, target = shlex.split(command)
            self.backups[target] = self.docs[source]
            return ''
        if 'rm -f' in command:
            return 'DELETED'
        raise AssertionError('Unexpected ADB shell: ' + command[:100])


class TestOrphanCleanup(unittest.TestCase):
    def _inspect(self, adb, existing=()):
        with patch.object(oc, '_path_states',
                          side_effect=lambda _adb, paths: {p: p in existing for p in paths}):
            return oc.inspect(adb, {'remote_root': ROOT})

    def _apply(self, adb, plan, existing=()):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(oc, '_path_states',
                              side_effect=lambda _adb, paths: {p: p in existing for p in paths}):
                result = oc.apply(adb, plan, Path(td))
                self.assertTrue((Path(td) / 'last_cleanup.json').is_file())
                return result

    def test_deleted_rom_unshared_media_cleanup(self):
        data = xml(
            ('./한글 폴더/마더 3.gba', {'image': './images/mother3.png',
                                      'video': './videos/mother3.mp4'}, '마더 3'),
            ('./젤다.gba', {'image': './images/zelda.png', 'desc': 'abc'}, '젤다')
        )
        adb = FakeAdb({SYS + '/gamelist.xml': data})
        current = {SYS + '/젤다.gba'}
        plan = self._inspect(adb, current)
        self.assertEqual(plan.game_count, 1)
        self.assertEqual(plan.media_count, 2)
        self.assertIn('한글 폴더', plan.examples()[0])
        result = self._apply(adb, plan, current)
        self.assertEqual(result['removed_games'], 1)
        self.assertEqual(result['removed_media'], 2)
        remaining = core.parse_xml(adb.docs[SYS + '/gamelist.xml'])
        self.assertEqual([x.findtext('name') for x in remaining.findall('game')], ['젤다'])
        self.assertEqual(len(adb.backups), 1)
        self.assertEqual(adb.backups[next(iter(adb.backups))], data)

    def test_shared_image_is_never_deleted(self):
        data = xml(
            ('./missing.gba', {'image': './images/shared.png'}, 'deleted'),
            ('./present.gba', {'thumbnail': './images/shared.png'}, 'present')
        )
        adb = FakeAdb({SYS + '/gamelist.xml': data})
        plan = self._inspect(adb, {SYS + '/present.gba'})
        self.assertEqual(plan.game_count, 1)
        self.assertEqual(plan.media_count, 0)
        result = self._apply(adb, plan, {SYS + '/present.gba'})
        self.assertEqual(result['removed_media'], 0)
        self.assertTrue(all('rm -f' not in s for s in adb.commands))

    def test_unmanaged_path_is_not_deleted(self):
        data = xml(
            ('./missing.gba', {'image': './missing.png',
                               'thumbnail': '/userdata/other/file.png',
                               'video': './videos/../private.mp4'}, 'deleted'),
        )
        adb = FakeAdb({SYS + '/gamelist.xml': data})
        plan = self._inspect(adb)
        self.assertEqual(plan.game_count, 1)
        self.assertEqual(plan.media_count, 0)

    def test_game_without_extension_is_skipped(self):
        data = xml(('./missing-folder', {'image':'./images/a.png'}, 'folder game'))
        adb = FakeAdb({SYS+'/gamelist.xml': data})
        self.assertEqual(self._inspect(adb).game_count, 0)

    def test_existing_rom_is_never_selected(self):
        data = xml(('./present.gba', {'image':'./images/a.png'}, 'present'))
        adb = FakeAdb({SYS+'/gamelist.xml': data})
        self.assertEqual(self._inspect(adb, {SYS+'/present.gba'}).game_count, 0)

    def test_stale_plan_is_rejected(self):
        data = xml(('./missing.gba', {'image':'./images/a.png'}, 'deleted'))
        adb = FakeAdb({SYS+'/gamelist.xml': data})
        plan = self._inspect(adb)
        adb.docs[SYS+'/gamelist.xml'] = core.xml_bytes(ET.Element('gameList'))
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, '변경'):
                oc.apply(adb,plan,Path(td))
        self.assertEqual(adb.uploads, 0)

    def test_reappeared_rom_is_rejected(self):
        data = xml(('./missing.gba', {}, 'deleted'))
        adb = FakeAdb({SYS+'/gamelist.xml': data})
        plan = self._inspect(adb)
        with tempfile.TemporaryDirectory() as td:
            with patch.object(oc, '_path_states', return_value={SYS+'/missing.gba': True}):
                with self.assertRaisesRegex(RuntimeError, '다시 발견'):
                    oc.apply(adb,plan,Path(td))
        self.assertEqual(adb.uploads, 0)

    def test_no_metadata_is_safe_noop(self):
        adb = FakeAdb({})
        plan = self._inspect(adb)
        self.assertEqual(plan.game_count, 0)
        self.assertEqual(plan.media_count, 0)

    def test_bad_xml_does_not_trigger_cleanup(self):
        adb = FakeAdb({SYS+'/gamelist.xml': b'not xml'})
        with self.assertRaises(Exception):
            self._inspect(adb)

    def test_unicode_existence_query_is_ascii_and_strict(self):
        class Shell:
            def __init__(self, response):
                self.response=response
                self.command=''
            def shell(self, command, timeout=70):
                self.command=command
                return self.response
        d = Shell('01')
        paths = [SYS+'/한글 모음/마더 3.gba',SYS+'/present.gba']
        self.assertEqual(oc._path_states(d,paths),{paths[0]:False,paths[1]:True})
        self.assertTrue(d.command.isascii())
        with self.assertRaisesRegex(RuntimeError,'ADB'):
            oc._path_states(Shell(''), paths)

    def test_plan_does_not_modify_device(self):
        data = xml(('./removed.gba', {'image':'./images/removed.png'}, 'gone'))
        adb = FakeAdb({SYS+'/gamelist.xml': data})
        plan = self._inspect(adb)
        self.assertEqual(plan.game_count,1)
        self.assertEqual(adb.docs[SYS+'/gamelist.xml'], data)
        self.assertEqual(adb.uploads, 0)
        self.assertEqual(adb.backups, {})
        self.assertFalse(adb.commands)

if __name__ == '__main__':
    unittest.main()
