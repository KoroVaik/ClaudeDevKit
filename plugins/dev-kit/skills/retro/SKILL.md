---
name: retro
description: Use when the session was started by the ClaudeDevKit project lead as «Обговорення: Ретро сесій ...» (or the project lead runs it in its own chat for 1-2 simple findings) to go through the logged problems of past sessions (extra or failed calls, slow steps, the owner's corrections, a wrong order of steps) and close the gaps they show in rules, skills and agents.
---

# Retro of session problems

The session talks with the owner directly, like an «Обговорення:» session (`dev-kit:project-lead`, "Retro of
session problems"), and runs in a worktree of ClaudeDevKit. With 1-2 simple findings there is no session: P
runs the retro in its own chat (its step 4 is only the commit and `dev-kit-retro done`); the flow is in
`dev-kit:project-lead`, "Retro of session problems". Its input is the unreviewed findings of
`dev-kit-retro list` (if the command is not found, `python <this plugin>/scripts/retro.py list`): first the section
"Priority: token problems", read first, then the lines of the
daily transcript scan and the lines sessions appended for what the scan cannot see (the owner's global
`docs/process-mistakes.md`), then the scan's spend tables (tokens in units, by session and by subagent). The
reviewer puts the priority findings first in its list, and the owner is asked about them before any other item
(why: the owner's yes of 2026-11-20 to the plan «Pult idle cost»: token waste went unseen for days). The rules
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

One `dev-kit:reviewer` (model sonnet) checks the whole list (when P's first prompt carries its gate reviewer's
result, only the findings added since); brief it to stop and report after 30 minutes. Give it the
list, the transcripts folder (`~/.claude/projects/<project folder>/`, a session's file is `<id>.jsonl`, the 8 hex
characters in brackets after a title are the start of the id, subagent files are in `<id>/subagents/`), the plugin
folder and the owner's global rules folder (`C:/Users/korov/.claude/` with its `docs/`). Per finding it returns:

- real, noise, already fixed (with the file and line of the fix) or handed over (another session or talk took it,
  as P or the owner said in this session), with the transcript lines it read (a watcher an older lead
  re-armed by design, an expected failed test, an owner who was away, are noise);
- the cause: which rule, skill or agent was missing, unclear or ignored, with `file:line`, or "no rule gap";
- the fix kind: a wording edit (which file), a script, hook or new agent, or nothing;
- one concrete example of what the agent did, in the owner's words (what he saw in the session), and what it led
  to or would have led to for him, and why that is a problem; the fix: what changes in the rules, in one plain
  line, and the same moment as it will look after the fix;
- for a wording edit, steps 1-2 of `dev-kit:edit-rules` done on it: the read set swept and the duplicates,
  conflicts, restatements and home listed with `file:line`, so the owner's yes covers an edit with no clash.

Findings with one cause are merged into one item. A line it marks unsure goes to a second reviewer before the owner
sees it.

## 2. Ask the owner

This step names itself as an exception to the owner's global "Question" cap (15 words plus a 6-word bracket
example) and "Batches of questions" format: a retro item needs its context. The rest of the global "Chat replies"
rules hold: Ukrainian, plain words, no file or rule names.

One real item per message, in the order of the reviewer's list; the next one only after the owner answers. Plain
labels with no bold:

    Проблема: <plain name of the problem, at most 6 words>
    Було: <one concrete moment from a session the owner can picture: what the agent did or wrote>
    Це проблема, бо: <what it led to or would have led to for the owner, one sentence>
    Виправлення: <what changes in the rules, in plain words, one sentence>
    Стане: <the same moment as it will look after the fix, as an example>
    <the question, at most 15 words, worded so that «так» agrees with it>
    Рекомендую: так - <reason, at most 12 words>

Було and Стане never lean on names or context the owner may not hold (another project, a session, a file): say in
plain words what happened. A spend item gets its numbers in Було, and its Виправлення is worded as the trial
«спробувати тиждень і порівняти» (see "Token spend"). Noise, findings the reviewer marks already fixed and findings
handed over are not asked: the message of the last real item opens with one line «Ще N знахідок - шум або вже
виправлене» (and «M передано в окреме обговорення» when there are any) and «подробиці покажу, якщо попросиш»,
so its question stays last; with no real item, the whole message is «Нових проблем у правилах немає.» and that line.

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
owner's «так» to it, and only if no owner message came after that «так», send P a done report by SendMessage (what was edited, the backlog entries added); P merges the branch as any
session's work.

Why: the owner decided on 2026-11-19 that sessions' problems are logged and reviewed daily, and that nothing reaches
a rule or the backlog without the owner's «так» in a retro session; the same day, that token spend is counted in
units with no dollars (a subscription) and serves only as evidence for trial rules (plans/retro-tokens.md). On the same
day the retro questions became Було/Стане blocks under headings (owner: «питання в стилі було - стало»), because
two-sentence batch items gave no context. On 2026-11-20 the owner asked for one item per message with Проблема, Було,
Це проблема, бо, Виправлення and Стане (an example), and for noise and fixed findings to be one line, not a question
(owner: «А нащо мені вже виправлені?», «Я маю розуміти про що ця проблема»). The in-chat variant for 1-2
simple findings (2026-11-20): `dev-kit:project-lead`, "Retro of session problems".
