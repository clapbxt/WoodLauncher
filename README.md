# Wood for TUNG

Native mod menus, Time Warp, a Windows launcher, and a single-file installer.

## Users

Download **WoodSetup.exe** from the download site. Close TUNG and Wood; exit Steam
if setup will configure launch options. Run setup, select your TUNG folder, and
install. Reopen Steam, launch TUNG, and press **F10** for the mod list. Select a
mod to open its settings; Back or Escape returns to the list.

The installer bundles Python and the pinned UE4SS runtime. No separate dependency
installation is required. Run **WoodLauncher.exe** in your game folder to manage
mods. Uninstall through Windows Installed Apps or **WoodUninstall.exe**.

Uninstall preserves personal settings and custom mods. It restores owned files
from backups and leaves files you modified afterward, reporting any conflicts.
Steam options are restored only if they still match the installed value.

## Time Warp

World speed ranges from 0.05× to 4×. F6 halves speed, F7 resets to 1×, and F8 doubles
speed. F10 toggles the native menu; Escape closes it. Persistent options include
enable/disable and reset on world changes. The engine confirms applied values.

This is a practice tool, not a leaderboard certification system. Check category
rules for submitted runs. Input recording, replay, and frame stepping are absent.

## Build on Windows

Python 3.10 (x64):

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-build.txt
.venv/Scripts/python -m unittest discover -s tests -v
.venv/Scripts/python scripts/build_release.py
.venv/Scripts/python site/build.py
```

Outputs: `release/WoodSetup.exe`, `release/WoodLauncher.exe`, and SHA-256 checksums.
The single executable dispatches as setup, launcher, or uninstaller according to
its installed filename. All modes share a bundled Python runtime.

The build verifies the official pinned UE4SS archive before packaging. Initial
download needs internet; user installation is offline. Executables are currently
unsigned. Game updates may require runtime changes.

## Repository layout

- `WoodLauncher.py`: searchable mod library and acknowledged runtime controls.
- `WoodSetup.py`: setup UI, uninstall UI, CLI, and Windows Installed Apps entry.
- `setup_core.py`: file ownership journal, backup, rollback, and uninstall.
- `steam_setup.py`: Steam libraries and reversible account launch options.
- `wood_runtime.py`: native deployment and local command/status bridge.
- `NativeMods/WoodRuntime`: UE4SS Lua runtime and native Unreal widgets.
- `NativeMods/_Example`: extension template with persistent native settings.
- `tests`: runtime, installation, and Steam restoration regression tests.
- `site`: static website generator; `dist` contains deployable pages.
- `.github/workflows/release.yml`: Windows tests, builds, and tagged releases.

No TUNG game binaries, assets, saves, account configuration, credentials, or local
runtime logs are part of this repository. UE4SS binaries are build outputs; its
license is included in the bundled archive and installed runtime.

## Prepare a GitHub release

The local repository is prepared but has not been pushed. When ready, create an
empty repository, add it as `origin`, and push `main`. Push a `v2.1.1` tag to run
the release workflow. The workflow publishes the standalone installer and
checksums as GitHub release assets. `workflow_dispatch` builds an artifact without
publishing a release.

The website currently serves the built installer directly. Run `python site/build.py`
after each release build to update the download and displayed checksum. Serve
`site/dist` with any static host; no server-side runtime or account is needed.

## License

Wood source: MIT. UE4SS: its upstream license, retained in the runtime archive.
Wood is independent of TUNG and its developers.
