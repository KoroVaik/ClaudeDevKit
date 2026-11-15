# Pult

"Пульт" (the hub): a small monitor project. Its Claude session is opened from the phone.
On "статус" it shows all projects' sessions, their state and what waits on the owner.
It only reads other projects' status files and session state; on a problem it proposes a fix and acts after an explicit yes.
Project list and rules: `CLAUDE.md`.

## Working with a project lead (P) from the phone

P is one session per project. It starts task sessions (C), each in its own worktree, merges their finished work into main and tells you the result. It does no task work itself.

1. At Windows logon, `scripts/start-servers.ps1` starts each P ("P: Zhratva", "P: Prishch", "P: ClaudeDevKit") as a background session with Remote Control. Its first prompt is `/dev-kit:project-lead`, so P is ready when you open it. You do not start it yourself.
2. On the phone, open the Claude app and pick the session "P: <project>" from the session list. Give P work in your own words: "add X", "fix Y". P may show what it understood and ask "так".
3. P starts a C named "C: <task>". It appears as its own session in the app. Talk to that C directly for details; it reports to P when it is done, stuck or needs your decision.
4. P checks the finished work, merges it into main, removes the C and tells you the result.
5. Ask P "що зараз іде?" to see what runs and what waits on you. Ask the "Pult" session for "статус" to see all projects at once. To list all desktop-app sessions of all projects, run `python scripts/list-sessions.py`.
6. After a dev-kit plugin update, a running P keeps the old skill. Run `scripts/stop-servers.ps1` (graceful stop), then `scripts/start-servers.ps1`, or restart Windows.

Not confirmed: whether you can still attach to a P from a terminal with `claude attach <id>` (the old plugin README said so; not checked here), and the exact wording of the session list in the phone app.
