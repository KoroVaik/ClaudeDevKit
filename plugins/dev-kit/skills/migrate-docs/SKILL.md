---
name: migrate-docs
description: Use when an existing project's docs must be moved onto the `dev-kit:documentation` standard - a project that newly adopts dev-kit, or the owner asks to migrate or restructure its docs, including a dry run.
---

# Migrate docs

Moves the docs of a project that already has some onto the layout of the `dev-kit:documentation`
standard, without losing a fact. The project's `CLAUDE.md` sets the language and approval rules. Read the
profile section `## migrate-docs` of `.claude/dev-kit.md` if it exists; it adds to these steps and
overrides them. The migration restructures docs and agent rules only; it never changes code or data.

A **dry run** stops after step 4 and changes nothing. A run is a dry run when the owner asks for one, or
when it is the first run: this skill has not migrated the project before (ask the owner if unsure). An
existing `## documentation` profile section does not make a run a full one. A dry run never blocks the
migration: the owner's explicit yes to its change list applies the list in the same or the next run, even
when the profile has no `## documentation` section yet.

## 1. Read the standard and take a baseline

Read the `dev-kit:documentation` skill whole: the kinds of content and their homes, "Names", "Rules of
upkeep", "Where things go", the feature file shape, the docs check. Then the project's `CLAUDE.md`, its
profile, and `docs/standards/documentation.md` if it exists. Run `git status` and note files with
others' uncommitted edits. Run `dev-kit-check-docs` once as the baseline and report its result (a dry
run reports it too).

## 2. Inventory

List every doc-like file with a bounded listing, never a drive root: `git ls-files` filtered to `*.md`
and other doc formats the project uses, or a glob inside the project folder. Include the root `*.md`,
`docs/` and any other documentation folder (wiki, notes, plans), every folder `CLAUDE.md`, every README
and operator reference, the agent rules (`CLAUDE.md`, `.claude/`), and the skills and agent files in
`.claude/`: they must not restate feature rules ("One home per fact"). Skip third-party skills the
project lists in `skills-lock.json`.

Per file note its size and what links to it. On a large repo do not read every file: find the
mechanical signs with grep passes (dates in headings, "archived", "(closed)", a feature without an
`Epic:` line, a rule written twice) and read whole only the files whose mapping needs judgment.

## 3. Map

Map each file, and each passage of a mixed file, to a kind of the standard and its home. One row per
file or passage: source, kind, target home, action - keep, move, split, merge, rename, link, trim to a
link, rewrite in place or delete.

- A file that holds several kinds is split; two files that hold the same fact are merged into the home
  the standard names, the rest are trimmed to a link ("One home per fact").
- A feature file takes the feature shape; a rule keeps its `Why:` line. Business rules go to features,
  how the code works to tech, layout and wording rules of the interface to the UI standard.
- A tool's README, command reference or threat model is the "Operator reference" kind and stays next
  to its code; rules a user would see link to their feature. If the standard has no kind that fits a
  file, list it with a question and propose a one-line addition to the standard's kinds table in the
  report; do not invent a kind here.
- Dates are allowed as evidence in findings and plans. Only dated logs and histories are deleted
  ("Current state only"), and a fact in one that still holds gets a home first.
- A kind the project has no source for (no glossary, no feature files, no product overview) is listed as
  missing for the owner. The migration does not invent it; a feature is written from the code as separate
  work the owner agrees.
- A passage that fits no kind is listed with a question, not guessed.
- Every removed or replaced passage names its new home in the list. A deletion with no new home needs a
  reason (an exact duplicate of a named passage, or history that git keeps) and **its own explicit
  yes**.

## 4. Write the change list and stop

Write the list to a file in the session scratchpad, not the repo: the rows of step 3 in the order of
application, the missing kinds, the questions, and the planned `## documentation` settings of the
profile (`scan` rows for the folders of code and agent files, `code-root` rows, `skip-dirs`, and the
other settings that `scripts/check_docs.py` of the plugin lists). If the profile already has a
`## documentation` table, compare each planned setting with it and list only the differences. In chat
give the file's full path, a short count per action (the actions of step 3) and one yes/no question for
applying the list. Each deletion row is not part of that yes: it is asked on its own in step 5. Stop. A
dry run ends here.

## 5. Apply, with the owner's yes

Before changing anything, require the touched files to be committed or clean in git (`git status` on
their paths), so that removed history stays in git; a project that is not under git is not migrated: stop
and tell the owner. Apply only the rows the owner agreed; a deletion row applies only with its own
explicit yes, asked per row or per named list of deletions. Work in this order so
links stay valid: renames and moves (`git mv`, to keep history), splits and merges, then the links and
the glossary, then the shape of epics and features (`Epic:` line, the four sections, the epic list in
`docs/product.md`), then the map and `docs/README.md` index. A row that touches a file with others'
uncommitted edits is applied last and separately, after the owner is told and has committed those
edits or agreed to go on. Write or extend the profile's
`## documentation` table with the planned settings.

## 6. Check

Run `dev-kit-check-docs` and fix until it reports 0 errors; answer every size warning (split the file,
or add a `size-ok` marker with its reason) and read the advisory lists. Then read the final diff against
the change list: every removed passage is found in its new home or its deletion was agreed. Report the
files changed, what was moved, split, merged and deleted, the missing kinds, what stays uncertain, and
the checks actually run. Do not claim a check that was not run. Commit as the project's rules say.
