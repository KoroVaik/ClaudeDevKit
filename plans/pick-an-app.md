# Plan: no «Pick an app» window when a Lead closes a session

Status: not started (2026-11-26).

Owner's words: «у мене постійно це вилазить, чому?» (a screenshot of two Windows «Pick an app» windows), then «так» to «Виправити правило Lead і додати перевірку проти таких вікон? (вікно «Pick an app» більше не вилазитиме)» (L: ClaudeDevKit, 2026-11-26).

Cause (investigator, confirmed): L: Prishch ran `dev-kit-app stop --project ...` in the PowerShell tool during the merge clean-up (transcript C:/Users/korov/.claude/projects/C--Users-korov-MyRepositories-Prishch/7f750d10-0fa0-4309-9000-6b0b7f5f63d3.jsonl, 10:58:20Z and 11:11:24Z). The bin file is extensionless (#!/bin/sh), so Windows shows «Pick an app»; `2>$null` hid the error. The fact is already in `plugins/dev-kit/claude-facts.md` («Plugin `bin` commands run only in the Bash tool»), but `plugins/dev-kit/skills/project-lead/SKILL.md` "Acceptance and merge" (the clean-up after a merge, ~line 975-982) mixes Bash commands with `cmd /c rmdir` (PowerShell) and names no shell.

Do:
1. The clean-up step says which tool: `dev-kit-sessions`, `dev-kit-app`, `claude rm` in the Bash tool; only `cmd /c rmdir` and `git worktree remove` in the PowerShell tool. Check other places in dev-kit skills that name a plugin bin command beside a PowerShell step.
2. A check that refuses a PowerShell tool call running a plugin bin command (`dev-kit-*`, `spend-kit*`, `rules-kit*` and the other extensionless files in plugins/*/bin) with a message to use the Bash tool: in `plugins/dev-kit/hooks/windows-traps.py` (or where the repo's shell-trap checks live), with tests.

Success criterion: a PowerShell tool call `dev-kit-app stop --project x` is refused before it runs, with a clear message; the same in the Bash tool passes; the skill names the tool for each clean-up command; tests and lint pass; dev-kit version bumped with a routine release mark.

Spend: -
