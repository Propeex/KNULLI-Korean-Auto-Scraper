"""PS1 multidisc safe grouping and playlist creation regressions."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import core,backend,multidisc
from test_v05 import FakeADB

ROOT='/userdata/roms'
D1=ROOT+'/psx/드래곤 퀘스트 7 (Disc 1).chd'
D2=ROOT+'/psx/드래곤 퀘스트 7 (Disc 2).chd'
M3U=ROOT+'/psx/드래곤 퀘스트 7.m3u'

def triples(*files):
    return [(p,core.safe_rel(p,ROOT),'psx') for p in files]

class Device(FakeADB):
    def __init__(self):
        super().__init__()
        self.files[D1]=b'DISC1'
        self.files[D2]=b'DISC2'
        xml=ET.fromstring('<gameList><game><path>./드래곤 퀘스트 7 (Disc 1).chd</path><name>나의 게임명</name><desc>사용자 설명</desc><image>./images/old.png</image></game></gameList>')
        self.files[ROOT+'/psx/gamelist.xml']=core.xml_bytes(xml)
        self.files[ROOT+'/psx/images/old.png']=b'original image'

class TestMultiDisc(unittest.TestCase):
    def test_title_parsing_and_no_false_positive(self):
        self.assertEqual(multidisc.disc_identity('Dragon Quest VII (Disc 1).chd'),('Dragon Quest VII',1))
        self.assertEqual(multidisc.disc_identity('Dragon Quest VII [Disk 2] (USA).cue'),('Dragon Quest VII (USA)',2))
        self.assertEqual(multidisc.disc_identity('게임 (디스크 2).chd'),('게임',2))
        self.assertIsNone(multidisc.disc_identity('Game (Rev 1).chd'))
        self.assertIsNone(multidisc.disc_identity('Disc 1.chd'))

    def test_complete_groups_only_and_disc_order(self):
        plan=multidisc.plans_for(triples(D2,D1),ROOT)
        self.assertEqual(len(plan),1)
        self.assertEqual(plan[0].remote,M3U)
        self.assertEqual(plan[0].tracks,(D1,D2))
        self.assertEqual(plan[0].text(), '드래곤 퀘스트 7 (Disc 1).chd\n드래곤 퀘스트 7 (Disc 2).chd\n')
        self.assertFalse(multidisc.plans_for(triples(D2),ROOT))
        self.assertFalse(multidisc.plans_for(triples(D1,ROOT+'/psx/드래곤 퀘스트 7 (Disc 3).chd'),ROOT))
        self.assertFalse(multidisc.plans_for(triples(D1,D2,ROOT+'/psx/드래곤 퀘스트 7 (CD 2).cue'),ROOT))

    def test_scan_groups_two_discs_read_only_preserves_custom_metadata(self):
        a=Device(); before=dict(a.files)
        rows=backend.catalogue(a,{'remote_root':ROOT})
        psx=[r for r in rows if r.system=='psx']
        self.assertEqual(len(psx),1)
        item=psx[0]
        self.assertEqual(item.rel,'psx/드래곤 퀘스트 7 (Disc 1).chd')
        self.assertEqual(item.display,'나의 게임명')
        self.assertEqual(item.metadata['desc'],'사용자 설명')
        self.assertEqual(item.status,'멀티디스크 묶기 필요')
        self.assertEqual(item.playlist_target,M3U)
        self.assertEqual(item.disc_group,(D1,D2))
        self.assertEqual(a.files,before)
        self.assertEqual(a.uploaded,[])

    def test_existing_m3u_hides_discs_and_is_the_only_game(self):
        a=Device()
        a.files[M3U]=multidisc.plans_for(triples(D1,D2),ROOT)[0].text().encode()
        games=[r for r in backend.catalogue(a,{'remote_root':ROOT}) if r.system=='psx']
        self.assertEqual([r.rel for r in games],['psx/드래곤 퀘스트 7.m3u'])

    def test_playlist_may_reference_game_subfolder(self):
        a=Device()
        a.files[ROOT+'/psx/Dragon Quest VII.m3u']=b'games/Disc 1.chd\ngames/Disc 2.chd\n'
        a.files[ROOT+'/psx/games/Disc 1.chd']=b'A'
        a.files[ROOT+'/psx/games/Disc 2.chd']=b'B'
        games={r.rel for r in backend.catalogue(a,{'remote_root':ROOT})}
        self.assertIn('psx/Dragon Quest VII.m3u',games)
        self.assertNotIn('psx/games/Disc 1.chd',games)
        self.assertNotIn('psx/games/Disc 2.chd',games)

    def test_traversal_or_broken_playlist_does_not_hide_real_roms(self):
        a=Device()
        a.files[M3U]=b'../private.chd\n../../outside.chd\n'
        games={r.rel for r in backend.catalogue(a,{'remote_root':ROOT})}
        self.assertIn('psx/드래곤 퀘스트 7.m3u',games)
        self.assertIn('psx/드래곤 퀘스트 7 (Disc 1).chd',games)
        self.assertIn('psx/드래곤 퀘스트 7 (Disc 2).chd',games)

@unittest.skipUnless(os.name=='posix','Local POSIX device shell simulation')
class TestCreation(unittest.TestCase):
    class Adb:
        def shell(self,cmd,timeout=60):
            p=subprocess.run(['sh','-c',cmd],capture_output=True,timeout=timeout)
            if p.returncode:raise RuntimeError(p.stderr.decode('utf-8','replace'))
            return p.stdout.decode('utf-8','replace').strip()
        def exists(self,p):return Path(p).is_file()
        def pull(self,remote,local):Path(local).write_bytes(Path(remote).read_bytes())
        def upload(self,local,remote):Path(remote).write_bytes(Path(local).read_bytes())
        def stat_size(self,p):return Path(p).stat().st_size

    def test_create_playlist_preserves_original_discs_saves_xml_and_custom_name(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'roms';psx=root/'psx';psx.mkdir(parents=True)
            d1=psx/'드래곤 퀘스트 7 (Disc 1).chd'
            d2=psx/'드래곤 퀘스트 7 (Disc 2).chd'
            d1.write_bytes(b'DISC1');d2.write_bytes(b'DISC2')
            (psx/'memory.mcr').write_bytes(b'SAVE')
            (psx/'gamelist.xml').write_bytes(core.xml_bytes(ET.fromstring(
                '<gameList><game><path>./드래곤 퀘스트 7 (Disc 1).chd</path><name>사용자 한글 게임명</name><desc>설명 보존</desc></game></gameList>')))
            rows=[(str(d),core.safe_rel(str(d),str(root)),'psx') for d in (d1,d2)]
            plan=multidisc.plans_for(rows,str(root))[0]
            a=self.Adb()
            out=multidisc.create_many(a,str(root),[plan])
            self.assertEqual(out['warnings'],[])
            self.assertEqual(out['created'],[str(psx/'드래곤 퀘스트 7.m3u')])
            playlist=psx/'드래곤 퀘스트 7.m3u'
            self.assertEqual(playlist.read_text(),d1.name+'\n'+d2.name+'\n')
            self.assertEqual(d1.read_bytes(),b'DISC1')
            self.assertEqual(d2.read_bytes(),b'DISC2')
            self.assertEqual((psx/'memory.mcr').read_bytes(),b'SAVE')
            xml=core.parse_xml((psx/'gamelist.xml').read_bytes())
            entry=core.find_entry(xml,'./드래곤 퀘스트 7.m3u')
            self.assertIsNotNone(entry)
            self.assertEqual(entry.findtext('name'),'사용자 한글 게임명')
            self.assertEqual(entry.findtext('desc'),'설명 보존')
            self.assertIsNotNone(core.find_entry(xml,'./드래곤 퀘스트 7 (Disc 1).chd'))
            self.assertFalse(any(p.suffix=='.bak' for p in psx.iterdir()))
            out2=multidisc.create_many(a,str(root),[plan])
            self.assertEqual(out2['created'],[])
            self.assertEqual(playlist.read_text(),d1.name+'\n'+d2.name+'\n')

    def test_missing_disc_fails_without_creating_playlist(self):
        with tempfile.TemporaryDirectory() as td:
            psx=Path(td)/'roms'/'psx';psx.mkdir(parents=True)
            d1=psx/'Game (Disc 1).chd';d2=psx/'Game (Disc 2).chd'
            d1.write_bytes(b'A')
            plan=multidisc.PlaylistPlan(str(psx/'Game.m3u'),'Game',(str(d1),str(d2)),str(d1))
            out=multidisc.create_many(self.Adb(),str(psx.parent),[plan])
            self.assertFalse(out['created'])
            self.assertTrue(out['warnings'])
            self.assertFalse((psx/'Game.m3u').exists())

if __name__=='__main__':
    unittest.main()
