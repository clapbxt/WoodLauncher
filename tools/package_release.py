"""Package source, verified app builds and website deployment into one ZIP."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile

REPOSITORY = Path(__file__).resolve().parents[1]


def package(workspace):
    workspace = Path(workspace).resolve()
    version = json.loads((REPOSITORY / 'NativeMods/WoodRuntime/manifest.json').read_text())['version']
    output = workspace / 'releases' / version
    output.mkdir(parents=True, exist_ok=True)
    source = output / f'Wood-{version}-source.zip'
    subprocess.run(['git', '-C', str(REPOSITORY), 'archive', '--format=zip',
                    '--output', str(source), 'HEAD'], check=True)
    files = {
        'UE4SS_v3.0.1-1164-g5e627997.zip': workspace / 'WoodSetup/.build/UE4SS.zip',
        'WoodSetup.exe': workspace / 'WoodSetup/release/WoodSetup.exe',
        'WoodLauncher.exe': workspace / 'WoodLauncher/release/WoodLauncher.exe',
        'WoodWebsite-Netlify.zip': workspace / 'WoodWebsite/release/WoodWebsite-Netlify.zip',
        'WoodModPackager.exe': workspace / 'WoodWebsite/release/downloads/WoodModPackager.exe',
        'WoodLiveSplit.zip': workspace / 'WoodWebsite/release/downloads/WoodLiveSplit.zip',
        'WoodLiveSplit.tungmod': workspace / 'WoodWebsite/release/downloads/WoodLiveSplit.tungmod',
        'PUBLISHING.md': REPOSITORY / f'docs/RELEASE-{version}.md',
        'BUILDING.md': REPOSITORY / 'BUILDING.md',
    }
    for name, path in files.items():
        shutil.copy2(path, output / name)
    sums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n'
                   for path in sorted(output.iterdir()) if path.is_file()
                   and path.name not in {'SHA256SUMS.txt', f'Wood-{version}.zip'})
    (output / 'SHA256SUMS.txt').write_text(sums, encoding='ascii')
    bundle = output / f'Wood-{version}.zip'
    with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.iterdir()):
            if path.is_file() and path != bundle:
                archive.write(path, path.name)
    with zipfile.ZipFile(bundle) as archive:
        assert archive.testzip() is None
        assert set(files) | {source.name, 'SHA256SUMS.txt'} == set(archive.namelist())
    print(bundle)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('workspace', type=Path)
    package(parser.parse_args().workspace)
