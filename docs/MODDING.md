# Make a mod for Wood

Wood loads one Lua file per mod. It supplies the F10 menu, settings controls, and saved preferences. Your mod supplies the behavior. Develop as `.lua`, then use Wood Mod Packager to release a `.tungmod`. Mods are released separately from Wood.

## 1. Start with a working mod

Install Wood, then save the example below as `hello-wood.lua` in TUNG's top-level `Mods` folder, beside `TUNG.exe`. Create the folder if needed. Use UTF-8 text, and check that the filename does not end in `.lua.txt`.

```lua
return {
    id = "hello-wood",
    name = "Hello Wood",
    version = "1.0.0",
    author = "Your name",
    description = "A small settings example.",

    onWorldReady = function(api)
        api.log("Hello Wood is ready")
    end,

    buildSettings = function(api, panel)
        local section = api.section(panel, "Greeting", "Saved between launches.")
        api.toggle(section, "Show greeting", api.get("show_greeting", true), function(value)
            api.set("show_greeting", value)
        end)
        api.button(section, "Say hello", function()
            if api.get("show_greeting", true) then
                api.log("Hello from your first mod!")
            end
        end)
    end,
}
```

Restart TUNG, press F10, and select Hello Wood. Click Say hello and look for `[Wood/hello-wood]` in `TUNG/Binaries/Win64/ue4ss/UE4SS.log`. Turn Show greeting off and restart: the setting should stay off. This example logs a message; it does not change gameplay.

## 2. Add behavior

The file must `return` a Lua table. Use the metadata fields shown above and a unique, stable ID. Use the same ID for the filename and package so disabling behaves consistently. A portable ID starts with a lowercase letter or digit and uses only lowercase letters, digits, `_`, or `-`, up to 40 characters. Do not start the filename with `_`: Wood skips it.

- `onWorldReady(api)`: called when Wood detects a different player-controller full name, including the first attachment. This is not a guaranteed callback for every map load. Reacquire game objects here.
- `onTick(api)`: optional repeated work while a valid controller exists, even when the menu is closed.
- `tickInterval`: number of Wood loop ticks between calls. Default 30; minimum 1, rounded down. The loop requests 16 ms, so 30 is roughly half a second, not a precise timer. Mods with the same interval are spread across those ticks to avoid running all their callbacks in one frame.
- `buildSettings(api, panel)`: called whenever Wood builds your settings page. Add controls here; avoid starting timers or installing hooks here because the page can rebuild.

Wood invokes these callbacks and its UI callbacks on the game thread. Keep them short. The Lua file itself executes during startup before a player controller is ready: put game-object work in callbacks. Wood catches load and lifecycle errors and logs them; a broken mod can still leave side effects.

There are no Wood `onEnable`, `onDisable`, or unload callbacks. Changes to mod files require a game restart. Avoid independent loops and keybinds unless you handle their state yourself; Wood does not stop them for you.

In Wood 1.2.0, changing Speedrun mode restarts TUNG. A Speedrun session never
executes user mod source, including top-level registrations; the restart helper
also isolates other UE4SS mods before starting the new process. Settings remain
saved for when the mode is turned off. `api.refreshSettings()` defers and merges
refresh requests until the next UI tick. Settings are cached during a session;
restart TUNG after changing INI files externally.

## 3. Use Wood's API

Call helpers with a dot, such as `api.get(...)`. These are the helpers implemented in `NativeMods/WoodRuntime/Scripts/main.lua` and `menu.lua`:

