# Project lead tools

Code: `plugins/dev-kit/scripts/sessions.py`, `plugins/dev-kit/scripts/migrations.py`, `plugins/dev-kit/scripts/retro.py`,
`plugins/dev-kit/bin`, `plugins/dev-kit/skills/project-lead`. The rules the owner sees:
[Hand work to the project lead](../features/hand-work-to-the-project-lead.md) and
[Take over a session I started](../features/take-over-a-session-i-started.md); the rules for P itself are in
`plugins/dev-kit/skills/project-lead/SKILL.md`.

## Sessions: `dev-kit-sessions`

- `others` lists the other live sessions of the repository, one the owner started included, without reading
  code. P, and any session through the manager skill, runs it before a task starts; the
  `dev-kit:overlap-checker` agent then compares them with the task.
- `watch` is a background watcher: generic (any session ids, so other tools can use it too), silent while
  its sessions live, it exits when one ends, writes the line "Роботу завершено", stops on the usage limit, or
  has waited `--stale-minutes` (20) since its last reply (`stale:`, each wait once; `stale.json` beside the
  registry keeps the waits reported, so a restart does not repeat one). P wakes only on a task
  session's report, the owner's message, or the exit of this watcher.
- `state` prints each registered session as working, waiting, finished or gone with the gist of its last reply.
- `add --owner` registers a session the owner started.

Why: Claude Code can stop a background shell of an idle session when Windows runs low on memory (seen on
2026-11-16), so P re-arms its watcher by itself with no owner yes (owner, 2026-11-16); a dead watcher's
leftover lock must not block the new one. The Pult watcher, which runs outside Claude Code, brings back task
sessions that Claude Code closed ([Start leads at logon and heal them](../features/start-leads-at-logon-and-heal-them.md)).

## Migrations: `dev-kit-migrations`

After a dev-kit update, Pult restarts the leads so they load the new skill. On start and after that restart
P runs `dev-kit-migrations pending` and hands the changes every project must make in its own files (the
entries of `plugins/dev-kit/migrations.md`) to one task session.

## Retro: `dev-kit-retro`

In this repo P also runs `dev-kit-retro check`: once a day it scans the transcripts of all sessions, with no
model, for repeated, failed, slow and very many calls, for commands worth a script and for token spend
(too-long sessions, Opus coder subagents). A subagent first checks the findings: with none real, P closes them itself; with
1-2 simple ones P asks the owner in its own chat; otherwise it proposes a retro session (`dev-kit:retro`).
The owner says yes or no to each fix.
