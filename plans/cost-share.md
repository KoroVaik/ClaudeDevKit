# Cost stated as a share of the subscription limit

Source: BACKLOG.md, «Rule: how agents state cost on a subscription» (with its Verdict line).

## Owner's words
- 2026-11-21, on the backlog idea: «всеодно неясно що це».
- 2026-11-21: «але ж зараз іде доволі точний підразунок витрат токен, а отже можна писати у відсотках підписки».
- 2026-11-21: «запусти обговорення.»

## Facts checked by P
- `plugins/dev-kit/scripts/retro.py` already turns tokens into units and a share of the weekly limit (`WEEKLY_LIMIT_UNITS`, fit from two `/usage` readings on 2026-11-19/20, about 30% uncertain; `plans/retro-tokens.md`).
- Claude Code's own cost figure (`/cost`, session records) prices tokens at API rates; on a subscription it is not billed. Not checked in Claude Code docs.
- Real money: only calls through `dev-kit-api` (manager skill, «Claude API calls»).

## Success criterion
The owner approves, in an «Owner's approval» section of this file, how agents state the cost of work (unit, label, where it applies, how an agent gets the number for its own session), and the short plan.

## Owner's approval
(not yet)
