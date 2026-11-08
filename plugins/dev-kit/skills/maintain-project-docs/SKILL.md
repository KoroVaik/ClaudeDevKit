---
name: maintain-project-docs
description: Use when the owner asks for documentation maintenance or a docs audit, not for routine documentation updates within a feature or bug fix.
---

# Maintain project docs

A strict periodic audit of the project docs against the documentation standard: rules kept in two homes,
features that describe a state the code no longer has, stale Known limits, tech files restating business
rules, finished Open items, backlog entries already built, finished plans, history in `PROGRESS.md`,
superseded findings, agents' leftovers in the repo.

The audit measures the docs against the `dev-kit:documentation` skill and the project's additions in
`docs/standards/documentation.md` (if it exists); read both first, they are the only statement of the
rules and this skill does not restate them. Apply the language and approval rules in the project's
`CLAUDE.md`. Read the profile section `## maintain-project-docs` of `.claude/dev-kit.md` if it exists; it
adds to these steps and overrides them. The audit may edit any docs, agent rules and skills, but only
after the owner's yes on the proposed list (step 3); it never changes code or data, a problem found there
is reported.

## 1. Mechanical part

Run `dev-kit-check-docs --pre-commit` and note
every error, warning and advisory line. Do not repeat by hand what it checks (links, anchors, paths,
epic and feature structure, sizes, unlisted code folders).

## 2. Judgment part

Inspect the working diff first and preserve concurrent edits; use bounded inventories, never a drive
root. For each point below list the exact file and passage.

- **Two homes.** A rule or fact written in more than one place: in two features, in a feature and an
  epic, in a feature and a standard, in `CLAUDE.md` or a skill instead of a link. Keep the home the
  standard names, turn the rest into links.
- **Files nothing links to.** A tech, feature, finding or plan file that no index or other file links to
  (list the files in each folder and grep for each name).
- **Features against the code.** Sample features (the most recently changed code, and the ones with the
  longest Rules) and check each rule and each "Built in" claim against the code. A feature that describes
  a state the code no longer has is rewritten; a decision the code does not follow is a Known limit.
- **Known limits.** One that came true is removed (and its rule corrected if needed); one that no longer
  describes the code is rewritten or removed.
- **Tech files.** A tech file that restates a business rule instead of linking to its feature, a
  `Why:` that belongs to a feature, a stale contract (sample against code).
- **Open items.** An item whose work is already done is removed; an item no one agreed is moved to
  `BACKLOG.md` or dropped after the owner's yes.
- **Backlog.** An entry is checked only for its format and for whether it is already built, a feature,
  an Open item or a plan. Never ask the owner about the future of an idea: the audit is about the docs,
  not about what to build next.
- **Plans.** A plan in `plans/` whose steps are all done is proposed for removal; a plan whose
  facts moved into features is trimmed.
- **Status.** `PROGRESS.md` holding history, a task diary, check evidence or decisions; open questions
  that the docs already answer; "next steps" that are done.
- **Findings.** A finding superseded by a newer result, or contradicted by the current code or pipeline,
  is edited or removed.
- **Names.** Terms in docs, skills and agent files that the glossary lists in "Do not say".
- **Leftovers.** Scratch files, logs, caches, run folders, one-off scripts and untracked files in the
  repo that the work no longer needs (`git status`, bounded folder listings). Durable data is never
  listed for deletion without saying so.

Sampling that needs reading many files goes to `dev-kit:reviewer` subagents on a cheaper model (sonnet), one
bounded set of files per call, each with the standard and the question to check; read the places they
name before putting a finding in the list. Subagents do not edit.

## 3. Propose, wait, edit

State a concrete change list: per item the file, the passage, the proposed change and why,
plus the success criterion (the "Before finishing" rule of the standard). Wait for the owner's
explicit yes before editing; a directly specified edit needs no repeat approval. Deleting a whole file
or discarding unique evidence needs its own explicit yes. Age alone does not prove a claim obsolete:
check it against the code or the evidence.

## 4. Verify and report

After the edits run the check of "Before finishing" in the standard and read the final diff for lost facts, a contradicted rule
or an unintended edit. Report which files changed, what was merged, moved or removed, what stays
uncertain, and the checks actually run. Do not claim a check, status or acceptance that was not run.
