# Tidy the docs once a week

Epic: [Keep docs and tests in order](../epics/keep-docs-and-tests-in-order.md)

## Purpose
The docs of every project with a lead are audited against the documentation standard once a week by a background
session that fixes the trivial problems itself, leaves the rest as items and ends, so you answer only what is
really yours.

## Rules
### One run a week, on the freshly fixed rules
Once a week, after the project's retro session has ended and its branch is merged (or 48 hours after it), a
background session «Документація: <project>» runs `dev-kit:maintain-project-docs` in its weekly mode. With no retro
that week it starts on its own after 7 days. The SessionStart hook of the retro starts it; there is no Pult task
and no scheduled task. It runs for every project that has a lead.
Why: owner, 2026-11-22: run the docs upkeep after the retro, so it uses the updated rules, and by itself, not by hand.

### It ends and does not stay open
The session fixes trivial problems in a worktree, writes every other problem as an item file (local, in the
project's retro folder, one file per item with a status line) and ends with one report to P. Trivial means a docs
edit with no change of meaning; a change of a rule is never trivial there, so it bumps no plugin version. A run
that ended without recording itself is tried again once a day.
Why: owner, 2026-11-22: the session finishes and leaves the items open, to be fixed separately, so no session
stays open.

### Only the important items reach you
An item that changes a rule or the product description waits for your answer and joins the weekly retro question
(one question a week, not two). The other items P hands to one task session after the docs session reports. An item
already fixed or rejected is not reopened unless its passage changed.
Why: owner, 2026-11-22: only truly important items are brought up.

## Acceptance criteria
- A project with a lead has had a retro that is merged: within a day a «Документація:» session starts, fixes a wrong link and ends.
- A week passes with no retro: the docs session starts on its own.
- The session finds a rule that contradicts another: it writes an item for you and does not edit the rule.
- Your weekly question counts the retro items and the important docs items together.

## Built in
- `plugins/dev-kit/skills/maintain-project-docs/SKILL.md`
- `plugins/dev-kit/hooks/retro-start.py`
- `plugins/dev-kit/scripts/retro.py`
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `tools/tests/test_retro.py`
