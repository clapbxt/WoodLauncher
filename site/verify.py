"""Check local links, page landmarks, release checksums, and static file limits."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import hashlib
import json
ROOT = Path(__file__).resolve().parent / 'dist'


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(); self.path = path; self.refs = []; self.ids = set(); self.main = False
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'main': self.main = True
        if attrs.get('id'):
            assert attrs['id'] not in self.ids, f'Duplicate ID: {self.path}'
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs: self.refs.append(attrs[key])


def main():
    pages = {path: Page(path) for path in ROOT.glob('*.html')}
    for path, page in pages.items():
        assert page.main, f'Missing main landmark: {path}'
        for ref in page.refs:
            url = urlsplit(ref)
            if url.scheme or url.netloc: continue
            if url.path.startswith('/api/'): continue
            target = ((ROOT / unquote(url.path.lstrip('/'))) if url.path.startswith('/')
                      else (path.parent / unquote(url.path))).resolve() if url.path else path.resolve()
            assert target.is_relative_to(ROOT.resolve()), f'Link outside site: {ref}'
            assert target.is_file(), f'Missing asset: {ref}'
            if url.fragment and target in pages:
                assert url.fragment in pages[target].ids, f'Missing anchor: {ref}'
    setup = ROOT / 'downloads/WoodSetup.exe'
    checksum = hashlib.sha256(setup.read_bytes()).hexdigest()
    assert checksum in (ROOT / 'downloads.html').read_text()
    assert checksum in (ROOT / 'downloads/SHA256SUMS.txt').read_text()
    assert setup.stat().st_size < 35 * 1024 * 1024
    launcher = ROOT / 'downloads/WoodLauncher.exe'
    launcher_checksum = hashlib.sha256(launcher.read_bytes()).hexdigest()
    assert launcher_checksum in (ROOT / 'downloads.html').read_text()
    assert launcher_checksum in (ROOT / 'downloads/SHA256SUMS.txt').read_text()
    assert launcher.stat().st_size < 20 * 1024 * 1024
    packager = ROOT / 'downloads/WoodModPackager.exe'
    packager_checksum = hashlib.sha256(packager.read_bytes()).hexdigest()
    assert packager_checksum in (ROOT / 'downloads.html').read_text()
    assert packager_checksum in (ROOT / 'downloads/SHA256SUMS.txt').read_text()
    assert packager.stat().st_size < 20 * 1024 * 1024
    downloads_page = (ROOT / 'downloads.html').read_text(encoding='utf-8')
    assert 'small Steam shortcut' in downloads_page
    assert 'A small Steam shortcut.' in downloads_page
    assert 'Install .lua mod' not in downloads_page
    assert 'Build .tungmod' in downloads_page
    assert 'Wood Mod Packager' in downloads_page
    assert 'Version 2.3.0' in (ROOT / 'index.html').read_text(encoding='utf-8')
    assert '.tungmod' in (ROOT / 'guides.html').read_text(encoding='utf-8')
    assert not (ROOT / 'mods.json').exists(), 'The public catalog must not ship a static seed.'
    assert not list(ROOT.rglob('*.lua')), 'Published mods must come only from the online catalog.'
    assert 'mods.json' not in (ROOT / 'mods.html').read_text(encoding='utf-8')
    live_split_page = (ROOT / 'live-split.html').read_text(encoding='utf-8')
    assert 'The Coordinates mod is a separate download' in live_split_page
    assert 'Hedge</li>' in live_split_page
    archive = ROOT / 'downloads/TUNG-LiveSplit-Autosplitter.zip'
    import zipfile
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert {'TUNG.asl', 'TUNG.lsl', 'TUNG-AnyPercent.lss',
                'Launch-TUNG-LiveSplit.cmd',
                'Launch-TUNG-LiveSplit.ps1'} <= set(bundle.namelist())
        assert not {'Coordinates.lua', 'JSDebug.lua'} & set(bundle.namelist())
        run = ET.fromstring(bundle.read('TUNG-AnyPercent.lss'))
        segments = [node.findtext('Name') for node in run.findall('./Segments/Segment')]
        assert segments == ['Valves unlocked', 'Valve 1', 'Valve 2', 'Valve 3',
                            'Valve 4', 'Door', 'Hedge', 'Finish']
        assert b'Coordinates.live' in bundle.read('TUNG.asl')
        assert b'NBHow' not in bundle.read('TUNG.lsl')
        assert b'NBHow' not in bundle.read('TUNG-AnyPercent.lss')
    admin_page = (ROOT / 'admin.html').read_text(encoding='utf-8')
    assert 'You create it yourself.' in admin_page
    assert 'MOD_ADMIN_TOKEN' in admin_page
    assert '256-bit secret' in admin_page
    assert 'Environment variables' in admin_page
    assert 'NETLIFY_SITE_ID' in admin_page
    assert 'NETLIFY_AUTH_TOKEN' in admin_page
    about_page = (ROOT / 'about.html').read_text(encoding='utf-8')
    assert 'waypoint' not in about_page.lower()
    print(json.dumps({'pages':len(pages),'local_links':'passed','installer_checksums':'passed',
                      'empty_catalog_has_no_seed':'passed','curator_token_instructions':'passed',
                      'mod_packager_download':'passed',
                      'livesplit_package':'passed','static_asset_size':'passed'}))


if __name__ == '__main__': main()
