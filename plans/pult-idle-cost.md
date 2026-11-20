# Pult idle token cost

Owner's words (to Pult): «Пропналізуй доцільність пульта... Чи не спалює це постійно токени», «Напиши керівнику плагіна». To P, on the stopgap «start the Pult conversation fresh once a day»: «Це вирішення симптому. Обговорення давай» (2026-11-20).

## Pult's finding (not measured in tokens)
- An idle Pult session costs nothing; the cost is the phone-push design. `plugins/pult/scripts/watch-log.py` exits with «time limit» about every 2 h, and each exit wakes the Pult model turn.
- Each wake re-reads the whole hub conversation, which resumes for days (transcript about 1.5 MB); at a 2 h gap the prompt cache (about 1 h) is cold, so each no-news wake pays the full context. About 12 wakes a day, almost all with nothing to push. The host also forces visible output after «no text» exits.
- Pult's options: (1) `watch-servers.ps1` pushes GIVEUP / GIVEUP-TASK / RESTART-LEAD-FAILED to the phone itself through a non-Claude channel, so Pult needs no log watcher; (2) start the hub conversation fresh regularly (stopgap, rejected by the owner as a symptom fix); (3) drop phone push.

## Checked by P
- The 2 h is self-imposed: `watch-log.py:104` `--max-minutes` default 120. Pult claims the host caps background Bash tasks at 2 h: not checked.
- The project leads have the same shape (their session watcher exits every 2 h for a skill update check), but only while they have active sessions.

## Goal
Find with the owner the cause-level fix: what must wake a model at all, and what the owner gets on the phone. Measure before deciding where cheap (tokens per wake, wakes per day). Write the agreed design in «Owner's approval» here.