- `api.playerController`: current Unreal player controller. Check `object and object:IsValid()` before using UObject references; reacquire them after travel.
- `api.label(panel, text, size)`: add a text label; size is optional.
- `api.section(panel, title, description)`: return a child panel for related controls; description is optional.
- `api.button(panel, text, callback)`: add a button; callback takes no arguments.
- `api.toggle(panel, text, initial, callback)`: add an On/Off control; callback receives a boolean.
- `api.slider(panel, text, min, max, step, initial, callback, format)`: add a slider; callback receives a number. Use a positive step and valid bounds. Optional `format(value)` returns display text.
- `api.input(panel, hint, initial)`: return an editable text widget. Read it with `widget:GetText():ToString()` from an Apply button; there is no Wood text-change callback or automatic Enter-to-apply behavior.
- `api.refreshSettings()`: rebuild the selected settings page if it is visible. Old widget references become stale; do not reuse them.
- `api.get(key, default)`: read a saved value. A boolean or number default controls conversion; otherwise the stored value is a string. Missing values return the default.
- `api.set(key, value)`: write a single-line value to `.wood/<id>.settings.ini`. Use strings, numbers, or booleans; tables are not serialized. Keys contain only letters, digits, or underscores. Save when a value changes, not on every tick.
- `api.log(message)`: write a message prefixed with your mod ID to the UE4SS log.

Example: a numeric setting with an Apply button.

```lua
buildSettings = function(api, panel)
    local field = api.input(panel, "Amount: 1 to 10", tostring(api.get("amount", 1)))
    api.button(panel, "Apply", function()
        local amount = tonumber(field:GetText():ToString())
        if not amount or amount ~= amount or amount < 1 or amount > 10 then
            api.log("Enter a number from 1 to 10")
            return
        end
        api.set("amount", amount)
        api.refreshSettings()
    end)
end,
```

Insert this field into your returned table in place of its existing `buildSettings`. Wood saves the preference; your gameplay callback must read and apply it.

Wood's helpers cover menus and preferences. Gameplay uses UE4SS and TUNG's reflected Unreal objects. Confirm actual class paths, methods, and properties from inspected game objects or a working mod. Do not guess a TUNG API or memory offset. A validity check cannot make an incorrect engine call safe.

## 4. Test and troubleshoot

1. Test the `.lua` file before packaging. Restart after each edit.
2. Check F10 for load/settings errors, then read `TUNG/Binaries/Win64/ue4ss/UE4SS.log` for details.
3. Test settings, restart persistence, and a new run or world transition. Confirm any gameplay effect in TUNG.
4. If the mod is missing, check the top-level folder, extension, and filename. Speedrun mode blocks all mod execution and settings.
5. Keep one installed copy per ID. Remove the development `.lua` before installing its `.tungmod`. Wood 2.3.1 prioritizes packages with the same filename stem and skips duplicate IDs, but avoiding duplicate files prevents confusion and startup side effects.

Disabling is checked at startup. For plain Lua, the disabled-list entry is the filename without `.lua`; for a package it is the metadata ID. The loader overwrites a returned `enabled` field, so it is not a way to disable your mod. To add your own feature toggle, persist it with `api.set` and check it in your behavior callbacks.

## 5. Package and share

1. Open Wood Mod Packager and choose your `.lua` source.
2. Enter ID, name, version, author, and description. Package metadata overrides those five fields in the Lua table.
3. Optionally choose a PNG icon (128 by 128 recommended), select an output file, and click Build .tungmod.
4. Install only the resulting `.tungmod` in TUNG's `Mods` folder, restart, and test again.

Lua source must be UTF-8 and at most 1 MiB. Icons display within 128 by 128 without stretching; the original PNG is preserved. PNG icons may be at most 4 MiB and 2048 by 2048 pixels. Metadata limits in UTF-8 bytes: ID 40, name 80, version 40, author 60, description 500. The packager and runtime enforce the same byte limits.

A `.tungmod` is Wood's custom `TUNG-MOD/1` format, not a renamed ZIP. Use the packager. It bundles one Lua source, metadata, and an optional icon; it does not bundle extra scripts or other assets and does not validate gameplay behavior.

Share the `.tungmod` with a description, tested TUNG/Wood versions, install steps, controls, and known limits. Raw `.lua` files are also supported for development. Mods run Lua with game and file access, so install only mods you trust.

## 6. Ask another AI to write a mod

Copy the prompt below and replace the bracketed fields. For gameplay work, also provide relevant inspected TUNG objects or a working mod example. The public GitHub repository is the source of truth for Wood's runtime; the AI can read it directly, so you do not need to upload the loader source files.

