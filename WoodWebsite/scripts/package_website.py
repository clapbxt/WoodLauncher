"""Build and zip this website from its locally staged release downloads."""
from pathlib import Path
import hashlib
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    for script in ('build.py', 'verify.py'):
        subprocess.run([sys.executable, str(ROOT / 'site' / script)], check=True)
    site = ROOT / 'site/dist'
    files = [ROOT / 'netlify.toml', ROOT / 'package.json', ROOT / 'package-lock.json']
    files += [path for path in site.rglob('*') if path.is_file()]
    files += [path for path in (ROOT / 'site/functions').glob('*.mjs')
              if not path.name.endswith('.test.mjs')]
    names = {path.relative_to(ROOT).as_posix() for path in files}
    required = {
        'netlify.toml', 'package.json', 'package-lock.json',
        'site/functions/mod-catalog.mjs', 'site/dist/mods.html',
        'site/dist/admin.html', 'site/dist/live-split.html',
        'site/dist/wood-launcher.json',
        'site/dist/downloads/WoodSetup.exe',
        'site/dist/downloads/WoodModPackager.exe',
        'site/dist/downloads/WoodLiveSplit.zip',
        'site/dist/downloads/WoodLiveSplit.tungmod',
    }
    assert required <= names, f'Missing deployment files: {sorted(required - names)}'

    output = ROOT / 'release/WoodWebsite-Netlify.zip'
    output.parent.mkdir(exist_ok=True)
    temporary = output.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(files):
            bundle.write(path, path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(temporary) as bundle:
        assert bundle.testzip() is None, 'Deployment archive is corrupt'
        assert set(bundle.namelist()) == names
        site_checksum = hashlib.sha256(bundle.read('site/dist/downloads/WoodSetup.exe')).hexdigest()
        downloads = bundle.read('site/dist/downloads.html').decode('utf-8')
        assert site_checksum in downloads
        assert 'WoodLauncher.exe' not in downloads
        assert 'WoodModPackager.exe' not in downloads
        developers = bundle.read('site/dist/developers.html').decode('utf-8')
        packager_checksum = hashlib.sha256(bundle.read('site/dist/downloads/WoodModPackager.exe')).hexdigest()
        assert packager_checksum in developers
        admin_page = bundle.read('site/dist/admin.html').decode('utf-8')
        assert 'MOD_ADMIN_TOKEN' in admin_page
        assert 'type="password"' in admin_page
    temporary.replace(output)
    print(f'Website deployment ZIP: {output}')
    print('Extract it, run npm ci, link the existing Netlify site, then deploy site/dist with Netlify CLI.')


if __name__ == '__main__':
    main()
