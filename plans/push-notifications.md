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
