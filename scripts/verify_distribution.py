"""Exercise the real payload on an isolated fake game, never a user's Steam config."""
from pathlib import Path
import json
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup_core
import steam_setup


def main():
    with tempfile.TemporaryDirectory(prefix='wood-package-') as temp:
        game = Path(temp) / 'Game With Spaces'
        shipping = game / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe'
        shipping.parent.mkdir(parents=True); shipping.write_bytes(b'fake game fixture')
        custom = game / 'NativeMods/MyMod/wood.lua'; custom.parent.mkdir(parents=True); custom.write_text('custom')
        steam = Path(temp) / 'Steam'
        config = steam / 'userdata/1/config/localconfig.vdf'; config.parent.mkdir(parents=True)
        doc = {}; steam_setup.apps_node(doc)['4341400'] = {'LaunchOptions': '-windowed'}
        config.write_text(steam_setup.vdf.dumps(doc, pretty=True))
        data = setup_core.install(game, ROOT / 'payload', ROOT / 'release/WoodSetup.exe', root=steam, check_running=False)
        assert (game / 'WoodLauncher.exe').exists()
        assert (game / 'WoodUninstall.exe').exists()
        assert (game / 'TUNG/Binaries/Win64/ue4ss/Mods/WoodRuntime/Scripts/main.lua').exists()
        assert (game / 'NativeMods/WoodUtilities/wood.lua').exists()
        extensions = (game / 'TUNG/Binaries/Win64/ue4ss/Mods/WoodRuntime/Scripts/extensions.lua').read_text()
        assert 'WoodUtilities' in extensions
        assert (game / 'TUNG/Binaries/Win64/ue4ss/LICENSE').exists()
        assert custom.read_text() == 'custom'
        mods = (game / 'TUNG/Binaries/Win64/ue4ss/Mods/mods.txt').read_text()
        assert 'WoodRuntime : 1' in mods
        assert 'CheatManagerEnablerMod : 1' not in mods
        option = steam_setup.apps_node(steam_setup.read_vdf(config))['4341400']['LaunchOptions']
        assert '--launch -- %command% -windowed' in option
        preferences = game / '.wood/WoodUtilities.settings.ini'
        preferences.write_text('master_volume=0.5\ninvert_y=true\n', encoding='utf-8')
        setup_core.install(game, ROOT / 'payload', ROOT / 'release/WoodSetup.exe', root=steam, check_running=False)
        assert preferences.read_text(encoding='utf-8') == 'master_volume=0.5\ninvert_y=true\n'
        assert setup_core.uninstall(game, check_running=False) == []
        assert custom.read_text() == 'custom'
        assert shipping.read_bytes() == b'fake game fixture'
        assert (game / '.wood/settings.ini').exists()
        assert preferences.read_text(encoding='utf-8') == 'master_volume=0.5\ninvert_y=true\n'
        assert not (game / 'WoodLauncher.exe').exists()
        assert not (game / 'WoodUninstall.exe').exists()
        assert not (game / 'TUNG/Binaries/Win64/dwmapi.dll').exists()
        assert steam_setup.apps_node(steam_setup.read_vdf(config))['4341400']['LaunchOptions'] == '-windowed'
        print(json.dumps({'install_upgrade_uninstall': 'passed', 'tracked_files': len(data['files']), 'custom_mods': 'preserved', 'steam_options': 'restored'}))


if __name__ == '__main__': main()
