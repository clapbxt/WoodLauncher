import unittest
from unittest.mock import patch
import process_launch as launch


class DLLSearchTests(unittest.TestCase):
    def fake_kernel(self):
        class Kernel:
            calls = []
            def GetDllDirectoryW(self, size, buffer):
                buffer.value = 'C:\\temp\\_MEI-parent'
                return len(buffer.value)
            def SetDllDirectoryW(self, value):
                self.calls.append(value)
                return 1
        return Kernel()

    def test_frozen_parent_resets_dll_search_only_during_spawn(self):
        kernel = self.fake_kernel()
        def spawn(*args, **kwargs):
            self.assertEqual(kernel.calls, [None])
            self.assertEqual(kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'], '1')
            return 'child'
        with patch.object(launch.sys, 'frozen', True, create=True), \
             patch.object(launch.sys, 'platform', 'win32'), \
             patch.object(launch, '_dll_api', return_value=kernel), \
             patch.object(launch.subprocess, 'Popen', side_effect=spawn):
            self.assertEqual(launch.external_popen(['game.exe']), 'child')
        self.assertEqual(kernel.calls, [None, 'C:\\temp\\_MEI-parent'])

    def test_spawn_failure_restores_parent_dll_search(self):
        kernel = self.fake_kernel()
        with patch.object(launch.sys, 'frozen', True, create=True), \
             patch.object(launch.sys, 'platform', 'win32'), \
             patch.object(launch, '_dll_api', return_value=kernel), \
             patch.object(launch.subprocess, 'Popen', side_effect=OSError('launch failed')):
            with self.assertRaises(OSError):
                launch.external_popen(['game.exe'])
        self.assertEqual(kernel.calls, [None, 'C:\\temp\\_MEI-parent'])

    def test_child_path_excludes_bundled_dll_directory(self):
        with patch.object(launch.sys, '_MEIPASS', 'C:\\temp\\_MEI-parent', create=True):
            environment = launch.clean_environment({'PATH':'C:\\Windows;C:\\temp\\_MEI-parent;C:\\temp\\_MEI-parent\\bin',
                                                     '_PYI_APPLICATION_HOME_DIR':'old'})
        self.assertEqual(environment['PATH'], 'C:\\Windows')
        self.assertNotIn('_PYI_APPLICATION_HOME_DIR', environment)
