import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import setup_core
import steam_setup


class SetupTests(unittest.TestCase):
    def test_journal_rollback_and_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / 'existing.txt').write_text('original')
            journal = setup_core.Journal(root)
            journal.put('existing.txt', b'changed'); journal.put('new.txt', b'new')
            with self.assertRaises(ValueError): journal.put('../escape.txt', b'no')
            journal.rollback()
            self.assertEqual((root / 'existing.txt').read_text(), 'original')
            self.assertFalse((root / 'new.txt').exists())

    def test_uninstall_preserves_custom_files_and_restores_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); shipping = root / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe'
            shipping.parent.mkdir(parents=True); shipping.write_bytes(b'game')
            (root / 'existing.txt').write_text('before')
            journal = setup_core.Journal(root)
            journal.put('existing.txt', b'installed'); journal.put('created.txt', b'wood')
            journal.put('edited.txt', b'wood'); (root / 'edited.txt').write_text('user edited')
            (root / 'custom.lua').write_text('custom mod')
            (root / 'custom.tungmod').write_bytes(b'user package')
            conflicts = setup_core.uninstall(root, check_running=False)
            self.assertEqual(conflicts, ['edited.txt'])
            self.assertEqual((root / 'existing.txt').read_text(), 'before')
            self.assertFalse((root / 'created.txt').exists())
            self.assertEqual((root / 'edited.txt').read_text(), 'user edited')
            self.assertTrue((root / 'custom.lua').exists())
            self.assertEqual((root / 'custom.tungmod').read_bytes(), b'user package')

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