# Open wake checks of the Pult watcher

Status: done (C: Перевірка пробуджень).

Owner «Так» 2026-11-24 to the start proposal, P: ClaudeDevKit chat («Запустити нову сесію «C: Перевірка пробуджень»? (перевірить, що зайвих запусків немає)»).

Scope: the still open items of `docs/features/start-leads-at-logon-and-heal-them.md` «Open», except the weekly limit forecast push (it fires only on a real pace):
1. A watcher message now reaches the Pult chat (sent in default mode to the hub's system name).
2. A quiet day of a lead in the watcher log shows no wake.
3. The exact wording of the session list in the phone app.

Earlier findings: `plans/wake-check.md`. Lead pushes reach the phone with the app closed: passed 2026-11-24.

The owner's phone or eyes: never ask the owner; send P a ПИТАННЯ with one step at a time (what to do, what to look for, answer + or -), P relays. Never stop Pult, its watcher or a real lead: throwaway test sessions only.

Success criterion: each check marked passed in the feature's «Open», or a defect filed with its cause.

## Findings (2026-11-24)

- Pult chat: passed. After the default-mode fix four phone-push requests went to Pult (servers.log WAKE-SENT/WAKE-TAKEN "via Pult", 2026-11-23 21:02 and 2026-11-24 05:05, 05:10, 10:03). Pult's transcript (`projects/C--Users-korov/7966c247...jsonl`) holds each as a user turn; Pult called PushNotification ("Mobile push requested") and answered in its chat. The 10:03 one first failed 24 tries on the 5-hour limit, then was taken after the reset.
- Lead quiet day: no lead had a full day without events (each lead has work daily). Longest quiet stretches, lead up the whole time: P: ClaudeDevKit 2026-11-22 17:37 to 2026-11-23 11:52 (18 h; only version restarts, no wake); P: Zhratva 2026-11-24 06:13 to 19:51 (13 h; restarts deferred, no wake). Every lead wake in the log has cause=event or cause=ping. Marked passed on the quiet stretches.
- Phone session list wording: passed. Owner via P: «P: ClaudeDevKit» is in the phone list by that exact name («Так це ж твоя сесія»).

Spend: <0.1% of the weekly limit, estimate; API: 0 USD
