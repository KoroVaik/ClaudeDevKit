# P messages to the owner: context and order

Owner's words (2026-11-19, P: ClaudeDevKit): «Краще запиши, що ти маєш чітко вказувати стосовно чого
це питання. Бо поки я відхожу саб сесії пишуть керівнику і він на кожне повідомлення спамить в чат
відповідь і це все перемішується. Запускай обговорення як це хендлити бо вже максимально набридло
розбиратись постійно в цьом хаосі повідомлень».

## What happened (P: ClaudeDevKit, 2026-11-19)
- After a handoff load, P sent a start status with two sessions, a long hand-action explanation,
  three next items (all waiting on the owner) and a proposal; owner: «перевантажений з купой питань
  і пропозицій».
- A reviewer found the cause in `plugins/dev-kit/skills/project-lead/SKILL.md`, Status template:
  it asks for every waiting question in full, 1-3 next items and a proposal at once, with no cap and
  no form for a hand action; P also listed next items that wait on the owner. Proposed idea, not yet
  approved: the status holds only sessions, short questions (one line each), tasks that need nothing
  from the owner and one proposal; hand-action steps only on the owner's ask.
- Then a C report arrived while the owner's question «Записати правило?» was open. P answered the C
  and in the same chat message repeated «Записати правило короткого статусу?» with no context; the
  owner did not know what it referred to («Що? Якого ше статусу?»).

## To agree with the owner
- Every P question names what it is about (which topic or session), so it stands alone.
- How P handles C reports and other events that arrive while the owner is away or mid-discussion,
  so the chat is not a mix of replies: what P says at once, what it batches, what it says nothing about.
- Whether the start-status idea above goes in too.

## Success criterion
The owner approves a short plan; the «Owner's approval» section here holds every agreed point in
the detail a builder needs.

## Owner's approval (2026-11-19, discussion «Повідомлення керівника»)

The owner said «так» to every point below. They replace P's current Status, Task done and owner-item
messages (`plugins/dev-kit/skills/project-lead/SKILL.md`: Status template, Task done, owner items, the
«Без відповіді ще N питань» count line, «one item per message»). Chat examples were shown and accepted.

1. Every P message to the owner is built from two bold blocks, in this order: «Статуси сесій» and
   «Питання без відповіді». A bold block title is followed by an empty line, so the list under it
   renders as a list (the owner saw a broken render without it). Minimum text: no intro, no
   «прийняв», no confirmation of an answer, no other parts.
2. «Статуси сесій»: one list line per session, the state first, then the exact session name in «»:
   `- працює - «C: Тести хуків»`. States used: «працює», «чекає на тебе», «стоїть, скінчився ліміт»
   (with when it goes on), «стоїть, сесія впала», «готово» (the owner's change, 2026-11-19: the merge is not mentioned). «чекає на тебе» always has the
   reason in brackets in the owner's words: `- чекає на тебе - «C: Чистка гілок» (дозвіл видалити гілки)`.
   Several finished sessions may share one «готово» line.
3. The start status lists all sessions. Every later message lists only sessions whose state changed
   since the previous P message, except «готово»: a finished session stays in every message until the
   owner next writes to P (any message); from the message after that it is gone.
4. P does not wait for the owner: it writes at once on each event (a C report, a watcher exit), and
   the message holds only what changed. A wake-up that changes nothing gets no text (as today).
5. «Питання без відповіді» shows no question text except urgent ones:
   ```
   - ❗ термінові: 2
     - видалити влиті гілки - «C: Чистка гілок»
     - дозволити запис у main - «C: Тести хуків»
   - від сесій: 2
   - від мене: 1
   ```
   Urgent = the session stands and cannot move without the answer; a session that asks and goes on,
   or a closed session with a leftover question, is not urgent. Every urgent question is listed, no
   cap and no «і ще N», each as a topic of a few words in the owner's words plus the session name.
   A kind with zero is left out; with no open questions at all the block is left out.
6. P's own proposals (start a new C, close a task, restart a crashed session) are P's questions and
   count under «від мене»; there is no separate closing proposal any more.
7. When any question is open, the message ends with exactly «Показати питання?». On the owner's
   «так» P shows every open question in full, numbered from 1, under the bold titles «Питання сесій»
   (urgent ones first, marked ❗) and «Питання від мене». The owner's answer by number («1 так, 3 ні»,
   «так всім») is matched to the last list shown; answered questions just disappear from the counts,
   with no confirmation line.
8. Each question stands alone: a session's question starts with its name and «питає:»; the topic is in
   the owner's words, never an internal name (bad: «Хук вузьких агентів»; good: «помічник для інших
   репозиторіїв»); the consequence goes in brackets; it is worded so the advice is «так», then an
   indented line `Рекомендую: так - <reason>`. Example:
   ```
   1. «C: Чистка гілок» питає: видалити 12 гілок, вже влитих у main? (їх можна відновити місяць)
      Рекомендую: так - вони лише засмічують список.
   ```

Not agreed, left out: the earlier idea that hand-action steps appear only on the owner's ask, and
the «Без тебе» line (tasks needing nothing from the owner) - neither is in the accepted format.
Builder notes: the owner's global rules (`C:/Users/korov/.claude/CLAUDE.md`, «Never block the
conversation while waiting», the paragraph that defers a result while a question is open) pull
against point 4 for P; the builder settles that through `dev-kit:edit-rules` (owner's global rules)
and asks the owner if a global line must change. The existing open-question queue (PROGRESS.md
«Open questions», the stale-question rule) stays the store behind the counts. A script-built status
with finished-task history is a separate backlog idea, not part of this build.

## Build (C: p-messages-build)
- Paid spend: $0.
- Built: `project-lead` "Message templates" and "Owner queue" rewritten; pointers, feature doc and glossary updated; dev-kit 0.1.61.
- Builder decisions: model check, docs-migration offer, backlog entries, retro, takeover and close offers are P's own questions; the «Вирішив сам» line and the «Раніше я сказав» prefix are dropped; taken-over sessions use the same states.
- Waits: the owner's yes (via P) to one exception line for P in the owner's global CLAUDE.md.
