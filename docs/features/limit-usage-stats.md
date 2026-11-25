# Show where the weekly limit went

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

Status: built (`spend-kit stats`). Plan: [plans/limit-usage-stats.md](../../plans/limit-usage-stats.md).

## Purpose
The owner asks the project lead «покажи статистику витрат» and gets, in chat, how the current weekly limit
split across projects, tasks, agents and skills, with past weeks kept for comparison.

## Rules
### Shown on request, as a chat table
- The owner asks P (any project lead) in his own words; P replies with a text table in chat. No new screen,
  page or push.
- Period: the current weekly limit window (its start and end dates in the header), shares as % of the weekly
  limit, the same base the Claude app shows.

### Groups
- Projects: every project with a share, largest first.
- Tasks: the top 5 sessions by share, as «project · session title».
- Agents: subagent type and model, share and number of runs.
- Skills: marked «приблизно»; a skill's share is the units of the session turns from its launch to the
  turn's end. A skill works inside a session, so an exact split is not possible.

### Detailed report on request
When the owner asks for more («детальніше», «по всіх агентах», «скільки пішло на помічників»), P shows the
asked group in full instead of the top 5: e.g. every subagent type with its model, share, number of runs and
usual units per run. Same data, no new tracking. The retro does not need it: it already gets spend-kit's
`table` (sessions, subagent types and models) with its findings.

### Not done: week-over-week jumps in the retro
A retro finding «a task's or agent's share jumped versus last week» was dropped (owner «Ок», 2026-11-25): a
weekly share grows with the amount of work too, so the retro would chase noise; spend-kit already flags
long sessions, coder runs on Opus and token waste.

### Log everything, keep weekly totals forever
Owner: «логувати треба все що тіки можна, щоб потім бачити повну картину витрат». Claude deletes session
transcripts after 30 days and spend-kit keeps its own per-session totals for 14 days, so at each weekly limit
reset spend-kit stores that week's totals (projects, tasks, agents, skills) in a file that is never cut. The
table can then compare with past weeks («минулого тижня Zhratva 40%, цього 31%»).

## Acceptance criteria
- The owner writes «покажи статистику витрат» to P and gets the table below for the current limit week.
- Shares are % of the weekly limit and add up to the header's total, give or take rounding.
- After a weekly reset, the past week's totals stay readable after its transcripts are deleted.
- Skills are labelled «приблизно».
- Asked «покажи детальніше по агентах», P lists every subagent type and model with share, runs and usual units per run.

## Approved design
Mockup (the chat reply; numbers are made up):

```
Тиждень ліміту: 18.11 - 25.11, витрачено 95%

Проєкти
  ClaudeDevKit   52%
  Zhratva        31%
  Pult           12%

Задачі (топ-5)
  ClaudeDevKit · Плавна зупинка при ліміті   14%
  Zhratva · Схвалення страви                  11%
  ClaudeDevKit · P (керівник)                  9%
  Pult · Перезапуск сесій                      7%
  Zhratva · Фото страв                         6%

Агенти
  coder · Sonnet          18%  (23 запуски)
  investigator · Sonnet    7%  (11)
  reviewer · Sonnet        4%  (9)
  core-engineer · Fable    6%  (1)

Скіли (приблизно)
  new-feature      22%
  discovery-round   8%
  fix-bug           6%
```

Acceptance criteria: the section above, written there at the approval.
User situation: the owner sees the limit run low and wants to know which work ate it, to decide what to cut
or run on a cheaper model.
State: built
