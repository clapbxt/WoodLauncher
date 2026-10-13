# WoodSetup

Builds WoodSetup.exe, the single Wood app users install. It installs the in-game runtime and installs itself as WoodUninstall.exe in the TUNG folder. The runtime checks the release feed on every game boot. Accepted updates download and verify the newest Setup, wait for TUNG to close, install, and reopen TUNG. Re-running WoodSetup.exe also checks the feed. Uninstall removes every Setup-owned file, including setup-bundled mods, even if changed after installation; restores files Setup replaced; and deletes backup copies. User-added mods, Wood preferences, and unrelated loader files remain. The build bundles the current runtime from ../WoodLauncher/runtime-source/. Run build.bat; output is release/WoodSetup.exe.

This is a supporting build component of WoodLauncher, not an individual mod. See ../DEVELOPMENT.md for aligned versions, website staging, and publishing.
