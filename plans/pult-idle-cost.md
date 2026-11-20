# Pult idle token cost

Owner's words (to Pult): «Пропналізуй доцільність пульта... Чи не спалює це постійно токени», «Напиши керівнику плагіна». To P, on the stopgap «start the Pult conversation fresh once a day»: «Це вирішення симптому. Обговорення давай» (2026-11-20).

## Pult's finding (not measured in tokens)
- An idle Pult session costs nothing; the cost is the phone-push design. `plugins/pult/scripts/watch-log.py` exits with «time limit» about every 2 h, and each exit wakes the Pult model turn.
- Each wake re-reads the whole hub conversation, which resumes for days (transcript about 1.5 MB); at a 2 h gap the prompt cache (about 1 h) is cold, so each no-news wake pays the full context. About 12 wakes a day, almost all with nothing to push. The host also forces visible output after «no text» exits.
- Pult's options: (1) `watch-servers.ps1` pushes GIVEUP / GIVEUP-TASK / RESTART-LEAD-FAILED to the phone itself through a non-Claude channel, so Pult needs no log watcher; (2) start the hub conversation fresh regularly (stopgap, rejected by the owner as a symptom fix); (3) drop phone push.

## Checked by P
- The 2 h is self-imposed: `watch-log.py:104` `--max-minutes` default 120. Pult claims the host caps background Bash tasks at 2 h: not checked.
- The project leads have the same shape (their session watcher exits every 2 h for a skill update check), but only while they have active sessions.

## Measured (2026-11-20, from the transcripts, tokens only)
- Pult hub (Opus), 2026-11-19..20: about 13 wakes a day, gap about 110 min; 22 of 22 wakes pushed nothing; 21 of 22 cold (each rewrites about 110k tokens to the cache and reads about 230k). About 4.4M tokens a day for nothing.
- The 2 h is the host's cap on a background Bash run (a 125-min run was killed at 120 min); the hub then re-armed itself with `--max-minutes 110`, written nowhere in the plugin. The Monitor tool caps at 30 min, so no in-session watcher avoids the wakes.
- Leads cost more: Zhratva lead about 18M tokens a day on 11-19 and 11-20 (contexts 340k-540k, cold wakes every 2 h), 1 push in 33 wakes; Prishch lead 7 idle wakes on 11-19.
- No way found for a script to wake a running session (`claude` CLI has no send; `restart-leads.ps1 -Ask` writes a file the lead's own watcher reads). Paid spend of this task: about 0.013 USD (two Haiku push tests).
- Total of idle wakes 2026-11-15..20 (retro units, Opus 1.5): 23.6M units, about 3.4% of a weekly limit; Pult hub 87% of its own usage, Zhratva lead 20%, Prishch lead 11%; about 85% of it is cache writes.

## Goal
Find with the owner the cause-level fix: what must wake a model at all, and what the owner gets on the phone. Measure before deciding where cheap (tokens per wake, wakes per day). Write the agreed design in «Owner's approval» here.

## Draft design (agreed point by point 2026-11-20; the change list is not approved yet)

Cause: a Claude session is woken only to re-arm a watcher the host kills every 2 h. Fix: no model keeps a watcher; the server watcher (`plugins/pult/scripts/watch-servers.ps1`, already a non-Claude process) does all watching and wakes a model only on a real event. One running script; plus a prompt hook.

1. Pult keeps no watcher. `watch-log.py` is no longer armed by Pult; `rules/hub.md` "Phone push" is rewritten (no re-arm, no forced-output text for time-limit exits).
2. Pult events (GIVEUP, GIVEUP-TASK, RESTART-LEAD-FAILED, as today): `watch-servers.ps1` restarts the Pult session (stop, then resume the same conversation, as `restart-leads.ps1` does for leads) with a message holding the event line(s). Pult then sends the PushNotification as today and writes the cause and proposed fix in its chat.
3. Silence before a restart: Pult must be idle (`claude agents --json` status) and its transcript .jsonl unchanged for 5 minutes (owner chose 5, not 10). Otherwise the script re-checks each round; events are queued, never dropped.
4. Pult down or failing to start: the script sends the push itself through a one-shot session: `claude -p --no-session-persistence --model haiku --allowedTools PushNotification` (checked: runs hidden from a script, about 0.006 USD). Text says what to do, e.g. «Pult не піднявся - запусти його на комп'ютері» plus the event. Why no persistence: the owner dislikes extra sessions in lists; a tap on that push likely leads nowhere (not checked), so the text must be self-sufficient.
5. While the owner talks to Pult: a UserPromptSubmit hook of the pult plugin, only in the hub session (cwd is exactly home, as `hooks/hub-rules.py` detects), adds the new problem lines (since the last delivered one; keep a position file) as additionalContext; silent when there is nothing new, so no model step and no tokens. Pattern: `plugins/dev-kit/hooks/owner-session-note.py`.
6. Leads, same scheme (owner: «так»): a lead keeps no `dev-kit-sessions watch` of its own. `watch-servers.ps1` runs the same session check (reuse `cmd_watch` logic in `plugins/dev-kit/scripts/sessions.py` as a one-shot round, not a copy) for each lead with registered C sessions; on an event line (gone, finished, limited, stale, restart requested) it restarts that lead with the line(s) under the rule of point 3. The same prompt hook for a lead's owner messages (the dev-kit plugin, lead sessions only). The plugin-update reason of the 2 h exit is already covered by `watch-servers.ps1` and `restart-leads.ps1 -Ask`; the restart request (exit 7) must reach the lead the same way. Update `project-lead/SKILL.md` (the watcher arming and "at least every 2 hours" lines, 609 and 734) and `hub.md:143`.
7. Not checked, builders check first: how to resume a background session with a first message from a script; whether a push from a restarted Pult reaches the phone when the owner is away (two tests with the owner at the PC were skipped by Claude as «terminal is active»; this needs the owner away from the PC for about 10 minutes).
8. Success check after the build: from the transcripts, Pult and a lead with no events show no wakes for a day; one forced GIVEUP gives one push and the fix line in Pult.
9. Critical problems in Pult's reports (owner, 2026-11-20, «так» to each point): Pult's status shows a short list of critical problems, technical and token ones. A token problem is critical only when a session spent over 2% of the weekly limit in a day, or wasted over 0.5% in a day (waste: idle wakes, cold restarts, bloated context, as in the BACKLOG entry «Retro: token waste findings»). The thresholds are first checked on the scans of the last 5 days: how many lines they would have given. Each problem is shown once and again only when it grew. The numbers come from the daily retro scan (`retro.py`, a script, no model), so the delay is at most a day.
10. Problems that can wait (below those thresholds) go to the retro as priority items: first in the reviewer's list of the retro session (owner: «Всі проблеми які можуть почекать, потрібно виносить на ретро приорітетними»).
11. Phone push for tokens only when a session's conversation grows past 700k tokens (input + cache read + cache write of its last call; checked readable: the Zhratva lead reached 703k), once per session; the push says to move it to a new session. Checked by `watch-servers.ps1` on the last call of each live session, not by the daily scan (owner: «пуш є сенс коли сесія виросла більш ніж 700к токенів... мені треба перенести її»). Other token problems wait for the status.
12. Critical technical problems stay as today: GIVEUP, GIVEUP-TASK, RESTART-LEAD-FAILED; the rest the server watcher heals itself.

Open (owner, «про це окремо поговорим»): leads often miss the moment their conversation has grown too big and should move to a new session.
