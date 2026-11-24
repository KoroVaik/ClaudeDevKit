---
name: retro
description: Use when a background session named «Ретро: <project>» starts (the rules-kit SessionStart hook starts it with "/rules-kit:retro") to review the problems logged from this project's sessions, fix the rules behind them through an approver and a replay, check earlier fixes and revert the ones that did not work, all with no owner ask.
---

# Retro of session problems

The session runs in the background with no owner, in the main checkout of one project with a lead. It asks the owner
nothing and never uses `AskUserQuestion`: an approver agent and a replay on past sessions replace his yes, and Pult's
«статус» shows what it did (`rules-kit list`). It sends its lead, `P: <project>`, one SendMessage at the end:
`ГОТОВО` (dev-kit's `messages.md`). Every `rules-kit` command runs in the Bash tool (in PowerShell it prints
nothing); where Bash cannot run it, use `python -X utf8 <this plugin>/scripts/retro.py` with the same arguments. The
folders, the commands and the item lines: the docstrings of `scripts/retro.py` and `scripts/fixes.py`.

Spend cap: before step 1 and before each fix run `rules-kit budget --session-id <this session's id>` (env
`CLAUDE_CODE_SESSION_ID`); on `over` go to step 6 at once and leave the rest for the next run.

## Scope

The retro catches every problem of agent work in this project, and only that (the scan already drops the findings
of «Ретро:» and «Документація:» sessions):
- A cause in the files of a rule set this project reviews (`rules-kit items` lists them) is fixed here.
- A bug in the project's code (a flaky test, a crash) is recorded as a defect where the project's
  `dev-kit:documentation` says ("Where things go"); the item gets `status: handed`.
- A cause in a set another project reviews (`reviewed by` in its `rules-subscription.md`) is moved there with
  `rules-kit add --set <set> --text "<item line>" --from <project>`; the item gets `status: handed`.
- A file with a special editor (`special editor` in the subscription) is never edited here: its findings go to it.

Spend findings (`long session`, `opus coder`, token spend and waste) are ordinary items, with the numbers as evidence.

## 1. Check every finding

Run `rules-kit parts`. For each packet path it prints, one `rules-kit:part-reader` (model haiku) gets that path as
its whole brief. An answer `<set> | <file>:<line> | <why>` is recorded with `rules-kit add --set <set> --text "part
reader: <file>:<line> | <why> | <session and part from the printed line>" --packet <packet path>`; `not a rule` is
dropped. Then run `rules-kit items` (it also expires one-offs, lists revert requests and marks `possible breakage`)
and `rules-kit check` (the fixed items, whether each reached main, and the sessions started after that).

One `rules-kit:rule-reviewer` (model sonnet) checks the new findings and the `check` output (in ClaudeDevKit not the
`claude app` and `owner check` lines: step 4 hands them to the facts keeper); brief it to stop and report after 30
minutes. Give it both outputs, the transcripts folder (`~/.claude/projects/<project folder>/`, a session's file is
`<id>.jsonl`, the 8 hex characters in brackets after a title start the id, subagent files are in
`<id>/subagents/`), this project's main checkout, the plugin folder and the owner's global rules folder. Per finding:
- noise, already fixed (with the `file:line` of the fix) or real, with the transcript lines it read (a watcher an
  older lead re-armed by design, an expected failed test, an owner who was away, are noise);
