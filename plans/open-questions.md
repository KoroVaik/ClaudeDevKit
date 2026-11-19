# Unanswered owner questions: never lost, never spammed

Owner's words (2026-11-19): «Зверху були питання до мене?», «Чому я їх не бачу в звіті?», «Отже є проблема з правилами звіту»; to the proposal «питання без відповіді повторюється в кожному наступному повідомленні»: «Запусти обговорення. Бо постійно спамити одне і те ж також поганий варіант».

## Checked facts (reviewer, 2026-11-19)
- The Task done template (plugins/dev-kit/skills/project-lead/SKILL.md, "Message templates") lists questions only for the sessions finished in that message; it has no queue line and no carry-over.
- The only re-ask rule is in "When P starts" (a skipped question from the start status, «in one line»).
- «У черзі ще N питань» appears only in the Status and the owner-item templates.
- The queue lives in PROGRESS.md "Open questions"; ClaudeDevKit has no PROGRESS.md and no rule says where the queue lives then.
- Pulls toward dropping: the global "one final next-step question", the "one item at a time" queue rule.
- Case: P sent two questions after a merge; the next Task done kept one and dropped the other with no count line.

## Questions to settle with the owner
- How an unanswered question stays visible without repeating it in every message (a count line, a reminder only at the status, a stored list the owner can ask for, a phone push once).
- Where the queue lives in a project without PROGRESS.md.
- When an unanswered question expires or is decided by P's recommendation.

## Checked facts (gap check, 2026-11-19)
- The queue always lives in PROGRESS.md "Open questions" (documentation standard); ClaudeDevKit simply lacks it, so no fallback place is needed.
- ClaudeDevKit enables dev-kit but was never moved onto the docs standard: no PROGRESS.md, docs/product.md, epics, features, tech map, standards, `## All agents` profile section.
- Plugin rules say "(if the project has it)" in many places (project-lead start, open items, agents' profile reads), so agents skip steps silently; several steps (fix-bug, new-feature, discovery-round, Pult hub) read PROGRESS.md with no rule for a missing file.
- The docs checker (plugins/dev-kit/scripts/check_docs.py) checks the docs that exist; it does not report missing base files.

## Owner's approval
Owner, 2026-11-19: «Так, додай скрипт який буде це робити» (point 4), then «Так» to points 1, 2 and 3.

1. Count line, no repeats. Every P message to the owner (Task done included) ends with one line «Без відповіді ще N питань» while N > 0; the questions themselves are shown only in the Status and when the owner asks «які питання» (a new trigger). Lives in: `plugins/dev-kit/skills/project-lead/SKILL.md`, "Message templates" (Task done and other templates) and a new rule for the owner's «які питання» / "what waits on me".
2. Where the queue lives. Always PROGRESS.md "Open questions", as the documentation standard already says; no fallback place. Lives in: `plugins/dev-kit/skills/documentation/SKILL.md` (no change); project-lead's "(if the project has it)" wording for the queue is dropped.
3. Stale questions. A question unanswered since the previous day that P may decide itself (its own-decision rights in project-lead) is decided by P's recommendation, recorded in PROGRESS.md, and told to the owner once; others stay in the queue. Lives in: `plugins/dev-kit/skills/project-lead/SKILL.md`, the queue rule next to "decisions P makes itself".
4. Structure check by script. At start P runs a script that reports missing base files of the docs standard (PROGRESS.md, docs/product.md, epics, features, tech map, standards, profile `## All agents`); if any are missing, P offers the docs migration (`dev-kit:migrate-docs`) once instead of skipping steps silently. Lives in: a new mode of `plugins/dev-kit/scripts/check_docs.py`, called from project-lead "When P starts".
5. ClaudeDevKit itself. A separate task moves ClaudeDevKit onto the dev-kit docs standard with `dev-kit:migrate-docs`, which creates its PROGRESS.md. Lives in: this repo (new task for P).

## Success criterion
The owner's «так» to the approved idea, written in the section «Owner's approval» below, with where each part lives.
