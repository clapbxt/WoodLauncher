# Build Wood from source

The source repository includes NativeMods/WoodRuntime (Lua runtime), WoodSetup
(installer/restart helper), WoodLauncher (optional desktop updater), and WoodWebsite.
No game files, user mods, generated executables, or credentials are committed.

## Windows prerequisites

- Python 3.10 or later with working Tcl/Tk (python.org Windows distribution).
- Git; Node.js and npm only for website function tests/deployment.
- Internet access for Python dependencies and the checksum-pinned UE4SS archive.

Clone and build from PowerShell:

```powershell
git clone https://github.com/clapbxt/WoodLauncher.git
cd WoodLauncher
New-Item -ItemType Directory -Force WoodSetup/.build
# For an offline build, extract the pinned archive from the Wood release bundle:
# Copy-Item /path/to/UE4SS_v3.0.1-1164-g5e627997.zip WoodSetup/.build/UE4SS.zip
py -3.10 -m venv BuildEnvironment/.venv
./BuildEnvironment/.venv/Scripts/python.exe -m pip install -r BuildEnvironment/requirements.txt
./BuildEnvironment/.venv/Scripts/python.exe -m unittest discover -s tests -v
cd WoodSetup
./build.bat
cd ../WoodLauncher
./build.bat
cd ..
```

Outputs: WoodSetup/release/WoodSetup.exe and WoodLauncher/release/WoodLauncher.exe,
with SHA256SUMS.txt alongside each. Build scripts verify their component tests,
Tcl/Tk, packaged resources and installer distribution. Runtime Lua is bundled
directly; there is no Lua compilation step. The installer downloads the pinned
UE4SS archive once and verifies its SHA-256 before bundling.
Upstream experimental assets rotate, so the builder also checks the matching
Wood GitHub release asset. The combined release ZIP includes the pinned archive
for offline builds; copy it into WoodSetup/.build/UE4SS.zip before building.
The expected hash is recorded in THIRD_PARTY.md and always enforced.

If `py -3.10` is unavailable, create BuildEnvironment/.venv with your installed
Python version before running build.bat. Builds require a working python.org
Tcl/Tk installation and fail explicitly if Tcl is inaccessible. Do not substitute
MSYS2 Python into the release build.

## Website/update feed

```powershell
Copy-Item WoodSetup/release/WoodSetup.exe WoodWebsite/release/downloads/
Copy-Item WoodLauncher/release/WoodLauncher.exe WoodWebsite/release/downloads/
# Build WoodModPackager with its build.bat and stage its executable too.
# Stage WoodLiveSplit.zip and WoodLiveSplit.tungmod from the release bundle.
./BuildEnvironment/.venv/Scripts/python.exe WoodWebsite/scripts/package_website.py
cd WoodWebsite
npm ci
npm run test:catalog
```

Stage the existing LiveSplit downloads separately when rebuilding those website pages;
the public website's existing LiveSplit download assets are not runtime source.
Set release/versions.json to the intended release versions before packaging.
Website packaging calculates executable hashes and verifies the generated pages.
See docs/RELEASE-1.2.0.md for deployment and required in-game validation.
