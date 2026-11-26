# Plan: the Lead's questions are not lost or misdirected

Status: built (2026-11-26, dev-kit 0.1.140, a clean release); next: the Lead merges.

Owner's words: «гадаю ці 2 можна обєднать в 1 діскас», then «+» to «Відкрити одне обговорення «Discuss: Питання Lead не губляться» на обидві проблеми?» (L: ClaudeDevKit, 2026-11-26).

Two problems, both in `plugins/dev-kit/skills/project-lead/SKILL.md` ("Message templates": closing-line cases 1-5, forced output, «Reading the owner's answer"; "Owner queue and critical items"):
1. An open list is replaced by a later message, so a bare «так» goes to the wrong question. Source: BACKLOG.md entry «Lead: an open question list is not replaced by a later message» (case, causes, reviewer's case-6 proposal and its doubts). Owner (L: Prishch): «Я написав так на попереднє повідомлення. Тут вже хаос якийсь».
2. A question the Lead shows only in chat, not in PROGRESS.md "Open questions", is lost when the Lead restarts. Source: open defect in docs/features/hand-work-to-the-project-lead.md (~line 232).

## Agreed so far (discussion, 2026-11-26)

- Goal (owner «так»): no Lead question to the owner is lost or replaced until it is answered; his «так» always goes to the open questions, and after a Lead restart they are shown again.
- A question leaves the open list only when the owner answered it (by a bare «так» / number answer in the Lead's chat, or in the session itself, found by `dev-kit-sessions answers` or a ВЛАСНИК ВІДПОВІВ message, as now).
- When the Lead finds the answer itself, it does not drop the question: the item stays open and its recommendation line becomes «Рекомендую: закрити - <причина>»; the owner closes it with his usual «так» / «так всім» (owner: «краще нехай питання відкрите, а в пораді стосовно нього вказано що можна закрити по такій то причині», then «+»). This replaces the earlier "Lead drops it and says so in one line".
- Such an item opens with a mark so the owner need not read it: «✅ Вирішено, закрити? (<причина>)» (owner: «ті питання які закрились автоматично повинні мати лейбу щоб я не вчитувався в те що вже вирішено», reading 1 chosen, then «так»).
- Question window (owner's own proposal, then «так»): the Lead's chat shows at most 2 open questions at a time, the oldest ones; every newer one is hidden behind a counter line like «і ще 24 питання». The window changes only after the owner's answer: answered items leave and the next oldest fill the window. So a bare «так» sent at any moment (even while the Lead posts something else) answers the same 2 shown questions. Replaces the reviewer's "case 6" idea from the backlog entry.
- Fewer Lead messages (owner «так краще, бо статуси всерівно втрачаються в потоці спаму ліда»): the Lead writes to the chat only when something waits on the owner or there is a result he sees: a merge, a session's work finished, a failure, a new question. Smaller changes (a session's progress, a step done, a status change) send no message; the Lead adds them to its next such message. Today every changed status gets a message ("One message per event", project-lead SKILL.md ~72-76); this narrows it. The owner can ask for statuses any time.
- Handoff skill stays generic (owner: «думай як зробити цей скіл дженеріком, бо сумніваюсь що всім іншим типам сесій потрібні такі специфічні штуки», then «так» to the principle): `continue-work-in-another-context` (local, `C:/Users/korov/.claude/skills/`) gets one general section «Дослівно» where open questions to the owner and his exact decisions are copied word for word, with no paraphrase; the skill that calls it (for the Lead: `dev-kit:project-lead`) may name extra items for that section (the Lead: its question queue). The exact contents are set after the analysis of real handoff files (running, report in the job's tmp `handoff-analysis.md`).
- Every question goes to PROGRESS.md "Open questions" before the Lead shows it (owner «так»): no question exists only in chat, so a restart or a context move keeps it. The existing exceptions that never enter the queue (push-test steps, hand data work returned to a Manager, decisions the Lead makes itself; project-lead SKILL.md ~389-392, 699) stay.
- Stale items too (owner «так»): the Lead no longer decides an old item by its own `Рекомендую:` line (project-lead SKILL.md ~347-353); it stays open with «✅ Вирішено, закрити? (<причина>)».
- Every Lead message that has text ends with the 2 window questions written out in full, as its closing line (owner «так»); this replaces the closing-line cases that show only counts («Показати всі питання?»), forced output included. A message with no open question has no closing line, as now.
- A Lead's own start proposal (a «Discuss:» or a task session, "The project state") becomes an ordinary item in the queue and the window, never a separate closing line (owner: «зазвичай я сам прощу почати обговорення», reading «Lead proposes rarely; such a proposal is an ordinary queue item» chosen). Closing-line case 5 goes.
- A number answer («1 так», «2 ні») closes only the named item; the next oldest item takes its place in the window (owner «так»). The usual answer is a bare «так» to both; a number answer is the rare case and says nothing about the other item.
- Critical questions go on top (owner: «так, критичні наверх»): a critical question takes the first place in the next window after the owner's answer, never replacing a shown question mid-window.

## Owner's approval

Owner, 2026-11-26, «Discuss: Питання Lead не губляться»: «коли доаналізує роби висновки і закривай обговрення, шажаю там технічні моменти якіі ти сам вирішиши», then «уже даю так» (a «так» to the short plan given in advance; the session said it would ask again only if the analysis changed an agreed point, and it did not). The points above are the owner's; the points below marked "technical" were left to the session.

### A. Lead: question window (`plugins/dev-kit/skills/project-lead/SKILL.md`)

1. Queue first. Every question the Lead shows the owner is written to PROGRESS.md "Open questions" before the message is sent (format as now: date · asker · ❗ if critical · question · `Рекомендую:` line). Exceptions as now (~389-392, 699). Closes the defect in `docs/features/hand-work-to-the-project-lead.md` ("a question the Lead shows only in chat...").
2. Window. A Lead message with any open question shows at most 2 of them, written out in full, numbered 1 and 2, the oldest first; critical items sort before all others (a critical item that arrives while a window is shown waits for the owner's next answer, then takes place 1). Below them one counter line «і ще N питань» when more wait. The closing line (technical): one shown item - that item's question is the last line; two items - «Приймаєш мої поради до обох?». This replaces closing-line cases 1, 3 and 5 and the counts-only form; case 2 (critical) becomes "critical sorts first in the window"; case 4 (no open question: no closing line) stays.
3. The window is stable. Its content changes only after an owner answer (or a ВЛАСНИК ВІДПОВІВ / `dev-kit-sessions answers` find that closes a shown item). New questions only raise the counter. Every Lead message with text repeats the same window, so a bare «так» sent at any time answers the shown items.
4. Reading answers. Bare «так» / «ні» / «так всім»: both shown items (or the one). «1 так», «2 ні»: only that item; the usual answer is a bare «так», a number answer says nothing about the other item. Answered items leave; the next oldest (critical first) fill the window in the Lead's next message.
5. The Lead never closes an item itself. When it finds the answer (from a session, the code, or an old item it would have decided by its own `Рекомендую:` under ~347-353), the item stays and is rewritten to open with «✅ Вирішено, закрити? (<причина>)»; the owner's «так» closes it. The rule at ~347-353 that decides stale items goes. Items answered by the owner in a session (ВЛАСНИК ВІДПОВІВ, `answers`) are still dropped with no question, as now.
6. A Lead's own start proposal («Discuss:» or task session, "The project state") is an ordinary queue item in the window, never its own closing line.
7. Restart and context move: the first message after any restart shows the window from PROGRESS.md (not the full list, technical; replaces "with the full list of questions" at ~1031 and the fresh-Lead full list at ~219-222).

### B. Lead: fewer messages (same SKILL.md, "One message per event" ~72-76, forced output ~77-92)

1. The Lead writes to the chat only when something waits on the owner or there is a result he sees: a new question (it raises the counter, so the message is the counter change), a merge, a session's work finished, a failure or stuck session. A Manager's progress, a step done or any other status change sends no message; it goes into «Статуси сесій» of the next message that is sent.
2. Forced output (host demand, keep-warm ping) stays as now but ends with the window (A.2), never counts only.
3. Technical: `plugins/dev-kit/hooks/lead-reply-form.py` keeps checking form only; its closing-line regex must accept the window's closing line. No new check of window content.

### C. Handoff skill (local `C:/Users/korov/.claude/skills/continue-work-in-another-context/SKILL.md`, edited through `rules-kit:edit-rules`)

Generic for all sessions; the calling skill may add items. Technical, from the analysis of 14 real handoffs (2026-11-26: owner words paraphrased in about 7, open questions given as a pointer in 5, "Settled decisions" filled with built work in 5, an unanswered last owner message dropped in 1; causes at SKILL.md ~57-61, ~131-135, ~146-147, ~49-53):
1. New section «Дослівно», mandatory, never shortened by the length cap or the "no long quotes" rule (shorten everything else first): (a) the owner's decisions, corrections and "важливо"-type remarks, copied word for word with their date; (b) every open question to the owner exactly as he saw it, with its recommendation and status (asked, unanswered); «немає» written out when empty. It replaces "Waiting for the user" and the never-used "Task instructions from the user".
2. Save step "owner sweep": before writing, read the owner's messages since the last handoff (or the session start); an unanswered one is answered first or listed in «Дослівно» as unanswered.
3. "Settled decisions" holds only owner decisions; built or merged work goes as one line under "Closed work".
4. Load: read «Дослівно» first; answer any unanswered owner item before anything else.
5. Hook for calling skills: one line saying a calling skill may name extra items for «Дослівно». `dev-kit:project-lead` names: the current window's items as shown, and a pointer that the full queue is PROGRESS.md "Open questions".

### Docs and cleanup

Update `docs/features/hand-work-to-the-project-lead.md` (the owner's view of the window, the ✅ mark, fewer messages) and close its defect; remove the BACKLOG.md entry «Lead: an open question list is not replaced by a later message»; release note per the plugin's versioning. A release that changes the Lead's message form is marked `"clean": true` (`plans/lead-early-clear.md`) if that is built by then.

Success criterion: an «Owner's approval» section here with every agreed point in builder detail, and the owner's «так» to the short plan. Remove the backlog entry and close the defect when built.

## Build notes (2026-11-26)

- Technical choices: a one-item window is unnumbered with no closing line; a one-item window does not grow until the owner answers (stable window); a «ні» to a «✅ Вирішено» item keeps it open as an ordinary question; «які питання» (show the full list) is gone with the full list; `sessions.py quiet` still treats the repeated window as an open question, as the old counts line already did, so routine restarts wait as before.
- The handoff skill is local and ignored by the `.claude` git repo, so its edit has no commit.

Spend: ~0.4% of the weekly limit, estimate; API: 0 USD
