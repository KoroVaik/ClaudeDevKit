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
- `check` is one round of the watch, run by the Pult watcher each minute for each lead: one line per event
  not delivered yet (gone, finished, limited, stale, fill, restart), marks nothing. The Pult watcher sends the
  lines to the lead as a cross-session message and, once the message reached the lead, runs `mark` for each
  (`delivered.json`, `limits.json`, `stale.json` or the restart file beside the registry). P wakes only on a
  task session's report, the owner's message, such an event message, or a keep-warm ping.
- `watch` is the older background watcher, kept for leads on dev-kit before 0.1.78: silent while its sessions
  live, it exits when one ends, writes the line "Роботу завершено", stops on the usage limit, or has waited
  `--stale-minutes` (20) since its last reply.
- `fill --over-only` prints only the sessions past the fill limit; `size --id ...` prints a session's
  conversation size and window (the Pult watcher's 0.7 push and its size log).
- `state` prints each registered session as working, waiting, finished or gone with the gist of its last reply.
- `answers` prints what the owner wrote in a session after its last SendMessage (its last report or
  question), so the lead never asks him what he already answered there.
- `add --owner` registers a session the owner started.

Why: the host kills a background watcher after 2 hours, and the leads and Pult were woken only to re-arm
theirs; the owner approved on 2026-11-20 that no Claude session keeps a watcher (plan «Pult idle cost»). The
Pult watcher, which runs outside Claude Code, also brings back task sessions that Claude Code closed
([Start leads at logon and heal them](../features/start-leads-at-logon-and-heal-them.md)).

## Migrations: `dev-kit-migrations`

After a dev-kit update, Pult restarts the leads so they load the new skill. On start and after that restart
P runs `dev-kit-migrations pending` and hands the changes every project must make in its own files (the
entries of `plugins/dev-kit/migrations.md`) to one task session.

## Retro: `dev-kit-retro`

In this repo P also runs `dev-kit-retro check`: once a day it scans the transcripts of all sessions, with no
model, for repeated, failed, slow and very many calls, for commands worth a script and for token spend
(too-long sessions, Opus coder subagents). A subagent first checks the findings: with none real, P closes them itself; with
1-2 simple ones P asks the owner in its own chat; otherwise it proposes a retro session (`dev-kit:retro`).
The owner says yes or no to each fix. Token problems come first in the list and in the retro; the critical
ones (`dev-kit-retro critical`) also show in Pult's «статус».
