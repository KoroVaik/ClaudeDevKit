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

(to fill)
