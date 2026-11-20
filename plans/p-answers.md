# P asks questions and does not accept the answer

Owner's words (2026-11-20, P: ClaudeDevKit): «Запускай чергову сесію щоб вирішити чому ти задаєш питання і
не приймаєш на них відповідь».

## What happened (P: ClaudeDevKit, 2026-11-20)
- P sent, in the format of `plugins/dev-kit/skills/project-lead/SKILL.md` «Message templates»:
  ```
  **Питання без відповіді**

  - від мене:
    1. Запустити ретро сесій? (8 нових знахідок)
       Рекомендую: так - ...
    - і ще 1 питання вище в чаті

  Показати всі питання?
  ```
- The owner answered «Так». P treated it as two possible readings (yes to question 1, or yes to
  «Показати всі питання?»), following the owner's global rule «two readings → ask 1 чи 2?», and asked
  «1 чи 2?». The owner did not understand («Прочитань?»), then: «Але ти задав тільки одне питання» -
  for him the closing «Показати всі питання?» is not a question.
- Earlier the same day: after «Показати питання?» with two counted questions the owner's «Так» meant
  «show them»; after a full list of two questions his «Так» was taken as yes to both; «1 так» was clear.
- So the format makes a bare «Так» ambiguous whenever a message has both a written-out question and
  the closing line, and P then asks back instead of acting.

## To agree with the owner
How P reads a bare «так» (and «ні») after its messages so it never asks back, and whether the closing
line or the numbering must change so one answer has one meaning.

## Owner's approval (2026-11-20, «Обговорення: P питає і не приймає відповідь»)

Principle (owner): the last line of every P message that has an open question is always one question
the owner can answer with a bare «так»; a bare «так» or «ні» always answers that last line and nothing
else. P never asks back «1 чи 2?» about a bare answer to its own message.

The closing line, by case (applies to the open-question message, the forced-output state and the full
question list in `plugins/dev-kit/skills/project-lead/SKILL.md` «Message templates»):
1. Some open question is not shown in full in this message (only counted, e.g. «і ще 1 питання вище
   в чаті», or an urgent question only named briefly): the message ends with «Показати всі питання?».
   A bare «так» shows the full list; a bare «ні» shows nothing and changes nothing. This holds even
   when the message also writes out a question: to answer that one the owner uses its number («1 так»).
2. Every open question is shown in full and there is exactly one: that question is the last thing in
   the message, with its «Рекомендую» line; no closing line after it. A bare «так»/«ні» answers it.
3. Every open question is shown in full and there are several: the message ends with «Приймаєш усі мої
   рекомендації?». A bare «так» means «так всім»; a bare «ні» means no to all of them.
4. No open question: no closing line (as now). The one-line state «Зараз нічого не працює і нічого не
   чекає на тебе.» stays.

Answers by number («1 так, 3 ні», «так всім») keep working as now, matched to the last list shown.
Owner accepted the weak spot: in the original incident (1 written-out question + 1 counted) a bare «так»
would show the list, not start the retro.

Build notes:
- Edit the lines on the closing line (now «ends with exactly «Показати всі питання?» only when...»), the
  forced-output paragraph, the full-list paragraph and the numbered-answer paragraph; update the example
  messages so each one ends per the cases above.
- Add the reading rule for a bare «так»/«ні» next to the numbered-answer paragraph, with a «Why:» line
  citing this incident (P: ClaudeDevKit, 2026-11-20).
- The owner's global rule «words can be read two ways → ask 1 чи 2?» made P ask back. The skill rule
  must say a bare answer to a P message has one reading by design. If the global rule still overrides
  it, add one line to the existing project-lead exception in the global `CLAUDE.md` «Chat replies» (via
  `dev-kit:edit-rules`; that is the owner's global file, local, outside the repo).
- Another session («Обговорення: Ретро сесій 2026-11-20») may edit the same skill: build after it merges
  and rebase on main.

## Success criterion
The owner approves a short plan; the «Owner's approval» section here holds the exact rule for reading
answers and any format change, in the detail a builder needs.
