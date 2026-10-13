"""Release feed and verified download helpers shared by Wood's setup updater."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import urllib.request

RELEASE_MANIFEST = 'https://woodlauncher.clapbxt.com/wood-launcher.json'
MAX_DOWNLOAD_BYTES = 100 * 1024 * 1024


def version_parts(value):
    parts = tuple(int(part) for part in value.split('.'))
    if len(parts) != 3:
        raise ValueError('Version must use MAJOR.MINOR.PATCH format.')
    return parts


def release_info(url=RELEASE_MANIFEST):
    request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'WoodSetup'})
    with urllib.request.urlopen(request, timeout=8) as response:
        data = json.load(response)
    keys = ('wood_version', 'installer_url', 'sha256')
    if not isinstance(data, dict) or not all(isinstance(data.get(key), str) for key in keys):
        raise ValueError('Wood update feed is incomplete.')
    version_parts(data['wood_version'])
    if not data['installer_url'].startswith('https://') or len(data['sha256']) != 64:
        raise ValueError('Wood update feed contains an invalid setup URL or checksum.')
    return data


def update_available(release, current_version):
    return version_parts(release['wood_version']) > version_parts(current_version)


def download_setup(release, directory=None):
    directory = Path(directory or tempfile.gettempdir())
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"WoodSetup-{release['wood_version']}.exe"
    temporary = target.with_suffix(target.suffix + '.part')
    request = urllib.request.Request(release['installer_url'], headers={'User-Agent': 'WoodSetup'})
    digest = hashlib.sha256()
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=30) as response, temporary.open('wb') as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_DOWNLOAD_BYTES:
                    raise ValueError('Wood setup exceeds the allowed download size.')
                digest.update(chunk)
                output.write(chunk)
        if digest.hexdigest().lower() != release['sha256'].lower():
            raise ValueError('Wood setup checksum verification failed.')
        temporary.replace(target)
        return target
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def launch_game(game_dir):
    game = Path(game_dir).resolve()
    steam = game / 'TUNG.exe'
    shipping = game / 'TUNG/Binaries/Win64/TUNG-Win64-Shipping.exe'
    if steam.is_file():
        return subprocess.Popen([str(steam)], cwd=game, env=game_environment())
    if shipping.is_file():
        return subprocess.Popen([str(shipping)], cwd=game, env=game_environment())
    raise FileNotFoundError('TUNG executable was not found in the selected installation.')


def game_environment():
    # A restarted game must not inherit the helper's soon-to-be-deleted _MEI path.
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('_PYI_') and key != '_MEIPASS2'}
    environment['PYINSTALLER_RESET_ENVIRONMENT'] = '1'
    return environment


def game_is_running():
    for name in ('TUNG.exe', 'TUNG-Win64-Shipping.exe'):
        result = subprocess.run(['tasklist', '/FI', f'IMAGENAME eq {name}', '/NH'],
                                capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode:
            raise RuntimeError('Could not check whether TUNG has exited. No restart was attempted.')
        if name.lower() in result.stdout.lower():
            return True
    return False
