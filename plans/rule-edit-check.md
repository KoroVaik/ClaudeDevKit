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

## Owner decision via P (2026-11-16)

«мені не треба дослівне правило, я апрувлю тіки ідею, щоб не читати полотна тексту які корисні агентам».
The owner sees each rule edit as one plain line on what will behave differently and says yes to that idea; the
exact wording goes to the owner only on request; the reviewer step also checks that the wording matches the
approved idea. Keep dev-kit consistent with the global `docs/process-mistakes.md`, which already says this.

## Work log

- Home: a new skill `dev-kit:edit-rules` (it must trigger from many places and for P's and the owner's own
  edits, so a section inside one skill would not load where needed).
- Dry-run case found: 7dc6468 added the stop-app rule to 5 skill files although `slots.md` already held it
  for all skills (duplicate); 1329358 reworded six of them and missed `README.md:159`, still stale at HEAD.
- Found on the way: project-lead's backlog flow says the `dev-kit:coder` commits, but `agents/coder.md` says
  it never commits (conflict). Fixed here: P commits.
- Paid spend: $0 (subagents only on the plan).
- Linked from: manager (size check, skill table, project's own rule files), documentation (Agent rules bullet),
  project-lead backlog flow (reviewer brief carries steps 1-2, P runs 5-6 and commits), maintain-project-docs,
  migrate-docs, coder and mechanical-editor agents. `README.md:159` stale stop-app line fixed.
- Dry run (blind sonnet investigator, steps 1-2 and 5 on 7dc6468 at its parent): found the stop-app sentence
  copied into four skills while `slots.md` holds it, the README restatement, and a web-kit browser-checks gap;
  verdict "yes, the procedure would have changed this commit". Its unclear points (missing files, unbounded
  read set, home tie-break, one idea line per behaviour) are fixed in the skill text.
- Review (sonnet reviewer): wrong Why-line fact, maintain-project-docs step 3 conflict, migrate-docs link
  missing, subagent cannot run a skill - all fixed. Left: stop-app wording still drifts slightly between
  manager, fix-bug, new-feature and slots.md (pre-existing, outside this task); settings deny lines in
  project-lead are shown with exact lines (config, not rule prose; left as is).
- Optional follow-up for P/owner: the global `docs/process-mistakes.md` could point to `dev-kit:edit-rules`
  once dev-kit is enabled in the home folder (global file, needs P's yes; not done).
