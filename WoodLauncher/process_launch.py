"""Launch independent Windows processes without lending them bundled DLLs."""
import ctypes
from ctypes import wintypes
import os
import subprocess
import sys
import threading

_launch_lock = threading.RLock()


def _dll_api():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetDllDirectoryW.argtypes = (wintypes.DWORD, wintypes.LPWSTR)
    kernel.GetDllDirectoryW.restype = wintypes.DWORD
    kernel.SetDllDirectoryW.argtypes = (wintypes.LPCWSTR,)
    kernel.SetDllDirectoryW.restype = wintypes.BOOL
    return kernel


def clean_environment(environment=None):
    result = {key: value for key, value in (os.environ if environment is None else environment).items()
              if not key.startswith('_PYI_') and key != '_MEIPASS2'}
    result['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    bundled = getattr(sys, '_MEIPASS', None)
    if bundled:
        bundled = os.path.normcase(os.path.abspath(bundled))
        for key in list(result):
            if key.upper() == 'PATH':
                def is_bundled(entry):
                    path = os.path.normcase(os.path.abspath(entry.strip('"')))
                    return path == bundled or path.startswith(bundled + os.sep)
                result[key] = os.pathsep.join(entry for entry in result[key].split(os.pathsep)
                                             if not entry or not is_bundled(entry))
    return result


def external_popen(command, **options):
    options['env'] = clean_environment(options.get('env'))
    if sys.platform != 'win32' or not getattr(sys, 'frozen', False):
        return subprocess.Popen(command, **options)
    with _launch_lock:
        kernel = _dll_api()
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel.GetDllDirectoryW(len(buffer), buffer)
        if length >= len(buffer):
            raise RuntimeError('DLL search directory exceeds the supported length.')
        previous = buffer.value if length else None
        if not kernel.SetDllDirectoryW(None):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            # SetDllDirectory is inherited by child processes independently of env.
            return subprocess.Popen(command, **options)
        finally:
            if not kernel.SetDllDirectoryW(previous):
                raise ctypes.WinError(ctypes.get_last_error())
