# Discussion: a question left by a task session that already ended

## Owner's words (2026-11-16)

«керівник дратви пише що сесій в роботі жодних а нижче C: Пілотна схема імпорту (питає)
це як рощуміть? Запусти саба для обговорення цього, нехай він прочитає лог тієй сесії»

## What is known (checked by a read-only look at the P: Zhratva log)

- Transcript: C:/Users/korov/.claude/projects/C--Users-korov-MyRepositories-Zhratva/2d56121f-d0a4-402c-882d-63fdb3b7856e.jsonl
- Around line 1488: «C: Пілотна схема імпорту» reported done and asked the owner a yes/no about the import.
- Lines 1516-1530: P merged it, ended it in the registry, removed the session, worktree and branch.
- Line 1536: P put the question into Zhratva PROGRESS.md "Open questions".
- Line 1621: the confusing status - «Сесії в роботі: жодної», and below it «### C: Пілотна схема імпорту (питає)».
- Cause: a gap in plugins/dev-kit/skills/project-lead/SKILL.md, not a P mistake. The owner-item template
  (`### <session name> (питає)`) has no form for a question left by a session that ended, and the rule
  "P sends the owner's answer to that C verbatim by SendMessage" has nothing for a C that no longer exists.
- Unsure: the line «У черзі ще 3 питання» may be an overcount by one.
- P's first idea (not agreed): heading «(завершена, лишилось питання)»; the answer goes to a new C or to P.

## Goal of the discussion

Agree with the owner how P shows such a question and what happens with the answer. Read the log
yourself first. End with the exact wording of the rule change written below, then the owner's yes.

## Agreed change

Log read: the transcript above is the session «P: Zhratva» (checked by its title); no other Zhratva
log holds the question.

1. Accepted (owner «+», 2026-11-16). After "P sends the owner's answer to that C verbatim by
   SendMessage." in "Message templates":

   > An owner item left by a C that P already merged and closed: heading
   > `### <session name> (закрита, є питання)` (in English `(closed, has a question)`), then the
   > question and its recommendation line as above, with no other line. "Sessions at work" does not
   > list that C.

2. Accepted (owner «так», 2026-11-16, after narrowing: no session for trivial work). Right after rule 1:

   > P acts on the answer to such an item itself. A yes that needs real work (code, a run, a data
   > change): P starts a new C with the answer in its task file and first prompt, with no second
   > question. A yes that needs only a record, or a no: P records the answer in the doc the question
   > came from and removes it from PROGRESS.md "Open questions". A small follow-up not worth its own
   > session: P adds it to that doc's open items, and the next C in that area takes it.
   >
   > Why: in Zhratva on 2026-11-16 P showed a merged C as «(питає)» under «Сесії в роботі: жодної»,
   > and the owner could not tell who asked; the owner wants no session for a trivial answer.

3. Accepted (owner «так», 2026-11-16). In "Start an «Обговорення:» session", after the first
   bullet:

   > - The owner's «сабсесія», «саб-сесія», «сесія для обговорення», or «саб» to talk something over,
   >   means this session, never a helper agent. When the owner's words point at a log, file or
   >   session («нехай прочитає лог тієї сесії»), P adds its path to the first prompt.
   >
   > Why: on 2026-11-16 the owner asked P: ClaudeDevKit for «саба для обговорення» and P started an
   > internal helper the owner could not talk to.
