# Keep a reserve at 98% of the weekly limit

Status: built 2026-11-25 (C: Запас ліміту на 98%); plugin version bump left for the merge.

Owner's words, 2026-11-25, P: ClaudeDevKit chat: «Давай всетаки на 98% старатись зупиняти всі сесії, якщо до ресета ще більше ніж 6годин, щоб мати ліміти на рандомні термінові запити». Owner «Так» to P's version: at 98% of the weekly limit, when the reset is more than 6 hours away, every lead stops all its C sessions at a safe point (the stop of plans/limit-wind-down.md), and the leads themselves stay up for the owner's urgent requests; after the reset the sessions wake as now.

This amends the wind-down rule of plans/limit-wind-down.md (default: keep working until the limit runs out); below 98%, or with 6 hours or less to the reset, that default stays.

Build: a 98% weekly notice from the Pult watcher (once per window, with the reset time, so the lead can tell the 6-hour condition), the lead rule in dev-kit:project-lead (the ЛІМІТ: notice lines), the feature doc docs/features/wind-down-at-weekly-limit.md, tests.

Not checked: whether 2% of the weekly limit is enough for an urgent request; record a measured share if one turns up.

Success criterion: a test shows the 98% notice sent once with the reset time; the lead rule says stop all C sessions at 98% when the reset is over 6 hours away; lint and tests green.


Built: WEEK_AT gets 98 (`usage_forecast.py`), tests for the 98% notice and a jump past it; the reserve exception in `dev-kit:project-lead` (ЛІМІТ: lines, P compares the reset with `date`); Pult README; the feature doc. Rule review: two doc criteria fixed, the `date` hint added.

Spend: ~0.1% of the weekly limit, estimate; API: 0 USD
