---
name: retro
description: Use when the session was started by the ClaudeDevKit project lead as «Обговорення: Ретро сесій ...» to go through the logged problems of past sessions (extra or failed calls, slow steps, the owner's corrections, a wrong order of steps) and close the gaps they show in rules, skills and agents.
---

# Retro of session problems

The session talks with the owner directly, like an «Обговорення:» session (`dev-kit:project-lead`, "Retro of
session problems"), and runs in a worktree of ClaudeDevKit. Its input is the unreviewed findings of
`dev-kit-retro list` (if the command is not found, `python <this plugin>/scripts/retro.py list`): the lines of the
daily transcript scan and the lines sessions appended for what the scan cannot see (the owner's global
`docs/process-mistakes.md`), then the scan's spend tables (tokens in units, by session and by subagent). The rules
and output are the owner's: nothing changes without the owner's «так» to it.

## Token spend

Spend is evidence for a way of working, not a finding of its own: the goal is a better habit, not the biggest
spender. The scan's spend findings (`long session`, `opus coder`) go through the steps below like the others,
with the spend tables as their evidence. Each retro proposes at most 2 spend rules, each with its numbers, worded
in step 2 as a trial: «спробувати тиждень і порівняти». A trial the owner accepts gets one line in `trials.md` of
the findings folder (`~/.claude/dev-kit/retro/`): `- <YYYY-MM-DD> | <the rule> | <what to compare: the kind of work
and its units>`. A later retro, once 7 or more days have passed since a trial's date, first compares it against the
`## Spend` sections of the `scan-*.md` files of those days and of the week before (`list` shows only unreviewed
days) and asks the owner to keep or roll back the rule; the line then gets `| kept` or `| rolled back`. The numbers are shown only
in this session.

## 1. Check every finding

One `dev-kit:reviewer` (model sonnet) checks the whole list; brief it to stop and report after 30 minutes. Give it the
list, the transcripts folder (`~/.claude/projects/<project folder>/`, a session's file is `<id>.jsonl`, the 8 hex
characters in brackets after a title are the start of the id, subagent files are in `<id>/subagents/`), the plugin
folder and the owner's global rules folder (`C:/Users/korov/.claude/` with its `docs/`). Per finding it returns:

- real or noise, with the transcript lines it read (a watcher re-armed by design, an expected failed test, an owner
  who was away, are noise);
- the cause: which rule, skill or agent was missing, unclear or ignored, with `file:line`, or "no rule gap";
- the fix kind: a wording edit (which file), a script, hook or new agent, or nothing;
- the fix in one plain line;
- for a wording edit, steps 1-2 of `dev-kit:edit-rules` done on it: the read set swept and the duplicates,
  conflicts, restatements and home listed with `file:line`, so the owner's yes covers an edit with no clash.

Findings with one cause are merged into one item. A line it marks unsure goes to a second reviewer before the owner
sees it.

## 2. Ask the owner

Ask about each item as the owner's global rules say for a batch of yes/no questions: the problem and the fix in
plain words, the reviewer's recommendation, worded so that "так" agrees with it. Noise items are asked too, as one
batch question «Відкинути як шум: ...?». The owner answers «так» or «ні» to each.

## 3. Apply the yeses

- A wording edit of a plugin skill, agent or rule doc, the repo's `CLAUDE.md`, or the owner's global rules and docs:
  edit it in this session through `dev-kit:edit-rules`, steps 4-6 (the reviewer did steps 1-2, the owner's «так»
  here is step 3). The owner's
  global files are local, outside the repo, and are edited in place. Bump the plugin version once if a plugin
  changed.
- A script, a hook, a new agent or skill, or a change of the scan itself (`plugins/dev-kit/scripts/retro.py`, its
  thresholds included): an entry at the end of this repo's `BACKLOG.md` in the format of `dev-kit:manager`, "A change
  to the plugins themselves", plus the line `Verdict: owner yes in retro <YYYY-MM-DD>`, so P does not ask the owner
  again ("Plugin backlog" in `dev-kit:project-lead`); a separate session builds it.
- A gap in another project's own rules (its `CLAUDE.md` or `.claude/`): an entry in that project's `BACKLOG.md`
  through an `other-repo-editor` subagent (model haiku).

## 4. Close

Run `dev-kit-retro done`, so the findings `list` showed are not proposed again, even when the owner said «ні» to
all; findings added during the retro stay new. Commit, show the owner the short plan of what this retro
changed and added (`dev-kit:project-lead`, "Start an «Обговорення:» session", "Short plan"), and only after the
owner's «так» to it send P a done report by SendMessage (what was edited, the backlog entries added); P merges the branch as any
session's work.

Why: the owner decided on 2026-11-19 that sessions' problems are logged and reviewed daily, and that nothing reaches
a rule or the backlog without the owner's «так» in a retro session; the same day, that token spend is counted in
units with no dollars (a subscription) and serves only as evidence for trial rules (plans/retro-tokens.md).
