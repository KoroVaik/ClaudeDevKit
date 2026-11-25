# Remove the weekly limit forecast push

Status: in progress (C: Прибрати пуш-прогноз ліміту).

Owner, 2026-11-25, P: ClaudeDevKit chat, after a forecast push «Тижневий ліміт: витрачено 6%, за темпом скінчиться чт 23:43, оновиться ср 16:00»: «Який сенс? Я маю ліміт і витрачаю його на задачі, яка різниця чи будуть задачі в паралелі йти чи по одній?», then «Прибирай» to «Прибираємо пуш-прогноз тижневого ліміту?». Reason: the same work costs the same limit in parallel or in series; the reserve for urgent requests is kept by the 98% stop (plans/limit-reserve-98.md).

Scope: stop the Pult watcher from sending the weekly forecast push; remove or retire the forecast code that only feeds it (spend-kit `usage_forecast.py`, its tests, its calls in the watcher), unless another feature uses it (check: the ЛІМІТ: 90/95/98% notices and their reset message must keep working). Update the rules that mention the forecast push (dev-kit:project-lead «Push request» line, pult README/hub rules, features: plans/limit-tracking.md is history, docs/features/* current), PROGRESS.md (the forecast push line: removed by the owner), claude-facts only through dev-kit:facts-keeper if needed. Bump versions with routine marks.

Success criterion: no code path sends the forecast push; the ЛІМІТ: notices still pass their tests; lint and tests green.
