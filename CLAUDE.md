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

Traps (checked 2026-11-14):
- In `claude agents --json`, state "blocked" with status "idle" only means the turn ended. It is not a block or a denial; show it as idle.
- Server alive: a running `claude.exe` process whose command line has `remote-control` and the project's session name (PowerShell `Get-CimInstance Win32_Process -Filter "Name='claude.exe'"`). A running server with no "P: ..." session only means nobody opened P yet: say that, never "server not running".

- Server history: the last lines of `logs/servers.log` (written by the watcher, see "Servers"). A DOWN or EXIT line since the last start is a problem: show when it happened and the cause the log gives.

Reply grouped by project. For each session show name, state and context fill when available (mark OVER as a problem). Under each project list what waits on the owner. Unreadable source: say "not checked: <what>", never guess.

A project's open question is only shown, never asked here: Pult cannot pass the answer on. The next-step question in Pult is a fix for a server or session, or, when there is none, which project session to open to answer what waits there.

## Servers

Pult owns the start of the Remote Control servers and project leads: `scripts/start-servers.ps1`
(run at Windows logon by the Startup folder shortcut "Pult - project servers") and
`scripts/stop-servers.ps1` (graceful stop; never kill these processes). The list of servers is
`scripts/servers.psd1`. Windows runs them; a Pult session runs them only after the owner's
explicit yes.

`scripts/watch-servers.ps1` (started by `start-servers.ps1`, hidden) checks every minute and
writes to `logs/servers.log` (not in git): STATE, DOWN with the session's last state and any
crash event, UP. Each Remote Control server's window adds an EXIT line with its exit code. The
watcher only logs; it never restarts anything.

## Limits

- Exception held by this project: read other projects' status files (PROGRESS.md and similar) and session state.
- Never change them during "статус". An edit in another repo, after the owner's yes, goes
  through the `other-repo-editor` subagent (global rule "Stay in the session's project"). Never start, stop or message sessions without the owner's explicit yes.
- On a problem (dead server, session over its limit, stuck session) only propose a fix. Act after the owner's explicit yes, and only on that fix.
- Use only read-only commands for "статус".

## Session title

Every Pult session title starts with "Пульт". The server also sets this as a name prefix; if the session can rename itself, it does.
