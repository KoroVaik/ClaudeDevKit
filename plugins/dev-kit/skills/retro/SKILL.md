---
name: retro
description: Use when a background session named «Ретро: <project>» starts (the dev-kit SessionStart hook starts it with "/dev-kit:retro") to review the problems logged from this project's sessions and fix the gaps in the rules, skills, agents and docs that made agents err.
---

# Retro of session problems

The session runs in the background with no owner, in the main checkout of one project with a lead (a project whose
profile `.claude/dev-kit.md` has a `## project-lead` section). It never asks the owner and never uses
`AskUserQuestion`; it talks only to its lead, `P: <project>` (the repo folder name), by SendMessage with the kind
words of `${CLAUDE_PLUGIN_ROOT}/messages.md`. Its input is `dev-kit-retro items` (if the command is not found,
`python -X utf8 <this plugin>/scripts/retro.py items`): the project's new findings (token problems first) and its
item files. The folder, the commands and the hooks that fill it: the docstring of `scripts/retro.py`.

## Scope

The retro catches every problem of agent work in this project, and only that:

- A cause in the project's own rules, docs or profile (an outdated doc that sends agents to the wrong file) is
  agent work: the retro fixes it here.
- A bug in the project's code (a flaky test, a crash) is not: it is recorded as a defect where the project's
  `dev-kit:documentation` says ("Where things go"), the item gets `status: handed`, and the retro stops there.
- A cause in a dev-kit plugin's rules, or in the owner's global rules (`C:/Users/korov/.claude/`, chat style
  included), is handled only by the ClaudeDevKit retro, so two projects never ask the owner the same thing: in
  any other project the item is moved there with `dev-kit-retro add --project ClaudeDevKit
  --text "<item line>" --from <project>` and gets `status: handed`.
- A cause in another project's own rules goes to that project the same way (rare).

Spend findings (`long session`, `opus coder`, token spend and waste) are ordinary items, with the spend numbers as
their evidence.

## 1. Check every finding

One `dev-kit:reviewer` (model sonnet) checks the new findings; brief it to stop and report after 30 minutes. Give
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
- for `no rule`: the fix in one plain line, the exact edit with `file:line`, steps 1-2 of `dev-kit:edit-rules`
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

One file per cause in `items/<cause key>.md` of the project's folder (the path `items` prints); a finding with an
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
- `no rule` seen again, trivial, and fewer than 5 trivial fixes in the last 7 days (`items` prints the count): fix
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
Each trivial fix goes through `dev-kit:edit-rules` steps 4-6 (the reviewer did steps 1-2; the trivial lane is
that skill's exception to step 3), and each removes or merges something as the reviewer named. In ClaudeDevKit,
bump the plugin version once for the whole run (one plugin update a day: every update restarts every lead). Commit
in the worktree; the lead merges it. The owner sees every trivial fix in the weekly list, where any one is reverted
with one word.

## 5. Close

Run `dev-kit-retro done --branch <branch>` (plain `dev-kit-retro done` when nothing was committed): the weekly docs
session waits for that branch's merge, so it runs on the fixed rules. Then send P one `ГОТОВО` in 3 lines: state, result (fixes made, items for the owner,
urgent ones sent), what is needed (merge branch `<branch>`, or nothing to merge). The session then waits; P closes
it.

Why: owner, 2026-11-21 and 2026-11-22 (`plans/retro-scope.md`, «Owner's approval»): the retro fixes the problems of
each project in that project's context, not only the plugin's rules; fixes only causes that recur, not random
ones; reviews by itself and brings the owner only disputed, high-impact, urgent items and anything about how
sessions talk to him, plus a weekly list of trivial fixes. This replaces, for trivial fixes only, the 2026-11-19
decision that nothing reaches a rule without the owner's «так». Earlier history: the retro questions as Було /
Стане blocks (owner, 2026-11-19..21) are now the item's text the lead shows.
