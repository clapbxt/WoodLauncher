"""Steam discovery and reversible launch-option edits. No account secrets are read."""
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


def apps_node(document):
    node = document
    for key in ('UserLocalConfigStore', 'Software', 'Valve', 'Steam', 'apps'):
        actual = next((k for k in node if k.lower() == key.lower()), key)
        node = node.setdefault(actual, {})
        if not isinstance(node, dict):
            raise ValueError('Steam config has an unsupported structure.')
    return node


def configure(root, game, records, write):
    option = f'"{Path(game) / "WoodLauncher.exe"}" --launch -- %command%'
    configs = sorted((Path(root) / 'userdata').glob('*/config/localconfig.vdf'))
    if not configs:
        raise RuntimeError('No Steam user configuration found. Sign into Steam once before setup, or untick Steam integration.')
    # Restore values individually, never replace the complete account configuration.
    for path in configs:
        doc = read_vdf(path)
        app = apps_node(doc).setdefault(APP_ID, {})
        existing = next((r for r in records if r['path'] == str(path)), None)
        if existing is None:
            previous = app.get('LaunchOptions')
            if previous and '%command%' in previous:
                raise RuntimeError('An existing Steam launch wrapper is configured. Untick Steam integration to preserve it.')
            installed = option + (' ' + previous if previous else '')
            records.append({'path': str(path), 'previous': previous, 'installed': installed})
        else:
            if app.get('LaunchOptions') != existing['installed']:
                raise RuntimeError('Steam launch options changed since the previous install. Preserve them by unticking Steam integration.')
            installed = option + (' ' + existing['previous'] if existing['previous'] else '')
            existing['installed'] = installed
        app['LaunchOptions'] = installed
        write(path, vdf.dumps(doc, pretty=True))
    return len(configs)


def restore(records, write):
    conflicts = []
    for record in records:
        path = Path(record['path'])
        if not path.exists():
            conflicts.append(str(path))
            continue
        doc = read_vdf(path)
        app = apps_node(doc).get(APP_ID, {})
        if app.get('LaunchOptions') != record['installed']:
            conflicts.append(str(path))
            continue
        if record['previous'] is None:
            app.pop('LaunchOptions', None)
        else:
            app['LaunchOptions'] = record['previous']
        write(path, vdf.dumps(doc, pretty=True))
    return conflicts