```text
Write a standalone Lua mod for Wood, the TUNG mod loader.

Feature: [describe the behavior, controls, defaults, and limits]
Mod ID / display name / author: [fill in]
Tested Wood / TUNG version: [fill in or say unknown]
Verified TUNG objects, methods, properties, or working example: [link to findings or paste a summary]

Wood runtime source and API guide: https://github.com/clapbxt/WoodLauncher
Read these source files directly before writing:
- https://github.com/clapbxt/WoodLauncher/blob/main/NativeMods/WoodRuntime/Scripts/main.lua
- https://github.com/clapbxt/WoodLauncher/blob/main/NativeMods/WoodRuntime/Scripts/menu.lua
- https://github.com/clapbxt/WoodLauncher/blob/main/NativeMods/WoodRuntime/Scripts/mod_package.lua
- https://github.com/clapbxt/WoodLauncher/blob/main/docs/MODDING.md
Do not ask me to upload these public Wood source files. If you cannot access
GitHub, say so and identify what additional Wood API detail you need.

Follow this Wood implementation contract:
- One UTF-8 .lua file must return a table with id, name, version, author,
  description and optional onWorldReady(api), onTick(api), tickInterval,
  buildSettings(api, panel). Use a unique lowercase ID, up to 40 characters,
  starting with a letter or digit; remaining characters may include _ and -.
- The source executes at startup before a controller is ready. Put UObject
  work in lifecycle/UI callbacks. Those callbacks run on the game thread.
- onWorldReady fires on a changed player-controller full name, including first
  attachment. Reacquire UObject references and check IsValid before use.
- onTick runs even with the menu closed when a controller is valid.
  tickInterval is loop ticks, default 30, minimum 1. A requested loop tick is
  16 ms; this is not a guaranteed real-time or frame-based interval. Mods
  sharing an interval are distributed across its ticks to smooth callback work.
- buildSettings can repeat. Use it to build controls, not register hooks/loops.
- Call API functions with dots:
  api.label(panel, text, optionalSize)
  api.section(panel, title, optionalDescription) -> child panel
  api.button(panel, text, callback())
  api.toggle(panel, text, initialBoolean, callback(boolean))
  api.slider(panel, text, min, max, positiveStep, initialNumber,
             callback(number), optionalFormat(number))
  api.input(panel, hint, initialText) -> editable widget
  api.refreshSettings()
  api.get(key, default), api.set(key, value), api.log(message)
  api.playerController is the current controller.
- Read input with widget:GetText():ToString() in an Apply callback. Validate
  numbers/ranges. There is no built-in input callback or Enter-to-apply.
- get converts by the default's type. set stores single-line strings, numbers,
  or booleans; keys contain letters/digits/underscores. No table serialization.
  Save only on changes. refreshSettings replaces widgets; discard old references.
- No Wood onEnable/onDisable/unload callbacks, automatic timer cleanup,
  hot reload, or general-purpose gameplay helper API exists. enabled is owned
  by the loader. Use a saved feature toggle checked by behavior callbacks.
- Use only supplied or verified UE4SS/TUNG symbols. Do not invent paths,
  properties, methods, offsets, or a JavaScript/JSON mod API. If gameplay
  evidence is missing, ask for the specific inspection needed and label any
  incomplete feature; do not present guessed code as a working implementation.
- Keep callbacks short. Avoid unnecessary loops/keybinds and top-level effects.
- Packaging overrides id/name/version/author/description. Keep the source and
  package ID identical. Install one copy; restart after edits or installation.

Return the complete Lua file, a brief explanation of controls, installation
steps for testing the Lua in TUNG's top-level Mods folder, then packaging it
with Wood Mod Packager and installing only the .tungmod for release. Include
a manual test checklist covering
settings, persistence, travel, and gameplay. State unverified assumptions.
Do not claim in-game testing unless you actually performed it.

Treat the linked GitHub repository as the source of truth. Use its actual
implementation over conflicting generic UE4SS tutorials. The mod packager is
a separate download on the Developers page; it is not part of the runtime repo.
```
