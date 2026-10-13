# Wood LiveSplit

Package **WoodLiveSplit.lua** as **WoodLiveSplit.tungmod** using WoodModPackager
(mod ID: `wood-livesplit`). Put the package beside the installer.

For the download, include only these six files:

- WoodLiveSplit.tungmod
- LiveSplit.WoodTUNG.dll
- Wood-TUNG.lsl
- TUNG-AnyPercent.lss
- Install-WoodLiveSplit.bat
- Install-WoodLiveSplit.ps1

Users extract the files, close TUNG and LiveSplit, and run the BAT. Setup finds
TUNG, asks for LiveSplit.exe if needed, and creates a TUNG LiveSplit desktop
shortcut. Wood must already be installed. Updates preserve saved splits/PBs.

Use that shortcut, launch TUNG normally, and start a normal Speedrun attempt.
Each distinct valve splits on interaction. Hedge checks only Z 360-425 after
the door opens. Finish uses the game's result time. Tiny Tung, B-hop and
checkpoint modes are excluded. Manual resets and pauses are respected.

The `source` folder is for rebuilding the LiveSplit DLL; leave it out of the
download. Run `source/BuildComponent.ps1 -LiveSplitPath C:/path/to/LiveSplit`.
No release folder, automatic mod packaging or ZIP generation is used.
