"""Update and start the installed TUNG game for Wood Launcher."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request
import webbrowser

LAUNCHER_VERSION = '1.2.0'
WOOD_VERSION = '1.2.0'
RELEASE_MANIFEST = 'https://woodlauncher.clapbxt.com/wood-launcher.json'
MAX_INSTALLER_BYTES = 100 * 1024 * 1024


def newer_version(remote: str, current: str = WOOD_VERSION) -> bool:
    def parts(value):
        result = tuple(int(part) for part in value.split('.'))
        if len(result) != 3:
            raise ValueError('Version must use MAJOR.MINOR.PATCH format.')
        return result
    return parts(remote) > parts(current)


def release_info(url=RELEASE_MANIFEST):
    request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'WoodLauncher'})
    with urllib.request.urlopen(request, timeout=8) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not all(isinstance(data.get(key), str) for key in ('version', 'wood_version', 'installer_url', 'sha256', 'launcher_url', 'launcher_sha256')):
        raise ValueError('Wood update feed is incomplete.')
    if (not data['installer_url'].startswith('https://') or len(data['sha256']) != 64
            or not data['launcher_url'].startswith('https://') or len(data['launcher_sha256']) != 64):
        raise ValueError('Wood update feed contains an invalid installer URL or checksum.')
    for key in ('version', 'wood_version'):
        newer_version(data[key], data[key])
    return data


def update_available(release):
    return newer_version(release['version'], LAUNCHER_VERSION) or newer_version(release['wood_version'], WOOD_VERSION)


def download_update(release, directory=None):
    directory = Path(directory or tempfile.gettempdir())
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"WoodSetup-{release['version']}.exe"
    installer_url = release['installer_url']
    if not installer_url.startswith('https://'):
        raise ValueError('Wood installer URL must use HTTPS.')
    request = urllib.request.Request(installer_url, headers={'User-Agent': 'WoodLauncher'})
    digest = hashlib.sha256()
    size = 0
    temporary = target.with_suffix('.exe.part')
    try:
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_INSTALLER_BYTES:
                    raise ValueError('Wood installer exceeds the allowed download size.')
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest().lower() != release['sha256'].lower():
            raise ValueError('Wood installer checksum verification failed.')
        temporary.replace(target)
        launcher = download_verified(release['launcher_url'], release['launcher_sha256'],
                                     directory / f"WoodLauncher-{release['version']}.exe")
        return target, launcher
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def download_verified(url, checksum, target):
    if not url.startswith('https://'):
        raise ValueError('Wood update URLs must use HTTPS.')
    temporary = target.with_suffix(target.suffix + '.part')
    digest = hashlib.sha256()
    size = 0
    try:
        request = urllib.request.Request(url, headers={'User-Agent': 'WoodLauncher'})
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_INSTALLER_BYTES:
                    raise ValueError('Wood update file exceeds the allowed download size.')
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest().lower() != checksum.lower():
            raise ValueError('Wood launcher checksum verification failed.')
        temporary.replace(target)
        return target
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def installed_game(game_dir):
    game = Path(game_dir).resolve()
    if not (game / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe').is_file():
        raise FileNotFoundError('Select the TUNG installation containing TUNG.exe.')
    return game


def launch_game(game_dir):
    game = installed_game(game_dir)
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('_PYI_') and key != '_MEIPASS2'}
    environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    steam = game / 'TUNG.exe'
    if steam.is_file():
        return subprocess.Popen([str(steam)], cwd=game, env=environment)
    shipping = game / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe'
    if shipping.is_file():
        return subprocess.Popen([str(shipping)], cwd=game, env=environment)
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Valve\Steam') as key:
            steam_root = Path(winreg.QueryValueEx(key, 'SteamExe')[0])
        return subprocess.Popen([str(steam_root), '-applaunch', '4341400'], cwd=game, env=environment)
    except (ImportError, OSError, FileNotFoundError):
        if webbrowser.open('steam://run/4341400'):
            return None
        raise RuntimeError('Steam could not be opened. Start TUNG through Steam.')
