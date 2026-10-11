"""Installation and file IPC for Wood's in-process Unreal runtime."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import time
import threading
import zipfile
import sys

BASE = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve().parent
BIN = BASE / 'TUNG' / 'Binaries' / 'Win64'
DATA = BASE / '.wood'
RUNTIME = BIN / 'ue4ss'
SOURCE = BASE / 'NativeMods' / 'WoodRuntime'
RUNTIME_VERSION = 'UE4SS_v3.0.1-1164-g5e627997'
RUNTIME_SHA256 = '3c72142a383e25e9f9553ac9e4d5677aa572e98cb369cac57200efb2e381e603'
RUNTIME_URL = f'https://github.com/UE4SS-RE/RE-UE4SS/releases/download/experimental-latest/{RUNTIME_VERSION}.zip'


def atomic_write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    os.replace(temporary, path)


def load_json(path, default):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8-sig'))
        return value if isinstance(value, type(default)) else default.copy()
    except (OSError, ValueError):
        return default.copy()


def valid_speed(value):
    speed = float(value)
    if not math.isfinite(speed) or not 0.05 <= speed <= 4.0:
        raise ValueError('Speed must be between 0.05x and 4x.')
    return round(speed, 2)


def installed():
    return all(p.is_file() for p in (BIN / 'dwmapi.dll', RUNTIME / 'UE4SS.dll',
                                    RUNTIME / 'Mods/WoodRuntime/Scripts/main.lua'))


def install_runtime(archive=None):
    """Deploy only Wood-owned files; preserve other mods and loader settings."""
    if not (BIN / 'TUNG-Win64-Shipping.exe').is_file():
        raise FileNotFoundError('TUNG shipping executable is missing.')
    if not SOURCE.is_dir():
        raise FileNotFoundError('NativeMods/WoodRuntime is missing from this installation.')
    archive = Path(archive or DATA / 'cache/UE4SS.zip')
    new_install = not (RUNTIME / 'UE4SS.dll').exists()
    if new_install:
        if not archive.is_file():
            raise FileNotFoundError(f'Download {RUNTIME_VERSION}.zip from the official UE4SS release into {archive}.')
        if hashlib.sha256(archive.read_bytes()).hexdigest() != RUNTIME_SHA256:
            raise ValueError('UE4SS archive checksum does not match the pinned official release.')
        with zipfile.ZipFile(archive) as bundle:
            # Limit extraction to the documented runtime layout; reject zip traversal.
            for item in bundle.infolist():
                target = (BIN / item.filename).resolve()
                if not target.is_relative_to(BIN.resolve()):
                    raise ValueError('Unsafe path in runtime archive.')
                if not item.is_dir() and (item.filename == 'dwmapi.dll' or item.filename.startswith('ue4ss/')):
                    if target.exists():
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(item) as src, target.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
    if not (BIN / 'dwmapi.dll').is_file():
        raise FileNotFoundError('The UE4SS proxy dwmapi.dll is missing. Restore it from the official archive.')
    destination = RUNTIME / 'Mods/WoodRuntime'
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE, destination, dirs_exist_ok=True)
    # Embed the resolved root rather than relying on Steam's current directory.
    root = str(BASE).replace('\\', '/')
    atomic_write(destination / 'Scripts/paths.lua', 'return ' + json.dumps(root, ensure_ascii=False) + '\n')
    disabled = load_json(BASE / 'wood_config.json', {}).get('mods_disabled', [])
    extensions = []
    for manifest in sorted((BASE / 'NativeMods').glob('*/manifest.json')):
        if manifest.parent.name.startswith('_') or manifest.parent.name == 'WoodRuntime': continue
        info = load_json(manifest, {})
        mod_id = info.get('id', manifest.parent.name)
        if not isinstance(mod_id, str) or not mod_id.replace('_', '').isalnum():
            raise ValueError(f'Invalid native mod id in {manifest}')
        script = manifest.parent / 'wood.lua'
        if mod_id not in disabled and info.get('enabled', True) and script.is_file():
            extensions.append('{id=' + json.dumps(mod_id) + ', path=' + json.dumps(str(script).replace('\\', '/'), ensure_ascii=False) + '}')
    atomic_write(destination / 'Scripts/extensions.lua', 'return {\n' + ',\n'.join(extensions) + '\n}\n')
    modlist = RUNTIME / 'Mods/mods.txt'
    lines = modlist.read_text(encoding='utf-8-sig').splitlines() if modlist.exists() else []
    lines = [line for line in lines if line.split(':')[0].strip() != 'WoodRuntime']
    # Default bundled debugging/cheat mods are unnecessary. Leave user mod entries alone.
    for i, line in enumerate(lines):
        if new_install and line.split(':')[0].strip() in {'CheatManagerEnablerMod', 'ConsoleCommandsMod',
                                        'ConsoleEnablerMod', 'BPML_GenericFunctions', 'BPModLoaderMod', 'Keybinds'}:
            lines[i] = line.split(':')[0].strip() + ' : 0'
    atomic_write(modlist, 'WoodRuntime : 1\n' + '\n'.join(lines) + '\n')
    DATA.mkdir(exist_ok=True)
    if not (DATA / 'settings.ini').exists():
        atomic_write(DATA / 'settings.ini', 'speed=1.0\nenabled=true\nrestore_on_travel=true\n')
    return destination


class Bridge:
    """Numbered commands are acknowledged by the game, never guessed as applied."""
    ACTIONS = {'speed', 'enabled', 'menu', 'reset', 'restore_on_travel', 'selftest'}

    def __init__(self):
        self._lock = threading.Lock()
        DATA.mkdir(exist_ok=True)

    def send(self, action, value=''):
        if action not in self.ACTIONS:
            raise ValueError('Unknown runtime command')
        if action == 'speed':
            value = valid_speed(value)
        elif action in {'enabled', 'restore_on_travel'}:
            value = 'true' if value is True or value == 'true' else 'false'
        with self._lock:
            serial = time.time_ns()
            with (DATA / 'commands.log').open('a', encoding='ascii') as queue:
                queue.write(f'{serial}|{action}|{value}\n')
        return serial

    def status(self):
        state = load_json(DATA / 'status.json', {})
        # A status from a previous game session must not report a live connection.
        try:
            age = time.time() - (DATA / 'status.json').stat().st_mtime
        except OSError:
            age = 999
        state['connected'] = age < 3 and state.get('ready') is True
        return state
