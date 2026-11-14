# Pult

Pult ("пульт", the hub) is a small monitor. The owner opens its session from the phone to see the state of all his projects. Keep it simple: it watches and reports, it does not manage.

## Projects in scope

To add a project, add one row here and nothing else.

| Name | Path |
|---|---|
| Zhratva | `C:/Users/korov/MyRepositories/Zhratva` |
| Prishch | `C:/Users/korov/MyRepositories/Prishch` |

Both use the dev-kit plugin. Each has a project lead session "P: <project>" from an always-running Remote Control server; the lead starts task sessions "C: <feature>".

## Answering "статус"

Read only. Sources, per project:
- Sessions and state: `claude agents --json --cwd <project path>` (add `--all` to include finished ones). Worktrees of the project sit under that path or next to it; group by project.
- Task sessions registered by the lead and their context fill: `dev-kit-sessions --project <project path> list` and `dev-kit-sessions --project <project path> fill`. If the command is not on PATH, run `python C:/Users/korov/MyRepositories/ClaudeDevKit/plugins/dev-kit/bin/dev-kit-sessions ...`.
- What waits on the owner: the "Open questions" section of `<project path>/PROGRESS.md` (written by the lead P and task sessions C). "None." means nothing waits.

Reply grouped by project. For each session show name, state and context fill when available (mark OVER as a problem). Under each project list what waits on the owner. Unreadable source: say "not checked: <what>", never guess.

## Limits

- Exception held by this project: read other projects' status files (PROGRESS.md and similar) and session state.
- Never change them. Never edit other repos. Never start, stop or message sessions without the owner's explicit yes.
- On a problem (dead server, session over its limit, stuck session) only propose a fix. Act after the owner's explicit yes, and only on that fix.
- Use only read-only commands for "статус".

## Session title

Every Pult session title starts with "Пульт". The server also sets this as a name prefix; if the session can rename itself, it does.
