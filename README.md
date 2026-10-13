# Wood Runtime

This is the WoodLauncher 1.2.0 source repository: the in-game runtime, installer/restart helper, optional desktop launcher, website source, tests, documentation and branding. Executables, game files and user mods are excluded. In the development workspace this checkout lives at WoodLauncher/runtime-source; application sources are mirrored into it for source releases.

WoodSetup bundles the runtime source into the installer. On TUNG startup, the runtime starts the installed Wood update helper. The helper checks the website feed; if an update is accepted, it downloads and verifies the current Setup, waits for TUNG to close, installs, then restarts the game. Running Setup again also checks for updates.

See [BUILDING.md](BUILDING.md) for standalone build instructions, [docs/MODDING.md](docs/MODDING.md) for the API, and [docs/RELEASE-1.2.0.md](docs/RELEASE-1.2.0.md) for Speedrun mode behavior, validation and publishing.
