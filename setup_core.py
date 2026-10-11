"""Transactional installation. A journal owns files, never entire mod folders."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import zipfile
import wood_runtime as runtime
import steam_setup

VERSION = '2.1.3'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_game(game):
    game = Path(game).resolve()
    if not (game / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe').is_file():
        raise ValueError('Choose the TUNG folder containing TUNG.exe and TUNG/Binaries/Win64.')
    return game


def bind_runtime(game):
    runtime.BASE = game
    runtime.BIN = game / 'TUNG/Binaries/Win64'
    runtime.DATA = game / '.wood'
    runtime.RUNTIME = runtime.BIN / 'ue4ss'
    runtime.SOURCE = game / 'NativeMods/WoodRuntime'


def require_closed(game, steam=False):
    if (game / '.wood/status.json').exists():
        import time
        if time.time() - (game / '.wood/status.json').stat().st_mtime < 3:
            raise RuntimeError('Close TUNG before installing or uninstalling Wood.')
    import ctypes
    from ctypes import wintypes
    class Entry(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('usage', wintypes.DWORD), ('pid', wintypes.DWORD),
                    ('heap', ctypes.c_size_t), ('module', wintypes.DWORD), ('threads', wintypes.DWORD),
                    ('parent', wintypes.DWORD), ('priority', wintypes.LONG), ('flags', wintypes.DWORD),
                    ('name', wintypes.WCHAR * 260)]
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    for name in ('Process32FirstW', 'Process32NextW'):
        getattr(kernel, name).argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    entry = Entry(); entry.size = ctypes.sizeof(entry)
    try:
        more = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while more:
            exe = entry.name.lower()
            if exe in {'tung.exe', 'tung-win64-shipping.exe', 'woodlauncher.exe'}:
                raise RuntimeError('Close TUNG and the Wood launcher before setup.')
            if steam and exe == 'steam.exe':
                raise RuntimeError('Exit Steam from Steam → Exit before setup changes launch options. You can reopen Steam afterward.')
            more = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)


class Journal:
    def __init__(self, game):
        self.game = game
        self.path = game / '.wood/install-manifest.json'
        self.original = self.path.read_bytes() if self.path.exists() else None
        self.data = json.loads(self.original) if self.original else {'version': VERSION, 'files': {}, 'steam': []}
        self.undo = {}

    def target(self, relative):
        path = (self.game / relative).resolve()
        if not path.is_relative_to(self.game) or path == self.game:
            raise ValueError('Installer path escapes the game directory.')
        return path

    def capture(self, path):
        path = self.target(path.relative_to(self.game))
        key = path.relative_to(self.game).as_posix()
        if path not in self.undo:
            self.undo[path] = path.read_bytes() if path.exists() else None
        if key not in self.data['files']:
            backup = None
            if path.exists():
                backup = '.wood/backups/' + hashlib.sha256(key.encode()).hexdigest()
                dst = self.target(backup); dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dst)
            self.data['files'][key] = {'backup': backup, 'sha256': None}
        self.save()

    def record(self, path):
        key = path.relative_to(self.game).as_posix()
        self.data['files'][key]['sha256'] = digest(path)
        self.save()

    def put(self, relative, content, replace=True):
        path = self.target(relative)
        if path.exists() and not replace:
            return
        self.capture(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        self.record(path)

    def save(self):
        self.data['version'] = VERSION
        runtime.atomic_write(self.path, json.dumps(self.data, indent=2))

    def rollback(self):
        for path, data in reversed(list(self.undo.items())):
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        if self.original is None:
            self.path.unlink(missing_ok=True)
        else:
            self.path.write_bytes(self.original)


def install(game, payload, installer, configure_steam=True, root=None, check_running=True):
    game = validate_game(game); payload = Path(payload)
    if check_running: require_closed(game, configure_steam)
    bind_runtime(game)
    archive = payload / 'UE4SS.zip'
    if digest(archive) != runtime.RUNTIME_SHA256:
        raise ValueError('Bundled runtime failed SHA-256 verification.')
    journal = Journal(game)
    steam_undo = {}
    new_loader = not (runtime.RUNTIME / 'UE4SS.dll').exists()
    try:
        # A foreign proxy may belong to another loader; do not silently replace it.
        if (runtime.BIN / 'dwmapi.dll').exists() and not (runtime.RUNTIME / 'UE4SS.dll').exists():
            raise RuntimeError('Another dwmapi.dll loader is installed. Remove it before installing Wood.')
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                if info.is_dir(): continue
                if info.filename == 'dwmapi.dll' or info.filename.startswith('ue4ss/'):
                    content = bundle.read(info)
                    if new_loader and info.filename == 'ue4ss/Mods/mods.txt':
                        debug = {'CheatManagerEnablerMod', 'ConsoleCommandsMod', 'ConsoleEnablerMod',
                                 'BPML_GenericFunctions', 'BPModLoaderMod', 'Keybinds'}
                        lines = content.decode('utf-8-sig').splitlines()
                        content = ('\n'.join(line.split(':')[0].strip() + ' : 0' if line.split(':')[0].strip() in debug else line for line in lines) + '\n').encode()
                    journal.put(Path('TUNG/Binaries/Win64') / info.filename, content, replace=False)
        for source in (payload / 'NativeMods').rglob('*'):
            if source.is_file():
                journal.put(Path('NativeMods') / source.relative_to(payload / 'NativeMods'), source.read_bytes())
        journal.put('WoodLauncher.exe', Path(installer).read_bytes())
        journal.put('WoodUninstall.exe', Path(installer).read_bytes())
        journal.put('Wood-Licenses.txt', (payload / 'Wood-Licenses.txt').read_bytes())
        journal.put('.wood/cache/UE4SS.zip', archive.read_bytes(), replace=False)
        generated = [runtime.RUNTIME / 'Mods/mods.txt', runtime.RUNTIME / 'Mods/WoodRuntime/Scripts/paths.lua',
                     runtime.RUNTIME / 'Mods/WoodRuntime/Scripts/extensions.lua']
        generated += [runtime.RUNTIME / 'Mods/WoodRuntime' / source.relative_to(payload / 'NativeMods/WoodRuntime')
                      for source in (payload / 'NativeMods/WoodRuntime').rglob('*') if source.is_file()]
        for path in generated: journal.capture(path)
        runtime.install_runtime(archive)
        for path in generated: journal.record(path)
        if configure_steam:
            def write(path, text):
                steam_undo[path] = path.read_bytes()
                runtime.atomic_write(path, text)
            steam_setup.configure(root or steam_setup.steam_root(), game, journal.data['steam'], write)
        journal.save()
        return journal.data
    except Exception:
        for path, content in steam_undo.items(): path.write_bytes(content)
        journal.rollback()
        raise


def uninstall(game, check_running=True):
    game = validate_game(game)
    journal = Journal(game)
    if journal.original is None:
        raise RuntimeError('No Wood installation record found. No files were removed.')
    if check_running: require_closed(game, bool(journal.data['steam']))
    conflicts = steam_setup.restore(journal.data['steam'], runtime.atomic_write)
    remaining = {}
    for relative, record in reversed(list(journal.data['files'].items())):
        path = journal.target(relative)
        if not path.exists(): continue
        if record['sha256'] is None or digest(path) != record['sha256']:
            if relative == 'TUNG/Binaries/Win64/ue4ss/Mods/mods.txt':
                lines = path.read_text(encoding='utf-8-sig').splitlines()
                runtime.atomic_write(path, '\n'.join(line for line in lines if line.split(':')[0].strip() != 'WoodRuntime') + '\n')
                continue
            conflicts.append(relative); remaining[relative] = record
            continue
        if record['backup']:
            backup = journal.target(record['backup'])
            if not backup.exists():
                conflicts.append(relative); remaining[relative] = record
                continue
            shutil.copy2(backup, path)
        else:
            path.unlink()
    # Keep personal settings, custom mods, and backups. Remove only empty directories.
    for relative in journal.data['files']:
        parent = journal.target(relative).parent
        while parent != game:
            try: parent.rmdir()
            except OSError: break
            parent = parent.parent
    journal.data['files'] = remaining
    journal.data['steam'] = [r for r in journal.data['steam'] if r['path'] in conflicts]
    if remaining or journal.data['steam']: journal.save()
    else: journal.path.unlink(missing_ok=True)
    return conflicts
