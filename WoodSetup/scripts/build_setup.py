"""Build WoodSetup.exe with the runtime source bundled in WoodLauncher."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
LOADER = WORKSPACE / 'WoodLauncher' / 'runtime-source'
if (WORKSPACE / 'NativeMods/WoodRuntime').is_dir():
    LOADER = WORKSPACE  # Standalone GitHub source checkout.
sys.path.insert(0, str(ROOT))
from setup_core import VERSION
from wood_runtime import RUNTIME_URL, RUNTIME_SHA256, RUNTIME_VERSION
from branding import make_icon


def main():
    import tkinter
    tkinter.Tcl().eval('info library')
    from PyInstaller.utils.hooks import tcl_tk
    if not tcl_tk.tcltk_info.available:
        raise RuntimeError('PyInstaller cannot discover Tcl/Tk.')
    release = ROOT / 'release'
    cache = ROOT / '.build'
    payload = ROOT / 'payload'
    release.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    make_icon(cache / 'wood.ico')
    archive = cache / 'UE4SS.zip'
    if not archive.exists():
        urls = (RUNTIME_URL, f'https://github.com/clapbxt/WoodLauncher/releases/download/v{VERSION}/{RUNTIME_VERSION}.zip')
        failure = None
        for url in urls:
            try:
                request = urllib.request.Request(url, headers={'User-Agent': 'WoodSetup-build'})
                with urllib.request.urlopen(request, timeout=30) as response, archive.open('wb') as target:
                    shutil.copyfileobj(response, target)
                break
            except OSError as exc:
                failure = exc
                archive.unlink(missing_ok=True)
        if not archive.exists():
            raise RuntimeError(f'Pinned UE4SS archive unavailable ({failure}). Copy {RUNTIME_VERSION}.zip '
                               f'from the Wood release bundle to {archive} and rebuild.')
    if hashlib.sha256(archive.read_bytes()).hexdigest() != RUNTIME_SHA256:
        raise ValueError('Official UE4SS checksum mismatch.')
    if payload.exists():
        shutil.rmtree(payload)
    payload.mkdir()
    shutil.copy2(archive, payload)
    shutil.copy2(LOADER / 'WoodLauncherLogo.png', payload / 'WoodLauncherLogo.png')
    shutil.copytree(LOADER / 'NativeMods/WoodRuntime', payload / 'NativeMods/WoodRuntime')
    python_root = Path(sys.base_prefix)
    python_license = next((path for path in (
        python_root / 'LICENSE.txt',
        python_root / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'LICENSE.txt',
    ) if path.is_file()), None)
    notices = [ROOT / 'LICENSE', LOADER / 'LICENSE', LOADER / 'THIRD_PARTY.md']
    if python_license:
        notices.append(python_license)
    for library_root in (python_root / 'tcl', python_root / 'lib'):
        for name in ('tcl8.6', 'tk8.6'):
            notices += list((library_root / name).glob('*/license*'))
            notices += list((library_root / name).glob('license*'))
    for package in ('pyinstaller',):
        distribution = importlib.metadata.distribution(package)
        notices += [Path(distribution.locate_file(path)) for path in distribution.files
                    if 'license' in str(path).lower() and Path(distribution.locate_file(path)).is_file()]
    (payload / 'Wood-Licenses.txt').write_text(
        '\n\n'.join('=== ' + path.name + ' ===\n' + path.read_text(encoding='utf-8', errors='replace')
                    for path in notices if path.is_file()), encoding='utf-8')
    version_tuple = f"({','.join(VERSION.split('.'))},0)"
    version_file = cache / 'setup_version.txt'
    version_file.write_text(
        f"VSVersionInfo(ffi=FixedFileInfo(filevers={version_tuple},prodvers={version_tuple},mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','Wood contributors'),StringStruct('FileDescription','Wood for TUNG'),StringStruct('FileVersion','{VERSION}'),StringStruct('InternalName','Wood'),StringStruct('OriginalFilename','WoodSetup.exe'),StringStruct('ProductName','Wood for TUNG'),StringStruct('ProductVersion','{VERSION}')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])",
        encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
        '--icon', str(cache / 'wood.ico'), '--add-data', str(cache / 'wood.ico') + ';.',
        '--add-data', str(ROOT / 'WoodLauncherLogo.png') + ';.',
        '--add-data', str(payload) + ';payload', '--version-file', str(version_file),
        '--distpath', str(release), '--workpath', str(cache / 'pyinstaller'), '--specpath', str(cache),
        '--name', 'WoodSetup', str(ROOT / 'WoodSetup.py')], check=True, cwd=ROOT)
    report = cache / 'payload-report.json'
    report.unlink(missing_ok=True)
    subprocess.run([str(release / 'WoodSetup.exe'), '--verify-payload', '--report', str(report)],
                   check=True, timeout=30, cwd=ROOT)
    if json.loads(report.read_text(encoding='utf-8')) != {
            'version': VERSION, 'runtime_valid': True, 'logo_valid': True}:
        raise ValueError('Built installer failed its runtime or logo resource check.')
    digest = hashlib.sha256((release / 'WoodSetup.exe').read_bytes()).hexdigest()
    (release / 'SHA256SUMS.txt').write_text(digest + '  WoodSetup.exe\n', encoding='ascii')
    print(f'Wood Setup {VERSION}: {release / "WoodSetup.exe"}')


if __name__ == '__main__':
    main()
