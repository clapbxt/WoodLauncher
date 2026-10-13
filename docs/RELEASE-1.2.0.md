# Wood 1.2.0 release and validation

Speedrun mode is in the F10 Wood menu. Changing it closes TUNG and restarts it.
Wait for the new game process before starting an attempt. The current process
never changes its speedrun status in place.

When enabled, Wood does not execute any user `.lua` or `.tungmod` source, including
top-level code, hotkey registration, settings builders, world callbacks and ticks.
The restart helper waits for TUNG to exit, moves every other item in UE4SS's Mods
directory into `.wood/speedrun-ue4ss`, saves the original `mods.txt`, and starts
TUNG with only WoodRuntime enabled. Turning the mode off restores those items
and the original mod list before relaunching. Wood mod preferences and files in
the user-facing Mods directory remain intact. Upgrading or uninstalling Wood
preserves or restores the isolated mods respectively.

The end screen shows the mode and lists all discovered Wood mod files, including
disabled, broken and duplicate files, plus isolated UE4SS items. Unexpected files
in the active UE4SS Mods directory produce an UNVERIFIED warning. This is a
loader status report, not anti-cheat proof or automatic moderator approval.
Separate injectors, modified game assets, other loader installations and external
tools are outside Wood's control. Use the moderators' approved game installation.
Wood LiveSplit is a mod and is disabled in Speedrun mode too.

## Changes

- Restart-only mode transitions prevent old mod effects carrying into a clean session.
- Missing helper, failed isolation, restore conflicts and failed process checks do
  not claim successful mode changes or relaunch an incompletely prepared game.
- Settings refreshes are coalesced and deferred until the calling widget's callback
  returns; old focus references are cleared when pages are rebuilt.
- Settings and per-mod API objects are cached; unchanged settings avoid disk writes.
- Repeated menu opening does not stack input suppression.
- End-screen detection requires an actual viewport widget.
- Restart uses the game's root TUNG.exe when present.
- Helper startup runs outside the game thread; the menu remains responsive until exit.
- Builds use standard Windows Python. MSYS2 fallback packaging has been removed.
- Restarted games do not inherit the helper's temporary PyInstaller directory.
- Cached mod icons are checked for validity; UMG class lookups are cached and
  player-controller discovery runs periodically instead of every frame.

## Automated checks

Run the commands in BUILDING.md. The tests use engine/widget doubles; they cannot
establish native Unreal stability. Installer builds additionally verify embedded
resources and perform install/upgrade/uninstall tests in a temporary game fixture.

## Required in-game acceptance checks before publishing

Automated tests and a real install/upgrade on the supplied TUNG installation have
passed. The user is handling in-game testing. Full gameplay completion, failure
scenarios, repeated GUI stress tests and moderator approval remain pending.

1. Install 1.2.0 with TUNG closed. Add Time Warp, Coordinates, a mod with top-level
   hotkeys/hooks, a broken Lua file, a package, and a separate UE4SS Lua/native mod.
2. In normal mode apply altered world speed. Toggle Speedrun on. Verify graceful
   exit and exactly one new game process. Verify normal game speed, no mod hotkeys,
   no mod GUI execution, and only WoodRuntime in UE4SS/Mods.
3. Finish and die in separate attempts. Verify the report says ON and disabled,
   and every installed Wood file and isolated UE4SS mod appears in the list.
4. Restart through Steam: the setting must persist. Repeated attempts and map
   travel must retain the same clean status.
5. Toggle off: verify another restart, exact native mod restoration, original
   mods.txt and saved settings, then normal mod callbacks and hotkeys.
6. Repeat on/off cycles; close the menu and travel between worlds. Open and change
   mod GUIs repeatedly, especially Time Warp sliders and toggles that refresh UI.
7. Test missing helper, locked mod files, restore-name conflict, failed game exit,
   and failed launch. No failure may claim a clean session or overwrite a mod.
8. While TUNG is closed in Speedrun mode, add an extra UE4SS mod and start through
   Steam. Verify the report says UNVERIFIED, never all mods disabled.
9. Upgrade and uninstall while Speedrun mode is on. Verify user mod restoration.

Do not publish as moderator-approved until those checks and moderator review pass.

## Publish the update

The workspace release bundle contains WoodSetup.exe, optional WoodLauncher.exe,
source, checksums, and WoodWebsite-Netlify.zip. Users normally need only Setup.

1. Perform the in-game acceptance checks above and obtain moderator sign-off.
2. On GitHub create release `v1.2.0` from the published source commit, paste the
   change notes, and attach the release ZIP, WoodSetup.exe and the bundled
   UE4SS_v3.0.1-1164-g5e627997.zip. The archive is needed for reproducible source
   builds because upstream experimental release assets can be removed.
3. Extract WoodWebsite-Netlify.zip to a new folder. Run:

   ```powershell
   npm ci
   npx netlify-cli login
   npx netlify-cli link
   npx netlify-cli deploy --prod --dir site/dist
   ```

   Link the existing site for woodlauncher.clapbxt.com. Keep existing server-side
   catalog environment variables; do not include credentials in release files.
4. Check `/wood-launcher.json` reports `version` and `wood_version` as `1.2.0` and
   that its SHA-256 values match the downloadable files. Test an old installation's
   update prompt, download verification, installation and restart.
5. Announce the update with the Setup download and the Speedrun mode restart rule.

For CLI deployment details see the
[Netlify deploy documentation](https://docs.netlify.com/cli/get-started/).
