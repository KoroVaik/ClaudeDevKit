# Cost stated as a share of the subscription limit

Source: BACKLOG.md, «Rule: how agents state cost on a subscription» (with its Verdict line).

## Owner's words
- 2026-11-21, on the backlog idea: «всеодно неясно що це».
- 2026-11-21: «але ж зараз іде доволі точний підразунок витрат токен, а отже можна писати у відсотках підписки».
- 2026-11-21: «запусти обговорення.»

## Facts checked by P
- `plugins/dev-kit/scripts/retro.py` already turns tokens into units and a share of the weekly limit (`WEEKLY_LIMIT_UNITS`, fit from two `/usage` readings on 2026-11-19/20, about 30% uncertain; `plans/retro-tokens.md`).
- Claude Code's own cost figure (`/cost`, session records) prices tokens at API rates; on a subscription it is not billed. Not checked in Claude Code docs.
- Calibration (checked 2026-11-21 in the Claude Code 2.1.330 bundle, `claude.exe`): the status line script gets JSON with `rate_limits.seven_day.used_percentage` (and the 5-hour one) for subscribers, so a script can log the weekly % on every turn with no `/usage` typing. `claude -p "/usage"` gave no output in 90 s. The % is account-wide (all parallel sessions), so it calibrates the units fit, not one session's share. No status line is set in the owner's user settings today.
- Real money: only calls through `dev-kit-api` (manager skill, «Claude API calls»).

## Success criterion
The owner approves, in an «Owner's approval» section of this file, how agents state the cost of work (unit, label, where it applies, how an agent gets the number for its own session), and the short plan.

## Owner's approval
Owner's «так» on 2026-11-21 to points 1-6; the short plan approved by the owner's «+» the same day.

1. Unit and label. Agents state the cost of their own work (sessions, subagents, `claude -p` runs on
   the subscription login) as a share of the owner's weekly subscription limit, marked as an estimate,
   never in USD. Form: «~2% тижневого ліміту, оцінка» (English deliverables: «~2% of the weekly limit,
   estimate»). The figure comes from the retro's units over `WEEKLY_LIMIT_UNITS`; the uncertainty (about
   a third) is carried by the word «оцінка», not repeated as a number. Claude Code's own USD figure
   (`/cost`, `costUSD` in session records) is never quoted, labelled or not.
2. Real money stays in USD. Calls through `dev-kit-api` (API keys, billed from the monthly Max API
   credit) keep their dollar figures: the spend log, `dev-kit-api report` / `reconcile`, P's weekly
   «API credit check». A report that has both writes them apart, e.g. «~1% тижневого ліміту, оцінка;
   API: 0.40 USD».
3. Own-session figure. A new `dev-kit-retro` command gives the share of the weekly limit for one
   session (default: the session that runs it; a session id or transcript path as an option), and,
   for a task, the sum over that session's subagents. Same unit weights and limit as the retro scan;
   one place for the limit (`WEEKLY_LIMIT_UNITS`). Agents call it when a report or plan states cost.

4. Calibration by the status line (owner, 2026-11-21: «треба подумать як краще відкалібрувать витрати.
   Чи можна запускати команду юзедж якось іше»). A dev-kit status line script reads
   `rate_limits.seven_day.used_percentage` (and its reset time) from the JSON Claude Code passes it and
   appends a line to a local log (outside any repo, under the owner's `.claude/dev-kit/`) only when the
   value changes; it prints a short line such as «тиждень: 23%». The retro refits `WEEKLY_LIMIT_UNITS`
   from pairs of log readings within one weekly window against the units of all transcripts between
   them (all sessions, since the % is account-wide), replacing the hand fit from two `/usage` readings;
   with too few readings it keeps the last value. Setting the status line is a change to the owner's
   local user settings: the builder names it in the report. Manual `/usage` is no longer needed.
5. Plans' spend lines. The «Paid spend: N USD» lines in `plans/` for subscription runs (`claude -p`,
   sessions, subagents) become «Spend: ~N% of the weekly limit, estimate»; API-key spend stays in USD on
   the same line, apart. Existing finished plans are not rewritten.
6. P's threshold. «Paid spend over $1 in total per task» in
   `docs/features/hand-work-to-the-project-lead.md` (and its rule in `dev-kit:project-lead`) covers only
   real API money through `dev-kit-api`; subscription use does not trigger a question to the owner.

## Build (2026-11-21, session «cost-share-build»)
- Spend: ~0.3% of the weekly limit, estimate (`dev-kit-retro session`); API: 0 USD.
- Rule text: `dev-kit:manager` gets «Stating the cost of work» (points 1, 2, 3 use, 5); the C's spend line, P's threshold
  and ask-P item in `dev-kit:project-lead` and `docs/features/hand-work-to-the-project-lead.md` now count only API money (point 6).
- Code (dev-kit:coder, sonnet): `dev-kit-retro session`, `dev-kit-statusline` with the usage log, refit of the weekly limit.
- Code details: the refit uses windows of the last 28 days (`FIT_DAYS`), needs 10+ points (`FIT_MIN_POINTS`), caches closed
  windows in `state.json` and rereads only the current one; the status line logs only a higher % in a window or a new window.
- Owner's local settings: `statusLine` added to the user settings (`~/.claude/settings.json`), after P's yes; it points to
  `plugins/dev-kit/scripts/statusline.py` in the main checkout, so it shows nothing until this branch is merged.
- Review (sonnet reviewer): fixed - old windows and deleted transcripts no longer drag the limit, reset jitter and stale
  readings from idle sessions, the calibrate/scan race, tests for the fitted limit. Left for P on merge: the BACKLOG entry's
  Verdict names «Claude API calls» (the rule now lives in «Stating the cost of work»); `PROGRESS.md` line on the short plan.
- Checks: full tests and lint pass.
