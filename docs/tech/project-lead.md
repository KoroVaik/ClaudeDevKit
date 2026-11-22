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
- `fill --self` prints the caller's own fill (the lead's move to a fresh session); `handoff save|go|status|clear`
  keeps the lead's handoff marker that the Pult watcher acts on.
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

Each project with a lead has its own retro. dev-kit hooks scan, with no model, each ending session's
transcript (and once a day all of them) for repeated, failed, slow and very many calls, for commands worth a
script and for token spend (too-long sessions, Opus coder subagents), and sort the findings into the project's
local item folder. When new findings wait, a session start in that project launches a background «Ретро:
<project>» session (`dev-kit:retro`): it reviews them with the project's rules in view, fixes trivial,
recurring gaps itself, sends urgent items to P and leaves the rest for P's weekly question to the owner. The
critical token problems (`dev-kit-retro critical`) also show in Pult's «статус». `dev-kit-retro session` gives one session's
units as a share of the weekly limit; the limit is refitted by `scan` and `calibrate` from the log that the status
line script `dev-kit-statusline` keeps (`usage-log.jsonl` in the dev-kit folder of the user's .claude folder).
