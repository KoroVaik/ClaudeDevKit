# Messages between sessions in different permission modes

Owner's words (2026-11-20, in «Обговорення: Спільний клієнт API»): «Фігня якась тиеба це фіксить», «Попроси керівника створить нове обговорення для фікса цьой пробоеми».

## The problem (seen 2026-11-20)
- A question from «Обговорення: Спільний клієнт API» (ClaudeDevKit, mode auto) to «P: Zhratva» (mode bypassPermissions) was held for the owner's approval and never delivered; a background session cannot show the approval, so the hold expires.
- `~/.claude/pult/logs/servers.log`: «MODE P: Zhratva bypassPermissions (hard bans on main)»; «MODE P: ClaudeDevKit auto (no Bash and PowerShell hard-ban deny lines on main)». Every session P starts gets P's own mode (project-lead «Start a C», «Permission mode»), so all ClaudeDevKit sessions are auto and all Zhratva sessions bypass.
- The same rule already caused the 2026-11-19 case inside one project; this is the cross-project case.

## Likely fix (to check, not decided)
Put the hard-ban deny lines on ClaudeDevKit main (dev-kit migration entry 3, plugins/dev-kit/migrations.md) so its sessions run in bypass too, then restart them; and cover cross-project messages in general (Pult, other leads, the new phase-1 server watcher that messages leads).

## Goal
Agree with the owner a fix so a message between any two sessions on this machine is delivered; write it in «Owner's approval» here.

- Fact: ClaudeDevKit profile `.claude/dev-kit.md` says «hard bans | accepted 2026-11-19», yet Pult logs no hard-ban deny lines on main: the owner may never have added them by hand (project-lead «Hard bans»: the owner adds the lines himself).

## Owner's approval
- 2026-11-20, owner's «так»: one permission mode, `bypassPermissions`, for every session a dev-kit project starts on this machine; no fallback to `auto` (the `--bg` disclaimer fallback goes). A project with no hard-ban deny lines on main starts no sessions until they are added. Sessions the owner starts by hand from the app are outside the plugin: their mode is the owner's. With that, a relay in the target's mode for session messages is not needed.
- 2026-11-20, owner's «так»: ClaudeDevKit hard bans are `rm -rf` deny lines (Bash and its PowerShell twin `Remove-Item`), no push-to-main ban, since ClaudeDevKit's P pushes main. Prishch's set is filled by its P through migration entry 3 and handed to the owner as ready lines.
- 2026-11-21, owner's «так»: only leads (P) and «Обговорення:» sessions message other sessions freely. An implementation session (C) messages only its own P; any other session only when its P allows it in the C's brief, in the same list as its other permissions. A rule in the skills; nothing blocks the tool itself.
- 2026-11-21, owner's «так всім» after the review: (a) sessions Pult starts (`start-session.ps1`) and the Pult hub itself also run in `bypassPermissions`; whether `remote-control` takes that mode is checked when building. (b) Replaces the Prishch part above: the owner adds Prishch's lines by hand before the switch, from a ready list handed to him; no migration C for it. (c) Hard bans can no longer be declined: migration entry 3 stops offering "no", since a project without them starts no sessions.

