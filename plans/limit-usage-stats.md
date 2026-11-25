# Statistics: where the weekly limit goes

Status: built (C: Статистика витрат ліміту), 2026-11-25.

Spend: ~0.3% of the weekly limit, estimate; API: 0 USD.

Owner's words, 2026-11-25, P: ClaudeDevKit chat: «У нас десь ведеться облік того на які задачі, агенти, скіли і тд. було потрачено відсотків ліміту? Цікаво бачити жесь подібну статистику. Давай обговорення».

What exists (P checked): spend-kit (`plugins/spend-kit/scripts/spend.py`) counts a session's token units as a share of the weekly limit and flags session days that spent or wasted too much; a C quotes its task's share in the task file's spend line (`dev-kit:manager`, «Stating the cost of work»). No view groups the share by task, agent, skill or project over time.

The weekly limit is at 95% now: keep the talk lean.

Success criterion: the owner's «так» to the short plan, with the agreed points written in «Owner's approval» below.

## Agreed so far (2026-11-25)

- The owner asks P «покажи статистику витрат»; P replies with a text table in chat. No new screen.
- Grouping: by project, by task (session title), by subagent type and model.
- Period: the current weekly limit window, shares as % of the weekly limit.
- Owner: «логувати треба все що тіки можна»: weekly totals kept forever; skills counted roughly. Design approved: see the feature file.
- Detailed report on request (full lists, e.g. every agent type); the retro week-over-week jump finding dropped. All points: docs/features/limit-usage-stats.md.

## Build (2026-11-25)

- `spend-kit stats` (`--detail projects|tasks|agents|skills`, `--week -1`): the chat table; each group top 5 except projects, `--detail` shows one group in full.
- Shares are scaled to the status line's weekly per cent, so groups add up to the header.
- `weekly.jsonl` in the spend-kit data folder: the last closed window's totals, appended once by `stats` or the SessionEnd detached run, never cut.
- Project rows merge worktrees into their repo; skills end at the next real owner message.
- P: section «Spend statistics» of the project-lead skill.
- Known: the week 18.11-25.11 in the archive has a per cent from a log that began 21.11, so its units-to-per-cent ratio is not comparable.
