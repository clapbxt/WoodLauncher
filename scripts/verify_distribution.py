"""Exercise the installer on isolated fake game files."""
from pathlib import Path
import json
import sys
import tempfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import setup_core
import wood_runtime


def main():
    with tempfile.TemporaryDirectory(prefix='wood-package-') as temp:
        game = Path(temp) / 'Game With Spaces'
        shipping = game / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe'
        shipping.parent.mkdir(parents=True); shipping.write_bytes(b'fake game fixture')
        preferences = game / '.wood/settings.ini'
        preferences.parent.mkdir(parents=True); preferences.write_text('speed=0.75\n')
        custom = game / 'Mods/MyMod.lua'; custom.parent.mkdir(parents=True); custom.write_text('custom')
        package = game / 'Mods/MyPackage.tungmod'; package.write_bytes(b'user package')
        assert not (ROOT / 'payload/Mods').exists(), 'Optional mods leaked into installer payload'
        data = setup_core.install(game, ROOT / 'payload', ROOT / 'release/WoodSetup.exe', check_running=False)
        assert (game / 'WoodUninstall.exe').exists()
        assert (game / '.wood/wood-logo.png').read_bytes() == (ROOT / 'WoodLauncherLogo.png').read_bytes()
        assert not (ROOT / 'payload/WoodLauncher.exe').exists()
        assert not (game / 'WoodLauncher.exe').exists()
        assert (game / 'TUNG/Binaries/Win64/ue4ss/Mods/WoodRuntime/Scripts/main.lua').exists()
        assert (game / 'TUNG/Binaries/Win64/ue4ss/Mods/WoodRuntime/Scripts/mod_package.lua').exists()
        assert sorted(path.name for path in (game / 'Mods').iterdir()) == ['MyMod.lua', 'MyPackage.tungmod']
        assert wood_runtime.installed()
        assert "root .. '/Mods'" in (game / 'TUNG/Binaries/Win64/ue4ss/Mods/WoodRuntime/Scripts/main.lua').read_text()
        assert (game / 'TUNG/Binaries/Win64/ue4ss/LICENSE').exists()
        assert custom.read_text() == 'custom'
        mods = (game / 'TUNG/Binaries/Win64/ue4ss/Mods/mods.txt').read_text()
        assert 'WoodRuntime : 1' in mods
        assert 'CheatManagerEnablerMod : 1' not in mods
        utility_preferences = game / '.wood/WoodUtilities.settings.ini'
        utility_preferences.write_text('application_volume=0.5\nsensitivity=1.25\n', encoding='utf-8')
        # Reproduce an old installer's journal so upgrade migration is exercised.
        legacy = setup_core.Journal(game)
        legacy.put('WoodLauncher.exe', b'legacy launcher')
        for name in ('TimeWarp.lua', 'WoodUtilities.lua', 'Coordinates.lua'):
            legacy.put('Mods/' + name, b'legacy bundled source')
        setup_core.install(game, ROOT / 'payload', ROOT / 'release/WoodSetup.exe', check_running=False)
        assert sorted(path.name for path in (game / 'Mods').iterdir()) == ['MyMod.lua', 'MyPackage.tungmod']
        assert not (game / 'WoodLauncher.exe').exists()
        assert utility_preferences.read_text(encoding='utf-8') == 'application_volume=0.5\nsensitivity=1.25\n'
        assert setup_core.uninstall(game, check_running=False) == []
        assert custom.read_text() == 'custom'
        assert package.read_bytes() == b'user package'
        assert shipping.read_bytes() == b'fake game fixture'
        assert preferences.read_text() == 'speed=0.75\n'
        assert not (game / 'WoodLauncher.exe').exists()
        assert utility_preferences.read_text(encoding='utf-8') == 'application_volume=0.5\nsensitivity=1.25\n'
        assert not (game / 'WoodUninstall.exe').exists()
        assert not (game / 'WoodLauncher.exe').exists()
        assert not (game / 'Mods/TimeWarp.lua').exists()
        assert not (game / 'Mods/WoodUtilities.lua').exists()
        assert not (game / 'Mods/Coordinates.lua').exists()
        assert custom.read_text() == 'custom'
        assert not (game / 'TUNG/Binaries/Win64/dwmapi.dll').exists()
        print(json.dumps({'install_upgrade_uninstall': 'passed', 'tracked_files': len(data['files']), 'custom_mods': 'preserved'}))


if __name__ == '__main__': main()
