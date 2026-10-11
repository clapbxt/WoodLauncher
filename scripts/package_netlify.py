"""Build, check, and package only public static assets for manual Netlify upload."""
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
    # An explicit allowlist excludes local host identity, caches, and credentials.
    names = ['index.html', 'downloads.html', 'guides.html', 'developers.html',
             'about.html', 'style.css', 'site.js', 'favicon.svg', '_headers',
             'downloads/WoodSetup.exe', 'downloads/SHA256SUMS.txt']
    output = ROOT / 'release/Wood-Netlify.zip'
    temporary = output.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            bundle.write(site / name, name)
    with zipfile.ZipFile(temporary) as bundle:
        assert bundle.testzip() is None, 'Upload archive is corrupt'
        assert set(bundle.namelist()) == set(names)
        actual = hashlib.sha256(bundle.read('downloads/WoodSetup.exe')).hexdigest()
        assert actual in bundle.read('downloads.html').decode('utf-8')
        assert actual in bundle.read('downloads/SHA256SUMS.txt').decode('utf-8')
    temporary.replace(output)
    print(f'Netlify upload package: {output}')


if __name__ == '__main__':
    main()
