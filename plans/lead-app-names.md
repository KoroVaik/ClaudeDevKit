# Plan: leads show their new «L:» names in the Claude desktop app

Status: not started (2026-11-26).

Owner's words: «доречі назви лідів лишились старі досі» (screenshot of the Claude desktop app session list: «P: Zhratva», «P: Prishch», «P: ClaudeDevKit», while Managers show «M: ...»), then «так» to «Запустити сесію «M: Нові назви Lead у застосунку»? (у списку з'явиться «L: ...»)».

Known (checked by the Lead): `claude agents --json` lists all three as `L: <project>`; `~/.claude/pult/logs/servers.log` has `RENAMED P: X -> L: X` for each (lines ~6287, 6562, 6600). The role-names build (`plans/role-names.md`) renamed by editing the job's `state.json` and resuming; the Remote Control title the app shows stayed the old one. So the app keeps the title set when the session first connected over Remote Control.

Do: find how a running session's Remote Control / app title is updated (docs, Claude Code CLI, e.g. a /rename command, reconnect, the remote-control settings) with the cheapest live check on a throwaway session; then make the Pult watcher's lead rename (and any future rename) update the app title too, and rename the three running leads that way, as a release or a question to the Lead (never stop or restart a lead yourself). Record the new fact through the dev-kit:facts-keeper agent. If no way exists, report that with the check.

Success criterion: the desktop app list shows «L: Zhratva», «L: Prishch», «L: ClaudeDevKit» (the owner checks the list once, through the Lead); the rename code covers the app title; tests pass.

Spend: -
