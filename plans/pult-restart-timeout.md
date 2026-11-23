# Pult does not hang on restarting leads

Status: build (C: Pult не зависає на перезапуску керівників).

Owner «так» 2026-11-23 to the start proposal, P: ClaudeDevKit chat.

Scope: the open defect in `docs/features/start-leads-at-logon-and-heal-them.md` «Open»: the watcher calls `restart-leads.ps1` with no time limit, so a hung restart stalls the watcher loop (`plugins/pult/scripts/watch-servers.ps1`). Found by the heal-timeout build; see `plans/pult-heal-timeout.md` for how HEAL got its limit (HEAL-TIMEOUT, HOLD-STALE).

Success criterion: a hung restart-leads call is cut after a bounded time, logged, any hold it left is cleared, and the loop goes on; a test covers it; no real Pult or lead restart during the work (throwaway test sessions only).
