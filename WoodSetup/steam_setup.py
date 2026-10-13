"""Steam discovery only. No launch-option edits needed; UE4SS loads via proxy DLL."""
from pathlib import Path
import os
import vdf

APP_ID = '4341400'


def steam_root():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
            return Path(winreg.QueryValueEx(key, 'SteamPath')[0])
    except OSError:
        return Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'Steam'


def read_vdf(path):
    return vdf.loads(Path(path).read_text(encoding='utf-8-sig'))


def find_games(root=None):
    root = Path(root or steam_root())
    libraries = [root]
    config = root / 'steamapps/libraryfolders.vdf'
    if config.exists():
        for value in read_vdf(config).get('libraryfolders', {}).values():
            if isinstance(value, dict) and value.get('path'):
                libraries.append(Path(value['path']))
    games = []
    for library in libraries:
        manifest = library / f'steamapps/appmanifest_{APP_ID}.acf'
        if manifest.exists():
            name = read_vdf(manifest).get('AppState', {}).get('installdir')
            if name:
                game = library / 'steamapps/common' / name
                if (game / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe').is_file():
                    games.append(game.resolve())
    return list(dict.fromkeys(games))


def configure(root, game, records, write):
    """No-op: UE4SS loads automatically via dwmapi.dll proxy. No Steam launch wrapper needed."""
    return 0


def restore(records, write):
    """No-op: no Steam launch options were modified."""
    return []
