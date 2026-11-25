# Plan: task sessions survive a PC reboot

Status: done (2026-11-25).

Owner's words: «Так» to «Запустити нову сесію «C: Сесії після перезапуску ПК»? (після перезапуску ПК фонові сесії підніматимуться самі)» (P: ClaudeDevKit, 2026-11-25).

Source: BACKLOG.md entry «Lead: do not end a task whose session died in a reboot» (cause with file:line, fix, cheapest test). Remove the entry when built.

Success criterion: a registry with one active C whose process is gone; a fresh lead runs its start steps; the record stays `active`, `state` does not report a plain `gone` inside the grace, and the Pult watcher respawns the C (or sends `gone:` after it fails). The lead skill says a lead never ends a C on `state` alone.

Result: `dev-kit-sessions state` reports a task session listed with no process as `closed` (gist `no process, the watcher may respawn it;`) until `check` has seen it closed for CLOSED_GRACE (300 s, read from `check-closed.json`); owner sessions keep `gone` at once (the watcher heals none). The lead skill ("Event lines") says P never ends a C on `state` or `claude agents --json` alone, only on the `gone:` event. Tests: `tools/tests/test_sessions.py` (new grace test, two expectations moved to `closed`), heal tests pass. dev-kit 0.1.133, routine.
Untested: a real reboot with the Pult watcher respawning; the watcher side is unchanged (`watch-servers.ps1` heals active records).

Spend: ~0.2% of the weekly limit, estimate; API: 0 USD
