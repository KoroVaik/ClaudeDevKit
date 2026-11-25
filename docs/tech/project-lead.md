# Project lead tools

Code: `plugins/dev-kit/scripts/sessions.py`, `plugins/dev-kit/scripts/migrations.py`, `plugins/rules-kit/scripts/retro.py`,
`plugins/dev-kit/scripts/docs_weekly.py`, `plugins/dev-kit/bin`, `plugins/dev-kit/skills/project-lead`. The rules the owner sees:
[Hand work to the project lead](../features/hand-work-to-the-project-lead.md) and
[Take over a session I started](../features/take-over-a-session-i-started.md); the rules for the Lead itself are in
`plugins/dev-kit/skills/project-lead/SKILL.md`.

## Sessions: `dev-kit-sessions`

- `others` lists the other live sessions of the repository, one the owner started included, without reading
  code; the `dev-kit:overlap-checker` agent then compares them with the task (who runs it and when: the
  feature, section "No two sessions on the same task").
- `check` is one round of the watch, run by the Pult watcher each minute for each lead: one line per event
  not delivered yet (gone, finished, limited, stale, fill, restart), marks nothing. The Pult watcher sends the
  lines to the lead as a cross-session message and, once the message reached the lead, runs `mark` for each
  (`delivered.json`, `limits.json`, `stale.json` or the restart file beside the registry). When the Lead wakes: the
  feature, section "The Lead wakes only when needed".
- `watch` is the older background watcher, kept for leads on dev-kit before 0.1.78: silent while its sessions
  live, it exits when one ends, writes the line "Роботу завершено", stops on the usage limit, or has waited
  `--stale-minutes` (20) since its last reply.
- `fill --self` prints the caller's own fill (the lead's move to a fresh context); `handoff save|go|request|status|clear`
  keeps the lead's handoff marker that the Pult watcher acts on (`request` is the watcher's ask that reaches the lead
  as `handoff requested: <file>`).
- `fill --over-only` prints only the sessions past the fill limit; `size --id ...` prints a session's
  conversation size and window (the Pult watcher's 0.7 push and its size log).
- `state` prints each registered session as working, waiting, limited, finished, closed (no process yet, the Pult watcher may respawn it) or gone with the gist of its last reply.
- `answers` prints what the owner wrote in a session after its last SendMessage (its last report or
  question), so the lead never asks him what he already answered there.
- `add --owner` registers a session the owner started.

Why: the host kills a background watcher after a cap ([Claude facts](../../plugins/dev-kit/claude-facts.md), "The host kills a background Bash run after 2 hours"), and the leads and Pult were woken only to re-arm
theirs ([measured](../findings/idle-wake-cost.md)); the owner approved on 2026-11-20 that no Claude session keeps a watcher. The
Pult watcher, which runs outside Claude Code, also brings back task sessions that Claude Code closed
([Start leads at logon and heal them](../features/start-leads-at-logon-and-heal-them.md)).

## Migrations: `dev-kit-migrations`

After a dev-kit update, Pult restarts the leads so they load the new skill (a routine update on a later day). On start and after that restart
the Lead runs `dev-kit-migrations pending` and hands the changes every project must make in its own files (the
entries of `plugins/dev-kit/migrations.md`) to one task session.

## Retro: `rules-kit`

Each project with a lead has its own retro. rules-kit hooks scan, with no model, each ending session's
transcript (and once a day all of them) for repeated, failed, slow and very many calls, for commands worth a
script and for token spend (too-long sessions, Opus coder subagents), and sort the findings into the project's
local item folder. When new findings wait, a session start in that project launches a background «Retro:
<project>» session (`rules-kit:retro`): it reviews them with the project's rules in view, fixes recurring gaps
through an approver agent and a replay on past sessions, reverts fixes that did not work, asks the owner nothing and
lists what it did for Pult's «статус» (`rules-kit list`). Once a
week, after the retro's branch is merged (or on its own in a week with no retro), a dev-kit hook (`dev-kit-docs`,
`docs_weekly.py`) launches a background
«Docs: <project>» session (`dev-kit:maintain-project-docs`, "Weekly background run"): it fixes trivial docs
problems, writes the rest as local docs items and ends; the Lead asks the owner its important items after it reports. The
critical token problems (`spend-kit critical`) also show in Pult's «статус». `spend-kit session` gives one session's
units as a share of the weekly limit; the limit is refitted by `spend-kit scan` and `calibrate` from the log that the status
line script `spend-kit-statusline` keeps (`usage-log.jsonl` in the spend-kit folder of the user's .claude folder); the retro takes the token findings by running `spend-kit findings`.
