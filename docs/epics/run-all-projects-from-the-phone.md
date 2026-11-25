# Run all projects from the phone

Part of the [ClaudeDevKit product](../product.md).

## What it gives

The `pult` plugin ("Пульт", the hub) starts the project leads at Windows logon, runs one Remote Control
server whose session you open from the phone, and shows all projects' sessions, their state and what
waits on you. It only reads other projects' status files and session state; on a problem it proposes a
fix and acts after an explicit yes. It is enabled at user scope and acts only in a session whose cwd is
exactly the home folder; everywhere else it prints nothing. How to operate it:
[the plugin README](../../plugins/pult/README.md); the hub rules:
[hub rules](../../plugins/pult/rules/hub.md).

## A day with a project lead from the phone

The lead's rules (queue, task sessions, merge) are in the epic
[Work through a project lead](work-through-a-project-lead.md).

1. Each Lead ("L: Zhratva", "L: Prishch", "L: ClaudeDevKit") is up and ready when you open it; you do not
   start it yourself. How it starts and comes back:
   [Start leads at logon and heal them](../features/start-leads-at-logon-and-heal-them.md).
2. On the phone, open the Claude app and pick the session "L: <project>" from the session list. Give the Lead work
   in your own words: "add X", "fix Y". The Lead may show what it understood and ask "так".
3. The Lead starts a Manager named "M: <task>". It shows in the Claude app (phone and desktop) with no push
   ([Claude facts](../../plugins/dev-kit/claude-facts.md), "The «Remote control enabled» push comes with the `--remote-control` flag, not with Remote Control itself").
   You may open it and write to it: it follows your words and tells the Lead at once. It reports to the Lead when it is done, stuck, waits over a minute or needs your decision, and the Lead tells you. For a
   talk about the details the Lead proposes a "Discuss:" session, made for talking with you (it sends no push; the Lead tells you in one line to open it).
4. The Lead checks the finished work, merges it into main, removes the Manager and tells you the result.
5. Ask the "Pult" session for "статус": it also sends you the status page, one HTML file with every
   project's sessions (free, busy or ended) and the open questions from its PROGRESS.md. The page is a
   snapshot: it does not refresh itself. Ask the Lead "що зараз іде?" to see what runs and what waits on you.
6. After a dev-kit plugin update, a running Lead keeps the old skill until it is restarted; each Lead then
   continues its previous conversation (resumed, not fresh), reloading the skill. When and how the restart
   happens: [Start leads at logon and heal them](../features/start-leads-at-logon-and-heal-them.md).
7. Only urgent events reach your phone: a Lead pushes when a Manager crashed or cannot go on without you, a risk to
   data or money, and once when its first question waits on you; Pult pushes when the watcher gave up on a
   server or session (the watcher tells Pult by message; when Pult is down, a running Lead pushes for it).
   You also get one push when a session's conversation grows past 0.7 of its window, so you move it to a
   new session. The watcher cannot push by itself (a new session's push is refused: [Claude facts](../../plugins/dev-kit/claude-facts.md), "A push from a fresh session is refused"), so it asks Pult, or a
   running Lead when Pult is down, to send each push. Nothing is shown while the Claude app is open on screen ("No push shows while the Claude app is open on the phone").

The commands behind steps 5 and 6 (`status-page.py`, `list-sessions.py`, `restart-leads.ps1`) are in the
plugin README.

## Features

- [Start leads at logon and heal them](../features/start-leads-at-logon-and-heal-them.md)

## Not written yet

The status page, the phone pushes and the hub rules (`plugins/pult/rules/hub.md`) have no feature files;
steps 5 and 7 above hold what the README stated about them.
