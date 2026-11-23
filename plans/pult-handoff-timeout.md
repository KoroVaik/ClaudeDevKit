# Pult does not hang on moving a lead

Status: build (C: Pult не зависає на переїзді керівника).

Owner «так» 2026-11-23 to the start proposal, P: ClaudeDevKit chat.

Scope: the open defect in `docs/features/start-leads-at-logon-and-heal-them.md` «Open»: the watcher's handoff move calls `start-servers.ps1 -Handoff` with no time limit, so a hung move stalls the watcher loop (`plugins/pult/scripts/watch-servers.ps1`, Invoke-HandoffCheck). Same pattern as `plans/pult-heal-timeout.md` and `plans/pult-restart-timeout.md`. Keep the agreed fallback of `plans/push-noise.md` (a failed `/clear` move falls back to a fresh session) working.

Success criterion: a hung handoff move is cut after a bounded time, logged, the old lead is brought back or the fallback runs, and the loop goes on; a test covers it; no real Pult or lead restart during the work (throwaway test sessions only).
