# Project lead: a session that waits on something shows as «чекає» with the reason

Status: done (C: Стан «чекає» у статусах керівника).

Source: BACKLOG.md entry of the same name (owner yes, 2026-11-23, Zhratva); its What, Why and Cheapest test are the scope. Remove the entry in the same branch.

Success criterion: the entry's cheapest test holds: a C that hits a 30-min retry wait sends P a report; P's next message has `чекає - «C: ...» (<reason>, повтор о HH:MM)`, not `працює`.

## What was built

- `plugins/dev-kit/messages.md`: two new kinds, `ЧЕКАЮ` (a C will wait over 1 minute on something other than P or the owner; reason and resume time) and `ПРОДОВЖУЮ` (it goes on). ЗАСТРЯГ was not reused: the owner said such a session is not stuck.
- `dev-kit:manager`, "A task from the project lead": the C sends `ЧЕКАЮ` before such a wait and `ПРОДОВЖУЮ` after; a wait for P's answer is not one.
- `dev-kit:project-lead`: new state `чекає` in «Статуси сесій» (sent at once, never folded into `працює` or «ще працюють»); the first-prompt report rule lists the wait and the new kinds; "Shared app": the app-queue wait reaches P as `ЧЕКАЮ`.
- `docs/features/hand-work-to-the-project-lead.md`: the owner-facing state list.
- dev-kit 0.1.109, routine.

## Checks

- Lint: 0 errors. Independent review (reviewer, sonnet): three gaps fixed - a `чекає` line stays until `ПРОДОВЖУЮ`, a `чекає` session counts as working for «Стан проєкту», and the C's own build, test or subagent is not a wait; the epic summary updated.
- Untested live: the cheapest test needs a real C hitting a wait; it is a rule change, so it shows on the next such wait.

Spend: <0.1% of the weekly limit, estimate; API: 0 USD
