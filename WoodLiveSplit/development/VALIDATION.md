# Validation

Version 1.1 adds the bundled BAT/PowerShell setup and valve `Interact` hooks.
The live test registered all four hooks and dispatched a Blue valve interaction
at game time 17.862910714; the snapshot recorded 17.8629107 immediately. Fixture
tests verify that repeat interactions count once and that timestamps are emitted
before the animation track completes. Setup tests verify installation, shortcut
arguments, and preservation of saved attempt count and PB on repeat installation.

Tested with the installed Steam game and LiveSplit 1.8.37 on 2026-10-11.

- The packaged `.tungmod` loads through Wood 2.3.2.
- Loading the supplied `.lsl` loads the custom component.
- A fresh normal Speedrun map starts LiveSplit and feeds it `FinalTimerFloat`.
- Real game snapshots continue advancing without Lua errors; manual LiveSplit
  pause holds the timer.
- Lua event fixtures cover four distinct valves, door, airborne-to-grounded
  Hedge height, result-widget time, menu, retries, unsupported mode, late
  attachment and the enable switch.
- Tests against LiveSplit's actual model cover automatic route creation,
  catch-up event times, duplicates, authoritative finish, skipped route events,
  retries, manual reset/pause, existing runs/PBs and Finish-only runs.

A complete played route has not been validated. In particular, the inherited
Hedge region remains experimental. This is a testable first release, not a
claim that every route event has been confirmed during a complete speedrun.

The reflected properties were checked against a fresh UE4SS object dump:
`BP_Player_C.FinalTimerFloat`, `GI_C.Speedrun?`, `GI_C.Checkpoint?`,
`GI_C.TinyTungSpeedrun?`, `GI_C.B-HOP MODE ON?`,
`BP_TurnValves_C.canStartObjective?`, `BP_ValveDoor_C.hasOpenedDoorBefore?`,
each valve's `RotateValveTimeline_RotateValveTrack_*`, and
`WB_EndSpeedrunningTime_C.TimerNumber`.

Run the Lua fixtures with Wood's Python environment: `python test_mod.py`.
Compile `Component.cs` and `TestComponent.cs` into a test executable referencing
`LiveSplit.Core.dll` and `UpdateManager.dll`, then run it next to LiveSplit's
dependency DLLs. The test executable uses isolated in-memory runs and does not
open or alter your saved splits.

Version 1.1.1: Hedge checks only Z 360-425 after the door opens. Tests cover
unrelated X/Y positions, airborne detection, both height boundaries, and no
trigger before the door or outside the height range.
