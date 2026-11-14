# ClaudeDevKit

[![CI](https://github.com/KoroVaik/ClaudeDevKit/actions/workflows/ci.yml/badge.svg)](https://github.com/KoroVaik/ClaudeDevKit/actions/workflows/ci.yml)

Three plugins for [Claude Code](https://claude.com/claude-code) that give AI coding agents a fixed
development process: plan, code, review, test, update the docs. It is a personal tool for solo
developers who let agents write most of the code and want to stay in charge of the decisions.

## The problem

An agent left alone on a project skips steps. It changes code without a test, forgets the docs, or
reviews its own work. These plugins write the process down as skills and agents, and a small amount of
Python code enforces the parts that can be checked by a program.

- `dev-kit` - the core: the process, generic agents (coder, reviewer, investigator), the documentation
  standard and its checker.
- `web-kit` - browser checks: end-to-end scenarios, layout checks, mockups, wide screenshots.
- `unity-kit` - Unity: a bridge to the open editor, a scripted "user check" of play, scene sketches, GIFs.

The plugins hold no project facts. Each project describes itself in one file, `.claude/dev-kit.md`.

## Example

A project enables the plugins and you tell Claude: "the Save button does nothing". The `fix-bug` skill then:

1. classifies the report (a functional bug, not a layout bug), so it knows which check to run later;
2. finds the root cause in code and writes a plan, then waits for your yes;
3. writes a failing test, fixes the cause, and runs the project's test command;
4. runs a browser check of the screen, if you allowed it;
5. updates the feature description in `docs/`, runs `dev-kit-check-docs`, and asks a separate
   `reviewer` agent to read the change.

Enable it in a project:

```bash
claude plugin marketplace add <path to this folder>
claude plugin install dev-kit@korov-dev --scope project
```

## What is code here

Most of the repo is Markdown prompts. The code that runs as a program:

| File | Lines | What it does |
|---|---|---|
| `plugins/dev-kit/scripts/check_docs.py` | 1355 | Checks a project's docs: every epic and feature has its sections, links, anchors and "Built in" paths resolve; finds the feature that owns a code file; lists open tasks and defects. |
| `tools/lint.py` | 461 | Checks this repo: plugin manifests, skill and agent front matter, slot tables, hook config, project profiles. |
| `plugins/dev-kit/hooks/narrow-agents.py` | 118 | A hook that lets a project launch only its own agents and those of its enabled plugins. |
| `plugins/dev-kit/scripts/run_app.py` | 330 | Starts and stops a project's app from the commands in its profile, with a queue lock between worktrees. |
| `plugins/unity-kit/scripts/user_check.py` | 544 | Plays a recipe (keys, mouse, console and state expectations) in the Unity editor and writes a report. |
| `plugins/unity-kit/scripts/frames_to_gif.py` | 240 | Cuts and crops recorded frames into a GIF. |
| `plugins/web-kit/scripts/build-mockups.mjs`, `capture.mjs` | 829, 351 | Builds mockup pages from JSON specs; takes full-resolution headless screenshots. |

The tests are in `tools/tests/`: 344 tests in 8 files (about 3000 lines), one skipped. Run them with:

```bash
python -m unittest discover tools/tests
python tools/lint.py
```

CI (`.github/workflows/ci.yml`) runs both on every push to `main` and on pull requests, with Python 3.13
and Node 22.

## Notes

- Some skill descriptions contain Ukrainian phrases. They are trigger phrases the author types to start
  a skill, so they are meant to stay.
- The marketplace is a local folder, so it is a working setup, not a packaged release.

## Project profile

A project that enables the plugins keeps `.claude/dev-kit.md`:

- `## All agents` - orientation files, processes agents never touch, shared rules.
- `## Slots` - optional table `| Slot | Skill or command |` that overrides a slot for this project;
  only `run-app` and `stop-app` may have several rows (a list of commands).
- `## <agent or skill name>` - rules for one role, e.g. `## reviewer`; they override the plugin
  defaults.
- `## documentation` - table `| Setting | Value |` for the docs check (code folders, scanned
  folders, size limits); the setting names are listed in `plugins/dev-kit/scripts/check_docs.py`.

## Docs check

`dev-kit-check-docs` (in `plugins/dev-kit/bin`, on the Bash tool PATH while dev-kit is enabled) checks
a project's docs against the `dev-kit:documentation` skill. A git pre-commit hook outside Claude Code
runs `plugins/dev-kit/scripts/check_docs.py --pre-commit`, finding this folder through
`~/.claude/plugins/known_marketplaces.json`.

## Web extension

`web-kit` fills `check-ui`, `check-usability`, `check-look` and `show-idea` (`plugins/web-kit/slots.md`).
Its skills `e2e-check`, `user-walk`, `visual-check` and `draw-mockup` name their agents (`web-kit:ui-tester`, `web-kit:app-user`,
`web-kit:layout-checker`, `web-kit:mockup-checker`, `web-kit:mockup-user`) and model themselves; the
manager reaches them through the slots. The skill `design-sandbox` runs the design-sandbox loop with `web-kit:sandbox-builder`, `web-kit:shot-taker` and `web-kit:design-critic`. Who answers which question, and the shared browser rules:
`plugins/web-kit/browser-checks.md`. Readable evidence screenshots of wide screens come from
`web-kit-shot` (headless full-resolution capture, `plugins/web-kit/scripts/capture.mjs`), because the in-app browser's
screenshot tool returns at most about 800 px wide. The project's facts go in its profile: `## e2e-check` (URLs, login,
screenshot folder, test-data marker; read by every browser skill and agent), `## ui-tester`, `## app-user`,
`## visual-check`, `## layout-checker` (sizes), `## mockup-checker`, `## draw-mockup` (mockups folder,
palette, languages), `## mockup-user` (persona of both user agents, `mockup-user` and `app-user`), `## design-sandbox` (worktree, sandbox URL, checks, boards), `## design-critic` (UI standard,
mockup folders, report language).
`web-kit-mockups` (in `plugins/web-kit/bin`, on the Bash tool PATH while web-kit is enabled) builds the
mockup pages from JSON specs; the format is `plugins/web-kit/skills/draw-mockup/spec-format.md`.

## Unity extension

`unity-kit` fills `show-idea` (`plugins/unity-kit/slots.md`) with `unity-kit:scene-sketch`, a temporary
storyboard of one moment of play, and `check-look` with `unity-kit:game-view-check`, one screenshot of
the Game view at its current size for the owner to judge. `unity-kit:unity-editor` holds the permissions and the order of every
Unity action in the owner's open editor (no batchmode, no restart, one operator at a time); it fills no
slot, so a project fills `run-app` and `run-tests` with its own commands or skills.
`unity-kit:unity-operator` runs the Unity commands the manager chose and returns raw results.
`unity-kit:game-clip` (no slot) shows the owner a short GIF of a moment of play: the operator records frames with the
project's own capture, the manager makes the GIF with `unity-kit-gif` (in `plugins/unity-kit/bin`; the script is
`plugins/unity-kit/scripts/frames_to_gif.py`, Python and Pillow) and sends it (a time window and, preferably, a crop around what moves), the owner judges the motion.
`unity-kit:user-check` fills `check-ui`: any agent writes a recipe of play (keys, mouse, the project's own
bridge commands, expectations on the console, state and files), the operator runs it with
`unity-kit-user-check <name>` (in `plugins/unity-kit/bin`, on the Bash tool PATH while unity-kit is enabled;
the runner is `plugins/unity-kit/scripts/user_check.py`) and returns the report, the manager concludes. The
plugin ships no Unity code: the project copies the sample state and IMGUI mouse commands from
`plugins/unity-kit/skills/user-check/samples/`. The project's facts go in its profile: `## unity-editor`
(the bridge, its wrapper command, versions, scene, build targets, devices, Profiler), `## unity-operator`,
`## user-check` (table `| Setting | Value |`: the bridge, recipe and report folders, scene, state command
and "ready", click command, panel scale; the format is in the skill), `## game-view-check` (the screenshot
command), `## game-clip` (the frame-recording command, where the frames and their time index land), `## scene-sketch` (subject, names, caption language).

## Slots

The core lists the process steps in `plugins/dev-kit/slots.md`. An extension fills slots in its own
`slots.md` (`| Slot | Skill |`, skill as `<plugin>:<skill>`). The manager reads these tables, not
skill descriptions.

## Starting and stopping the application

The `run-app` and `stop-app` slots of a profile may list several commands, one row each, in start order.
`dev-kit-app start` (in `plugins/dev-kit/bin`, on the Bash tool PATH while dev-kit is enabled; the runner is
`plugins/dev-kit/scripts/run_app.py`) runs the run-app commands in order, `dev-kit-app stop` the stop-app
commands in reverse, `dev-kit-app list` shows both. The plugin only sequences the project's commands: what may be
stopped (the owner's processes) is decided by the project's own helpers. The skills that start the application
run the teardown before the task ends. The rules: `plugins/dev-kit/slots.md`.

## Hooks

`dev-kit` ships a PreToolUse hook on the `Agent` tool (`plugins/dev-kit/hooks/`): a project may launch
only its own agents (`.claude/agents/*.md`) and agents of its enabled plugins (`<plugin>:<agent>`); built-in
and user agent types are denied. A project that had its own copy of this hook removes it.

## Authoring rules

- A skill description says only when to use it and starts with "Use when"; it never summarizes the
  steps (an agent that reads a summary follows it instead of the skill).
- An agent sets `name`, `description` and `model` explicitly.
- Agents and skills are addressed as `<plugin>:<name>`, e.g. `dev-kit:coder`.

## Checks

`python tools/lint.py` checks manifests, skills, agents, slot tables and the profiles of the projects
in `tools/projects.json` (local, not in git: `{"name": "folder"}`). It runs before every commit
(`.githooks/pre-commit`, enabled with `git config core.hooksPath .githooks`) together with
`claude plugin validate .` (the validate step needs the Claude Code CLI, so CI runs only the lint).

## After enabling a plugin

The install rewrites `.claude/settings.json`; check that existing hook fields (e.g. `onFailure`)
survived. The marketplace is a local folder, so an edit here reaches every project at its next
session start or after `/reload-plugins`. A new agent or skill cannot be called in a session that was
already running until `/reload-plugins` has run there; `claude plugin update` does not help while the
plugin version is unchanged.
