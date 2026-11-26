# Plan: leads show their new «L:» names in the Claude desktop app

Status: done (2026-11-26); the owner's look at the list is left.

Owner's words: «доречі назви лідів лишились старі досі» (screenshot of the Claude desktop app session list: «P: Zhratva», «P: Prishch», «P: ClaudeDevKit», while Managers show «M: ...»), then «так» to «Запустити сесію «M: Нові назви Lead у застосунку»? (у списку з'явиться «L: ...»)».

Known (checked by the Lead): `claude agents --json` lists all three as `L: <project>`; `~/.claude/pult/logs/servers.log` has `RENAMED P: X -> L: X` for each (lines ~6287, 6562, 6600). The role-names build (`plans/role-names.md`) renamed by editing the job's `state.json` and resuming; the Remote Control title the app shows stayed the old one. So the app keeps the title set when the session first connected over Remote Control.

Do: find how a running session's Remote Control / app title is updated (docs, Claude Code CLI, e.g. a /rename command, reconnect, the remote-control settings) with the cheapest live check on a throwaway session; then make the Pult watcher's lead rename (and any future rename) update the app title too, and rename the three running leads that way, as a release or a question to the Lead (never stop or restart a lead yourself). Record the new fact through the dev-kit:facts-keeper agent. If no way exists, report that with the check.

Success criterion: the desktop app list shows «L: Zhratva», «L: Prishch», «L: ClaudeDevKit» (the owner checks the list once, through the Lead); the rename code covers the app title; tests pass.

## Result

- Cause (checked live, Claude Code 2.1.332): the app lists a background session by the title of its Remote Control session on claude.ai, set at the first connect. A job rename plus resume, and `/rename` as a resume prompt, change only the local name (fact: `plugins/dev-kit/claude-facts.md`, "The app's session title is set once, at the first Remote Control connect").
- Fix: `plugins/pult/scripts/sync-app-titles.py` reads each lead's title (GET `/v1/code/sessions/<bridgeSessionId>`) and sets it to the name (PUT `{"title"}`, the call Claude Code makes) with the owner's Claude login token; `start-servers.ps1` runs it after pinning, so every lead start (logon, heal, restart) covers any future rename. Test: `tools/tests/test_sync_app_titles.py`. Releases: pult 0.1.39, dev-kit 0.1.139 (facts only), both routine.
- The three running leads: the script ran once by hand with no restart; their server titles are now «L: Zhratva», «L: Prishch», «L: ClaudeDevKit» (read back). Left: the owner's one look at the desktop app list.
- Throwaway test sessions stopped and removed (their Remote Control sessions are archived).

Spend: ~0.3% of the weekly limit, estimate; API: 0 USD
