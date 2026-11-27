# Support repositories whose main branch is `master`

Status: started 2026-11-27 by L: ClaudeDevKit.

## Task

Owner's words (2026-11-27, relayed from Pult in the Lead's chat): «зроби, щоб dev-kit-bans add-approved і
start-session.ps1 працювали з гілкою master (MyPC, Job). Заборони для MyPC уже лежать у .claude/hard-bans.json, для
Job я їх погодив. Після цього запусти сесію в MyPC.»

Scope:
- `plugins/dev-kit/bin/dev-kit-bans` (`add-approved`, `check`, `undo` if they assume `main`) and
  `plugins/pult/scripts/start-session.ps1` work when the repo's default branch is `master` (MyPC:
  C:/Users/korov/MyRepositories/MyPC, Job: find its path from Pult's project list or ask the Lead). Detect the branch
  (e.g. the current branch of the main checkout or `origin/HEAD`), do not hard-code a second name.
- Grep the plugins for other places that assume `main` in the same flow (worktree creation, bans) and list them in this
  file; fix only those on the path of these two scripts unless the fix is the same one line.
- Do NOT run `add-approved` on MyPC or Job yourself and do not edit those repos: the Lead does that after the merge.

## Success criterion

In a throwaway git repo whose only branch is `master`, `dev-kit-bans add-approved` adds the lines and commits on
`master`, and `start-session.ps1` passes its branch checks (dry run or test); the same tests on a `main` repo still pass.

## Decision

- Trunk = the first of `main`, `master` that exists as a local branch (`trunk_branch` in hard_bans.py, `Get-TrunkBranch`
  in resume-lib.ps1). Why not "the branch the main checkout is on" (first try): that took a main checkout left on a work
  branch as the trunk, so `add` / `add-approved` would commit bans there and the old "not on branch" guard was lost
  (an existing test caught it). Why not `origin/HEAD`: MyPC's `origin/HEAD` is `origin/main` (a placeholder README)
  while its work is on local `master`; Job has no remote. `sessions.py` already uses the same main-then-master order.
- Read-only dry run on the real repos: `Get-TrunkBranch` gives `master` for MyPC and Job, `main` for ClaudeDevKit; the
  gate on MyPC says "no Bash and PowerShell hard-ban deny lines on master" (its hard-bans.json is not added yet).

## Other places assuming `main` (inventory, not changed)

- `plugins/dev-kit/scripts/sessions.py:615` already tries main, then master.
- `plugins/rules-kit/scripts/fixes.py:373` main, else the current branch (retro check, not on this path).
- `plugins/dev-kit/hooks/owner-session-note.py:16` text "коміть у main"; `plugins/dev-kit/scripts/run_app.py:58` text.
- NO-BANS texts in start-session.ps1, start-servers.ps1, restart-leads.ps1, watch-servers.ps1: changed to "the trunk
  branch" (the same one-line text). `plugins/pult/rules/hub.md` still says "on main" loosely (rule text, not changed).

## Spend

Spend: ~1% of the weekly limit, estimate; API: 0 USD
