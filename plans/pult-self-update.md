# Pult takes new rules by itself

Owner's words: «Так» to «Запустити нову сесію «C: Pult бере нові правила»? (зміни Pult доходитимуть до нього самі)» (2026-11-19).

## Problem (checked 2026-11-19, see plans/push-notifications.md, Built)
- Nobody runs `claude plugin update pult@korov-dev`: Pult ran pult 0.1.0 from the plugin cache from 2026-11-15 to 2026-11-19.
- A resumed Pult keeps its old rules, so pult rule changes never reach it.
- Now installed: pult 0.1.10 (updated by P 2026-11-19); the running Pult has not restarted on it yet.

## Goal
After a pult change is merged into main of ClaudeDevKit, the installed pult is updated and Pult runs on the new rules and scripts, with no hand step from the owner. Same check for dev-kit, web-kit and unity-kit if they have the same gap.

## Success criterion
A pult version bump merged into main reaches the installed plugin and the running Pult (its rules and watchers) within the existing restart flow, shown on one live bump.

## Paid spend
0

## Findings (checked 2026-11-19)
- Premise wrong: Pult does not run from the plugin cache. `claude plugin list --json` shows pult (and dev-kit, web-kit, unity-kit) with `readFromFolder` = the main checkout's `plugins/<name>`; Pult's transcript shows the hub rules injected with PLUGIN = `ClaudeDevKit/plugins/pult` at every start/resume (2026-11-15, 11-16, 11-19). The `version` in installed_plugins.json is only an install record (README "After enabling a plugin"). No `claude plugin update` is needed.
- Rules: the SessionStart hook re-injects hub.md from the repo on every resume, and hub.md already has the "Rules update check, on every owner message" (since 2026-11-16; in the rules injected 2026-11-19, absent from the 11-15/11-16 ones). So a merged hub.md reaches Pult at the owner's next message, no restart.
- watch-log.py: Pult re-runs it from the repo folder on every wake, so it picks up new code on the next re-arm.
- Real gap: `watch-servers.ps1` is one long PowerShell process started at logon (running one: started 2026-11-18 22:15, its script changed 22:24, so it runs older code now). A merged change to it reaches nothing until the next logon or a manual start-servers run.
- Smaller gap: the lead version check compares only dev-kit's version; a web-kit/unity-kit-only change does not restart the leads.

## Agreed with P (2026-11-19)
watch-servers.ps1 checks its own script (and the pult version) each round; on a change it starts a fresh copy of itself and exits (log WATCH-RESTART). Pult's conversation is not restarted. Optional: lead version check also counts web-kit/unity-kit versions.
- P: build both (self-restart and extension count). P's doubt that {PLUGIN} is the cache folder: checked, does not hold - both SessionStart hook outputs in Pult's tool-results (11-16 and 11-19) carry only repo paths; the 6 cache-path hits in the transcript are all inside one peer message (line 145, from the C of push-notifications). So no hub-rules.py change.
- Rollout: the running watcher has old code without self-restart, so one manual watcher restart is needed after the merge (ask P first). Pult itself needs no restart.

## Built (2026-11-19, pult 0.1.11)
- watch-servers.ps1 restarts itself on a stable, parse-checked change of its own code (watch-servers.ps1, new shared plugin-versions.ps1); the new copy must log "WATCH started" within 20 s, else it is stopped, WATCH-RESTART-SKIPPED is logged and the old copy keeps running. In-memory HEAL/try counters reset on such a restart (judged safe: rare).
- Lead restart also counts the korov-dev extensions a project enables (web-kit, unity-kit): idle lead at once, busy lead never woken, restarted once idle; dev-kit handshake unchanged; old lead-versions.json entries adopt the installed extension versions (no storm). restart-leads.ps1 -Ask prints "Not asked, busy and only an extension changed: <name>".
- hub.md and README updated (rule edit checked by a reviewer, findings fixed). Tests: tools/tests/test_watch_servers_restart.py (stubs only, no real powershell copy started).
- Not done live: the running watcher predates this code, so after the merge one manual watcher restart is needed (ask P), then the next pult change shows WATCH-RESTART live. Risk: a lead with an armed session watcher may rarely be idle, so an extension-only restart may wait long.
- Rollout (2026-11-19 01:48, P's yes): new watcher started from main (pid 31916, "WATCH started" logged), then the old one (pid 28488) stopped; no lead, Pult or server stopped. After two rounds: one watcher, no restart lines, lead-versions.json gained `ext` (web-kit for Zhratva, unity-kit for Prishch) with no restart storm. WATCH-RESTART itself shows live on the next change of the watcher's code.