- the cause key: an existing key when the cause is the same, else a new short kebab-case key;
- the cause kind: `no rule`, `ignored rule` (with the rule's `file:line`), `one-off`, `code bug`, `sign-gap` or
  `other set`;
- the fix: one plain line, the exact edit with `file:line`, steps 1-2 of `rules-kit:edit-rules` done on it, and what
  it removes or merges so the rules do not grow; for `ignored rule` another means (a hook, a check, a script);
- urgent or not: lost work, a critical token problem, blocked work, or one cause repeated the same day;
- per fixed item of `check`: `worked`, `did not work` or `not met yet`, from the listed sessions only; per
  `possible breakage: <key>` line: whether fix `<key>` caused it.

A line it marks unsure goes to a second reviewer before it counts.

## 2. Write the items

One file per cause, `items/<cause key>.md` of the set that owns the file at fault (the path `items` prints; a cause
that names no file of a set goes to the project's own set); a known key adds a `seen:` line instead:

    # <plain name of the problem in Ukrainian, at most 6 words; the done list quotes it>
    - status: waiting | fixed | worked | reverted | second-try | parked | expired | rejected | handed | no-fix
    - kind: <cause kind>
    - from: <project the finding came from>
    - seen: <YYYY-MM-DD> | <session title (id8)> | <the finding line, its part and lines kept>
    <the cause and the planned fix with `file:line`, two lines>

The `fix:`, `revert:` and `mark:` lines are written only by `rules-kit fixed`, `revert` and `mark`. A recurrence
counts separate sessions or days: a lead and its own subagents are one session.

## 3. Decide each item

- Noise or already fixed: no item. `code bug` and `other set`: as "Scope" says.
- `one-off`, or a first sighting that is not urgent: `status: waiting`; it expires by itself after 14 days.
- Seen in a second session or on a second day, or urgent: fix it now (step 4), while `items` shows fewer than 5
  landed fixes for its set this week; an urgent one also over the cap.
- `ignored rule`: its fix is a hook, script or check, never a new wording: a `task: <what to build and why>` line for
  the closing `ГОТОВО`, then `rules-kit mark --item <key> --status handed --note "<task>"`.
- `sign-gap`: the fix is a new row in that set's Signs table, through step 4 like any fix (`fixed --sign`).
- `check` verdicts: `worked` -> `rules-kit mark --item <key> --status worked`; `did not work`, or a breakage the
  reviewer lays to that fix -> step 5; `not met yet` changes nothing.
- A revert request `items` lists -> step 5 at once, with no check.
- In ClaudeDevKit only: each plugin commit since the last review that changes agent behaviour (`git log
  --since=<last review> -- plugins`) gets an item `check-<slug>` with `status: fixed` and a hand-written line `- fix:
  <date> | <set> | <hash> | <files> | plugin commit`; the check reads later sessions for it the same way, and its
  `did not work` becomes a new finding, never a revert of another session's work.

## 4. Fix through the gates

Before the first edit call `EnterWorktree` (name `retro-<YYYY-MM-DD>`): writes into the main checkout are blocked.
A fix of the owner's global set is made in that folder (`C:/Users/korov/.claude/`, its own git repo) instead. Each
fix, one at a time:
1. Edit through `rules-kit:edit-rules` steps 4-5 (the reviewer did steps 1-2; steps 3 and 6 are replaced by the
   gates below): the smallest edit, removing or merging what the reviewer named.
2. Approve: one `rules-kit:approver` (model opus) gets the item file, the diff (`git diff`), the set's
   `rules-subscription.md` and the read set. `reject: <why>` -> undo the edit (`git checkout -- <files>`) and
   `rules-kit mark --item <key> --status rejected --note "<why>"`.
3. Replay: `rules-kit replay --item <key> --file <each edited file>`; one `rules-kit:replayer` (model sonnet) per
   printed packet gets the old and the new rule text, the packet path and its role. It lands only when every problem
   part answers `covers` and no good part `breaks`; no problem part found, or any other answer -> undo and mark
   `rejected` as above.
4. Commit it alone (`retro-fix: <set> <key>`), so a revert is one `git revert`; then `rules-kit fixed --item <key>
   --commit <hash> --what "<what it removed or merged>"` (add `--sign` for a Signs row).

After the last fix, each changed plugin gets one version bump (`.claude-plugin/plugin.json`) with a routine release
mark in its own `releases.json` (the format of `plugins/dev-kit/releases.json`; create the file when missing), in one
commit. A project set lands by its lead's merge; the global set's commits stay in its folder, with no push.

In the ClaudeDevKit retro, one `dev-kit:facts-keeper` (model sonnet) gets the `claude app` lines and the added
`claude app:` and `owner check` lines as candidates and writes `plugins/dev-kit/claude-facts.md` in the worktree,
even when the run has no other fix; its brief also says "re-check", with `claude --version`, when a line reads
`updated <old> -> <new>` or `weekly re-check due`, or the file's `Last re-check:` line is `none yet`. Its edits are
one commit and alone need no bump. The owner-only questions it returns are not asked: they replace the body of
`items/claude-facts-owner-check.md`, then `rules-kit mark --item claude-facts-owner-check --status parked`.

## 5. Revert and the second try

`rules-kit revert --item <key>` in the worktree (for the global set it reverts in that folder). Status `reverted`:
one second try by other means, through step 4 again when it is rule text; a hook, script or check becomes a `task:`
line for the closing `ГОТОВО` and `rules-kit mark --item <key> --status second-try --note "<task>"`. When the second
try fails too, `revert` parks a rule-text item itself; a handed one gets `rules-kit mark --item <key> --status
parked`. A parked item is shown in Pult and never asked.

## 6. Close

Run `rules-kit done --branch <branch>` (plain `rules-kit done` when nothing was committed): the weekly docs session
waits for that branch's merge. Then send P one `ГОТОВО` in 3 lines: state, result (fixes landed, reverted, parked),
what is needed (merge branch `<branch>`, the `task:` lines, or nothing). The session then waits; P closes it.

Why: owner, 2026-11-21 and 2026-11-22 (`docs/features/fix-agent-problems-in-the-retro.md` of the plugin repo): the
retro fixes each project's problems in its own context, only causes that recur. Owner, 2026-11-24
(`plans/retro-auto-rules-check.md`, «Мінімізуй мою участь, я всеодно буду бездумно апрувать»): the retro asks the
owner nothing; an approver on another model, a replay on past sessions and a revert of what did not work replace
his yes, and everything it did is a passive list in Pult's «статус».
