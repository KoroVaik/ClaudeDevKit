# The lead adds approved hard bans itself

Owner's words (2026-11-21, P: ClaudeDevKit chat): to «Нехай керівник сам додає заборону після твого «так» на точні рядки? (тобі не треба нічого набирати)» the owner answered «то зроби щоб відразу всюди додалось».
Why: the owner cannot run «! dev-kit-bans add-approved» in a lead's chat: from the phone «!» arrives as a plain message, and in the desktop app a lead is not a local session («Shell commands are only available in local sessions»). Seen live 2026-11-21. In bypassPermissions P ran `dev-kit-bans add-approved .` itself with no guard refusal (commit 0604b3f, ClaudeDevKit).

Change: after the owner's «так» to the exact lines, P (and the Pult hub when no P runs) writes `.claude/hard-bans.json` and runs `dev-kit-bans add-approved` itself. Adding stays tightening only. Removing or editing a ban (`undo`, any edit) stays the owner's alone; no agent runs `undo`. A C never adds, changes or lifts bans.
Places to update (find all): plugins/dev-kit/skills/project-lead/SKILL.md «Hard bans» and «Apply dev-kit migrations»; plugins/dev-kit/migrations.md entry 4; plugins/pult/rules/hub.md «Missing hard bans»; the NO-BANS output text in plugins/pult/scripts (start-servers.ps1, restart-leads.ps1, the shared helper that prints the command); dev-kit-bans help text if it says only the owner runs add-approved; any test that pins that text. Follow dev-kit:edit-rules. Bump dev-kit and pult versions.

Success criterion: no rule or script output still tells the owner to type `! dev-kit-bans add-approved`; the rules say P runs it after the owner's «так»; `undo` stays owner-only; tests and lint pass.

Paid spend: 0 USD so far.

Done 2026-11-21: P and the Pult hub run `dev-kit-bans add-approved` after the owner's «так»; `add` and `undo` stay with no agent, removing a ban is the owner's. Changed: project-lead and manager skills, migrations entry 4, pult hub rules and README, the feature doc, the `hard_bans.py` docstring, the NO-BANS text in the Pult scripts (the command no longer starts with `! `). dev-kit 0.1.88, pult 0.1.20. Tests 666 OK, lint clean (one earlier run had 2 failures that did not repeat in two reruns). Review: one stale line in the manager skill, fixed. Left as is: migrations entry 3 (history, replaced by entry 4).
