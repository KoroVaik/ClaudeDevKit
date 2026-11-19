# Sessions talk without the owner in the middle

Owner's words (2026-11-19, via Pult): «напиши дев кіт керівнику, щоб розібрав проблему спілкування між сесіями, бо мені не хочеться бути посередником постійно». Then «Так» to both:
1. «Запускати сесії обговорення в режимі їхнього керівника?» (their reports reach the lead without the owner).
2. «Запити з інших проєктів до мене писати лише в список змін плагіна?» (P: ClaudeDevKit picks them up itself, no stuck messages).

## Checked facts (research 2026-11-19)
- A SendMessage to a session in a different permission mode is held for the owner's approval and may expire.
- Leads now start in their C sessions' mode (plugins/pult/scripts/resume-lib.ps1:111-126, start-servers.ps1:80-95); P: Zhratva is bypassPermissions, P: ClaudeDevKit and P: Prishch are auto.
- «Обговорення:» sessions are always started in auto (plugins/dev-kit/skills/project-lead/SKILL.md, «Start an «Обговорення:» session»); their done report to a bypass P was held (plans/lead-bypass-mode.md, live check).
- Requests to P: ClaudeDevKit (plugins/dev-kit/skills/manager/SKILL.md, «A change to the plugins themselves») are sent by SendMessage; from a bypass session they are held in P: ClaudeDevKit's chat.

## Goal
1. «Обговорення:» sessions start in P's mode (the same mode rule C sessions use).
2. Plugin change requests from other projects go only as a BACKLOG.md entry, no SendMessage to P: ClaudeDevKit; P: ClaudeDevKit finds new entries itself (it already lists entries with no Verdict line on start and every wake-up). Make sure it does see them without a message.

## Success criterion
Rule text and launch code match both points; no rule left that sends a cross-session message between sessions that can be in different modes.

## Paid spend
0
