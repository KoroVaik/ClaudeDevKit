# Pult does not hang on healing sessions

Status: build (C: Pult не зависає на відновленні сесій).

Owner «так» 2026-11-23 to the start proposal, P: ClaudeDevKit chat.

Scope: the two defects in `docs/features/start-leads-at-logon-and-heal-them.md` «Open»:
- a HEAL has no timeout, so a hung `claude --bg` stalls the watcher loop (`plugins/pult/scripts/watch-servers.ps1`);
- a hold file left by a crashed `restart-leads.ps1` stays until the next full `start-servers.ps1` (`plugins/pult/scripts/restart-leads.ps1`).

Success criterion: a hung HEAL is cut after a bounded time, logged, and the loop goes on; a stale hold file is cleared without a full start; tests cover both; no real Pult or lead restart during the work (throwaway test sessions only).
