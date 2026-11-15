# Pult

Pult ("пульт", the hub) is a small monitor. The owner opens its session from the phone to see the state of all his projects. Keep it simple: it watches and reports, it does not manage.

## Projects in scope

To add a project, add one row here and nothing else.

| Name | Path |
|---|---|
| Zhratva | `C:/Users/korov/MyRepositories/Zhratva` |
| Prishch | `C:/Users/korov/MyRepositories/Prishch` |
| ClaudeDevKit | `C:/Users/korov/MyRepositories/ClaudeDevKit` |

All use the dev-kit plugin. Each has a project lead "P: <project>": a background session with Remote Control that `scripts/start-servers.ps1` starts directly (no server). The lead starts task sessions "C: <feature>". Only Pult itself runs as a Remote Control server.

## Answering "статус"

Read only. Sources, per project:
- Sessions and state: `claude agents --json --cwd <project path>` (add `--all` to include finished ones). Worktrees of the project sit under that path or next to it; group by project.
- Task sessions registered by the lead and their context fill: `dev-kit-sessions --project <project path> list` and `dev-kit-sessions --project <project path> fill`. If the command is not on PATH, run `python C:/Users/korov/MyRepositories/ClaudeDevKit/plugins/dev-kit/bin/dev-kit-sessions ...`.
- Desktop-app sessions of all projects (title, project folder, state, age): `python scripts/list-sessions.py`.
- What waits on the owner: the "Open questions" section of `<project path>/PROGRESS.md` (written by the lead P and task sessions C). "None." means nothing waits.

Traps (checked 2026-11-14):
- In `claude agents --json`, state "blocked" with status "idle" only means the turn ended. It is not a block or a denial; show it as idle. Name a session's state only as idle or busy ("вільна" / "зайнята"); never "працює", which the owner reads as busy on a task.
- P alive: `claude agents --json --cwd <project path>` lists a live background session named "P: <project>" (the same check `start-servers.ps1` uses). None means P is down.
- Pult server alive: a running `claude.exe` process whose command line has ` remote-control ` and "Pult" (PowerShell `Get-CimInstance Win32_Process -Filter "Name='claude.exe'"`).

- Server history: the last lines of `logs/servers.log` (written by the watcher, see "Servers"). A DOWN or EXIT line since the last start is a problem: show when it happened and the cause the log gives.

Reply grouped by project. For each session show name, state and context fill when available (mark OVER as a problem). Under each project list what waits on the owner. Unreadable source: say "not checked: <what>", never guess.

Pult only informs. A project's open question is only shown, never asked here: Pult cannot pass the answer on. A Pult reply ends with no question, except when a server or session is broken and a fix needs the owner's yes. This wins over the global "end every reply with the next-step question".

## Servers

Pult owns the start of the Remote Control servers and project leads: `scripts/start-servers.ps1`
(run at Windows logon by the Startup folder shortcut "Pult - project servers") and
`scripts/stop-servers.ps1` (graceful stop; never kill these processes; it refuses while a session under a server's folder is busy, `-Force` overrides, `-CheckOnly` only lists). The list of servers is
`scripts/servers.psd1`. Windows runs them; a Pult session runs them only after the owner's
explicit yes. A lead is resumed, not started fresh: `start-servers.ps1` takes the newest background
session with the lead's name and folder (`claude agents --json --all`) and runs
`claude --bg --resume <sessionId> -- '/dev-kit:project-lead'` (helpers in `scripts/resume-lib.ps1`;
the log gets RESUMED instead of STARTED). No other flag may be added to that command: a flag makes
claude start a copy, so before resuming it rewrites `--model` / `--effort` in the job's saved
options (`~/.claude/jobs/<short id>/state.json`, "respawnFlags"; log MODEL): leads run on Opus,
medium reasoning (`$LeadModel` / `$LeadEffort` in `resume-lib.ps1`). Without an earlier session
it starts fresh with the same model. Then it pins every
live lead in `~/.claude/jobs/pins.json` (log PINNED): Claude's background service closes an
unpinned background session after 8 h of waiting (daemon.log "bg retire ... idle-prompt"). A Remote Control
server first tries `claude remote-control --continue` (no `--spawn`: they cannot be combined);
if that fails within 20 s, the log gets CONTINUE-FAILED and the server starts fresh. Not yet
checked on a real restart.

`scripts/restart-leads.ps1 [-Name ...] [-Force]` restarts leads so they load a new dev-kit
version (stop, then `start-servers.ps1` resumes them); a busy lead is skipped unless `-Force`.

`scripts/watch-servers.ps1` (started by `start-servers.ps1`, hidden) checks every minute and
writes to `logs/servers.log` (not in git): STATE, DOWN with the session's last state and any
crash event, UP. Each Remote Control server's window adds an EXIT line with its exit code. The
watcher only logs; it never restarts anything.

## Limits

- Exception held by this project: read other projects' status files (PROGRESS.md and similar) and session state.
- Never change them during "статус". An edit in another repo, after the owner's yes, goes
  through the `other-repo-editor` subagent (global rule "Stay in the session's project"). Never start or stop sessions without the owner's explicit yes.- On a problem (dead server, session over its limit, stuck session) only propose a fix. Act after the owner's explicit yes, and only on that fix.
- Use only read-only commands for "статус".

## Session title

Every Pult session title starts with "Pult". The server also sets this as a name prefix; if the session can rename itself, it does.
