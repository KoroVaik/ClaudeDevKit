# Wind down work when the weekly limit runs out

Status: built 2026-11-25 (owner «так» to the short plan, 2026-11-25, «Обговорення: Плавна зупинка при вичерпанні ліміту»).

Owner's words, 2026-11-24, P: ClaudeDevKit chat: «потрібно подумать над тим як плавно зупинять роботу менеджерів у яких ще доволі великий скоуп робіт, а тижневий ліміт уже перескочив 95% і навіть за кращого прогнозу не встигне до ресета. Обговорення. Приклад сесія менеджера ядра в жратві».

Example session: «C: Переробка ядра аналізу» in Zhratva (worktree C:/Users/korov/MyRepositories/Zhratva/.claude/worktrees/analysis-core), transcript C:/Users/korov/.claude/projects/C--Users-korov-MyRepositories-Zhratva--claude-worktrees-analysis-core/d0846956-2bb7-4945-87c6-74f448dbe3d1.jsonl. Read only; never message it or its lead.

Related: plans/limit-tracking.md (the weekly limit forecast push), the Pult watcher's LIMIT-RESUME (plugins/pult/README.md).

Success criterion: the owner's «так» to the short plan, with the agreed points written in «Owner's approval» below.

## Owner's approval

Owner «так» to the short plan, 2026-11-25. Points agreed one by one in the discussion (2026-11-24/25); product rules in
[docs/features/wind-down-at-weekly-limit.md](../docs/features/wind-down-at-weekly-limit.md).

How it works now (checked 2026-11-24): the usage % comes from the status line (`rate_limits.seven_day`,
`five_hour`) appended by `plugins/spend-kit/scripts/statusline.py:69-96` to
`~/.claude/spend-kit/usage-log.jsonl` (fields `week_pct`, `week_resets`, `five_hour_pct`, written only when a %
rises). The weekly forecast push (`plugins/spend-kit/scripts/usage_forecast.py`, watcher
`Invoke-LimitForecast`, `plugins/pult/scripts/watch-servers.ps1:1294-1315`) goes to the owner's phone only;
no rule tells a lead or a C what to do near a limit; `messages.md` has no kind for it. LIMIT-RESUME
(`watch-servers.ps1:575-677`) wakes only sessions that stopped on the limit, not ones paused on purpose.

1. Notices to leads (the decision is each lead's, nothing stops sessions centrally).
   - Weekly limit: a notice to every live lead at 90% and again at 95% of `week_pct`, each threshold once per
     weekly window (mark per `week_resets`, like the forecast's mark file).
   - 5-hour limit: one notice at 90% of `five_hour_pct`, once per 5-hour window.
   - Sent by Pult's watcher through the existing one-shot sender; a new message kind in
     `plugins/dev-kit/messages.md` (name it in the build, e.g. `ЛІМІТ`) carrying which limit, the % and the reset
     time.
2. What a lead does on a notice: base stop rules in `plugins/dev-kit/skills/project-lead/SKILL.md`.
   - Default: a session keeps working until the limit runs out; the importance of its task is not a reason to
     stop it (owner: the last share of the limit must not be left unused out of caution).
   - Stop at a safe point only on a sign from the list: helpers (subagents) are running; a large change is half
     done. A paid API run is not a sign by itself (a background script keeps running at the limit; a run driven
     by a helper falls under the helpers sign).
   - A stop is a `ВКАЗІВКА` to the C: no new step, bring the current one to a safe point, stop helpers, write
     where it stopped and the resume steps in its plan, save the work (WIP commit), send `ЧЕКАЮ`. This is what the
     Zhratva core C did on P's ad hoc order on 2026-11-24 in about one minute.
   - The lead keeps the list of sessions it paused, for step 3.
   - A project adds its own signs or rules in its `.claude/dev-kit.md` (a `## project-lead` section); the base
     list may grow over time.
3. After the reset: the watcher tells every lead that got a notice in that window that the limit is back (once
   per window); the lead wakes the sessions it paused (a `ВКАЗІВКА` to resume from the written steps).
   LIMIT-RESUME for sessions cut by the limit stays as is.
4. Fix: the watcher missed the Zhratva core C's 5-hour stop on 2026-11-24 (no LIMIT line in `servers.log`; it
   slept about 18 h). Likely cause: `plugins/dev-kit/scripts/sessions.py:753-771` (`usage_limit`, lines 761-764)
   counts any later non-meta user entry as "it went on", and the reports of the cut helpers
   (`task-notification` entries) came after the limit notice. Confirm on a copy of that transcript cut at line
   1979 (`d0846956-...jsonl`, path in the task line above), then fix so such entries with no assistant reply
   after them do not end the stop.
5. Unchanged: the weekly forecast push to the owner's phone.

Docs to bring up to date in the build: `plans/limit-tracking.md:27` still says the scripts are in dev-kit (they
moved to spend-kit); `plugins/pult/README.md`; the feature file above.

## Build steps

Status: built 2026-11-25, all steps done. Spend: ~0.6% of the weekly limit, estimate; API: 0 USD.

Known gap (reviewer doubt, not fixed): a notice that finds no live lead (all restarting) is used up; the next
threshold or window still notifies, but no lead gets the `back` line for it.

How the parts fit (fixed before the parallel work):
- Data: the status line logs a line also when `five_hour_pct` rises in the same 5-hour window or a new 5-hour window
  starts, and writes `five_hour_resets` (epoch). The weekly forecast reads only lines whose weekly % rose, so its
  pace is unchanged.
- `usage_forecast.py notices --mark <StateDir>\limit-notices.json [--log F] [--now E]` (spend-kit) owns the
  thresholds and the once-per-window marks. It prints zero or more lines:
  `notice | week|five | <threshold> | <pct> | <reset epoch> | <text>` and, once the reset time of a window it gave a
  notice for has passed, `back | week|five | <reset epoch> | <text>`. Exit 0; 2 on bad arguments.
- The watcher (`Invoke-LimitNotices`, pult) calls it when the usage log changed or every 5 minutes, sends each
  `notice` text as a wake line to every live lead (same version gate as lead events), remembers per window which
  leads got one (wake-state.json `LimitNotified`), and sends each `back` text only to those leads. Logged:
  LIMIT-NOTICE <limit> <threshold> <pct> leads=<names>, LIMIT-BACK <limit> leads=<names>.
- Line text the lead gets (kind word `ЛІМІТ`, `plugins/dev-kit/messages.md`):
  `ЛІМІТ: тижневий 95%, оновиться пн 10:00` / `ЛІМІТ: 5-годинний 90%, оновиться 14:00` /
  `ЛІМІТ: тижневий ліміт оновився, можна будити призупинені сесії`.

Steps:
1. Status line logs the 5-hour window; forecast reads only weekly rises; `notices` subcommand with tests
   (manager). 
2. Watcher `Invoke-LimitNotices` with tests and header doc (dev-kit:coder, sonnet).
3. `usage_limit` fix: confirm the cause on the cut transcript copy, fix, test (dev-kit:coder, sonnet).
4. Rules: `ЛІМІТ` kind in `messages.md`; lead's base stop rules in `project-lead/SKILL.md` (manager,
   rules-kit:edit-rules).
5. Docs and versions: feature acceptance criteria and status, `plans/limit-tracking.md:27`, `plugins/pult/README.md`,
   version bumps with release marks (manager).
6. Independent review of the whole diff (dev-kit:reviewer, sonnet); fix confident problems; full tests and lint.
