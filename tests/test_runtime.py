import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import wood_runtime as runtime
from WoodLauncher import discover_mods


class RuntimeTests(unittest.TestCase):
    def test_rejects_invalid_speed_and_unknown_commands(self):
        for value in (0, -1, 4.01, float('nan'), float('inf'), 'garbage'):
            with self.assertRaises((ValueError, TypeError)):
                runtime.valid_speed(value)
        self.assertEqual(runtime.valid_speed(0.05), 0.05)
        self.assertEqual(runtime.valid_speed(4), 4)
        with tempfile.TemporaryDirectory() as folder, patch.object(runtime, 'DATA', Path(folder)):
            with self.assertRaises(ValueError): runtime.Bridge().send('execute', 'anything')

    def test_commands_do_not_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(runtime, 'DATA', Path(folder)):
            bridge = runtime.Bridge()
            first = bridge.send('enabled', False)
            second = bridge.send('speed', 0.25)
            records = (Path(folder) / 'commands.log').read_text().splitlines()
            self.assertEqual(records, [f'{first}|enabled|false', f'{second}|speed|0.25'])

    def test_previous_session_status_is_offline(self):
        import os
        with tempfile.TemporaryDirectory() as folder, patch.object(runtime, 'DATA', Path(folder)):
            path = Path(folder) / 'status.json'
            path.write_text('{"ready":true,"applied":0.5}')
            os.utime(path, (1, 1))
            self.assertFalse(runtime.Bridge().status()['connected'])
            path.write_text('{broken')
            self.assertFalse(runtime.Bridge().status()['connected'])

    def test_install_preserves_user_mods_settings_and_loader_preferences(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            binary = base / 'TUNG/Binaries/Win64'
            loader = binary / 'ue4ss'
            source = base / 'NativeMods/WoodRuntime'
            (source / 'Scripts').mkdir(parents=True)
            (source / 'Scripts/main.lua').write_text('-- Wood')
            (loader / 'Mods/OtherMod').mkdir(parents=True)
            (binary / 'TUNG-Win64-Shipping.exe').write_bytes(b'game')
            (binary / 'dwmapi.dll').write_bytes(b'proxy')
            (loader / 'UE4SS.dll').write_bytes(b'existing-runtime')
            (loader / 'UE4SS-settings.ini').write_text('user preferences')
            (loader / 'Mods/OtherMod/user.lua').write_text('keep me')
            (loader / 'Mods/mods.txt').write_text('OtherMod : 1\nConsoleEnablerMod : 1\nWoodRuntime : 0\n')
            data = base / '.wood'
            data.mkdir()
            (data / 'settings.ini').write_text('speed=0.25\nenabled=false\n')
            with patch.multiple(runtime, BASE=base, BIN=binary, DATA=data, RUNTIME=loader, SOURCE=source):
                runtime.install_runtime()
                runtime.install_runtime()
            self.assertEqual((loader / 'Mods/OtherMod/user.lua').read_text(), 'keep me')
            self.assertEqual((loader / 'UE4SS-settings.ini').read_text(), 'user preferences')
            self.assertEqual((data / 'settings.ini').read_text(), 'speed=0.25\nenabled=false\n')
            modlist = (loader / 'Mods/mods.txt').read_text()
            self.assertEqual(modlist.count('WoodRuntime : 1'), 1)
            self.assertIn('OtherMod : 1', modlist)
            self.assertIn('ConsoleEnablerMod : 1', modlist)

    def test_discovery_reads_manifests_without_running_python_mods(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / 'Mods').mkdir()
            (base / 'Mods/Bad.py').write_text("__manifest__ = {'name':'Safe manifest'}\nraise Exception('must not execute')")
            with patch('WoodLauncher.BASE', base):
                mods = discover_mods()
            self.assertEqual(mods[0]['name'], 'Safe manifest')
            self.assertEqual(mods[0]['state'], 'Legacy Python')


if __name__ == '__main__': unittest.main()
