import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import launcher_core


class LauncherTests(unittest.TestCase):
    def test_version_comparison(self):
        self.assertTrue(launcher_core.newer_version('2.3.4', '2.3.3'))
        self.assertFalse(launcher_core.newer_version('2.3.3', '2.3.3'))
        self.assertFalse(launcher_core.newer_version('2.3.2', '2.3.3'))
        with self.assertRaises(ValueError):
            launcher_core.newer_version('latest', '2.3.3')

    def test_update_checks_launcher_and_wood_versions(self):
        current_parts = launcher_core.LAUNCHER_VERSION.split('.')
        next_launcher_version = '.'.join((*current_parts[:2], str(int(current_parts[2]) + 1)))
        release = {'version': next_launcher_version, 'wood_version': launcher_core.WOOD_VERSION}
        self.assertTrue(launcher_core.update_available(release))
        self.assertFalse(launcher_core.update_available({'version': launcher_core.LAUNCHER_VERSION,
                                                          'wood_version': launcher_core.WOOD_VERSION}))
        self.assertTrue(launcher_core.update_available({'version': launcher_core.LAUNCHER_VERSION,
                                                         'wood_version': '2.3.4'}))

    def test_feed_validation_and_checksum_gated_download(self):
        installer_bytes = b'installer bytes'
        launcher_bytes = b'launcher bytes'
        release = {'version': '2.3.4', 'installer_url': 'https://example.invalid/setup.exe',
                   'launcher_url': 'https://example.invalid/launcher.exe',
                   'sha256': hashlib.sha256(installer_bytes).hexdigest(),
                   'launcher_sha256': hashlib.sha256(launcher_bytes).hexdigest()}

        class Response:
            def __init__(self, content): self.content = content
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, size=-1):
                value, self.content = self.content, b''
                return value

        with patch.object(launcher_core.urllib.request, 'urlopen',
                          side_effect=[Response(installer_bytes), Response(launcher_bytes)]):
            with tempfile.TemporaryDirectory() as temp:
                installer, launcher = launcher_core.download_update(release, temp)
                self.assertEqual(installer.read_bytes(), installer_bytes)
                self.assertEqual(launcher.read_bytes(), launcher_bytes)

        invalid = dict(release, sha256='0' * 64)
        with patch.object(launcher_core.urllib.request, 'urlopen', return_value=Response(installer_bytes)):
            with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
                launcher_core.download_update(invalid, temp)

    def test_release_feed_requires_both_verified_files(self):
        feed = {'version': '1.1.0', 'wood_version': '1.1.0',
                'installer_url': 'https://example.invalid/setup.exe', 'sha256': 'a' * 64,
                'launcher_url': 'https://example.invalid/launcher.exe', 'launcher_sha256': 'b' * 64}

        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def read(self, size=-1): return json.dumps(feed).encode()

        with patch.object(launcher_core.urllib.request, 'urlopen', return_value=Response()):
            self.assertEqual(launcher_core.release_info('https://example.invalid/feed.json'), feed)
        incomplete = dict(feed)
        incomplete.pop('launcher_sha256')

        class IncompleteResponse(Response):
            def read(self, size=-1): return json.dumps(incomplete).encode()

        with patch.object(launcher_core.urllib.request, 'urlopen', return_value=IncompleteResponse()):
            with self.assertRaises(ValueError):
                launcher_core.release_info('https://example.invalid/feed.json')

    def test_game_installation_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp)
            with self.assertRaises(FileNotFoundError):
                launcher_core.installed_game(game)
            executable = game / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe'
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b'game')
            self.assertEqual(launcher_core.installed_game(game), game.resolve())


if __name__ == '__main__':
    unittest.main()
