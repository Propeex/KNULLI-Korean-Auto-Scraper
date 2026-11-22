"""Regression tests: offline PortMaster game/metadata support (v0.8.7)."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backend
import bundle_engine
import core
import orphan_cleanup
import portmaster


ROOT = '/userdata/roms'
PORTS = ROOT + '/ports'
LAUNCH = '별의 모험.sh'
REL = 'ports/' + LAUNCH
SCRIPT = PORTS + '/' + LAUNCH
PORT_DIR = PORTS + '/starquest'
MANIFEST = PORT_DIR + '/port.json'
INFO = PORT_DIR + '/gameinfo.xml'
COVER = PORT_DIR + '/cover.png'


def fixture_files():
    info = ET.Element('gameList')
    node = ET.SubElement(info,'game')
    for tag,value in {
        'path':'./'+LAUNCH,'name':'Star Quest',
        'desc':'An adventurous puzzle game','genre':'Adventure',
        'developer':'Team Constellation','publisher':'Publisher X',
        'releasedate':'20240601T000000',
        'image':'./starquest/cover.png'
    }.items():
        ET.SubElement(node,tag).text=value
    port_json = {
        'version':2,'name':'starquest.zip',
        'items':[LAUNCH,'starquest'],
        'attr':{'title':'PortMaster Star Quest','desc':'Short blurb',
                'genres':['Puzzle','Adventure'],'porter':['Example']},
    }
    return {
        MANIFEST: json.dumps(port_json,ensure_ascii=False).encode(),
        INFO: core.xml_bytes(info),
        COVER: b'\x89PNG' + b'\0'*24,
    }


class Device:
    def __init__(self, docs=None):
        self.docs = dict(docs or {})
        self.writes = []
        self.calls = []
    def exists(self, path):
        return path in self.docs
    def pull(self, remote, dest):
        Path(dest).write_bytes(self.docs[remote])
    def upload(self, local, remote):
        self.writes.append(remote)
        self.docs[remote] = Path(local).read_bytes()
    def stat_size(self, remote):
        return len(self.docs[remote])
    def shell(self, cmd, timeout=60):
        self.calls.append(cmd)
        if 'od -An -v -tx1' in cmd:
            # Metadata-only discovery is patched in most tests; reads are
            # encoded to ASCII even for Korean launch script filenames.
            for path,data in self.docs.items():
                if cmd.endswith(core.Adb._encoded_remote_path(path)):
                    return ' '.join(f'{x:02x}' for x in data)
        raise AssertionError('Unexpected shell: '+cmd[:160])


class TestPortMasterDiscovery(unittest.TestCase):
    def test_game_launchers_are_top_level_and_tools_excluded(self):
        self.assertTrue(portmaster.is_game_launcher(REL))
        for name in ('PortMaster.sh', 'Install.PortMaster.sh',
                     'Install Portmaster.sh','PortMaster Scraper.sh',
                     'portmaster scraper (Rescan All).sh',
                     'starquest/run.sh', '.hidden.sh'):
            self.assertFalse(portmaster.is_game_launcher('ports/'+name))
        self.assertFalse(portmaster.is_game_launcher('gba/zelda.sh'))

    def test_core_catalogue_only_returns_port_games_not_scripts_elsewhere(self):
        class List:
            def listing(self, root):
                return [
                    SCRIPT, PORTS+'/PortMaster.sh', PORTS+'/Install.PortMaster.sh',
                    PORTS+'/starquest/data/runner.sh',
                    ROOT+'/gba/run.sh', ROOT+'/gba/mario.gba',
                ]
        games=core.collect_roms(List(),ROOT)
        self.assertEqual({str(rel) for _,rel,_ in games}, {REL,'gba/mario.gba'})
        self.assertIn('ports',core.SYSTEM_IDS)

    def test_port_scanner_avoids_recursing_into_game_files(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            root=base/'roms'
            ports=root/'ports'
            data=ports/'starquest'/'gameassets'
            data.mkdir(parents=True)
            (ports/'Star Quest.sh').write_bytes(b'#!/bin/sh')
            (data/'big.dat').write_bytes(b'simulated')
            (data/'trick.sh').write_bytes(b'#!/bin/sh')
            (ports/'portmaster.sh').write_bytes(b'#!/bin/sh')
            script=core.Adb._listing_script([str(ports)])
            run=subprocess.run(['sh','-c',script],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr)
            files=core.Adb._parse_hex_listing(run.stdout,str(root))
            self.assertEqual(set(files),{str(ports/'Star Quest.sh'),
                                          str(ports/'portmaster.sh')})
            self.assertNotIn('find',script.split('case "$d" in */ports)')[1].split('continue')[0])


class TestPortMasterMetadata(unittest.TestCase):
    def setUp(self):
        self.docs=fixture_files()
        self.device=Device(self.docs)
        self.files=list(self.docs)

    def load(self):
        with patch.object(portmaster,'_metadata_paths',return_value=self.files):
            return portmaster.load_ports(self.device,ROOT,[REL])

    def test_gameinfo_takes_priority_over_short_port_json(self):
        info=self.load()
        self.assertEqual(set(info),{LAUNCH})
        game=info[LAUNCH]
        self.assertEqual(game.metadata['name'],'Star Quest')
        self.assertEqual(game.metadata['desc'],'An adventurous puzzle game')
        self.assertEqual(game.metadata['genre'],'Adventure')
        self.assertEqual(game.metadata['developer'],'Team Constellation')
        self.assertEqual(game.image,COVER)
        self.assertEqual(game.relative_launcher,'./'+LAUNCH)
        self.assertEqual(game.source,'gameinfo.xml')

    def test_port_json_without_gameinfo_is_supported(self):
        self.files.remove(INFO)
        info=self.load()[LAUNCH]
        self.assertEqual(info.metadata['name'],'PortMaster Star Quest')
        self.assertEqual(info.metadata['desc'],'Short blurb')
        self.assertEqual(info.metadata['genre'],'Puzzle, Adventure')
        self.assertEqual(info.image,COVER)

    def test_no_heuristic_match_for_unknown_scripts(self):
        with patch.object(portmaster,'_metadata_paths',return_value=self.files):
            info=portmaster.load_ports(self.device,ROOT,['ports/other title.sh'])
        self.assertEqual(info,{})

    def test_untrusted_path_and_mismatched_launcher_are_skipped(self):
        self.device.docs[MANIFEST]=json.dumps({
            'items':['wrong.sh'], 'attr':{'title':'Not this game'}
        }).encode()
        self.device.docs[INFO]=core.xml_bytes(ET.Element('gameList'))
        self.assertEqual(self.load(),{})

    def test_cover_path_traversal_is_never_used(self):
        xml=ET.Element('gameList')
        game=ET.SubElement(xml,'game')
        ET.SubElement(game,'path').text='./'+LAUNCH
        ET.SubElement(game,'name').text='Star Quest'
        ET.SubElement(game,'image').text='./../../private.png'
        self.device.docs[INFO]=core.xml_bytes(xml)
        self.files.remove(COVER)
        self.assertEqual(self.load()[LAUNCH].image,'')

    def test_manifest_unicode_read_is_ascii(self):
        actual=portmaster._read_small(self.device,MANIFEST)
        self.assertEqual(actual,self.docs[MANIFEST])
        self.assertTrue(self.device.calls[-1].isascii())
        self.assertFalse(any('pull' in cmd for cmd in self.device.calls))

    def test_valid_image_references_are_bounded_to_ports(self):
        self.assertEqual(portmaster._media_candidate(PORTS,'./starquest/cover.png'),COVER)
        for unsafe in ('../secrets.jpg', './starquest/../../other.jpg',
                       '/userdata/roms/gba/art.png', './foo.sh',
                       './other\\file.jpg','./x\nsecret.png'):
            self.assertIsNone(portmaster._media_candidate(PORTS,unsafe))

    def test_existing_custom_metadata_and_image_are_preserved(self):
        xml=ET.Element('gameList')
        node=ET.SubElement(xml,'game')
        for tag,value in {'path':'./'+LAUNCH,'name':'내가 정한 이름',
                          'desc':'내가 작성한 한국어 설명',
                          'image':'./images/custom.png'}.items():
            ET.SubElement(node,tag).text=value
        self.device.docs[PORTS+'/gamelist.xml']=core.xml_bytes(xml)
        with patch.object(portmaster,'_metadata_paths',return_value=self.files):
            result=portmaster.apply_one(
                self.device,backend.RomItem(SCRIPT,REL,'ports',''),
                {'remote_root':ROOT},
                portmaster.load_ports(self.device,ROOT,[REL]),
                ['image','thumbnail','desc','genre','developer','publisher'])
        self.assertEqual(result['status'],'applied')
        updated=core.parse_xml(self.device.docs[PORTS+'/gamelist.xml'])
        entry=updated.find('game')
        self.assertEqual(entry.findtext('name'),'내가 정한 이름')
        self.assertEqual(entry.findtext('desc'),'내가 작성한 한국어 설명')
        self.assertEqual(entry.findtext('image'),'./images/custom.png')
        self.assertEqual(entry.findtext('thumbnail'),'./starquest/cover.png')
        self.assertEqual(entry.findtext('developer'),'Team Constellation')
        self.assertEqual(self.device.writes,[PORTS+'/gamelist.xml'])
        self.assertFalse(any('bak' in x for x in self.device.docs))

    def test_missing_gamelist_creates_entry_without_touching_launcher(self):
        catalogue=self.load()
        with patch.object(portmaster,'_metadata_paths',return_value=self.files):
            result=portmaster.apply_one(
                self.device,backend.RomItem(SCRIPT,REL,'ports',LAUNCH),
                {'remote_root':ROOT},catalogue,
                ['image','thumbnail','desc','genre','developer','publisher','releasedate'])
        self.assertEqual(result['status'],'applied')
        xml=core.parse_xml(self.device.docs[PORTS+'/gamelist.xml'])
        row=xml.find('game')
        self.assertEqual(row.findtext('path'),'./'+LAUNCH)
        self.assertEqual(row.findtext('name'),'Star Quest')
        self.assertEqual(row.findtext('image'),'./starquest/cover.png')
        self.assertEqual(row.findtext('desc'),'An adventurous puzzle game')
        self.assertEqual(self.device.writes,[PORTS+'/gamelist.xml'])
        self.assertNotIn(SCRIPT,self.device.writes)
        # A second run does not alter the XML.
        self.device.writes.clear()
        again=portmaster.apply_one(
            self.device,backend.RomItem(SCRIPT,REL,'ports',LAUNCH),
            {'remote_root':ROOT},catalogue,['image','desc','genre','developer'])
        self.assertEqual(again['status'],'unchanged')
        self.assertEqual(self.device.writes,[])

    def test_no_metadata_does_not_change_gamelist(self):
        data=core.xml_bytes(ET.Element('gameList'))
        self.device.docs[PORTS+'/gamelist.xml']=data
        result=portmaster.apply_one(self.device,
            backend.RomItem(SCRIPT,REL,'ports',LAUNCH),{'remote_root':ROOT},{},
            ['image','desc'])
        self.assertEqual(result['status'],'unmatched')
        self.assertEqual(self.device.docs[PORTS+'/gamelist.xml'],data)
        self.assertEqual(self.device.writes,[])

    def test_port_selection_never_starts_screenscraper_engine(self):
        with tempfile.TemporaryDirectory() as td, \
             patch.object(bundle_engine.backend,'HERE',Path(td)), \
             patch.object(bundle_engine.legacy,'find_engine',
                          side_effect=AssertionError('No Skyscraper for PortMaster')), \
             patch.object(bundle_engine.portmaster,'_metadata_paths',return_value=self.files):
            item=backend.RomItem(SCRIPT,REL,'ports',LAUNCH)
            result=bundle_engine.process_selected(
                self.device,{'remote_root':ROOT,'knulli_scraper':None,
                             'scrape_fields':['image','desc','genre']},
                [item],{},engine=None)
        self.assertEqual(result[0]['status'],'applied')
        self.assertEqual(self.device.writes,[PORTS+'/gamelist.xml'])

    def test_orphan_cleanup_only_touches_missing_launcher_xml(self):
        self.assertEqual(orphan_cleanup._game_path(ROOT,'ports','./'+LAUNCH),SCRIPT)
        for p in ('./PortMaster.sh','./Install.PortMaster.sh',
                  './starquest/something.sh','./starquest/port.json',
                  './starquest/cover.png'):
            self.assertIsNone(orphan_cleanup._game_path(ROOT,'ports',p))


if __name__=='__main__':
    unittest.main()
