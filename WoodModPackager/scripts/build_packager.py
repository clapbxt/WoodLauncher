"""Build only WoodModPackager.exe."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
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
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed',
        '--icon', str(icon), '--add-data', str(icon) + ';.',
        '--add-data', str(ROOT / 'WoodLauncherLogo.png') + ';.',
        '--distpath', str(release), '--workpath', str(cache / 'pyinstaller'),
        '--specpath', str(cache), '--name', 'WoodModPackager', str(ROOT / 'WoodModPackager.py')],
        check=True, cwd=ROOT)
    digest = hashlib.sha256((release / 'WoodModPackager.exe').read_bytes()).hexdigest()
    (release / 'SHA256SUMS.txt').write_text(digest + '  WoodModPackager.exe\n', encoding='ascii')
    print(f'Wood Mod Packager: {release / "WoodModPackager.exe"}')


if __name__ == '__main__':
    main()
