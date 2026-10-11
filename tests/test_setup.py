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
            conflicts = setup_core.uninstall(root, check_running=False)
            self.assertEqual(conflicts, ['edited.txt'])
            self.assertEqual((root / 'existing.txt').read_text(), 'before')
            self.assertFalse((root / 'created.txt').exists())
            self.assertEqual((root / 'edited.txt').read_text(), 'user edited')
            self.assertTrue((root / 'custom.lua').exists())

    def test_steam_roundtrip_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / 'userdata/1/config/localconfig.vdf'
            path.parent.mkdir(parents=True)
            doc = {}; apps = steam_setup.apps_node(doc)
            apps['4341400'] = {'LaunchOptions': '-windowed'}; apps['123'] = {'LaunchOptions': 'other'}
            path.write_text(steam_setup.vdf.dumps(doc, pretty=True))
            records = []
            write = lambda p, text: p.write_text(text, encoding='utf-8')
            steam_setup.configure(root, root / 'Game Space', records, write)
            doc = steam_setup.read_vdf(path); steam_setup.apps_node(doc)['123']['NewSetting'] = 'keep'
            write(path, steam_setup.vdf.dumps(doc))
            self.assertEqual(steam_setup.restore(records, write), [])
            apps = steam_setup.apps_node(steam_setup.read_vdf(path))
            self.assertEqual(apps['4341400']['LaunchOptions'], '-windowed')
            self.assertEqual(apps['123']['NewSetting'], 'keep')

    def test_steam_uninstall_preserves_later_launch_options(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / 'userdata/1/config/localconfig.vdf'
            path.parent.mkdir(parents=True); path.write_text('"UserLocalConfigStore" {}')
            records = []; write = lambda p, text: p.write_text(text)
            steam_setup.configure(root, root, records, write)
            doc = steam_setup.read_vdf(path); steam_setup.apps_node(doc)['4341400']['LaunchOptions'] = 'changed by user'
            write(path, steam_setup.vdf.dumps(doc))
            self.assertEqual(steam_setup.restore(records, write), [str(path)])
            self.assertEqual(steam_setup.apps_node(steam_setup.read_vdf(path))['4341400']['LaunchOptions'], 'changed by user')


if __name__ == '__main__': unittest.main()
