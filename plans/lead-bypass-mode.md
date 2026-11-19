# Leads run in the same permission mode as their C sessions

Owner's words (2026-11-19): «Тіки керівник керує сесійой розробки, я туди не маю лизти взагалі»; «Так» to «Запустити сесію, яка переведе керівників у режим без запитів дозволів?».

## Problem
BACKLOG.md entry «P cannot message a C started with bypassPermissions (from P: Zhratva)». P starts C with bypassPermissions after the hard bans; P itself runs in another mode, so every P message to that C is held for the owner's approval in the C's chat. The SendMessage tool says a session in a different permission mode holds cross-session messages for its user's approval.

## Goal
P sessions run in the same mode as their C sessions (bypassPermissions where the project's hard bans are in place), so P -> C messages arrive with no owner step and the owner never opens a C's chat. Cover every way a P starts: Pult launch and autorun (plugins/pult/scripts), plugin-update restart and resume, P's own refresh and the project-lead skill text. Remove the BACKLOG entry when built.

## Success criterion
A P and a C both in bypassPermissions: one P -> C message is delivered with no approval (live check on a throwaway pair), and the launch code for P passes the same mode C gets.

## Paid spend
0

## State (C, 2026-11-19)
- Built: `Get-LeadPermissionMode` in `plugins/pult/scripts/resume-lib.ps1` (hard-ban Bash + PowerShell deny lines committed on main, plus `skipDangerousModePermissionPrompt` in user settings -> bypassPermissions, else auto). `start-servers.ps1` passes it to a fresh start and rewrites `--permission-mode` in the saved respawnFlags before a resume; logs `MODE <lead> <mode> (<reason>)`. Covers logon autorun, watcher heal and restart-leads (all go through start-servers.ps1).
- Skill (project-lead, "Permission mode"): P runs in this mode; a C gets P's own mode (last MODE line in servers.log), so the two always match.
- Tests: `tools/tests/test_lead_permission_mode.py` (9, pass); watcher/hub tests pass; lint clean.
- ClaudeDevKit itself stays auto (its main has no shell deny lines), same as its C sessions.
- Live check 2026-11-19 (P's yes; throwaway haiku sessions in a temp detached worktree, no real lead, Pult or watcher touched; all stopped and the worktree removed after):
  - P fresh-started by `Get-LeadStartArgs -Mode bypassPermissions` -> bypass C: «ping from P» delivered with no approval.
  - P resumed after `Set-LeadRespawnModel -Mode auto` -> its message held at the bypass C (C's job state `needs: approve message from ... P LiveCheck`); claude printed «woke session with its saved options (..., --permission-mode)».
  - Same P stopped, `Set-LeadRespawnModel -Mode bypassPermissions`, resumed -> «ping from P resumed bypass» delivered. So a resume takes the rewritten mode.
  - An auto session -> the bypass P: held (P's job state `needs: approve message from ... D LiveCheck`). So an «Обговорення:» session (auto) report to a bypass P is held in P's chat for the owner - open decision for P.
  - Side finding: `claude --bg --resume` right after `claude stop`, even once `claude agents` shows `stopped`, can say «already running» and start a flag-less copy (default model and mode). Seen twice; a wait of about 15 s avoided it. Not changed here.
  - A fresh temp repo gets «Workspace not trusted» for `claude --bg`, so the end-to-end `start-servers.ps1 -ConfigFile` run on a temp repo with hard bans was not possible; `Get-LeadPermissionMode` is covered by unit tests instead.
