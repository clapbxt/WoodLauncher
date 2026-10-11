# Wood for TUNG

Wood loads Lua and `.tungmod` mods through UE4SS and supplies an in-game mod
library and settings menu. This repository contains the loader, Windows
installer/uninstaller, Wood Mod Packager, branding, documentation, and build tools.
Standalone mods, the website, LiveSplit, and game files are separate projects.

## Install and use

1. Close TUNG and run **WoodSetup.exe**. Select the folder containing `TUNG.exe`.
2. Copy your downloaded `.tungmod` packages into the top-level `Mods` folder
   beside `TUNG.exe`. `.lua` files are also supported for development.
3. Launch TUNG normally through Steam. Press **F10** to open Wood.

Setup supplies UE4SS. No Python installation, separate launcher, or Steam
launch-option change is needed. The installer never bundles optional mods.

Restart TUNG after adding, changing, or removing mods. Packages take priority
when a `.tungmod` and `.lua` share a filename stem. Keep one copy per mod ID.
For startup disabling, list Lua filename stems or package metadata IDs in
`.wood/mods_disabled.txt`, one per line. Discovery errors appear in `UE4SS.log`.
Icons display within 128 by 128 pixels with their aspect ratio preserved.

Run **WoodUninstall.exe** or use Windows Installed Apps to remove Wood. Setup
tracks its own files, restores backups, and preserves personal mods and settings.
Upgrades retire unchanged copies of the old launcher and legacy bundled mods.

## Build

Use Windows x64 and Python 3.10 with working Tcl/Tk. Run `build+package.bat`, or:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts\build_release.py
.\.venv\Scripts\python.exe scripts\verify_distribution.py
```

The build verifies the pinned UE4SS archive, generates application icons from
`WoodLauncherLogo.png`, and checks the built installer executable. Outputs are
`release/WoodSetup.exe`, `release/WoodModPackager.exe`, and `release/SHA256SUMS.txt`.
Build caches and binaries are not tracked. The Windows GitHub workflow runs tests,
builds, and installation checks; version tags also publish the release binaries.

## Source map

- `WoodSetup.py`, `setup_core.py`, `setup_ui.py`: setup, rollback, uninstall, and UI.
- `wood_runtime.py`, `NativeMods/WoodRuntime`: UE4SS deployment and in-game loader.
- `steam_setup.py`: Steam installation discovery.
- `WoodModPackager.py`: `.tungmod` packaging utility.
- `scripts`, `tests`, `.github/workflows/release.yml`: build and verification tools.
- [Mod author guide](docs/MODDING.md): loader API and package format.

Wood source is MIT licensed. See [third-party notices](THIRD_PARTY.md) for UE4SS,
Python, and build dependencies. Wood is independent of TUNG and its developers.
Executables are unsigned, and game updates may require a runtime update.