## Review notes for the builders (2026-11-21, not owner decisions)
- Order: deny lines on main in all three projects first, then the Pult change, then the restart; else a version-bump restart of a lead fails and HEAL gives up.
- ClaudeDevKit profile already says `hard bans | accepted`, so entry 3 will not fire again; the lines arrive as a hand action, not via migration.
- Remove every `auto` fallback: `start-servers.ps1:81`, `resume-lib.ps1` returns and `-Mode` defaults, `Get-LeadMode`, `start-session.ps1:28`, `start-servers.ps1:133`, `watch-servers.ps1:769,815`; project-lead SKILL.md 349-351 becomes "stop and ask the owner for the hand action". `start-servers.ps1:98-122` must check the exit code instead of logging STARTED. Update `tools/tests/test_lead_permission_mode.py` auto cases.
- `rm -rf` lines for ClaudeDevKit pass Pult's gate (resume-lib.ps1:117-118) but are a ticket, not protection; say so in the profile.
- "C messages only its own P" means sessions, not subagents (manager SKILL.md:158 messages subagents). A Pult-started session reports to the Pult hub or the P named in its brief. The permission is its own brief line, not the Ask-P list (that list is actions needing a yes).
- Goal covers plugin-started sessions; owner-started sessions keep SKILL.md 591-592 / 610-611 (reason: owner's unknown mode).
- Running sessions started in `auto` finish or restart; `claude respawn` keeps old flags.
- Texts: project-lead SKILL.md 337-354, 445-447, 537-571, 591; manager SKILL.md 244-247; pult hub.md 59-60, README:50; watch-servers.ps1 79-80; resume-lib.ps1 105-110.
- Unchecked: bypass->bypass delivery across projects, `claude -p` wake in bypass, hub start in bypass; one live send each after the change.
- 2026-11-21: owner's «так» to the short plan; discussion closed; owner asked to start the build at once.
- 2026-11-21, owner's «так» (after the plan): a script the owner runs himself with one command (`! <command>` in chat) writes a project's hard-ban lines into `.claude/settings.json` on main; P picks the set, the script only inserts it. Agents never run it (rule in the skills). Used first for ClaudeDevKit and Prishch, then once per new project.
- 2026-11-21, owner's «так»: when Pult's gate finds a project with no hard-ban lines on main, it does not start the lead and instead tells the owner which project lacks them and gives the ready script command to paste.
- 2026-11-21, owner's «так» (replaces «the owner runs himself» and «Agents never run it» in the script entry above): the script only adds deny lines, never removes or changes any. P shows the owner the set, and on his «так» P runs the script itself; the owner only approves. Pult's missing-bans notice then asks for that «так» instead of giving a command to paste. Reason: adding bans only tightens agents; removing or editing them stays forbidden to agents.
- 2026-11-21, owner's «так»: undo of a wrong ban. Each script run is its own commit on main, so no separate snapshot. On the owner's «так» P may revert only the latest ban-adding commit (one step back); older bans stay and only the owner removes them by hand.

## Build log (C «one-mode», 2026-11-21)
Paid spend so far: 0 USD.

### Step 1: ban sets for the owner's yes (sent to P)
Pult's gate (`plugins/pult/scripts/resume-lib.ps1:111-126`) reads only committed `main:.claude/settings.json` and needs one deny line per shell starting with `Bash(git push` / `Bash(rm -rf` / `Bash(docker` and `PowerShell(git push` / `PowerShell(Remove-Item` / `PowerShell(docker`. `skipDangerousModePermissionPrompt` is already true in the user settings.

ClaudeDevKit now: only `Edit(.claude/settings.json)`, `Edit(.claude/settings.local.json)` (commit a9c6ac8), so the gate fails. Lines to add (owner's choice: rm -rf, no push ban; the repo has no data folders, so they guard the repo's own history and product, a ticket for the gate more than protection):
- `Bash(rm -rf .git*)`, `PowerShell(Remove-Item*.git*)`
- `Bash(rm -rf plugins*)`, `PowerShell(Remove-Item*plugins*)`

Prishch now: no `permissions` block on main. `Push: ask` (an agent pushes main after the owner's yes), so no push-to-main ban; no docker, no database. Lines to add:
- `Bash(git push --force*)`, `PowerShell(git push --force*)`, `Bash(git push -f*)`, `PowerShell(git push -f*)`
- `Bash(git push*--delete*)`, `PowerShell(git push*--delete*)`
- `Bash(rm -rf Logs/archive*)`, `PowerShell(Remove-Item*Logs*archive*)` (run records the owner keeps, CLAUDE.md:19-20)
- `Edit(.claude/settings.json)`, `Edit(.claude/settings.local.json)`

Side effect to know: `Remove-Item*plugins*` also blocks deleting a single file under `plugins/` by PowerShell; agents use `git rm` for tracked files (which needs P's yes anyway).

### Step 2: rule edits (edit-rules step 3 list; ideas approved in «Owner's approval»)
Decisions made by C within the approved ideas:
- Migration: entry 3 text points to a new entry 4 «Hard bans on main pass Pult's check» (entries are never removed). Entry 4 catches projects that declined or whose profile says accepted with no lines on main (ClaudeDevKit). Its check is `dev-kit-bans check`.
- BACKLOG rule (manager «A change to the plugins themselves»): still no message to `P: ClaudeDevKit`; new reason: P finds entries itself, and a session messages only its own P.
- A project with no lead running (Pult's no-bans notice): the Pult hub prepares the set and runs `dev-kit-bans add` on the owner's «так».
- Owner-started sessions stay outside: P still sends them no message.
Changes of behaviour:
1. Every session a dev-kit project starts runs in bypassPermissions; no bans on main means no session starts (project-lead «Permission mode», «Обговорення:» launch; feature doc).
2. On the `--bg` disclaimer error P starts nothing and asks the owner for the one-time hand action.
3. Bans can no longer be declined; P adds them with `dev-kit-bans add` on the owner's «так»; only the latest add can be undone, by P on a «так»; nobody but the owner removes older ones.
4. A C messages only its own P (sessions, not subagents), unless its brief names another session; «Обговорення:» and P message freely (not owner-started sessions).
5. Pult starts no lead without bans and asks the owner's «так»; the hub adds the set (hub.md, README, by the Pult coder).

### Step 3: design change, the owner runs the add (P, 2026-11-21)
The auto-mode guard refused P running `dev-kit-bans add` («Undermining Oversight»): no agent may write permission settings, even after the owner's yes. So agents never run `add` or `undo`; the owner runs one short command. P asked for `dev-kit-bans add-approved [<repo>]`, reading the approved set from a file in the repo; Pult's notice gives that command. Design:
- The approved set lives in `.claude/hard-bans.json` (`{"deny": [...]}`) in the project; P (or the hub for a project with no lead) writes it after the owner's «так» to the exact lines. It is not a settings file, so agents may write it.
- `dev-kit-bans add-approved [<repo>]` (repo defaults to the current git top folder): adds the missing lines of that file to `.claude/settings.json` on main, one commit with both files; prints what it added. `undo` is owner-only too.
- The owner types it with `! ` in P's chat (or the hub's); the command is what P or Pult gives.
- 2026-11-21: bans added. The guard refused P's own run, but allowed it when the owner typed the command as his own message. ClaudeDevKit main 996a252 (pushed), Prishch main 8bf0bd3 (local, Prishch pushes by its own rules). `check` passes in all three leads' projects. The add-approved design above stays for new projects: the owner types the short command.

### Hand-in (2026-11-21)
Done: one mode in Pult and the skills, `dev-kit-bans` (add, add-approved, undo, check), the no-bans notice, C messaging limit, migration entry 4, dev-kit 0.1.82, pult 0.1.17. Tests 601 OK, lint clean. Review found 4 problems, all fixed.
On merge: the version bump makes the Pult watcher restart the leads (into bypass; leads without bans are not stopped). The watcher also sends its wakes in bypass at once.
Unchecked, need one live run each after the restart: bypass-to-bypass message across projects, the `claude -p` wake in bypass, the hub start with `--permission-mode bypassPermissions`.
Paid spend: 0 USD.
