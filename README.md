# Wood for TUNG

An in-game native mod menu, Time Warp, Wood Utilities, a live Coordinates overlay, a lightweight Steam shortcut, and a single-file installer.

## Users

Download **WoodSetup.exe** from the download site. Close TUNG and Wood, then run
setup and select your TUNG folder. The installer does not change Steam launch
options and places a small **WoodLauncher.exe** Steam shortcut beside the game.
Launch TUNG through Steam and press **F10** for the mod list. Select a
mod to open its settings; Back or Escape returns to the list. Search and the All,
Active, and Settings filters keep larger libraries easy to browse. The list stays
visible beside each mod's Settings and Info pages.

The installer bundles Python, the pinned UE4SS runtime, and the included mods.
No separate dependency installation is required. Manage mods from the in-game
F10 menu to enable or disable installed mods. Wood Launcher simply opens TUNG
through Steam; the UE4SS proxy installed by setup loads Wood automatically when
the game starts. Uninstall through Windows Installed Apps or **WoodUninstall.exe**.
Run **WoodModPackager.exe** to bundle a Lua mod, its metadata, and an optional
PNG icon into one `.tungmod` file. Copy that file into the game’s `Mods` folder
and restart TUNG; packaged icons appear in the in-game mod list.

Uninstall preserves personal settings and custom mods. It restores owned files
from backups and leaves files you modified afterward, reporting any conflicts.

## Time Warp

World speed ranges from 0.05x to 4x. F6 halves speed, F7 resets to 1x, and F8 doubles
speed. F10 toggles the native menu; Escape returns to the list, then closes it. Persistent options include
enable/disable and reset on world changes. The settings page includes presets,
an exact speed field (0.05 to 4, Enter or Apply), and separate saved/applied readouts.
The engine confirms applied values. Changes save automatically. Hotkeys do not
change speed while you are typing in the search or exact speed field.

This is a practice tool, not a leaderboard certification system. Check category
rules for submitted runs. Input recording, replay, and frame stepping are absent.

## Wood Utilities

Included and enabled by default. Press F10, select **Wood Utilities**, and open
Settings. Auto-speedrunner mode enables TUNG's native mode on startup, with an
independent speedrunner music preference. Disabling auto mode leaves the current
run unchanged; soundtrack selection applies on the next run, and switching it
off also mutes the speedrunner soundtrack immediately.

One Application volume slider controls the final audio output, including menus.
Set it to 0% to mute TUNG.
Mouse controls have one Sensitivity slider (0.10x to 3.00x), applied to the
live game input. Reset sensitivity restores 1.00x. Inversion and smoothing
controls have been removed; TUNG keeps its vanilla direction and smoothing.
Preferences save automatically in `.wood/WoodUtilities.settings.ini` and survive
updates and uninstall. These controls never edit Windows mouse settings or game
save files. Disable Wood Utilities in the F10 mod menu and restart to return to
vanilla.

## Coordinates

The Coordinates mod is a standalone Lua file included with Wood Setup and
available separately from the official mod collection. It shows live world X/Y/Z
in a configurable screen corner, with Simple (0), Detailed (2), or Exact (up to 7)
decimal places. The overlay refreshes about ten times per second.

When installed, Coordinates also writes live position and grounded-state samples
to `.wood/Coordinates.live` for the separate LiveSplit Hedge split. The
autosplitter ZIP does not include or install the mod.

## Build on Windows

Python 3.10 (x64):

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\build_release.py
.\.venv\Scripts\python.exe scripts\verify_distribution.py
.\.venv\Scripts\python.exe scripts\package_netlify.py
```

The build produces `release/WoodSetup.exe`, a small `release/WoodLauncher.exe`,
`release/WoodModPackager.exe`, and `release/SHA256SUMS.txt`. The installer embeds the UE4SS loader and the
standalone mods from `Mods/`, and installs the launcher beside the game. The
launcher has no mod manager or injector: it opens the Steam game URI; setup's
UE4SS `dwmapi.dll` proxy is the component that hooks into TUNG.
After installation it copies itself as `WoodUninstall.exe` into the game folder;
the native mod menu runs inside TUNG.
`scripts/package_netlify.py` rebuilds and verifies `site/dist`, then creates
`release/Wood-Netlify.zip` with the site, functions, and Netlify CLI config.
It is a deployment-source archive, not a static drag-and-drop upload. Extract it,
install Node dependencies, configure the private `MOD_ADMIN_TOKEN` in Netlify,
and deploy through Netlify CLI; see [site/NETLIFY.md](site/NETLIFY.md).

The build verifies the official pinned UE4SS archive before packaging. Initial
download needs internet; user installation is offline. Executables are currently
unsigned. Game updates may require runtime changes.

## Repository layout

- `WoodSetup.py`: setup UI, uninstall UI, CLI, and Windows Installed Apps entry.
- `WoodLauncher.py`: minimal Steam URI shortcut; Wood's UE4SS proxy loads in-game.
- `WoodModPackager.py`: GUI that packages Lua source, metadata, and optional PNG artwork.
- `setup_core.py`: file ownership journal, backup, rollback, and uninstall.
- `steam_setup.py`: Steam library discovery; no launch-option edits.
- `wood_runtime.py`: native deployment and local command/status bridge.
- `NativeMods/WoodRuntime`: UE4SS Lua runtime, package reader, and native Unreal widgets.
  `Scripts/menu.lua` owns library browsing and settings presentation.
- `Mods`: standalone Lua mods loaded from the game's `Mods` folder, including Coordinates.
- `tests`: runtime, mod menu, utilities, and installation regression tests.
- `site`: static website generator; `dist` contains deployable pages.
- `.github/workflows/release.yml`: Windows tests, builds, and tagged releases.

No TUNG game binaries, assets, saves, account configuration, credentials, or local
runtime logs are part of this repository. UE4SS binaries are build outputs; its
license is included in the bundled archive and installed runtime.

## Prepare a GitHub release

The local repository is prepared but has not been pushed. When ready, create an
empty repository, add it as `origin`, and push `main`. Push a `v2.3.0` tag to run
the release workflow. The workflow publishes the standalone installer and
checksums as GitHub release assets. `workflow_dispatch` builds an artifact without
publishing a release.

After each release build, run `.\.venv\Scripts\python.exe scripts\package_netlify.py`
to refresh the download and checksum and create `release/Wood-Netlify.zip`. The
generated `site/dist` is also a static site that can be served by any host; it
needs no server-side runtime or account.

## Netlify hosting

Run `.\.venv\Scripts\python.exe scripts\package_netlify.py` after building the
Windows release.
Extract `release/Wood-Netlify.zip` and deploy the extracted project using
Netlify CLI. Netlify Drop does not deploy its serverless catalog function.
Full deployment and curator-token instructions: [site/NETLIFY.md](site/NETLIFY.md).

## License

Wood source: MIT. UE4SS: its upstream license, retained in the runtime archive.
Wood is independent of TUNG and its developers.
