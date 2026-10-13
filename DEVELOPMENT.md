# Wood development guide

Wood Setup is the only Wood app users need to download. It installs the in-game runtime, updater, and uninstaller. On every TUNG boot, the runtime checks the website feed and asks before updating. If accepted, it downloads and verifies the newest Setup, waits for TUNG to close, installs Wood, and reopens TUNG. Re-running Setup also checks for updates. Players add mods by placing their .tungmod files in the game folder's Mods directory.

## Workspace map

| Folder | Contents | Build output |
| --- | --- | --- |
| WoodLauncher/ | Launcher/updater plus runtime source in runtime-source/ | WoodLauncher/release/ |
| WoodSetup/ | Installer and uninstaller; bundles WoodLauncher/runtime-source/ | WoodSetup/release/ |
| WoodModPackager/ | App for packaging a selected mod as .tungmod | WoodModPackager/release/ |
| WoodWebsite/ | Website source, manually staged downloads, update feed, deployment ZIP | WoodWebsite/release/ |
| WoodLiveSplit/ | LiveSplit integration and its development files | See WoodLiveSplit/README.md |
| IndividualModDevelopment/ | Separate mod and utility experiments, docs, and tests | Not part of the Wood app release |
| mod data/, packaged mods/ | Individual mod sources and packages | Not part of the Wood app release |
| BuildEnvironment/ | Shared local Python build environment | No release outputs |

The Git checkout at WoodLauncher/runtime-source is the source-only runtime repository for github.com/clapbxt/WoodLauncher. Its repository root stays there so GitHub publishes only the loader/runtime, guide, tests, and branding. Launcher, Setup, website, packager and LiveSplit sources are mirrored into that repository by tools/sync_workspace.py for the 1.2.0 source release. Executables and user mods are excluded. See its BUILDING.md for standalone build instructions.

## Build a component

Open a terminal in the named folder and run build.bat. Each script builds only that app into its own release folder.

- WoodLauncher/build.bat builds the boot launcher/updater.
- WoodSetup/build.bat builds the installer and includes the current runtime-source.
- WoodModPackager/build.bat builds the separate authoring utility.

The Setup and Launcher scripts use BuildEnvironment/.venv with standard Windows Python and working Tcl/Tk; they fail if Tcl is unavailable. Each batch file runs that component's existing tests before packaging. Test source stays in each project's tests/ folder. Archived test reports are in WoodSetup/test-results/archive/; generated build caches stay in the project's .build/ folder.

## Version one Wood release

Keep Setup and runtime versions aligned for a coordinated Wood update:

- Set LAUNCHER_VERSION and WOOD_VERSION in WoodLauncher/launcher_core.py.
- Set VERSION in WoodSetup/setup_core.py.
- Set version in WoodLauncher/runtime-source/NativeMods/WoodRuntime/manifest.json and the runtime version constants in its Scripts/main.lua.
- Set launcher_version and wood_version in WoodWebsite/release/versions.json to the versions being published. These remain for the optional desktop launcher and website feed compatibility.

The runtime calls the installed WoodUninstall.exe with `--check-updates` when TUNG boots. That helper reads https://woodlauncher.clapbxt.com/wood-launcher.json and checks `wood_version`. On Yes, it downloads WoodSetup.exe and verifies its SHA-256. It waits for the player to exit TUNG, then applies Setup's bundled runtime and restarts TUNG. No asks again on the next boot. If the feed is unreachable, play continues without an update prompt. Running WoodSetup.exe also checks the feed; accepting downloads the current installer before continuing. Uninstall removes every file recorded as Setup-owned, including bundled mods, even if changed; restores replaced originals; removes Setup backup copies and the uninstall registration; and keeps user-added mods, preferences, and unrelated loader files. Deploy the website bundle to publish the feed and installer together.

The in-game updater is included in this release. Players already running an older release must run the new WoodSetup.exe once to install that updater; older runtimes cannot start a feature they do not contain.

## Stage website downloads manually

Build only the components you intend to release, then copy WoodSetup.exe and any separately offered integration files into WoodWebsite/release/downloads/. The public Downloads page offers only Wood Setup; neither the desktop launcher nor mod authoring utility is needed by players. This staging folder is the handoff between app builds and website packaging; the website builder does not fetch files from other projects.

    Copy-Item WoodSetup/release/WoodSetup.exe WoodWebsite/release/downloads/

If publishing LiveSplit files, copy WoodLiveSplit.zip and WoodLiveSplit.tungmod there too. Update WoodWebsite/release/versions.json. The website build calculates hashes from the staged downloads and writes the feed and download checksums.

## Package and deploy the website

From WoodWebsite, run:

    ..\BuildEnvironment\.venv\Scripts\python.exe scripts/package_website.py

The output is WoodWebsite/release/WoodWebsite-Netlify.zip. It contains the generated site, Netlify function source, config, and npm manifests. It is intended for Netlify CLI deployment, not Netlify Drop.

Extract the ZIP, open a terminal in the extracted folder, and run:

    npm ci
    npx netlify-cli login
    npx netlify-cli link
    npx netlify-cli deploy --prod --dir site/dist

Link to the existing site for woodlauncher.clapbxt.com. Keep MOD_ADMIN_TOKEN, NETLIFY_SITE_ID, and NETLIFY_AUTH_TOKEN set in the Netlify site environment. Never put their values in source or in the ZIP. A launcher update reaches players after this deployment publishes the feed and files.

## Publish runtime source to GitHub

After runtime changes, inspect the nested repository and publish only the intended source changes:

    git -C WoodLauncher/runtime-source status
    git -C WoodLauncher/runtime-source diff
    git -C WoodLauncher/runtime-source add NativeMods docs tests README.md
    git -C WoodLauncher/runtime-source commit -m "Describe runtime change"
    git -C WoodLauncher/runtime-source push

The repository remains source-only; built applications and website files stay in their separate folders.

## Individual mods

Individual mod source and packages remain separate from WoodLauncher releases and its updater. Build and publish individual mod packages using the existing mod workflow.
