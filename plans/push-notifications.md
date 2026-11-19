# Push urgent items to the owner's phone

Owner (P: ClaudeDevKit chat, 2026-11-19): «Так» to «Запустити нову сесію «C: Сповіщення про термінове»? (на телефон приходять лише важливі події)». Backlog entry: «Pult: phone notification from a script» in BACKLOG.md.

## Checked facts (2026-11-19)
- The PushNotification tool of a Claude session (here P: ClaudeDevKit, a background session with Remote Control) reaches the owner's phone when the Claude app is closed or minimized; it is not shown while the app is open on screen. The tool itself skips a push when the user is active at the terminal.
- So no separate script channel is needed: sessions push.

## Goal
Only urgent events reach the phone, so the owner need not open chats to check:
- a project lead's critical items (a session cannot go on without the owner, crashed, a risk to data or money - project-lead "Owner queue and critical items");
- possibly an owner-queue item that waits on the owner while no answer comes (decide: push once, not per item, to avoid noise);
- Pult: what the Pult watcher gave up on (dead server or lead after its retries) - pult rules/hub.md.
Not routine progress, not done reports, not watcher exits that need nothing.

## Success criterion
The project-lead skill and the Pult hub rules say exactly when to push (with the one-line message format: what to act on first, under 200 characters) and when not to; the BACKLOG entry is removed; lint and tests pass. A live check: one real push from a test case reaches the phone (ask P to have the owner confirm).

## Approved push list (owner «Так» via P, 2026-11-19)
Push:
1. A C crashed or quit without a report - P pushes. «P: Zhratva: «C: Каталог» впала без звіту - відкрий P»
2. A C cannot go on without the owner (critical stuck) - P pushes. «P: Prishch: «C: Оплата» чекає на тебе - потрібен вхід у Stripe»
3. A risk to data or money - P pushes. «P: Zhratva: міграція може стерти дані - зупинив, відкрий P»
4. Owner queue: one push only when the empty queue gets its first item, none for later items until the owner writes. «P: ClaudeDevKit: 1 питання чекає на тебе»
5. Pult watcher gave up (a lead or C not restored after 3 tries, a failed heal or lead restart) - Pult pushes, woken by a background log watcher (`plugins/pult/scripts/watch-log.py`). «Pult: P: Zhratva не піднявся після 3 спроб - відкрий Pult»
Leave out: done reports and merges, routine progress, sessions that came back by themselves (HEAL then UP), usage-limit stops (queue item only), watcher time-limit exits, plugin-update restarts that worked, more queue items while one already waits.

## Paid spend
$0.

## Built (2026-11-19)
- project-lead "Owner queue and critical items": push rule (items 1-4). Pult hub.md "Phone push" + `plugins/pult/scripts/watch-log.py` (item 5), tests `tools/tests/test_watch_log.py`. dev-kit 0.1.51, pult 0.1.10.
- Review fixes: a failed HEAL try is not pushed on its own (GIVEUP follows it, one push per incident); a log line older than the watcher's last run (Pult was down > 10 min) is not pushed; after a Pult restart nothing is pushed until the owner's first message to Pult arms the watcher (Pult has no first prompt to arm it).
- Live check (2026-11-19, owner): test line «GIVEUP P: тест-пушу» in servers.log; idle Pult woke on its watcher's exit, pushed «Pult: P: тест-пушу не піднявся ... - відкрий Pult» and the owner got it on the phone with the app closed. P-side push was already proven earlier the same day.
- Found in the live check: watch-log.py crashed on a Cyrillic line (Windows cp1252 stdout); fixed (utf-8 stdout, position saved only after the print), pult 0.1.10, test added.
- Found: Pult ran pult 0.1.0 from the plugin cache since 2026-11-15 (nobody runs `claude plugin update pult@korov-dev`), and a resumed Pult keeps its old rules. Updated by hand to 0.1.9 with the owner's yes and Pult restarted; reported to P as a separate task.
