"""v0.8.5-beta.2: short ADB shell batches and app-owned backup cleanup."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backup_cleanup
import core
import orphan_cleanup


class ConstrainedAdb:
    """Simulate the shell command limit that triggered a real user error."""

    def __init__(self, max_length=500):
        self.maximum = max_length
        self.calls = []
        self.refusals = 0

    def shell(self, command, timeout=70):
        self.calls.append(command)
        if len(command) > self.maximum:
            self.refusals += 1
            raise RuntimeError('ADB shell failed: error: shell command too long')
        return '1' * command.count('then printf 1')


class TestShellLength(unittest.TestCase):
    def test_many_korean_names_fit_or_fall_back_to_small_batches(self):
        paths = [
            f'/userdata/roms/gba/한글 폴더/게임 {i:03d}.gba'
            for i in range(37)
        ]
        adb = ConstrainedAdb(max_length=500)
        result = orphan_cleanup._path_states(adb, paths)
        self.assertEqual(result, {path: True for path in paths})
        self.assertGreater(len(adb.calls), 1)
        self.assertTrue(adb.refusals >= 1)
        self.assertTrue(all(cmd.isascii() for cmd in adb.calls))
        self.assertTrue(all(len(cmd) <= 500 for cmd in adb.calls if len(cmd) <= 500))

    def test_long_single_path_refusal_aborts_instead_of_marking_missing(self):
        adb = ConstrainedAdb(max_length=100)
        with self.assertRaisesRegex(RuntimeError, '안전상 자료 삭제 중단'):
            orphan_cleanup._path_states(adb, [
                '/userdata/roms/gba/한글 폴더/마더 3.gba'
            ])
        self.assertGreaterEqual(adb.refusals, 1)

    def test_short_response_is_not_taken_as_missing(self):
        class Truncated:
            def shell(self, command, timeout=70):
                return ''
        with self.assertRaisesRegex(RuntimeError, '불완전'):
            orphan_cleanup._path_states(Truncated(), [
                '/userdata/roms/gba/missing.gba',
            ])

    def test_empty_and_duplicate_paths(self):
        adb = ConstrainedAdb()
        self.assertEqual(orphan_cleanup._path_states(adb, []), {})
        self.assertEqual(adb.calls, [])
        x = '/userdata/roms/gba/마더 3.gba'
        self.assertEqual(orphan_cleanup._path_states(adb, [x, x]), {x: True})


class TestBackupSelection(unittest.TestCase):
    def test_local_only_app_named_backups_removed(self):
        with tempfile.TemporaryDirectory() as td:
            work = Path(td) / 'work'
            backups = work / 'xml_backups'
            backups.mkdir(parents=True)
            app_backup = backups / 'gba_20261123_210000_123456.xml'
            app_backup.write_text('XML backup', encoding='utf-8')
            old_stamp = backups / 'psx_20261123_210000.xml'
            old_stamp.write_text('XML backup', encoding='utf-8')
            user_file = backups / 'my_manual_copy.xml'
            user_file.write_text('preserve', encoding='utf-8')
            other = work / 'last_report.json'
            other.write_text('preserve', encoding='utf-8')

            self.assertEqual(backup_cleanup.remove_local_backups(work), 2)
            self.assertFalse(app_backup.exists())
            self.assertFalse(old_stamp.exists())
            self.assertTrue(user_file.exists())
            self.assertTrue(other.exists())
            self.assertEqual(backup_cleanup.remove_local_backups(work), 0)

    def test_only_verified_adjacent_old_installations_are_cleaned(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            current = parent / 'KNULLI-Korean-Auto-Scraper-v0.8.5-beta.2'
            old = parent / 'knulli_auto_scraper_v084'
            unrelated = parent / 'knulli_scraper_notes'
            for install in (current, old, unrelated):
                install.mkdir()
                (install / 'work' / 'xml_backups').mkdir(parents=True)
                filename = install / 'work' / 'xml_backups' / 'gba_20261123_210000_123456.xml'
                filename.write_bytes(b'OLD XML BACKUP')
            for install in (current, old):
                (install / 'GUI_실행.pyw').touch()
                (install / 'backend.py').touch()
            with mock.patch.object(backup_cleanup, 'remove_device_backups', return_value=0):
                result = backup_cleanup.cleanup(object(), {'remote_root': '/userdata/roms'},
                                                current / 'work')
            self.assertEqual(result['local_removed'], 2)
            self.assertFalse((current / 'work' / 'xml_backups').exists())
            self.assertFalse((old / 'work' / 'xml_backups').exists())
            self.assertTrue((unrelated / 'work' / 'xml_backups' /
                             'gba_20261123_210000_123456.xml').exists())

    def test_symlinked_backup_directory_is_never_followed(self):
        if os.name == 'nt':
            self.skipTest('Symlinks may require elevated privileges on Windows')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'user_files'
            source.mkdir()
            target = source / 'gba_20261123_210000_123456.xml'
            target.write_bytes(b'USER CONTENT')
            work = root / 'work'
            work.mkdir()
            (work / 'xml_backups').symlink_to(source, target_is_directory=True)
            with self.assertRaisesRegex(RuntimeError, '정상 폴더'):
                backup_cleanup.remove_local_backups(work)
            self.assertEqual(target.read_bytes(), b'USER CONTENT')


@unittest.skipUnless(os.name == 'posix', 'POSIX shell simulation')
class TestDeviceBackupPruning(unittest.TestCase):
    def test_deletes_only_program_tagged_xml_backup_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'roms'
            gba = root / 'gba'
            psx = root / 'psx'
            gba.mkdir(parents=True)
            psx.mkdir()
            target1 = gba / 'gamelist.xml.knulli-autoscraper-20261123_220101_123456.bak'
            target2 = psx / 'gamelist.xml.knulli-autoscraper-20251120_010203_987654.bak'
            untouched = [
                gba / 'gamelist.xml',
                gba / 'gamelist.xml.bak',
                gba / 'gamelist.xml.knulli-autoscraper-manual.bak',
                gba / 'rom.gba',
                gba / 'images' / 'art.png',
            ]
            for p in [target1, target2] + untouched:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b'USER-DATA')

            class LocalAdb:
                def __init__(self):
                    self.calls = []
                def shell(self, command, timeout=35):
                    self.calls.append(command)
                    done = subprocess.run(['sh', '-c', command],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          timeout=timeout)
                    if done.returncode:
                        raise RuntimeError(done.stderr.decode('utf-8', 'replace'))
                    return done.stdout.decode('utf-8', 'strict').strip()

            adb = LocalAdb()
            count = backup_cleanup.remove_device_backups(adb, str(root))
            self.assertEqual(count, 2)
            self.assertFalse(target1.exists())
            self.assertFalse(target2.exists())
            for p in untouched:
                self.assertEqual(p.read_bytes(), b'USER-DATA')
            self.assertEqual(backup_cleanup.remove_device_backups(adb, str(root)), 0)
            self.assertTrue(all(len(x) < 1200 for x in adb.calls))

    def test_unicode_path_existence_matches_real_shell(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / 'roms'
            d = root / 'gba' / '한국어 타이틀'
            d.mkdir(parents=True)
            rom = d / '젤다의 전설 4개의 검.gba'
            rom.write_bytes(b'game')
            missing = d / '삭제된 게임.gba'

            class Shell:
                def shell(self, command, timeout=70):
                    done = subprocess.run(['sh', '-c', command],
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          timeout=timeout)
                    if done.returncode:
                        raise RuntimeError(done.stderr.decode('utf-8', 'replace'))
                    return done.stdout.decode('ascii').strip()

            self.assertEqual(
                orphan_cleanup._path_states(Shell(), [str(rom), str(missing)]),
                {str(rom): True, str(missing): False},
            )


if __name__ == '__main__':
    unittest.main()
