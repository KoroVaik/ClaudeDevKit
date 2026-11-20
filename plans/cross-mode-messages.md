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
