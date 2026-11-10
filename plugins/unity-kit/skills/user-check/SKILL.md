---
name: user-check
description: Use when the `check-ui` slot comes up in a Unity project, or an agent must check a piece of play in the running game (a button, a key, a drag, a rare event and what follows) without the owner playing it - to write or change a user check recipe, to brief its run, or to read its report.
---

# User check

A user check is a short piece of play written as a recipe: a list of steps in plain words. The agent that
needs the answer (the manager or any agent) writes the recipe; `unity-kit:unity-operator` runs it with one
command; the manager reads the report and draws the conclusion. The author never touches Unity.

Read the profile section `## user-check` of `.claude/dev-kit.md` first (format below). Without it, tell the
owner which settings are missing; never guess a bridge command.

## Run

    unity-kit-user-check <name> [--dry-run]

From the project folder; `<name>` is a recipe in the profile's `recipes` folder (or a path to a `.json`).
`--dry-run` reads the recipe and its blocks and prints the steps without Unity: the author runs it after
every edit. A real run enters Play Mode, so it follows `unity-kit:unity-editor`: the owner's yes for the task,
run by `unity-kit:unity-operator`, whose brief holds the command and that yes.

The runner refuses (exit 2) in Play Mode, while compiling or with another scene than the profile's `scene`;
enters Play Mode, plays the steps in order, stops at the first failed step and plays the recipe's
`on-failure` steps (default `shot failure`), counts the console errors since the start, leaves Play Mode and
writes `<reports>/<stamp>_<name>/report.txt` with the screenshots beside it. Exit code: 0 passed, 1 a step
failed, 2 not run or broken off (a refusal, a bridge that did not answer, a bad recipe or profile).

## Recipe

    {
      "about": "Reset makes every item whole again",
      "steps": [
        "use ready",
        "drag 0.30,0.60 0.50,0.60 0.5",
        "wait 3",
        "click panel:137,33",
        "expect-state ready within 30",
        "expect-file Logs/save/*.json items.length=12 within 2",
        "shot after-reset",
        "use no-errors"
      ],
      "on-failure": ["shot failure"]
    }

A step is a line of words; a regex with spaces goes in double quotes. `within S` lets an expectation re-read
the game for up to S seconds (at most 600); without it the expectation is checked once.

| Step | What it does |
|---|---|
| `wait S` | waits S seconds |
| `key <Key> [S]` | presses an Input System key (`simulate-keyboard`), held S seconds |
| `click <point>`, `drag <point> <point> [S]` | the mouse of an IMGUI panel, through the project's `click-command` |
| `mouse <Action> <point> [options]` | the Input System's mouse (`simulate-mouse-input`: `Click`, `LongPress`, ...; options as its `--help`) |
| `call <command> [args]` | any bridge command, e.g. the project's fault command or `simulate-mouse-ui`; fails if it answers `Success: false` |
| `expect-log <regex> [within S]` | a console line written after the last action matches |
| `expect-state [not] ready\|Field=value [within S]` | the project's state command: `ready` is the profile's condition |
| `expect-file <glob> [path=value] [within S]` | the newest file written since the last action; `path` is a dotted JSON path (`items.1.n`), `length` gives a list's length |
| `expect-no-errors` | no console error since the check started |
| `shot [label]` | a screenshot of the game picture, `NN_<label>.png` |
| `use <block>` | the block's steps in place of this line |

- A point is `x,y` as fractions of the game picture from its top left (`0.5,0.5` is the middle), or
  `panel:x,y` in the panel's units from its top left (a unit is `max(1, height / panel-height)` pixels; a
  panel button keeps its place there when the window size changes).
- An action (`key`, `click`, `drag`, `mouse`, `call`) marks the console and the time: `expect-log` and
  `expect-file` look only after the last mark.
- `{setting}` in a step is replaced by that profile setting, e.g. `within {ready-within}`.

## Blocks

