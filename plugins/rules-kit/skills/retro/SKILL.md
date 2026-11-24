---
name: retro
description: Use when a background session named «Ретро: <project>» starts (the rules-kit SessionStart hook starts it with "/rules-kit:retro") to review the problems logged from this project's sessions and fix the gaps in the rules, skills, agents and docs that made agents err.
---

# Retro of session problems

The session runs in the background with no owner, in the main checkout of one project with a lead (a project whose
profile `.claude/dev-kit.md` has a `## project-lead` section). It never asks the owner and never uses
`AskUserQuestion`; it talks only to its lead, `P: <project>` (the repo folder name), by SendMessage that starts with one
kind word: `ГОТОВО` (done) and, while it still asks, `ПИТАННЯ` (an urgent item); dev-kit's `messages.md` defines the
kinds. Its input is `rules-kit items`: the new
findings (token problems first) and the item files of the rule sets the project reviews (`rules-kit sets` lists
every set and its reviewer). Every `rules-kit` command runs in the Bash tool (in
PowerShell it prints nothing); where Bash cannot run it, use `python -X utf8 <this plugin>/scripts/retro.py`
with the same arguments. The folder, the commands and the hooks that fill it: the docstring of `scripts/retro.py`.

## Scope

The retro catches every problem of agent work in this project, and only that:

- A cause in the project's own rules, docs or profile (an outdated doc that sends agents to the wrong file) is
  agent work: the retro fixes it here.
- A bug in the project's code (a flaky test, a crash) is not: it is recorded as a defect where the project's
  `dev-kit:documentation` says ("Where things go"), the item gets `status: handed`, and the retro stops there.
