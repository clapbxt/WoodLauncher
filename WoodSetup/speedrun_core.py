"""Restart-only speedrun isolation. Never change loader files in a live game."""
from pathlib import Path
import json
import time
from wood_runtime import atomic_write
from update_core import game_is_running, launch_game


def apply_mode(game, enabled):
    game = Path(game).resolve()
    mods = game / 'TUNG/Binaries/Win64/ue4ss/Mods'
    data = game / '.wood'
    vault = data / 'speedrun-ue4ss'
    state = data / 'speedrun-backup.json'
    modlist = mods / 'mods.txt'
    if not (mods / 'WoodRuntime/Scripts/main.lua').is_file():
        raise RuntimeError('Wood runtime is missing. Run Wood Setup again.')
    if enabled:
        if not state.exists():
            atomic_write(state, json.dumps({'mods_txt': modlist.read_text(encoding='utf-8-sig')
                                          if modlist.exists() else None}))
        vault.mkdir(parents=True, exist_ok=True)
        # Include enabled.txt autodiscovery, Lua mods, native dll mods and loaders.
        for item in sorted(mods.iterdir()):
            if item.name.lower() in {'woodruntime', 'mods.txt'}:
                continue
            target = vault / item.name
            if target.exists():
                raise RuntimeError(f'Conflicting isolated mod: {item.name}. No game was launched.')
            item.rename(target)
        atomic_write(modlist, 'WoodRuntime : 1\n')
        atomic_write(data / 'speedrun-native.txt', '\n'.join(item.name for item in sorted(vault.iterdir())) + '\n')
        atomic_write(data / 'speedrun.ini', 'enabled=true\n')
    else:
        if state.exists():
            saved = json.loads(state.read_text(encoding='utf-8'))
            entries = list(vault.iterdir()) if vault.exists() else []
            for item in entries:
                if (mods / item.name).exists():
                    raise RuntimeError(f'Cannot restore {item.name}: destination exists. No game was launched.')
            for item in entries:
                item.rename(mods / item.name)
            if saved['mods_txt'] is None:
                modlist.unlink(missing_ok=True)
            else:
                atomic_write(modlist, saved['mods_txt'])
            state.unlink()
            if vault.exists():
                vault.rmdir()
        atomic_write(data / 'speedrun.ini', 'enabled=false\n')
        (data / 'speedrun-native.txt').unlink(missing_ok=True)


def restart_for_mode(game, enabled, token):
    game = Path(game).resolve()
    if not token.isalnum() or len(token) > 80:
        raise ValueError('Invalid restart request.')
    data = game / '.wood'
    ready = data / ('restart-' + token + '.ready')
    error = data / ('restart-' + token + '.error')
    # Readiness acknowledges a running helper, before the game requests exit.
    atomic_write(ready, 'ready\n')
    try:
        deadline = time.monotonic() + 120
        while game_is_running():
            if time.monotonic() >= deadline:
                raise RuntimeError('TUNG did not exit within two minutes. Mode was not changed.')
            time.sleep(0.25)
        time.sleep(1)
        apply_mode(game, enabled)
        launch_game(game)
    except Exception as exc:
        atomic_write(error, str(exc))
        raise
    finally:
        ready.unlink(missing_ok=True)
