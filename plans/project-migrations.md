# Changes every project needs, rolled out through the leads

## Owner's words (2026-11-16)

Via Pult (quoted by Pult): «Гадаю це можна зробить ерез якийсь файл версій який читає сесія кожного проекта і
зобовязна сапустить спецільного саб агента який внесе ці зміни в проект відповідно до правил конкретного
проекта... Можливо це прибере необзідність агента для змін в чужих проектах.... Але сумніваюсь, бо деякі зміни
в усіх проектах треба тут і зараз, а коли сесія іншого агента піхопить оновлення невідомо. Або зробити так щоб
керівники проектів постійно трекали якимось чином нові оновлення.»
To P: projects without a lead (KnowledgeBase, Zhratva-design-sandbox, the old Pult repo) - «вони і не треба ці
репо, топу пофіг». «Пульт має реюзать плагін. Видумувать свої костилі не треба». «так» to starting this session.

## Idea agreed with the owner (P's verdict, owner's yes)

- dev-kit keeps a versioned list of project-level changes (structure, profile, rule files a project must
  change), each written so an agent can apply it to any project following that project's own rules.
- Leads already learn about updates within minutes: after each dev-kit version bump P: ClaudeDevKit messages
  Pult, and Pult restarts the leads (project-lead "Restart for a plugin update"). On that restart, and on a
  normal start, P compares the project's applied version (recorded in the project, e.g. its dev-kit profile)
  with the list and hands the pending changes to a C or a subagent that applies them under the project's rules,
  then records the new applied version. A change that needs a product choice goes to the owner queue.
- Only projects with a lead count; projects without one are out of scope.
- Rare urgent "here and now" edits in all projects stay with the owner's local other-repo-editor, launched
  from Pult.

## Success criterion

- The list file, its format and the P step exist in dev-kit (rules in project-lead, the format documented),
  and the first entry is a real pending change if one exists, otherwise a harmless test entry.
- Dry run on one project's copy (a throwaway worktree, not a real lead) shows the change applied and the
  applied version recorded.
- Lint passes; dev-kit version bumped.

## Build (C, 2026-11-16)

- List: `plugins/dev-kit/migrations.md`, entries `## <n>. <title>` with Added / What / How / Owner choice /
  Done when. Numbers only grow; an entry is never renumbered or removed.
- Applied level: the project's `.claude/dev-kit.md`, section `## project-lead`, `| Setting | Value |` row
  `migrations applied | <n>` (lint learns this second table; missing = 0).
- Command: `dev-kit-migrations pending` / `record <n>` (script `migrations.py`, shared parser with the lint).
- Entry 1 (bootstrap, harmless, real): record the applied level in the profile.
- P step: in project-lead, on start and after a plugin-update restart; pending entries go to one C.
- Dry run: a throwaway local clone in the job's temp folder, not a real lead or worktree.
- Paid spend: $0 (subagents only, no paid API calls).

## Result (C, 2026-11-16)

- Built: `plugins/dev-kit/migrations.md` (entry 1 = bootstrap row), `scripts/migrations.py` + `bin/dev-kit-migrations`,
  lint check of the list and of the project-lead `| Setting | Value |` table, tests, project-lead section
  "Apply dev-kit migrations" (on start before the status, silently after a plugin-update restart), README.
  dev-kit 0.1.44.
- Dry run on a throwaway local clone of Zhratva (job temp folder): `pending` listed entry 1, `record 1` added
  the table above the existing `| Path | How |` table, `pending` then printed `none`, `record 0` refused (exit 2).
- Lint 0 errors; 463 tests OK.
- Choices made in the C: the migration C's rule edits use edit-rules steps 1-2 and 5-6 (owner's yes to the entry
  is the approval, as in migrate-docs); entries applied in order, an owner-choice entry waits for P's answer.
  The plugin repo itself has no profile yet, so its lead's first check starts a migration C for entry 1.
- Paid spend: $0.
- After merging main (pult 0.1.5: Pult uses no other-repo-editor), the urgent all-project path in the skill
  now points to Pult starting a session in each project, not to other-repo-editor.
