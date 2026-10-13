"""Build only WoodLauncher.exe."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from launcher_core import LAUNCHER_VERSION
from branding import make_icon


def main():
    import tkinter
    tkinter.Tcl().eval('info library')
    from PyInstaller.utils.hooks import tcl_tk
    if not tcl_tk.tcltk_info.available:
        raise RuntimeError('PyInstaller cannot discover Tcl/Tk.')
    release = ROOT / 'release'
    cache = ROOT / '.build'
    release.mkdir(exist_ok=True)
    cache.mkdir(exist_ok=True)
    icon = cache / 'wood.ico'
    make_icon(icon)
    version = cache / 'launcher_version.txt'
    version_tuple = f"({','.join(LAUNCHER_VERSION.split('.'))},0)"
    version.write_text(
        f"VSVersionInfo(ffi=FixedFileInfo(filevers={version_tuple},prodvers={version_tuple},mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904B0',[StringStruct('CompanyName','Wood contributors'),StringStruct('FileDescription','Wood Launcher for TUNG'),StringStruct('FileVersion','{LAUNCHER_VERSION}'),StringStruct('InternalName','WoodLauncher'),StringStruct('OriginalFilename','WoodLauncher.exe'),StringStruct('ProductName','Wood Launcher for TUNG'),StringStruct('ProductVersion','{LAUNCHER_VERSION}')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])",
        encoding='utf-8')
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
        '--icon', str(icon), '--add-data', str(icon) + ';.',
        '--add-data', str(ROOT / 'WoodLauncherLogo.png') + ';.', '--version-file', str(version),
        '--hidden-import', 'vdf', '--distpath', str(release), '--workpath', str(cache / 'pyinstaller'),
        '--specpath', str(cache), '--name', 'WoodLauncher', str(ROOT / 'WoodLauncher.py')],
        check=True, cwd=ROOT)
    subprocess.run([str(release / 'WoodLauncher.exe'), '--verify-tk'], check=True, timeout=30, cwd=ROOT)
    checksum = hashlib.sha256((release / 'WoodLauncher.exe').read_bytes()).hexdigest()
    (release / 'SHA256SUMS.txt').write_text(checksum + '  WoodLauncher.exe\n', encoding='ascii')
    print(f'Wood Launcher {LAUNCHER_VERSION}: {release / "WoodLauncher.exe"}')


if __name__ == '__main__':
    main()
