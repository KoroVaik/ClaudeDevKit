# Project lead: state and a next-task proposal when nothing is working

Status: done (C: Стан проєкту від керівника).

Source: BACKLOG.md entry «Project lead: state and a next-task proposal when nothing is working» (owner yes, 2026-11-23, Zhratva). Owner's words: «Давай зробим так щоб керівник пропонував якусь задачу коли нічого вже не виконується, бо я не розумію стану. Тобто пише поточний стан проекту і що було б логічним взять далі. Типу стислий опис.» and «Повідомлення довшим не страшне бо робота не виконується а отже нічого не сховає цей опис».

Where: `plugins/dev-kit/skills/project-lead/SKILL.md` («Message templates», «Acceptance and merge» last paragraph), the feature doc `docs/features/hand-work-to-the-project-lead.md`. Remove the BACKLOG.md entry in the same branch.

Success criterion: in a P with no working session, after a C's merge, the message has 2-4 plain sentences of project state and one start proposal; with a working session, it has neither.

## Done

- `project-lead` SKILL.md: new paragraph "The project state" in «Message templates» (block «Стан проєкту» after «Статуси сесій», proposal written in full last), closing-line case 5, reader check covers the proposal, «Acceptance and merge» last paragraph, "beside the blocks" and the restart's "cases of the closing line".
- Choices: an open critical question wins (proposal stays counted); other questions stay counted without «Показати всі питання?»; the block is not repeated unchanged (forced output and plugin-update restart keep the short form); in a fresh P's full list the proposal stays in the list. A session in «чекає на тебе» or «стоїть» counts as not working (BACKLOG wording).
- Feature doc and `docs/glossary.md` "Owner queue" updated; BACKLOG entry removed; dev-kit 0.1.107, routine release mark.
- Checks: lint 0 errors; reviewer (sonnet) found 7 stale or unclear places, all fixed.

Spend: <0.1% of the weekly limit, estimate; API: 0 USD
