# Statistics: where the weekly limit goes

Status: discussion (Обговорення: Статистика витрат ліміту).

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
