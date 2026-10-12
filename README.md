# Wood Runtime

This repository is the in-game runtime source component of the WoodLauncher product. Locally it lives at WoodLauncher/runtime-source so launcher, runtime, and build files are grouped together. GitHub keeps this repository root source-only: runtime code, API documentation, runtime tests, and branding. It does not include the launcher executable, Setup app, website, game files, or optional mods.

WoodSetup bundles the runtime source into the installer. On TUNG startup, the runtime starts the installed Wood update helper. The helper checks the website feed; if an update is accepted, it downloads and verifies the current Setup, waits for TUNG to close, installs, then restarts the game. Running Setup again also checks for updates.

See docs/MODDING.md for the public mod API and ../README.md in the workspace root for product/build instructions.
