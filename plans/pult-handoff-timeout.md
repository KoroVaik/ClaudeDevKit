# Pult does not hang on moving a lead

Status: done (C: Pult не зависає на переїзді керівника).

Owner «так» 2026-11-23 to the start proposal, P: ClaudeDevKit chat.

Scope: the open defect in `docs/features/start-leads-at-logon-and-heal-them.md` «Open»: the watcher's handoff move calls `start-servers.ps1 -Handoff` with no time limit, so a hung move stalls the watcher loop (`plugins/pult/scripts/watch-servers.ps1`, Invoke-HandoffCheck). Same pattern as `plans/pult-heal-timeout.md` and `plans/pult-restart-timeout.md`. Keep the agreed fallback of `plans/push-noise.md` (a failed `/clear` move falls back to a fresh session) working.

Success criterion: a hung handoff move is cut after a bounded time, logged, the old lead is brought back or the fallback runs, and the loop goes on; a test covers it; no real Pult or lead restart during the work (throwaway test sessions only).

## Result
- `Invoke-HandoffCheck` (watch-servers.ps1) runs `start-servers.ps1 -Handoff` through `Invoke-Bounded`: a run past
  `-HandoffMoveWaitSec` (default 600: the /clear wait up to 120 s, two stop waits up to 60 s each, and the fallback's
  fresh start) is stopped with its child processes and logged HANDOFF-TIMEOUT (a critical line: Pult shows and pushes
  it, as HANDOFF-FAILED). It is a failed move: the marker and the one-try mark stay, so it is not tried again for that
  marker; a lead left down comes back by HEAL in the next rounds (resumed with its full conversation), and the loop goes on.
- A run whose output already says `Resumed lead:` or `Started lead:` counts as moved even if it was cut later (the
  move itself ended; only the pin step after it hung).
- The `/clear` fallback of `plans/push-noise.md` is unchanged: it runs inside start-servers.ps1, within the bound.
- Tests: `tools/tests/test_watch_servers_handoff.py`, test_hung_move_is_stopped_reported_once_and_the_old_lead_comes_back_by_heal
  (hung move cut in 3 s, run and child gone, one HANDOFF-TIMEOUT, no retry, HEAL resumes the lead, marker kept).
  Docs: feature, pult README, hub rules. pult 0.1.27.
- Left as is: `plugins/dev-kit/skills/project-lead/SKILL.md` step 5 names only HANDOFF-FAILED; P's behaviour is the
  same for a timeout (it reads `handoff status`), so no dev-kit bump for it.
- Reviewer doubt, recorded, not fixed: a move cut after its `/clear` but during the handoff resume may leave the
  lead live in an empty context with the marker kept; the same holds for a HANDOFF-FAILED at that point today.

Spend: ~0.1% of the weekly limit, estimate; API: 0 USD
