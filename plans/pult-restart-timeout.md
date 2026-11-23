# Pult does not hang on restarting leads

Status: done (C: Pult не зависає на перезапуску керівників).

Owner «так» 2026-11-23 to the start proposal, P: ClaudeDevKit chat.

Scope: the open defect in `docs/features/start-leads-at-logon-and-heal-them.md` «Open»: the watcher calls `restart-leads.ps1` with no time limit, so a hung restart stalls the watcher loop (`plugins/pult/scripts/watch-servers.ps1`). Found by the heal-timeout build; see `plans/pult-heal-timeout.md` for how HEAL got its limit (HEAL-TIMEOUT, HOLD-STALE).

Success criterion: a hung restart-leads call is cut after a bounded time, logged, any hold it left is cleared, and the loop goes on; a test covers it; no real Pult or lead restart during the work (throwaway test sessions only).

## Result
- `Invoke-LeadRestart` (watch-servers.ps1) runs restart-leads.ps1 through `Invoke-Bounded`: a run past
  `-LeadRestartWaitSec` (default 600: the 60 s stop wait plus a full start) is stopped with its child processes,
  logged RESTART-LEAD-TIMEOUT (a critical line: Pult gets it, as RESTART-LEAD-FAILED), counted as a failed restart (no
  new try on the same versions). Its hold is removed at once by `Clear-StaleHold` (HOLD-STALE), so a lead it stopped
  comes back by HEAL in the next rounds.
- The parameter is not `-RestartWaitSec`: that name is already the script-level wait of the watcher's own
  WATCH-RESTART (20 s), and the param would have been overwritten.
- `Invoke-Bounded` now waits up to 5 s for a stopped run to be gone, so the hold check right after sees its pid gone.
- Tests: `tools/tests/test_watch_servers_heal.py`, class WatchServersRestartTimeoutTest (hung restart cut, hold
  removed, loop goes on, processes gone; a restart in time is no failure). Docs: feature, pult README, hub rules.
  pult 0.1.26.
- Found, recorded in the feature's Open: the handoff move's `start-servers.ps1 -Handoff` call is still unbounded.

Spend: ~0.1% of the weekly limit, estimate; API: 0 USD