A block is a file `{"about": ..., "steps": [...]}` that a recipe includes with `use <name>`. The plugin's
blocks (`${CLAUDE_PLUGIN_ROOT}/skills/user-check/blocks/`): `ready` (the profile's ready condition within
`ready-within`) and `no-errors`. A project adds its own in `<recipes>/blocks/<name>.json`; a project block
with a plugin block's name replaces it. A block may use other blocks.

## Choosing expectations

- Wait for a condition, not a time: `expect-state ... within S` or `expect-log ... within S` instead of
  `wait`. Keep `wait` for what has no signal (letting a motion play out before the next action).
- Bound each wait by what a player would accept, not by the slowest run seen; a step that needs more is
  a finding.
- Prove the effect, not the action: after `click`, expect the state, log line or file the button causes. A
  `PASS` of an action step only says the input was delivered.
- Prefer state and files over log text: a reworded message breaks a log expectation.
- When the game shows nothing to expect, the project adds a field to its state command or a small bridge
  command; never judge the look from a screenshot: screenshots go to the owner.
- End with `use no-errors` unless an error is the point of the check.

## Report

    user check reset-whole: Reset makes every item whole again
    game picture 2194x1043
    PASS  1 [ready] expect-state ready within 60 | Loaded True
    PASS  2 drag 0.30,0.60 0.50,0.60 0.5 | drag at 658,626 of 2194x1043 game pixels to 1097,626
    PASS  3 wait 3 | waited 3 s
    PASS  4 click panel:137,33 | click at 278,67 of 2194x1043 game pixels
    FAIL  5 expect-state ready within 30 | Loaded False
    PASS  1 on failure: shot failure | Logs/agent_checks/20261110_120000_reset-whole/01_failure.png (2194x1043)
    console errors since the start 0
    Play Mode left
    result: FAILED (code 1); report Logs/agent_checks/20261110_120000_reset-whole

- Each step line: `PASS`/`FAIL`, its number, the block it came from, the step, and after `|` the evidence
  (what the game answered). The first `FAIL` is the answer; later steps did not run.
- A `FAIL` of an expectation means the game did not reach that state in time (its evidence is the last value
  seen); a `FAIL` of an action means the input or command was refused. Exit 2 means nothing about the game was checked.
- The manager concludes: a bug, a wrong recipe (a wrong point, a too-short bound) or an unclear rule. The
  recipe is corrected by its author, never by the operator, and a changed bound is said to the owner.
- Screenshots go to the owner as files; the agents do not judge the look.

## Profile: `## user-check`

A table `| Setting | Value |` in `.claude/dev-kit.md`:

| Setting | Value |
|---|---|
| `uloop` | the `uloop` command or its full path (default `uloop` on PATH) |
| `uloop-env` | environment for `uloop`, `NAME=value; NAME=value` |
| `recipes` | the recipes folder from the project root (required) |
| `reports` | the reports folder from the project root (required) |
| `scene` | the scene that must be open, e.g. `Assets/Scenes/Main.unity` (empty: any) |
| `state-command` | the project's state command (required); it answers JSON with `Playing`, `Compiling`, `Scene`, `GameWidth`, `GameHeight` and the game's own fields |
| `ready` | what "ready" means, `Field=value; Field=value` on the state command's answer (default `Playing=true`) |
| `ready-within` | seconds the `ready` block waits (default 60) |
| `click-command` | the project's IMGUI mouse command for `click` and `drag` (empty: those steps fail) |
| `panel-height` | the height in pixels at which the panel's unit is one pixel (empty: always one pixel) |

## Project bridge commands

unity-kit ships no Unity code. The samples in `${CLAUDE_PLUGIN_ROOT}/skills/user-check/samples/` are copied
into the project's Editor code, renamed and named in the profile: `StateCommand.cs` (the five fields the
runner needs; add the game's own) and `GuiCommand.cs` (the IMGUI mouse: the Input System's mouse does not
reach IMGUI). A fault or other project action is a small command of the project, called with `call`. A new
command is a code change of the project, with its usual review and compile.
