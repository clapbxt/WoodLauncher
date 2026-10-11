"""Build the Wood tools and loader-only installer with pinned UE4SS."""
from pathlib import Path
import hashlib
import shutil
import subprocess
import sys
import urllib.request
import importlib.metadata
import json
from branding import make_icon
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from wood_runtime import RUNTIME_URL, RUNTIME_SHA256


def main():
    # Import alone can succeed with unusable Tcl data. PyInstaller then silently
    # omits tkinter, producing executables that crash before setup opens.
    import tkinter
    try:
        tkinter.Tcl().eval('info library')
    except tkinter.TclError as error:
        raise RuntimeError('Tcl/Tk cannot initialize in this build environment. '
                           'Use a Python installation with working Tcl/Tk and access to its data files.') from error
    out = ROOT / 'release'; out.mkdir(exist_ok=True)
    (out / 'WoodLauncher.exe').unlink(missing_ok=True)
    cache = ROOT / '.build'; cache.mkdir(exist_ok=True)
    make_icon(cache / 'wood.ico')
    version = cache / 'version.txt'
    version.write_text("VSVersionInfo(ffi=FixedFileInfo(filevers=(2,3,2,0),prodvers=(2,3,2,0),mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','Wood contributors'),StringStruct('FileDescription','Wood for TUNG'),StringStruct('FileVersion','2.3.2'),StringStruct('InternalName','Wood'),StringStruct('OriginalFilename','WoodSetup.exe'),StringStruct('ProductName','Wood for TUNG'),StringStruct('ProductVersion','2.3.2')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])")
    archive = cache / 'UE4SS.zip'
    if not archive.exists():
        with urllib.request.urlopen(RUNTIME_URL, timeout=120) as response, archive.open('wb') as target:
            shutil.copyfileobj(response, target)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != RUNTIME_SHA256:
        raise ValueError('Official UE4SS checksum mismatch')
    common = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
              '--icon', str(cache / 'wood.ico'), '--add-data', str(cache / 'wood.ico') + ';.',
              '--add-data', str(ROOT / 'WoodLauncherLogo.png') + ';.',
              '--version-file', str(version),
              '--distpath', str(out), '--workpath', str(cache / 'pyinstaller'), '--specpath', str(cache)]
    packager_version = cache / 'packager_version.txt'
    packager_version.write_text(version.read_text(encoding='utf-8').replace(
        "StringStruct('FileDescription','Wood for TUNG')",
        "StringStruct('FileDescription','Wood Mod Packager for TUNG')",
    ).replace("StringStruct('InternalName','Wood')", "StringStruct('InternalName','WoodModPackager')").replace(
        "StringStruct('OriginalFilename','WoodSetup.exe')",
        "StringStruct('OriginalFilename','WoodModPackager.exe')",
    ), encoding='utf-8')
    subprocess.run([
        sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
        '--icon', str(cache / 'wood.ico'), '--version-file', str(packager_version),
        '--add-data', str(cache / 'wood.ico') + ';.',
        '--add-data', str(ROOT / 'WoodLauncherLogo.png') + ';.',
        '--distpath', str(out), '--workpath', str(cache / 'packager-pyinstaller'),
        '--specpath', str(cache), '--name', 'WoodModPackager', str(ROOT / 'WoodModPackager.py'),
    ], check=True, cwd=ROOT)
    payload = ROOT / 'payload'
    # Recreate the staging folder so an old build cannot leak optional mods.
    if payload.resolve() != ROOT.resolve() / 'payload':
        raise ValueError('Payload staging directory points outside the project.')
    if payload.exists():
        shutil.rmtree(payload)
    payload.mkdir()
    shutil.copy2(archive, payload)
    shutil.copy2(ROOT / 'WoodLauncherLogo.png', payload / 'WoodLauncherLogo.png')
    shutil.copytree(ROOT / 'NativeMods/WoodRuntime', payload / 'NativeMods/WoodRuntime', dirs_exist_ok=True)
    notices = [ROOT / 'LICENSE', Path(sys.base_prefix) / 'LICENSE.txt']
    notices += list((Path(sys.base_prefix) / 'tcl').glob('*/license*'))
    for package in ('vdf', 'pyinstaller'):
        distribution = importlib.metadata.distribution(package)
        notices += [Path(distribution.locate_file(path)) for path in distribution.files
                    if 'license' in str(path).lower() and Path(distribution.locate_file(path)).is_file()]
    (payload / 'Wood-Licenses.txt').write_text('\n\n'.join('=== '+path.name+' ===\n'+path.read_text(encoding='utf-8', errors='replace') for path in notices if path.exists()), encoding='utf-8')
    subprocess.run(common + ['--name', 'WoodSetup', '--add-data', str(payload) + ';payload', str(ROOT / 'WoodSetup.py')], check=True, cwd=ROOT)
    report = cache / 'payload-report.json'
    report.unlink(missing_ok=True)
    subprocess.run([str(out / 'WoodSetup.exe'), '--verify-payload', '--report', str(report)],
                   check=True, timeout=30, cwd=ROOT)
    if json.loads(report.read_text(encoding='utf-8')) != {'version': '2.3.2', 'runtime_valid': True}:
        raise ValueError('Built installer failed its executable payload check.')
    checksums = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.name + '\n' for path in sorted(out / name for name in ('WoodSetup.exe', 'WoodModPackager.exe')))
    (out / 'SHA256SUMS.txt').write_text(checksums)
    print(f'Release built: {out}')


if __name__ == '__main__': main()
