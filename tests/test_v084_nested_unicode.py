"""v0.8.4: Regression for Korean nested PSX ROM folder becoming question marks.

These tests run with a local POSIX shell standing in for the remote KNULLI shell.
No device is modified or required for the tests.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core


class TestUnicodeHexTransport(unittest.TestCase):
    def test_hex_paths_preserve_nested_korean_and_ampersand(self):
        original = ("/userdata/roms/psx/한글 게임 모음/Silent Hill (K).cue",
                    "/userdata/roms/gba/젤다의 전설 & 검.gba")
        raw = b'\x00'.join(p.encode('utf-8') for p in original) + b'\x00'
        ascii_only = ' '.join(f'{b:02x}' for b in raw)
        self.assertEqual(core.Adb._parse_hex_listing(ascii_only, '/userdata/roms'), list(original))
        self.assertNotIn('????', ''.join(core.Adb._parse_hex_listing(ascii_only, '/userdata/roms')))

    def test_truncated_output_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'truncated'):
            core.Adb._parse_hex_listing('2f 61 62 63', '/userdata/roms')

    def test_malformed_output_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'non-hex'):
            core.Adb._parse_hex_listing('?? ??', '/userdata/roms')

    def test_invalid_utf8_rejected_instead_of_replacement_chars(self):
        with self.assertRaisesRegex(RuntimeError, 'non-UTF-8'):
            core.Adb._parse_hex_listing('2f 75 73 65 72 64 61 74 61 2f 72 6f 6d 73 2f ff 00', '/userdata/roms')

    def test_nested_paths_in_collect_roms(self):
        class Device:
            def listing(self, root):
                return [root+'/psx/한글 모음/Silent Hill (K).cue',
                        root+'/psx/한글 모음/Silent Hill (K).bin',
                        root+'/gba/게임 & 롬/마더 3.gba',
                        root+'/gba/게임 & 롬/images/test.gba']
        roms=core.collect_roms(Device(),'/userdata/roms')
        names=[str(rel) for _, rel, _ in roms]
        self.assertIn('psx/한글 모음/Silent Hill (K).cue', names)
        self.assertIn('gba/게임 & 롬/마더 3.gba', names)
        self.assertNotIn('psx/한글 모음/Silent Hill (K).bin', names)
        self.assertNotIn('gba/게임 & 롬/images/test.gba', names)

    @unittest.skipUnless(os.name == 'posix', 'POSIX remote shell simulation')
    def test_actual_shell_script_and_stat_with_korean_folders(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            cue=root/'psx'/'한글 PS1 게임 모음'/'Silent Hill (K).cue'
            cue.parent.mkdir(parents=True)
            cue.write_text('FILE "Silent Hill (K).bin" BINARY\n', encoding='utf-8')
            rom=root/'gba'/'게임 & 모음'/'마더 3.gba'
            rom.parent.mkdir(parents=True)
            rom.write_bytes(b'GBA contents')
            (rom.parent/'images').mkdir()
            (rom.parent/'images'/'notrom.gba').write_bytes(b'not-a-rom')

            class LocalShellDevice(core.Adb):
                def __init__(self):
                    self.commands=[]
                def shell(self, command, timeout=60):
                    self.commands.append(command)
                    done=subprocess.run(['sh','-c',command],capture_output=True,timeout=timeout)
                    if done.returncode:
                        raise RuntimeError(done.stderr.decode('utf-8','replace'))
                    # Simulated ADB shell stdout mangling, which only occurs
                    # when raw UTF-8 is sent rather than ASCII hex.
                    return done.stdout.decode('utf-8','replace').strip()
            d=LocalShellDevice()
            names=d.listing(str(root))
            self.assertIn(str(cue),names)
            self.assertIn(str(rom),names)
            self.assertNotIn(str(rom.parent/'images'/'notrom.gba'),[p for p,_,_ in core.collect_roms(d,str(root))])
            self.assertEqual(d.stat_size(str(cue)),cue.stat().st_size)
            self.assertTrue(all(c.isascii() for c in d.commands[-1]),'stat command must be ASCII-only')
            self.assertTrue(all(c.isascii() for c in d.commands[0]),'listing command must be ASCII-only')

    def test_stat_does_not_parse_digits_from_error_message(self):
        class ErrorDevice(core.Adb):
            def __init__(self): pass
            def shell(self, command, timeout=60):
                return "stat: can't stat '/bad/abc123.cue': No such file or directory"
        with self.assertRaisesRegex(RuntimeError,'파일 크기'):
            ErrorDevice().stat_size('/userdata/roms/psx/한글/abc123.cue')

if __name__ == '__main__':
    unittest.main()
