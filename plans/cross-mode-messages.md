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