- A cause in a file of a rule set this project does not review (a plugin's rules, the owner's global rules
  `C:/Users/korov/.claude/` with chat style, another project's own rules) is handled by the retro of the project
  that reviews that set (`reviewed by` in the set's `rules-subscription.md`), so two projects never handle the
  same set: the item is moved there with `rules-kit add --set <set> --text "<item line>" --from <project>` and
  gets `status: handed`.

Spend findings (`long session`, `opus coder`, token spend and waste) are ordinary items, with the spend numbers as
their evidence.

## 1. Check every finding

First the parts with a sign: run `rules-kit parts` (the sessions since yesterday). For each packet
path it prints, one `rules-kit:part-reader` (model haiku) gets that path as its whole brief. An answer
`<set> | <file>:<line> | <why>` is recorded with `rules-kit add --set <set> --text "part reader: <file>:<line> |
<why> | <session and part from the printed line>" --packet <packet path>` (it adds the `sign-gap` line itself);
`not a rule` is dropped. Transcripts of parts with no packet are not read. Then run `items`.

One `rules-kit:rule-reviewer` (model sonnet) checks the new findings (in ClaudeDevKit not the `claude app` lines and the
added `claude app:` and `owner check` lines: step 4 hands them to the facts keeper); brief it to stop and report
after 30 minutes. Give
it the `items` output (the new findings and the list of existing cause keys), the transcripts folder
(`~/.claude/projects/<project folder>/`, a session's file is `<id>.jsonl`, the 8 hex characters in brackets after a
title are the start of the id, subagent files are in `<id>/subagents/`), this project's main checkout (its
`CLAUDE.md`, `.claude/`, docs and code), the plugin folder and the owner's global rules folder. Per finding it
returns:

- noise, already fixed (with the file and line of the fix) or real, with the transcript lines it read (a watcher an
  older lead re-armed by design, an expected failed test, an owner who was away, are noise);
- the cause key: an existing key when the cause is the same, else a new short kebab-case key;
- the cause kind: `no rule` (missing or unclear), `ignored rule` (the rule exists and is clear, agents did not
  follow it; `file:line` of the rule), `one-off` (random, no rule would have helped), `code bug`, `dev-kit rule`,
  `global rule` or `other project`;
- for `no rule`: the fix in one plain line, the exact edit with `file:line`, steps 1-2 of `rules-kit:edit-rules`
  done on it, and what the same edit removes or merges, so the rules do not grow; for `ignored rule`: another
  means (a hook, a check, a script), never a new wording;
- whether the fix is trivial: one place, a word or a sentence made clearer, with no clash; a fix about how
  sessions talk to the owner (his messages, his questions), a high-impact fix (a new step, a script, hook, agent
  or skill, a deleted rule), an edit of the owner's global rules, or one the reviewer is unsure about is never
  trivial;
- urgent or not: lost work, a critical token problem, blocked work, or one cause repeated the same day;
- for each item with a `- fix:` line: whether a session started after the fix date met the same situation, and
  how it went (`worked`, `did not work`, `not met yet`). Only sessions started after the fix count.

A line it marks unsure goes to a second reviewer before it counts.

## 2. Write the items

One file per cause in `items/<cause key>.md` of the set that owns the file at fault (the path `items` prints in
that set's heading; a cause that names no file of a set goes to the project's own set); a finding with an
existing key adds a sighting to that file instead of a new one. The file:

    # <plain name of the problem, at most 6 words>
    - status: waiting | trivial-fixed | fixed | disputed | urgent | worked | no-fix | handed
    - kind: <cause kind>
    - from: <project the finding came from>
    - seen: <YYYY-MM-DD> | <session title (id8)> | <the scan line or note>
    - fix: <YYYY-MM-DD> | <files> | <what was removed or merged> | trivial | owner
    - check: <YYYY-MM-DD> | worked | did not work | not met yet
    <Було / Це проблема, бо / Виправлення / Стане, one line each, in Ukrainian: the text the lead shows the owner>

A recurrence counts separate sessions or days: a lead and its own subagents are one session. Each `fix:` keeps the
`seen:` lines it rests on.

## 3. Decide each item

- Noise or already fixed: no item (a sighting of an already fixed item goes to its post-change check).
- `code bug`, `dev-kit rule`, `global rule`, `other project`: as "Scope" says.
- `one-off`, or a first sighting that is not urgent: `status: waiting`. A fix needs the same cause in a second
  session or on a second day.
- `no rule` seen again, trivial, and fewer than 5 trivial fixes in the last 7 days (`items` prints the count per set): fix
  it now (step 4), `status: trivial-fixed`. Over the cap it waits for next week.
- `ignored rule`, a fix that is not trivial, or anything about how sessions talk to the owner: `status: disputed`.
- Urgent: `status: urgent`, and send P at once one `ПИТАННЯ` per urgent item (the Було / Виправлення lines and the
  recommendation); P asks the owner. If P is not reachable, the item waits in its file: the lead's prompt hook shows
  it.
- Post-change check: `did not work` turns the item `disputed` (an ignored rule now, so not reworded again);
  `worked` closes it; `not met yet` changes nothing.
- In the ClaudeDevKit retro only: each plugin commit since the last review that changes agent behaviour
  (`git log --since=<the last review that items prints> -- plugins`) gets an item `check-<slug>` with `status: fixed` and its `fix:`
  line, so the same post-change check reads later sessions for it.

## 4. Apply the trivial fixes

Before the first edit, call `EnterWorktree` (name `retro-<YYYY-MM-DD>`): writes into the main checkout are blocked.
Each trivial fix goes through `rules-kit:edit-rules` steps 4-6 (the reviewer did steps 1-2; the trivial lane is
that skill's exception to step 3), and each removes or merges something as the reviewer named. In ClaudeDevKit,
bump the plugin version once for the whole run, with its release mark (`.claude/dev-kit.md`); the facts keeper's
edits go in the same commit and alone need no bump. Commit
in the worktree; the lead merges it. The owner sees every trivial fix in the weekly list, where any one is reverted
with one word.

In the ClaudeDevKit retro, after `EnterWorktree`, one `dev-kit:facts-keeper` (model sonnet) gets the `claude app`
lines (the scan routes them here from every project) and the added `claude app:` and `owner check` lines as
candidates and writes `plugins/dev-kit/claude-facts.md` in the worktree; it runs even when the run has no other
fix. Its brief also says "re-check", with `claude --version`, when a line reads `updated <old> -> <new>` or `weekly
re-check due`, or the file's `Last re-check:` line is `none yet`. The owner-only questions it returns replace the
body of the item `items/claude-facts-owner-check.md` (`status: disputed`, `kind: owner check`, its Було /
Виправлення lines one plain question per fact), so they reach the owner in P's weekly question; with none, the
item gets `status: fixed`.

## 5. Close

Run `rules-kit done --branch <branch>` (plain `rules-kit done` when nothing was committed): the weekly docs
session waits for that branch's merge, so it runs on the fixed rules. Then send P one `ГОТОВО` in 3 lines: state, result (fixes made, items for the owner,
urgent ones sent), what is needed (merge branch `<branch>`, or nothing to merge). The session then waits; P closes
it.

Why: owner, 2026-11-21 and 2026-11-22 (`docs/features/fix-agent-problems-in-the-retro.md` of the plugin repo): the retro fixes the problems of
each project in that project's context, not only the plugin's rules; fixes only causes that recur, not random
ones; reviews by itself and brings the owner only disputed, high-impact, urgent items and anything about how
sessions talk to him, plus a weekly list of trivial fixes. This replaces, for trivial fixes only, the 2026-11-19
decision that nothing reaches a rule without the owner's «так». Earlier history: the retro questions as Було /
Стане blocks (owner, 2026-11-19..21) are now the item's text the lead shows.
