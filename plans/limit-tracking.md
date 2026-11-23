# Tracking the usage limits

Status: approved by the owner 2026-11-23; ready to build after limit-resume merges.

Owner's words (2026-11-23, P: ClaudeDevKit chat): «Також потрібно поговорить про відслідковування лімітів».

Known context (to check): sessions stop on the usage limit; the Pult watcher logs `LIMIT ... (resets <time>)` and P shows `стоїть, скінчився ліміт (до <time>)`; the subscription spend line per task is an estimate (dev-kit:manager, «Stating the cost of work»); API spend has its own log and weekly Console check (`docs/features/log-and-reconcile-api-spend.md`). A separate build «C: Сесії самі продовжують після ліміту» (plans/limit-resume.md) makes sessions resume after the reset; this discussion is about tracking, not resuming.

## Talk notes (not yet approved)

- Owner sees the limits in the Claude apps himself; no display of the % is wanted.
- Owner, 2026-11-23: warn about the weekly limit only when the lead is sure the work will not finish and the wait for the reset is over 6 hours; no spam. So no 5-hour warnings (its wait is at most 5 hours, and the resume build wakes the work).
- Weak spot told to the owner: the lead cannot know how much a task still needs; "sure" has to mean a pace forecast plus open tasks.
- Owner «ок» (2026-11-23) to: "sure" = at the pace of the last hours the weekly limit runs out more than 6 hours before its reset, and open tasks exist; one warning per weekly window, no repeats; after it the lead stops nothing by itself. The warning is a phone push; that is enough (no chat display wanted).

## Owner's approval

Owner «+» to the short plan, 2026-11-23 («Обговорення: Відстеження лімітів»). Approved plan as shown:
1. Pult по ходу роботи всіх сесій стежить за тижневим лімітом.
2. Якщо за темпом останніх годин тиждень скінчиться більш ніж за 6 годин до скидання, а задачі ще не закриті, керівник шле тобі пуш на телефон.
3. Пуш приходить раз на тиждень, у ньому час, коли скінчиться ліміт, і час скидання.
4. Про 5-годинний ліміт попереджень немає, а після пушу керівник сам нічого не зупиняє.

Details for the builders:

- Goal: a runtime forecast of the account's weekly subscription limit, and one early phone push when the work will stand for long. Not a display: the owner sees the % in the Claude apps himself.
- Data source (exists): `~/.claude/dev-kit/usage-log.jsonl`, lines `{ts, week_pct, week_resets, five_hour_pct}` written by `plugins/dev-kit/scripts/statusline.py` (`worth_logging`) from the status line JSON `rate_limits.seven_day` on each turn of any session, only when the weekly % rose or a new window began. Real account %, not the retro estimate; do not use `dev-kit-retro` units for this.
- Who checks: the Pult watcher (`plugins/pult/scripts/watch-servers.ps1`), on its normal loop, when the log got new lines. No new wakes of leads just to check.
- Forecast: readings of the current weekly window (same `week_resets`) from the last 6 hours; at least 2 readings at least 1 hour apart, else no forecast. Pace = % rise / hours between first and last reading of that span. Run-out time = now + (100 - last %) / pace. Warn only when `week_resets - run-out time` > 6 hours. (A 5-hour window wait is at most 5 hours, so it never qualifies; no 5-hour logic at all.)
- "Open tasks": at least one live session that a lead manages besides the leads themselves (a C or an «Обговорення:»), not finished. No open work, no push.
- Once per weekly window across all leads and projects (the limit is per account): keep a mark keyed by `week_resets` in Pult's state; never repeat in that window, even if the forecast worsens.
- Delivery: the watcher sends one lead (P: ClaudeDevKit if alive, else any alive lead) an event using the existing push-request form (`dev-kit:project-lead`, "Wake-up", "Push request"); that P sends the PushNotification. Push text in Ukrainian, e.g. «Тижневий ліміт за темпом скінчиться пт 20:00, скидання пн 10:00.» Local time. A push skipped because the owner is at the screen is fine (`claude-facts.md`, "The push tool skips a push while the owner is at the screen"); also log a `LIMIT-FORECAST` line in the watcher log.
- After the push the lead changes nothing: no pausing, no queue item, no question.
- Order: build after «C: Сесії самі продовжують після ліміту» is merged; both edit `watch-servers.ps1` and its tests.
- Tests: unit tests of the forecast on sample logs (too few readings, slow pace, fast pace, new window, mark already set, no open tasks), next to `tools/tests/test_watch_servers_limit.py`; docs: the Pult feature file and the project-lead "Wake-up" line on this push.
