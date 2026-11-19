# pult

"Пульт" (the hub), a plugin of the `korov-dev` marketplace. It starts the project leads at Windows logon,
runs one Remote Control server whose session you open from the phone, and shows all projects' sessions,
their state and what waits on you. It only reads other projects' status files and session state; on a
problem it proposes a fix and acts after an explicit yes.

## How it works

- The plugin is enabled at user scope, so it loads in every session on the machine. It acts only in a
  session whose cwd is exactly the home folder: the SessionStart hook `hooks/hub-rules.py` then adds the
  hub rules (`rules/hub.md`) to the context. Everywhere else (any project folder, including those under
  home) the hook prints nothing.
- The Remote Control server "Pult" runs with cwd = the home folder, so its sessions get these rules.
- The project list is the lead entries of `scripts/servers.psd1`. To add a project, add one row there.
- Logs: `~/.claude/pult/logs/servers.log` (written by `start-servers.ps1` and `watch-servers.ps1`; nothing is
  written inside the plugin folder).
- The watcher (`scripts/watch-servers.ps1`, started at logon) checks every minute. A lead or server of
  `servers.psd1` that is down for two checks is brought back the same way as at logon (log HEAL; at most 3
  tries an hour, then GIVEUP). A task session a project lead registered, closed by Claude Code (no
  process, not stopped on purpose), comes back with `claude respawn` (log HEAL-TASK). A live lead or task session that stopped on the
  usage limit is logged once per stop (LIMIT, with the reset time; LIMIT-END when it goes on). It also removes
  dev-kit lock files whose owner is gone (log UNLOCK). It restarts a lead that runs on an older dev-kit version
  than the installed `plugins/dev-kit/.claude-plugin/plugin.json`, with no message from the hub: an idle lead
  at once (log RESTART-LEAD). A busy lead is not interrupted: on its ordinary wake-ups it notices the new
  version, reaches a safe point and runs `dev-kit-sessions restart ready --version <V>` (a file `restart.json`
  in the project's dev-kit state folder); the watcher then restarts it (RESTART-LEAD with `ready`) if the mark
  is under 10 minutes old, else it clears it (READY-EXPIRED). `scripts/restart-leads.ps1 -Ask` is the fast
  path on your ask: it restarts the idle leads now and writes a request for each busy one (`Asked: <name>`);
  that lead's session watcher exits 7 once with `restart requested: <V>`. One try per lead per version; a
  failure is logged as RESTART-LEAD-FAILED. A leftover `restart.json` of a lead already on the new version
  is cleared (RESTART-CLEARED). The versions the lead processes started on (by pid and start time) are kept
  in `~/.claude/pult/lead-versions.json` (log LEAD-VERSION). It never touches your own sessions, taken-over ones included. `stop-servers.ps1` and `restart-leads.ps1` pause it
  (a hold file) until the next `start-servers.ps1` run, so a stop on purpose stays stopped. A lead stopped
  only with `claude stop` comes back; to retire one project, remove its row from `servers.psd1`.
- A lead row in `servers.psd1` may set `Prompt`, `Model` and `Effort` (defaults: `/dev-kit:project-lead`,
  Opus, medium); a throwaway test lead uses a cheap model this way.

## Start at logon

Put a shortcut "Pult - project servers" in the Windows Startup folder (`shell:startup`) with the target:

    powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "<repo>/plugins/pult/scripts/start-servers.ps1"

`<repo>` is this repository's folder. `scripts/stop-servers.ps1` stops everything gracefully (it refuses while
a session is busy, `-Force` overrides, `-CheckOnly` only lists).

## Working with a project lead (P) from the phone

P is one session per project. It starts task sessions (C), each in its own worktree, merges their finished work into main and tells you the result. It does no task work itself.

1. At Windows logon, `scripts/start-servers.ps1` starts each P ("P: Zhratva", "P: Prishch", "P: ClaudeDevKit") as a background session with Remote Control. Its first prompt is `/dev-kit:project-lead`, so P is ready when you open it. You do not start it yourself.
2. On the phone, open the Claude app and pick the session "P: <project>" from the session list. Give P work in your own words: "add X", "fix Y". P may show what it understood and ask "так".
3. P starts a C named "C: <task>". It appears as its own session in the app. Talk to that C directly for details; it reports to P when it is done, stuck or needs your decision.
4. P checks the finished work, merges it into main, removes the C and tells you the result.
5. Ask the "Pult" session for "статус": it also sends you the status page, one HTML file with every project's sessions (free, busy or ended) and the open questions from its PROGRESS.md. To make the page yourself, run `python scripts/status-page.py`; it writes `~/.claude/pult/status.html` (`--out` for another file). The page is a snapshot: it does not refresh itself. Ask P "що зараз іде?" to see what runs and what waits on you. To list all desktop-app sessions of all projects, run `python scripts/list-sessions.py`.
6. After a dev-kit plugin update, a running P keeps the old skill. The watcher notices the new version by itself and restarts each P (see the watcher above); to hurry it, run `scripts/restart-leads.ps1 -Ask`. By hand: `scripts/restart-leads.ps1`, or `scripts/stop-servers.ps1` (graceful stop) and then `scripts/start-servers.ps1`, or restart Windows. Each P continues its previous conversation (resumed, not fresh), reloading the skill.

7. Only urgent events reach your phone: a P pushes when a C crashed or cannot go on without you, a risk to data or money, and once when its first question waits on you; Pult pushes when the watcher gave up on a server or session (it wakes on `scripts/watch-log.py`, armed by your first message to Pult after it restarts). Nothing is shown while the Claude app is open on screen.

Not confirmed: whether you can still attach to a P from a terminal with `claude attach <id>` (the old plugin README said so; not checked here), and the exact wording of the session list in the phone app.
