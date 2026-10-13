from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import speedrun_core as speedrun
import update_core


class SpeedrunTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.game = Path(temporary.name)
        self.mods = self.game / 'TUNG/Binaries/Win64/ue4ss/Mods'
        (self.mods / 'WoodRuntime/Scripts').mkdir(parents=True)
        (self.mods / 'WoodRuntime/Scripts/main.lua').write_text('-- runtime')
        (self.mods / 'Other/Scripts').mkdir(parents=True)
        (self.mods / 'Other/enabled.txt').write_bytes(b'')
        (self.mods / 'Other/Scripts/main.lua').write_text('mod code')
        (self.mods / 'native.dll').write_bytes(b'native')
        self.original = 'Other : 1\nWoodRuntime : 1\n'
        (self.mods / 'mods.txt').write_text(self.original)
        (self.game / 'Mods').mkdir()
        (self.game / 'Mods/user.lua').write_text('keep')

    def test_roundtrip_isolates_autoload_and_native_mods_preserves_user_files(self):
        speedrun.apply_mode(self.game, True)
        self.assertEqual(sorted(p.name for p in self.mods.iterdir()), ['WoodRuntime', 'mods.txt'])
        self.assertEqual((self.mods / 'mods.txt').read_text(), 'WoodRuntime : 1\n')
        speedrun.apply_mode(self.game, True)
        speedrun.apply_mode(self.game, False)
        self.assertEqual((self.mods / 'mods.txt').read_text(), self.original)
        self.assertEqual((self.mods / 'Other/Scripts/main.lua').read_text(), 'mod code')
        self.assertEqual((self.mods / 'native.dll').read_bytes(), b'native')
        self.assertEqual((self.game / 'Mods/user.lua').read_text(), 'keep')
        self.assertFalse((self.game / '.wood/speedrun-backup.json').exists())

    def test_restore_conflict_does_not_overwrite_or_partially_restore(self):
        speedrun.apply_mode(self.game, True)
        (self.mods / 'native.dll').write_bytes(b'new')
        with self.assertRaises(RuntimeError):
            speedrun.apply_mode(self.game, False)
        self.assertEqual((self.mods / 'native.dll').read_bytes(), b'new')
        self.assertFalse((self.mods / 'Other').exists())
        self.assertEqual((self.game / '.wood/speedrun.ini').read_text(), 'enabled=true\n')

    def test_helper_waits_for_exit_before_changing_mode_and_launching(self):
        with patch.object(speedrun, 'game_is_running', side_effect=[True, False]), \
             patch.object(speedrun.time, 'sleep') as sleep, \
             patch.object(speedrun, 'apply_mode') as apply, \
             patch.object(speedrun, 'launch_game') as launch:
            speedrun.restart_for_mode(self.game, True, 'abc123')
            apply.assert_called_once_with(self.game, True)
            launch.assert_called_once_with(self.game)
            self.assertEqual(sleep.call_count, 2)
        self.assertFalse((self.game / '.wood/restart-abc123.ready').exists())

    def test_isolation_failure_never_launches(self):
        with patch.object(speedrun, 'game_is_running', return_value=False), \
             patch.object(speedrun.time, 'sleep'), \
             patch.object(speedrun, 'apply_mode', side_effect=OSError('locked')), \
             patch.object(speedrun, 'launch_game') as launch:
            with self.assertRaises(OSError):
                speedrun.restart_for_mode(self.game, True, 'failed')
            launch.assert_not_called()
        self.assertIn('locked', (self.game / '.wood/restart-failed.error').read_text())

    def test_exit_timeout_never_changes_mode(self):
        with patch.object(speedrun, 'game_is_running', return_value=True), \
             patch.object(speedrun.time, 'monotonic', side_effect=[0, 121]), \
             patch.object(speedrun, 'apply_mode') as apply, \
             patch.object(speedrun, 'launch_game') as launch:
            with self.assertRaises(RuntimeError):
                speedrun.restart_for_mode(self.game, True, 'timeout')
            apply.assert_not_called()
            launch.assert_not_called()

    def test_relaunch_removes_frozen_parent_environment(self):
        with patch.dict(update_core.os.environ, {'_PYI_APPLICATION_HOME_DIR': 'old-temp',
                                               '_MEIPASS2': 'old-temp'}):
            environment = update_core.game_environment()
        self.assertNotIn('_PYI_APPLICATION_HOME_DIR', environment)
        self.assertNotIn('_MEIPASS2', environment)
        self.assertEqual(environment['PYINSTALLER_RESET_ENVIRONMENT'], '1')

    def test_failed_process_check_is_not_mistaken_for_game_exit(self):
        from types import SimpleNamespace
        with patch.object(update_core.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout='')):
            with self.assertRaises(RuntimeError):
                update_core.game_is_running()
