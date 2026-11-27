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
