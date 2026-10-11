# Third-party components

## UE4SS

Official upstream: https://github.com/UE4SS-RE/RE-UE4SS

Pinned archive: `UE4SS_v3.0.1-1164-g5e627997.zip`

SHA-256: `3c72142a383e25e9f9553ac9e4d5677aa572e98cb369cac57200efb2e381e603`

MIT license, copyright 2022 Narknon. The complete upstream license is included
inside the runtime archive and installed at `TUNG/Binaries/Win64/ue4ss/LICENSE`.
The archive is verified before packaging and before installation. It is not
tracked in the source repository.

## Python and build tools

The standalone executable contains the Python runtime and Tcl/Tk. Their bundled
notices are included in `Wood-Licenses.txt`. The VDF parser is vdf 3.4 (MIT). PyInstaller
uses its upstream license and bootloader exception. Build dependencies are pinned
in `requirements-build.txt`; they are not copied into the source tree.

## Website

All Wood graphics are created from code in this repository. PaperMC supplied
visual direction only; no PaperMC branding or artwork is distributed.
