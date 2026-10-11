import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import wood_runtime as runtime


class RuntimeTests(unittest.TestCase):
    def test_rejects_invalid_speed(self):
        for value in (0, -1, 4.01, float('nan'), float('inf'), 'garbage'):
            with self.assertRaises((ValueError, TypeError)):
                runtime.valid_speed(value)
        self.assertEqual(runtime.valid_speed(0.05), 0.05)
        self.assertEqual(runtime.valid_speed(4), 4)

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
            with patch.multiple(runtime, BASE=base, BIN=binary, DATA=data, RUNTIME=loader):
                runtime.install_runtime(source=source)
                runtime.install_runtime(source=source)
            self.assertEqual((loader / 'Mods/OtherMod/user.lua').read_text(), 'keep me')
            self.assertEqual((loader / 'UE4SS-settings.ini').read_text(), 'user preferences')
            self.assertEqual((data / 'settings.ini').read_text(), 'speed=0.25\nenabled=false\n')
            modlist = (loader / 'Mods/mods.txt').read_text()
            self.assertEqual(modlist.count('WoodRuntime : 1'), 1)
            self.assertIn('OtherMod : 1', modlist)
            self.assertIn('ConsoleEnablerMod : 1', modlist)

    def test_install_creates_user_mods_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            binary = base / 'TUNG/Binaries/Win64'
            binary.mkdir(parents=True)
            loader = binary / 'ue4ss'
            loader.mkdir(parents=True)
            (loader / 'Mods').mkdir(parents=True)
            source = base / 'NativeMods/WoodRuntime'
            (source / 'Scripts').mkdir(parents=True)
            (source / 'Scripts/main.lua').write_text('-- Wood')
            (binary / 'TUNG-Win64-Shipping.exe').write_bytes(b'game')
            (binary / 'dwmapi.dll').write_bytes(b'proxy')
            (loader / 'UE4SS.dll').write_bytes(b'existing-runtime')
            (loader / 'Mods/mods.txt').write_text('OtherMod : 1\n')
            data = base / '.wood'
            data.mkdir()
            with patch.multiple(runtime, BASE=base, BIN=binary, DATA=data, RUNTIME=loader):
                runtime.install_runtime(source=source)
            self.assertTrue((base / 'Mods').is_dir())


if __name__ == '__main__': unittest.main()