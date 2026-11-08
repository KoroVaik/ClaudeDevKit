---
name: documentation
description: Use when you write, change or check project documentation (product, epics, features, standards, tech, map, status, backlog, plans), when a task changes behaviour a doc describes, or before finishing a task that touches code or docs.
---

# Documentation standard

How the docs are kept: what kinds of content exist, where each lives, who may change it and what the
docs check enforces. Agents follow it after every change; a project's `CLAUDE.md` links here instead of
restating it.

Goal: docs stay short and show only the current picture, and an agent finds the context of the part it
works in. Every piece of knowledge has exactly one home, no rule is written in two places, and nothing
describes a state that is gone.

**Project additions.** A project keeps its own additions (naming language, project-specific routing) in
`docs/standards/documentation.md`; read it first if it exists. Its rules add to this skill.

## Kinds of content

| Kind | What it answers | Who changes it | Home |
| --- | --- | --- | --- |
| Product overview | The problem, the purpose, the principles; the list of epics | Owner approves | `docs/product.md` |
| Epic | What a big part of the product gives the users and why; its features | Owner approves | `docs/epics/<name>.md` |
| Feature | What the user gets, the rules, acceptance criteria; links to tech and mockups | Owner approves | `docs/features/<name>.md` |
| Standard | How everything is built: engineering, UI design, test rules, these docs | Owner approves | `docs/standards/<name>.md` |
| Tech | How it is built now: contracts, data, processes, traps; a `Why:` line next to a deliberate technical choice | Agents, with the code | `docs/tech/<area>.md` |
| Map | The top level only: one line per process, code folder and data store, linking down | Agents, with the code | `docs/tech/map.md` |
| Folder rules | Commands and traps of one code folder; a pointer to the reverse index. Never a list of the folder's contents | Agents, with the code | `<folder>/CLAUDE.md`, loaded by Claude Code when it works in that folder |
| Operator reference | How to run and operate one tool or script: commands, parameters, threat model; rules a user sees link to their feature | Agents, with the code | `<folder>/README.md` next to the code |
| Finding | A measured fact (models, cost, performance, executors), with evidence | Agents, with evidence | `docs/findings/<topic>.md` |
| Glossary | One name per concept | Owner approves | `docs/glossary.md` |
| Status | What is built, in flight, blocked; the few top priorities, linking to their Open items | Agents | `PROGRESS.md` |
| Open question | A question waiting for the owner's answer | Agents record, owner answers | `PROGRESS.md`, section "Open questions" |
| Open item | Agreed work not started yet, or a defect found on the way | Owner approves a task; agents record a defect | Section "Open" of the feature or tech file the work belongs to |
| Backlog | Ideas not agreed: 2-4 lines each, what, why and the cheapest test | Owner approves | `BACKLOG.md` |
| Plan | Agreed work in flight, removed when done | Owner approves | `plans/<name>.md` |
| Agent rules | How agents work in this repo | Owner approves | `CLAUDE.md`, `.claude/` |

Mockups are design assets under `docs/mockups/`, linked from features. The index of the docs is
`docs/README.md`; it holds no rules.

## Names

An epic or a feature is named by the action and its object as the user sees them. A feature name is not
a page or screen name: the page keeps its own name in the glossary, while the feature is named by what
the user does with it. A name enters the glossary when its feature or epic file is written. Chat, docs,
skills, agent files and UI text use glossary names only, never a synonym from the "Do not say" column; a
concept without an entry gets a name proposed to the owner and is added after the owner's yes.

Content that is not a feature goes elsewhere: layout, language and navigation rules of the interface
in the UI design standard, platform rules in the engineering standard, product principles in
`docs/product.md`.

## Rules of upkeep

- **One home per fact.** Other files link to it. `CLAUDE.md` and skills link to standards and features
  instead of restating them; a skill is an executor and does not restate its feature's rules. The map
  is the only hand-written list of code folders.
