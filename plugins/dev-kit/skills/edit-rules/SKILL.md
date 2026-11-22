---
name: edit-rules
description: Use when rule text is about to change - a `CLAUDE.md`, `.claude/` rules or the dev-kit profile, a skill, an agent file, `slots.md`, a rule doc, the owner's global rules and docs, or a memory or infra note and its index line - whether the edit comes from a task, a bug fix, a process-mistake fix, a backlog entry or the owner's own request.
---

# Edit rules

Rules are read by agents that load several rule files at once. A rule written twice drifts, and two rules
that disagree make the agent pick one at random. This skill keeps every rule edit to one home and no clash.
It does not change who approves an edit: agent rules still need the owner's yes ("Agent rules" in
`dev-kit:documentation`). Feature rules in product docs follow that skill's "Review" instead.

The session that owns the edit runs the steps (the manager, P, a C or a «Ретро:» session); a subagent cannot run a skill. A
`dev-kit:coder` or `dev-kit:mechanical-editor` may apply the edit from a brief that carries the step-3 list.

## 1. Read set

Read the target file whole, then, in every rule file that loads with it or that it points to (those that
exist), the parts on the same topic:

- a skill: the project's `CLAUDE.md`, the profile `.claude/dev-kit.md`, `slots.md`, the skills that route to it
  and the skills and agents it hands work to;
- an agent file: the skills that brief it and the profile section for it;
- a `CLAUDE.md` or the owner's global rules: the files it says to read before an action;
- a memory or infra note: its index line and the notes it links.

Then Grep the key words of the new rule (and of the old wording, for a change) across the whole rule set:
plugins, `CLAUDE.md` files, `README.md`, the profile. A user-facing doc that restates a rule counts. Over
about 100 lines in total, a `dev-kit:reviewer` (sonnet) does this sweep and returns the places with
`file:line`.

## 2. Find

List, with `file:line`:

- **Duplicates**: the same instruction already written elsewhere. Extend or reword that rule in its home;
  never add a second copy.
- **Conflicts**: a rule that cannot hold together with the new one, or names a different doer or moment.
  Where a rule already says which wins (the owner's global rules, a profile over a plugin default), write
  the new rule as a named exception to the one it overrides. Otherwise stop and ask the owner (a C asks P).
- **Restatements**: other files that repeat the old wording; they change with it or become a link.
- **Home**: the narrowest file that loads for every reader that needs the rule - one skill step before a
  skill's general section, a skill before `slots.md` or a shared doc, those before `CLAUDE.md`, the owner's
  global rules only for a ban that must hold at once. A rule several skills need lives in the shared file
  they all load; the skills link to it.

## 3. Propose

Show the owner one plain line per change of behaviour (not per file) on what will behave differently. The owner approves the
idea; the exact wording goes to the owner only on request (owner, 2026-11-16: «я апрувлю тіки ідею»). A
duplicate or conflict that changes the idea (a rule moved, another rule given way) is part of that line.
The full list with the wording stays in the task file or a scratchpad for the agents.

Exception: a trivial fix of a «Ретро:» session skips this step; the owner sees it afterwards in the weekly
list and may revert it (`dev-kit:retro`, steps 3-4, which also say what counts as trivial).

## 4. Edit

Make the smallest edit in the chosen home: reword an existing sentence before adding one, and replace
restatements with a link. Keep the target's conventions (a `Why:` line for an owner decision, its
language, no em dash). A typo or broken link with no change of meaning skips step 3 and the review.

## 5. Re-check

- Re-read every changed section whole.
- Every path, skill, agent and section the edit names exists (Grep).
- Grep the old wording again: no restatement is left behind.
- A note and its index line say the same thing.
- Run the repo's lint or docs check if it has one (`python -X utf8 tools/lint.py` in the plugin repo).

## 6. Review

A `dev-kit:reviewer` (sonnet) gets the diff, the read set, the step-2 list and the approved idea line. It
checks for a duplicate, a conflict or a stale restatement left, a broken pointer, and wording that says
more, less or other than the approved idea. Fix its confirmed findings; a change of the idea goes back to
step 3.

After the review, an edit of the owner's global rules (`CLAUDE.md` and `docs/` in the owner's `.claude`
folder) is committed in that folder's local git repo, when it is one (no remote, no push), with the
reason in the message: the incident or the owner's decision and its date. Why: owner, 2026-11-20 (plugin
backlog): nobody could say why five global rules exist, since the folder kept no history.

Why: on 2026-11-10 one commit wrote the stop-app rule into four skills, `slots.md` and `README.md`, although
`slots.md` holds it for every skill; the next rewording missed the `README.md` copy, which then contradicted it. The owner asked on
2026-11-16 for every rule edit to be checked this way as part of the dev-kit workflow.
