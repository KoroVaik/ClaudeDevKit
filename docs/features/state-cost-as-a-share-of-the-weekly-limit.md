# State cost as a share of the weekly limit

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
You work on a subscription, so agents state what their work cost as a share of your weekly limit, not in dollars
that are not billed. Real API money stays in dollars.

## Rules
### Subscription work is a share of the weekly limit, marked as an estimate
An agent states the cost of its own work (sessions, subagents, `claude -p` on the subscription login) as «~2%
тижневого ліміту, оцінка» (in English «~2% of the weekly limit, estimate»), never in USD. The uncertainty (about a
third) is carried by the word «оцінка», not by a number. Claude Code's own dollar figure (`/cost`, `costUSD`) is never quoted, labelled or not
([Claude facts](../../plugins/dev-kit/claude-facts.md), "Claude Code's own USD figure prices tokens at API rates"). A task file's spend line has the same form.
Why: owner, 2026-11-21: the retro counts tokens closely enough to state cost in per cent of the subscription.

### Real money stays in dollars, apart
Calls through `spend-kit-api` keep their dollar figures ([Log and reconcile API spend](log-and-reconcile-api-spend.md)).
A report with both writes them apart: «~1% тижневого ліміту, оцінка; API: 0.40 USD». The Lead's question about spend over
$1 per task counts only the API money; subscription use never asks you.

### The figure comes from a command
`spend-kit session` gives the share for the session that runs it and its subagents (`--id` or `--path` for
another), with the same unit weights and limit as the retro scan.

### The limit is refitted from the status line
The status line script `spend-kit-statusline` shows «тиждень: N%» and logs the weekly per cent (account-wide, all
parallel sessions) when it rises. `spend-kit` refits the weekly limit in units from windows of the last 28 days with
at least 10 points; with fewer it keeps the last value. Manual `/usage` readings are no longer needed.
Why: owner, 2026-11-21: «треба подумать як краще відкалібрувать витрати»; the status line JSON carries the weekly
per cent ([Claude facts](../../plugins/dev-kit/claude-facts.md), "The status line JSON holds the subscription limits"), so no typing of `/usage`.

## Acceptance criteria
- An agent reports its task: the report says «~N% тижневого ліміту, оцінка», no dollar figure of `/cost`.
- A task also made `spend-kit-api` calls: the report shows the share and the API dollars apart.
- `spend-kit session` prints the share of the session that runs it.
- The status line is set: after a turn, `usage-log.jsonl` has the weekly per cent.

## Built in
- `plugins/spend-kit/scripts/spend.py`
- `plugins/spend-kit/scripts/statusline.py`
- `plugins/spend-kit/bin/spend-kit`
- `plugins/spend-kit/bin/spend-kit-statusline`
- `plugins/dev-kit/skills/manager/SKILL.md`
- `tools/tests/test_spend.py`
