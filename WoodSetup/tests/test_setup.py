import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import setup_core
import steam_setup


class SetupTests(unittest.TestCase):
    def test_journal_normalizes_root_before_checking_containment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'alias').mkdir()
            journal = setup_core.Journal(root / 'alias' / '..')
            journal.put('inside.txt', b'valid target')
            self.assertEqual(journal.game, root.resolve())
            self.assertEqual((root / 'inside.txt').read_bytes(), b'valid target')
            with self.assertRaises(ValueError):
                journal.put('../escape.txt', b'outside')

    def test_upgrade_retires_only_unchanged_owned_mods_and_rolls_back(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'Mods').mkdir()
            (root / 'Mods/Coordinates.lua').write_bytes(b'original user mod')
            journal = setup_core.Journal(root)
            journal.put('WoodLauncher.exe', b'old launcher')
            journal.put('Mods/TimeWarp.lua', b'old bundled mod')
            journal.put('Mods/Coordinates.lua', b'old bundled mod')
            journal.put('Mods/WoodUtilities.lua', b'old bundled mod')
            (root / 'Mods/WoodUtilities.lua').write_bytes(b'user edit')
            (root / 'Mods/TimeWarp.tungmod').write_bytes(b'user package')
            upgrade = setup_core.Journal(root)
            upgrade.retire('WoodLauncher.exe')
            for name in ('TimeWarp.lua', 'Coordinates.lua', 'WoodUtilities.lua'):
                upgrade.retire('Mods/' + name)
            self.assertFalse((root / 'Mods/TimeWarp.lua').exists())
            self.assertFalse((root / 'WoodLauncher.exe').exists())
            self.assertEqual((root / 'Mods/Coordinates.lua').read_bytes(), b'original user mod')
            self.assertEqual((root / 'Mods/WoodUtilities.lua').read_bytes(), b'user edit')
            self.assertEqual((root / 'Mods/TimeWarp.tungmod').read_bytes(), b'user package')
            upgrade.rollback()
            self.assertEqual((root / 'WoodLauncher.exe').read_bytes(), b'old launcher')
            self.assertEqual((root / 'Mods/TimeWarp.lua').read_bytes(), b'old bundled mod')
            self.assertEqual((root / 'Mods/Coordinates.lua').read_bytes(), b'old bundled mod')

    def test_journal_rollback_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'existing.txt').write_text('original')
            journal = setup_core.Journal(root)
            journal.put('existing.txt', b'changed'); journal.put('new.txt', b'new')
            with self.assertRaises(ValueError): journal.put('../escape.txt', b'no')
            journal.rollback()
            self.assertEqual((root / 'existing.txt').read_text(), 'original')
            self.assertFalse((root / 'new.txt').exists())

    def test_uninstall_removes_changed_owned_files_and_restores_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); shipping = root / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe'
            shipping.parent.mkdir(parents=True); shipping.write_bytes(b'game')
            (root / 'existing.txt').write_text('before')
            journal = setup_core.Journal(root)
            journal.put('existing.txt', b'installed'); journal.put('created.txt', b'wood')
            journal.put('edited.txt', b'wood'); (root / 'edited.txt').write_text('user edited')
            journal.put('Mods/SetupBundledMod.lua', b'setup bundled mod')
            (root / 'custom.lua').write_text('custom mod')
            (root / 'custom.tungmod').write_bytes(b'user package')
            conflicts = setup_core.uninstall(root, check_running=False)
            self.assertEqual(conflicts, [])
            self.assertEqual((root / 'existing.txt').read_text(), 'before')
            self.assertFalse((root / 'created.txt').exists())
            self.assertFalse((root / 'edited.txt').exists())
            self.assertFalse((root / 'Mods/SetupBundledMod.lua').exists())
            self.assertTrue((root / 'custom.lua').exists())
            self.assertEqual((root / 'custom.tungmod').read_bytes(), b'user package')
            self.assertFalse((root / '.wood/backups').exists())

    def test_steam_find_games(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)  # This is the Steam root
            library = root / 'SteamLibrary'
            library.mkdir()
            (library / 'steamapps').mkdir()
            # Create libraryfolders.vdf in the Steam root
            (root / 'steamapps').mkdir()
            library_vdf = root / 'steamapps/libraryfolders.vdf'
            import vdf
            vdf_data = {'libraryfolders': {'0': {'path': str(library)}}}
            library_vdf.write_text(vdf.dumps(vdf_data, pretty=True))
            appmanifest = library / 'steamapps' / 'appmanifest_4341400.acf'
            appmanifest.write_text(vdf.dumps({'AppState': {'installdir': 'TUNG'}}, pretty=True))
            game_dir = library / 'steamapps/common/TUNG'
            game_dir.mkdir(parents=True)
            (game_dir / 'TUNG/Binaries/Win64').mkdir(parents=True)
            (game_dir / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe').write_bytes(b'game')
            games = steam_setup.find_games(root)
            self.assertTrue(any('TUNG' in str(g) for g in games))

    def test_steam_configure_is_noop(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            game = root / 'TUNG'
            game.mkdir()
            records = []
            write = lambda p, text: p.write_text(text)
            # configure should return 0 and do nothing
            count = steam_setup.configure(root, game, records, write)
            self.assertEqual(count, 0)

    def test_steam_restore_is_noop(self):
        records = []
        write = lambda p, text: p.write_text(text)
        # restore should return empty conflicts
        conflicts = steam_setup.restore(records, write)
        self.assertEqual(conflicts, [])


if __name__ == '__main__': unittest.main()
