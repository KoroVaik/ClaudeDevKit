# Checked rule edits as part of the dev-kit workflow

## Owner's words (2026-11-16)

Via Pult (quoted by Pult): «передай цю інфу керівнику того проекта, такий скіл треба в любом випадку».
To P: «схожк не вірно та сесія мене поняла. Це має бути частиной воркфлоу дев кіта гадаю»;
«та сесія мала вказати що в планах підключити дев кіт» (Pult will enable dev-kit in the home folder).
Owner's «так» to «Запустити нову сесію «C: Перевірка правок у правилах»? (правки правил без дублікатів і
суперечностей)».

## Pult's request (summary of its message)

No dev-kit part edits rule text (CLAUDE.md, rule docs, skills, agent files, infra notes) with conflict and
duplicate checks. Closest today: agents/reviewer.md (generic review), agents/mechanical-editor.md (applies
worded edits), maintain-project-docs (periodic audit), documentation + dev-kit-check-docs (doc layout only).
Process-mistake fixes to a project's own rules are not covered either.
Wanted, for every rule edit: read the target and every rule file that loads with it or that it points to;
list duplicates (extend the existing rule instead), conflicts (which wins, or stop and ask) and the narrowest
home for the rule; make the smallest edit; re-check the section, paths and pointers (for notes: index line and
note agree); then the reviewer agent checks the result.

## Decisions

- Part of the dev-kit workflow, not a standalone skill and not a copy for Pult. Pult gets it when dev-kit is
  enabled in the home folder.
- It must trigger whenever a task, a bug fix, a process-mistake fix, a backlog entry or P's own rule edit
  changes rule text (CLAUDE.md files, rule docs, skills, agents, the owner's global docs).

## Success criterion

- The step exists in dev-kit (its own skill or a section of an existing one, the C decides) and is linked
  from every place that edits rules (manager, documentation, project-lead backlog flow, the coder/editor
  agents' briefs if needed).
- One dry run on a real earlier rule edit from this repo's history shows it would catch a duplicate or a
  conflict.
- Lint passes; dev-kit version bumped.
