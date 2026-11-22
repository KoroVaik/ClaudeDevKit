# Map

Top level only. Most of the repo is Markdown prompts (skills and agents); the code that runs as a program
is listed below.

## Code folders

- `plugins/dev-kit/skills`, `plugins/dev-kit/agents` - the process as Markdown: skills and generic agents (coder, reviewer, investigator).
- `plugins/dev-kit/scripts` - Python: `check_docs.py` checks a project's docs (every epic and feature has its sections, links, anchors and "Built in" paths resolve), finds the feature that owns a code file, lists open tasks and defects and the base docs files a project lacks; `check_tests.py` is the tests check; `run_app.py` starts and stops a project's app from the commands in its profile; `sessions.py`, `migrations.py`, `retro.py` (also `session`, one session's units as a share of the weekly limit, and `calibrate`, the refit of that limit), `hard_bans.py` serve the project lead; `statusline.py` is the status line that shows the weekly use and logs it for that refit; `api_client.py` is the shared Claude API client that logs and reconciles spend, with its price table `plugins/dev-kit/api-prices.json`.
- `plugins/dev-kit/bin` - the commands on the Bash tool PATH while dev-kit is enabled: `dev-kit-check-docs`, `dev-kit-check-tests`, `dev-kit-app`, `dev-kit-sessions`, `dev-kit-migrations`, `dev-kit-retro`, `dev-kit-statusline`, `dev-kit-bans`, `dev-kit-api`.
- `plugins/dev-kit/hooks` - the hook that lets a project launch only its own agents, the hook that stops the known Windows shell traps, and the hook that tells an owner-started session the lead watches it ([hooks](hooks.md)).
- `plugins/dev-kit/slots.md`, `plugins/dev-kit/migrations.md` - the process steps (slots) and the changes every project must make after an update.
- `plugins/web-kit` - browser checks: skills and agents, `slots.md`, `browser-checks.md`; `scripts` holds `build-mockups.mjs` (mockup pages from JSON specs) and `capture.mjs` (headless full-resolution screenshots); `bin` holds `web-kit-mockups` and `web-kit-shot`.
- `plugins/unity-kit` - Unity: skills and agent, `slots.md`; `scripts` holds `user_check.py` (plays a recipe in the editor and writes a report) and `frames_to_gif.py` (cuts and crops frames into a GIF); `bin` holds `unity-kit-user-check` and `unity-kit-gif`.
- `plugins/pult/scripts` - PowerShell and Python of the hub: start, stop, watch and restart of the leads, the status page, the session list.
- `plugins/pult/hooks`, `plugins/pult/rules` - the SessionStart hook and the hub rules it adds in the home folder.
- `.claude-plugin`, `plugins/dev-kit/.claude-plugin`, `plugins/web-kit/.claude-plugin`, `plugins/unity-kit/.claude-plugin`, `plugins/pult/.claude-plugin` - the marketplace and plugin manifests.
- `tools/lint.py` - checks this repo: plugin manifests, skill and agent front matter, slot tables, hook config, project profiles ([repo checks](repo-checks.md)).
- `tools/tests` - the tests of the scripts and hooks.
- `.githooks/pre-commit`, `.github/workflows/ci.yml` - the checks before a commit and in CI.

## Processes

- The Pult watcher (`plugins/pult/scripts/watch-servers.ps1`, started at logon) checks the leads every minute,
  runs `dev-kit-sessions check` for each lead and wakes the leads and Pult by a cross-session message (a one-shot
  `claude -p`) only on an event; it also moves a lead that saved a handoff to a fresh session.
- The Remote Control server "Pult", with cwd = the home folder, serves the phone.
- The session watcher (`dev-kit-sessions watch`) runs in the background only of a project lead on dev-kit before 0.1.78.
- The retro scan runs from dev-kit's SessionEnd hook (one transcript) and SessionStart hook (the full pass once a day), which also starts a background «Ретро: <project>» session in a project with a lead.
- `dev-kit-app start` queues a project's app start between worktrees with a lock.

## Data stores

- `.claude/dev-kit.md` in every project - its profile ([project profile](project-profile.md)).
- The Pult state folder (pult under the user's .claude folder): logs (`servers.log`), `lead-versions.json`, the hold file, `status.html`, the wake files (`wake-pending.json`: messages not delivered yet; `wake-state.json`: size pushes and last send per target; `size-state.json`: transcript offsets for the size log).
- The dev-kit state folder of a project: the session registry, locks, `restart.json`, the delivered marks of `check` (`delivered.json`, `check-closed.json`, beside `limits.json` and `stale.json`).
- The API spend log (`api-calls.jsonl` in the dev-kit folder of the user's .claude folder, beside `credits.md`): one line per paid Claude API call from every project ([log and reconcile API spend](../features/log-and-reconcile-api-spend.md)).
- The usage log (`usage-log.jsonl` in the dev-kit folder of the user's .claude folder): one line per change of the weekly subscription per cent, written by `dev-kit-statusline`; `dev-kit-retro` fits the weekly limit from it and keeps the fit in its `state.json`.