- **A shared rule lives where it is enforced.** A rule that several features depend on (for example "an
  order needs a selected delivery address") lives in the feature that enforces it; the others link to it.
- **Feature or tech.** How the user sees and uses something (layout, sizes, wording) is a feature rule;
  how the code does it is tech.
- **Current state only.** Every file is rewritten in place and shows only the current state; git keeps
  the history. There is no closed or archived state and no dated log of passes or fixes: a removed
  feature, plan, idea or finished Open item is deleted. An accepted rule that changes an earlier one
  edits that entry; a cancelled rule is removed.
- **Why.** The reason for a deliberate choice is a `Why:` line next to it, so a later agent does not
  undo it. A technical choice has the line in the tech file; a business rule has it in its feature.
  There is no Decisions section.
- **Radical change.** Whether a feature change is radical is the owner's call; the agent asks and then
  rewrites the file.
- **Check with the code.** An agent runs `dev-kit-check-docs --who <path>` before editing code, to find
  the features that list the path, and updates the feature, its epic and the tech files after the
  change when their description became incorrect or incomplete.
- **What to document.** Choose by the consequences needed for future work, not by the type of change or
  the number of changed lines. This also governs the outcome-recording steps of task skills; separate
  decision and audit requirements stay in force.
- **Before finishing.** Run `dev-kit-check-docs --pre-commit`: it must report 0 errors, and every size
  warning must be answered (split the file, or add a `size-ok` marker with its reason, see "Docs
  check"). Read the advisory lists: a feature that lists a changed file is updated or confirmed
  unchanged.
- **Review.** When feature rules are added, removed or rewritten, `dev-kit:reviewer`, model sonnet,
  checks the file: glossary names, no contradiction with other features, the epic or the standards, no
  technical detail, nothing stale. Small wording fixes need no review.

Tech files follow the code. When interdependent parts share code (two frontends, an API and a worker),
one shared tech file holds what they share and one file per part holds what belongs only to it; a change
is recorded where its code lives.

### Where things go

- **Accepted product rule:** recorded when the owner accepts it, in the feature, epic or standard it
  belongs to (or `docs/product.md`), as a `###` rule with a meaningful name, no number and no date.
- **Outcome of a task:** the result (what changed, the checks actually run, the remaining work) goes to
  chat and the commit. `PROGRESS.md` gets one consolidated line only when capabilities, stage readiness,
  blockers, risks or next steps change. A task that stops unfinished leaves one short handoff there,
  replaced by the outcome when the task is done. `PROGRESS.md` holds no history, no decision log and no
  experiment journal.
- **Open question:** a question that waits for the owner goes to "Open questions" in `PROGRESS.md` and
  links its feature. Before recording it, read that feature and the plan it links: a question they
  already answer is not recorded. It is closed only when the owner's answer settles it.
- **Open item:** agreed work not started goes to the "Open" section of its feature or tech file as a
  `[ ]` item. Out-of-scope work that surfaced is proposed in chat and added only after the owner agrees.
  An item is ticked `[x]` only for what was actually run and checked, and removed once finished; never
  create an item just to tick it.
- **Defect:** an agent that finds something broken outside its task records
  `- [ ] Defect: <what goes wrong>; <where in code or screen>` in the "Open" section of the feature (or
  tech file) of that code and goes on with its task. A defect is a fact, so it needs no owner yes (a task
  does). It is taken from `dev-kit-check-docs --open --defects` by the bug-fix flow and its line is
  deleted when fixed.
- **Plan:** `plans/<name>.md` records the agreed design and steps of work in flight. A finished step is
  marked done, progress notes go to chat, and the plan is deleted when the work is done.
- **Idea:** an idea the owner has not agreed goes to `BACKLOG.md`. It leaves when the owner agrees it
  (it becomes a feature, an Open item or a plan) or drops it. A brainstorming session ends with new
  entries there; its working file, if any, is deleted once the surviving ideas are in the backlog.
- **Finding:** durable conclusions of research (model behaviour, executor comparisons, cost and
  performance measurements) go to `docs/findings/`, one file per topic, never to `PROGRESS.md`. A
  finding states the claim, its evidence (date, numbers, run folder) and its consequence; a new result
  edits the finding in place and a disproved one is removed.
- **Chat and commit only:** intermediate attempts, hypotheses, changing results, check results with
  their evidence (commands, counts, sizes, dates) and skipped, declined or not-yet-run checks (including
  checks awaiting the owner's consent) are never written to docs. Isolated experiments are reported in
  chat with the existing tool's required evidence; they need no status update, architecture note or new
  journal unless the owner asks or accepts a product rule to record. Mandatory audit journals and raw
  evidence remain separate from docs.
- **No documentation needed:** a change that makes no description incorrect or incomplete is recorded in
  chat and the commit only, unless the owner asks for documentation. An icon move may need only a
  commit; a changed startup command needs corrected instructions; a one-line fix to an important risk
  may need a `PROGRESS.md` update.

## Feature file

```markdown
# <Feature name from the glossary>

Epic: <link>

## Purpose
Two or three lines: what the feature gives the users.

## Rules
### <Rule name>
Current rule only.
Why: optional, one line - the reason, so a later agent does not undo a deliberate choice.

Known limits: optional, one line - what the feature deliberately does not do yet.

## Acceptance criteria
3-7 lines: the user does X and sees Y, naming the rules they check instead of restating them.
Used by the test and scenario-check steps.

## Built in
Code paths (files, folders or globs), tables, links to tech sections and mockups.
```

A feature describes what the product does today, read from the code. A decision the code does not follow
is a `Known limits:` line; reworking the feature is separate work the owner agrees first. An epic has a
`Part of the [product]` line and a "Features" list linking each of its features; every feature belongs
to exactly one epic.

## Docs check

`dev-kit-check-docs`, run by the pre-commit hook (`--pre-commit`) and on demand. Without flags it runs
the full check. Its project specifics (code folders, folders to scan, size limits) live in the project
profile `.claude/dev-kit.md`, section `## documentation`, a `| Setting | Value |` table.

- every epic is listed in `docs/product.md`, every feature is linked from exactly one epic;
- every feature has the `Epic:` line and the four sections;
- every link and every `docs/...` path resolves, including heading anchors, in `docs/`, the root
  `*.md` files and the folders the profile's `scan` rows name, such as `.claude/` or code folders
  (code comments included);
- every path, folder or glob in "Built in" and the map matches at least one existing path.

The reverse index (code path to features) is built on demand from the "Built in" sections and never
committed: `--who <path>` resolves by the longest matching prefix and may name several features. In
pre-commit it is advisory: for staged code files it prints "feature X lists this path: did its rules
change?", and it lists code folders that no feature or map line mentions. It does not check whether a
feature was edited together with code: that check would raise false alarms and invite cosmetic edits.
`--open` lists all Open items across the docs and plans as two groups, tasks then defects, each grouped
by code area (the "Built in" paths of a feature, the code paths named at the top of a tech file, else
`docs`), so one agent can take all items of one area; `--open --defects` lists only defects and
`--by-file` groups by file. Generated on demand and never committed.

Size warning, never a block: a feature file over about 200 lines gets two questions. Is this one
feature (a part that can change without reading the rest and has its own acceptance criteria is a
separate feature of the same epic)? Is everything here a business rule (executors, formats and
commands belong in tech)? If both answers are yes, the file may stay long: a
`<!-- size-ok: <reason> -->` marker records the answer and silences the warning for that file. Tech
files get the same warning; the map has its own, lower limit.

A plan or another file that names planned or removed paths on purpose carries
`<!-- docs-check: no-path-mentions -->` to skip the mentioned-path rule.
