# Wood Runtime for TUNG

Wood is the Lua and `.tungmod` loader runtime for TUNG. This repository contains
only the runtime source, its public mod API guide, runtime tests, and the runtime
branding asset. It does not contain optional mods or game files.

## Runtime behavior

Wood loads enabled `.lua` and `.tungmod` mods from TUNG's top-level `Mods` folder.
Press **F10** to open the Wood mod menu. Disabled and failed mods remain visible
in that menu with their state.

When TUNG shows its speedrun completion or death result screen, Wood displays the
mods it successfully loaded for that run. The list scrolls like end credits and
stops at the last entry. This reports Wood-loaded mods; it cannot identify mods
loaded by other tools or prevent cheating on its own.

## Source map

- `NativeMods/WoodRuntime/`: loader, menu, package reader, and version manifest.
- `docs/MODDING.md`: public Lua API and `.tungmod` format.
- `tests/test_mod_library.py`: runtime and UI tests against an Unreal widget double.
- `WoodLauncherLogo.png`: source branding used by the runtime installer.

Wood source is MIT licensed. UE4SS is a separate upstream dependency; see
[third-party notices](THIRD_PARTY.md). Setup, updater, packager, website, and
optional mod sources are maintained outside this loader-source repository.
