# Pult does not hang on healing sessions

Status: done (C: Pult не зависає на відновленні сесій).

Owner «так» 2026-11-23 to the start proposal, P: ClaudeDevKit chat.

Scope: the two defects in `docs/features/start-leads-at-logon-and-heal-them.md` «Open»:
- a HEAL has no timeout, so a hung `claude --bg` stalls the watcher loop (`plugins/pult/scripts/watch-servers.ps1`);
- a hold file left by a crashed `restart-leads.ps1` stays until the next full `start-servers.ps1` (`plugins/pult/scripts/restart-leads.ps1`).

Success criterion: a hung HEAL is cut after a bounded time, logged, and the loop goes on; a stale hold file is cleared without a full start; tests cover both; no real Pult or lead restart during the work (throwaway test sessions only).

## Result
- HEAL and HEAL-TASK runs go through `Invoke-Bounded` (watch-servers.ps1): output to temp files, a run past
  `-HealWaitSec` (default 300) is stopped with its child processes, except Remote Control server windows,
  `claude daemon run` and `--bg-pty-host`; logged HEAL-TIMEOUT / HEAL-TASK-TIMEOUT, counted as a failed try.
  HEAL-TASK was included: the same unbounded call, the same fix.
- restart-leads.ps1 writes its pid into the hold; the watcher removes a hold whose pid is gone or reused
  (HOLD-STALE), not with -Once, not during a full start. stop-servers holds and holds without a pid stay.
- Tests: `tools/tests/test_watch_servers_heal.py` (10 cases). Docs: feature, pult README, hub rules. pult 0.1.25.
- No release mark: marks exist only for dev-kit (`plugins/dev-kit/releases.json`); dev-kit is not bumped. The
  watcher takes its own new code by itself (WATCH-RESTART) after the merge.
- Not done, possible follow-up: `Invoke-LeadRestart` (restart-leads.ps1 run by the watcher) is still unbounded.

Spend: ~0.2% of the weekly limit, estimate; API: 0 USD
