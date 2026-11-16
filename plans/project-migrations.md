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
