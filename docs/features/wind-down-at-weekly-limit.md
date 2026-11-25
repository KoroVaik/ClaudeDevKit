# Wind down work near a usage limit

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

Status: built 2026-11-25. Plans: [plans/limit-wind-down.md](../../plans/limit-wind-down.md),
[plans/limit-reserve-98.md](../../plans/limit-reserve-98.md) (the 98% reserve).

## Purpose
When the weekly or the 5-hour usage limit is close, work stops at safe points chosen by each project lead,
instead of sessions being cut mid-step or stopped by hand.

## Rules
### Each lead is told and decides itself
Accepted product rule (owner, 2026-11-24, «Обговорення: Плавна зупинка при вичерпанні ліміту»): every
project lead gets a notice when the weekly or the 5-hour limit is getting close. The lead itself decides
which of its sessions to stop and how best to stop each one. Nothing stops sessions centrally.

### Thresholds
Accepted product rule (owner «так», 2026-11-24): for the weekly limit a lead gets a notice at 90% and
again at 95%; for the 5-hour limit, one notice at 90%. Amended (owner «Так», 2026-11-25): a third weekly
notice at 98%.

### Base stop rules and project additions
Accepted product rule (owner «так», 2026-11-24): the base stop rules live in the project lead's rules;
a project adds its own in its dev-kit settings file.

### Which sessions stop
Accepted product rule (owner «ок», 2026-11-24): by default a session keeps working until the limit runs
out, so the last share of the limit is used, not left idle out of caution. A lead stops a session at a
safe point only on a concrete sign from a list: helpers (subagents) are running, or a large change is
half done. The importance of the task alone is not a sign. A paid run is not a sign by itself: a
background script keeps running at the limit; a run driven by a helper is covered by the helpers sign.
More signs may be added over time, to the base list or by a project.

### A reserve at 98% of the weekly limit
Accepted product rule (owner «Так», 2026-11-25, «Давай всетаки на 98% старатись зупиняти всі сесії, якщо до
ресета ще більше ніж 6годин, щоб мати ліміти на рандомні термінові запити»): at 98% of the weekly limit, when
the reset is more than 6 hours away, every lead stops all its sessions at a safe point, signs or not, and the
leads themselves stay up for the owner's urgent requests. Below 98%, or with 6 hours or less to the reset,
the default above holds. Not checked: whether 2% of the weekly limit is enough for an urgent request.

### After the reset
Accepted product rule (owner «так», 2026-11-24): after the limit resets, Pult tells each lead the limit is
back, and the lead itself wakes the sessions it paused. (Today Pult's watcher wakes only sessions cut by
the limit itself; a session paused on purpose stays asleep.)

### Pult does not miss a limit stop
Accepted product rule (owner «так», 2026-11-25): Pult's watcher must see a session cut by the limit even
when reports of its cut helpers arrive after the limit notice. (On 2026-11-24 the Zhratva core session
slept about a day after a 5-hour stop the watcher did not see.)

### The owner's weekly forecast push stays
Accepted product rule (owner «так», 2026-11-24): the weekly limit forecast push to the owner's phone stays
as it is.

## Acceptance criteria
- When the weekly limit reaches 90%, every live project lead gets one notice with the per cent and the reset
  time; at 95% one more; at 98% one more (next item); never again in that week. A jump straight past a threshold gives one notice, for the highest.
- At 98% of the weekly limit every live lead gets one more notice with the reset time; when the reset is more
  than 6 hours away, the lead stops all its sessions at safe points and stays up itself.
- When the 5-hour limit reaches 90%, every live lead gets one notice, once per 5-hour window.
- After a limit resets, the leads that got a notice for it are told once that it is back; a lead that got no
  notice is told nothing.
- Below 98%, or with 6 hours or less to the reset, a lead lets its sessions run to the limit unless it sees helpers running or a large change half done; then
  it stops that session at a safe point with its resume steps written and its work saved, and wakes it after
  the reset.
- A session cut by the limit whose helpers report after the limit notice is still seen as stopped by Pult and
  woken after the reset.
- The weekly forecast push to the owner's phone comes as before.

## Built in
- Thresholds and once-per-window marks: `plugins/spend-kit/scripts/usage_forecast.py` (`notices`); the 5-hour
  readings it needs: `plugins/spend-kit/scripts/statusline.py`.
- Sending to the leads: `plugins/pult/scripts/watch-servers.ps1` (`Invoke-LimitNotices`).
- What a lead does: `plugins/dev-kit/skills/project-lead/SKILL.md`, "Wake-up", the `ЛІМІТ:` lines.
- The missed stop: `plugins/dev-kit/scripts/sessions.py` (`usage_limit`).
