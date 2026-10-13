"""Check local links, page landmarks, release checksums, and static file limits."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import hashlib
import json
ROOT = Path(__file__).resolve().parent / 'dist'
WEBSITE = ROOT.parents[1]


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
    downloads_page = (ROOT / 'downloads.html').read_text(encoding='utf-8')
    logo = (WEBSITE / 'WoodLauncherLogo.png').read_bytes()
    assert (ROOT / 'wood-logo.png').read_bytes() == logo
    assert (ROOT / 'favicon.png').read_bytes() == logo
    assert not (ROOT / 'favicon.svg').exists()
    for path in pages:
        content = path.read_text(encoding='utf-8')
        assert content.count('class="brand-logo"') == 2
        assert 'href="favicon.png"' in content
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
    if (WEBSITE / 'release/downloads/WoodLauncher.exe').is_file():
        assert (ROOT / 'downloads/WoodLauncher.exe').is_file()
    packager = ROOT / 'downloads/WoodModPackager.exe'
    packager_checksum = hashlib.sha256(packager.read_bytes()).hexdigest()
    assert packager_checksum in (ROOT / 'developers.html').read_text()
    assert packager_checksum in (ROOT / 'downloads/SHA256SUMS.txt').read_text()
    assert packager.stat().st_size < 20 * 1024 * 1024
    manifest = json.loads((ROOT / 'wood-launcher.json').read_text(encoding='utf-8'))
    update_base = 'https://woodlauncher.clapbxt.com'
    assert manifest['installer_url'] == f'{update_base}/downloads/WoodSetup.exe'
    versions = json.loads((WEBSITE / 'release/versions.json').read_text(encoding='utf-8-sig'))
    assert manifest['version'] == versions['launcher_version']
    assert manifest['wood_version'] == versions['wood_version']
    assert manifest['sha256'] == checksum
    if 'launcher_url' in manifest:
        assert manifest['launcher_sha256'] == hashlib.sha256((ROOT / 'downloads/WoodLauncher.exe').read_bytes()).hexdigest()
    assert manifest['installer_url'].startswith('https://')
    assert 'Install .lua mod' not in downloads_page
    assert 'developers.html' in downloads_page
    assert 'Wood Mod Packager' not in downloads_page
    assert f"Version {versions['wood_version']}" in (ROOT / 'index.html').read_text(encoding='utf-8')
    assert '.tungmod' in (ROOT / 'guides.html').read_text(encoding='utf-8')
    developer_page = (ROOT / 'developers.html').read_text(encoding='utf-8')
    assert 'return {' in developer_page
    assert 'id="copy-prompt"' in developer_page
    assert 'id="ai-prompt"' in developer_page
    assert 'api.input(panel, hint, initial)' in developer_page
    assert (ROOT / 'downloads/wood-modding.md').read_text(encoding='utf-8') == (WEBSITE / 'wood-modding-source.md').read_text(encoding='utf-8')
    assert 'Write a standalone Lua mod for Wood' in (ROOT / 'downloads/wood-mod-prompt.txt').read_text(encoding='utf-8')
    assert not (ROOT / 'mods.json').exists(), 'The public catalog must not ship a static seed.'
    assert not list(ROOT.rglob('*.lua')), 'Published mods must come only from the online catalog.'
    assert 'mods.json' not in (ROOT / 'mods.html').read_text(encoding='utf-8')
    live_split_page = (ROOT / 'live-split.html').read_text(encoding='utf-8')
    assert 'https://livesplit.org/downloads/' in live_split_page
    assert 'Coordinates' not in live_split_page
    assert 'Limits and fixes' not in live_split_page
    archive = ROOT / 'downloads/WoodLiveSplit.zip'
    import zipfile
    import xml.etree.ElementTree as ET
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert {'WoodLiveSplit.tungmod', 'LiveSplit.WoodTUNG.dll', 'Wood-TUNG.lsl',
                'TUNG-AnyPercent.lss', 'Install-WoodLiveSplit.bat', 'Install-WoodLiveSplit.ps1'} <= set(bundle.namelist())
        assert not any(name.endswith('.asl') for name in bundle.namelist())
        assert bundle.read('WoodLiveSplit.tungmod') == (WEBSITE / 'release/downloads/WoodLiveSplit.tungmod').read_bytes()
        run = ET.fromstring(bundle.read('TUNG-AnyPercent.lss'))
        segments = [node.findtext('Name') for node in run.findall('./Segments/Segment')]
        assert segments == ['Valves unlocked', 'Valve 1', 'Valve 2', 'Valve 3',
                            'Valve 4', 'Door', 'Hedge', 'Finish']
        assert b'NBHow' not in bundle.read('Wood-TUNG.lsl')
        assert b'NBHow' not in bundle.read('TUNG-AnyPercent.lss')
    admin_page = (ROOT / 'admin.html').read_text(encoding='utf-8')
    assert 'You create it yourself.' in admin_page
    assert 'MOD_ADMIN_TOKEN' in admin_page
    assert '256-bit secret' in admin_page
    assert 'Environment variables' in admin_page
    assert 'NETLIFY_SITE_ID' in admin_page
    assert 'NETLIFY_AUTH_TOKEN' in admin_page
    assert 'name="mod_file"' in admin_page
    assert 'accept=".tungmod,application/octet-stream"' in admin_page
    about_page = (ROOT / 'about.html').read_text(encoding='utf-8')
    assert 'waypoint' not in about_page.lower()
    print(json.dumps({'pages':len(pages),'local_links':'passed','installer_checksums':'passed',
                      'empty_catalog_has_no_seed':'passed','curator_token_instructions':'passed',
                      'single_installer_download':'passed',
                      'livesplit_package':'passed','static_asset_size':'passed'}))


if __name__ == '__main__': main()
