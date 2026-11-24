# Wind down work near a usage limit

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

Status: approved, not built. Plan: [plans/limit-wind-down.md](../../plans/limit-wind-down.md).

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
again at 95%; for the 5-hour limit, one notice at 90%.

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
- To be set once the thresholds and the base stop rules are agreed.
