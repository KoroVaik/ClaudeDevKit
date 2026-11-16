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
6. After a dev-kit plugin update, a running P keeps the old skill. P: ClaudeDevKit tells the Pult session after each version it merges; Pult asks each P to reach a safe point, and restarts each one that answers «готовий» (`scripts/restart-leads.ps1 -Ready`, see `rules/hub.md`, "Restart leads for a plugin update"). By hand: `scripts/restart-leads.ps1`, or `scripts/stop-servers.ps1` (graceful stop) and then `scripts/start-servers.ps1`, or restart Windows. Each P continues its previous conversation (resumed, not fresh), reloading the skill.

Not confirmed: whether you can still attach to a P from a terminal with `claude attach <id>` (the old plugin README said so; not checked here), and the exact wording of the session list in the phone app.
