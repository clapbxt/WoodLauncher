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
            target = (path.parent / unquote(url.path)).resolve() if url.path else path.resolve()
            assert target.is_relative_to(ROOT.resolve()), f'Link outside site: {ref}'
            assert target.is_file(), f'Missing asset: {ref}'
            if url.fragment and target in pages:
                assert url.fragment in pages[target].ids, f'Missing anchor: {ref}'
    setup = ROOT / 'downloads/WoodSetup.exe'
    checksum = hashlib.sha256(setup.read_bytes()).hexdigest()
    assert checksum in (ROOT / 'downloads.html').read_text()
    assert checksum in (ROOT / 'downloads/SHA256SUMS.txt').read_text()
    assert setup.stat().st_size < 25 * 1024 * 1024
    print(json.dumps({'pages':len(pages),'local_links':'passed','installer_checksum':'passed','static_asset_size':'passed'}))


if __name__ == '__main__': main()
