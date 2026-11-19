# A lead restart never loses its mode

Owner's words (2026-11-19): «Так» to «Запустити нову сесію «C: Перезапуск без втрати режиму»? (керівник після перезапуску не втратить режим)».

## Problem
BACKLOG.md entry «A resume right after a stop can start a flag-less copy»: `claude --bg --resume` right after `claude stop`, even once `claude agents` shows `stopped`, can say «already running» and start a copy with the default model and mode (seen twice in the live check of plans/lead-bypass-mode.md; a wait of about 15 s avoided it).

## Goal
Every Pult restart or resume of a lead (and any P refresh of a C that resumes) starts the session with its own flags, never a flag-less copy. Remove the BACKLOG entry when built.

## Success criterion
A loop of 5 stop-then-resume runs on a throwaway bg session (cheap model, temp state) starts no copy without the flags; the restart code waits or retries until the old process is gone.

## Paid spend
0

## Cause (checked live 2026-11-19, throwaway sessions on haiku in a temp folder)
After `claude stop`, `claude agents --json` drops the pid about 1.2 s after the stop, but the session's OS processes (the `--bg-pty-host ...-pty-<short id>` host and its worker) exit only at about 1.9 s. A `claude --bg --resume <sid>` in that gap prints «already running ... started a copy as <id>» and forks a copy with no `--model` / `--permission-mode` and an auto name. Baseline loop (resume as soon as the pid left the list): 2 copies in 3 clean runs. Resume after the processes were gone: 3 of 3 woke the same session.

## Done
- `resume-lib.ps1`: `Get-SessionProcessIds` (claude.exe processes whose command line holds the full session id, forked copies left out; a resumed lead's pty pipe carries the job id, not the session id prefix), `Wait-SessionGone` (up to 60 s), `Get-ResumeCopyId` (copy id from claude's note).
- `start-servers.ps1`, lead branch: waits for the old processes before rewriting the saved flags and resuming (else STILL-RUNNING, no resume); if claude still reports a copy, stops and removes it and retries once (COPY-REMOVED, NOT-RESUMED). Covers restart-leads.ps1 and the watcher's HEAL, which both go through start-servers.ps1.
- `rules/hub.md` sentence; pult 0.1.13; BACKLOG entry removed; unit test `tools/tests/test_resume_copy_guard.py`.

## Check
- Unit: test_resume_copy_guard + test_lead_permission_mode, 13 OK.
- Review (dev-kit:reviewer, sonnet): no problems; its doubts on the pty short id, forked copies and rm timing were checked and fixed.
- Live: throwaway lead (haiku, low, temp state), 5 runs of `claude stop` then at once `start-servers.ps1 -Only`: 5 of 5 resumed the same session with `--model haiku --effort low --permission-mode auto`, 0 copies, no COPY-REMOVED needed. Run again after the review fix: same, 5 of 5, 0 copies. Copy removal forced once (resume while running): copy stopped and removed, the original's processes not counted. Throwaway sessions removed and unpinned after.
- Not covered: P's refresh of a C (dev-kit project-lead) starts a new session with --predecessor, not a resume, so it does not hit this.
