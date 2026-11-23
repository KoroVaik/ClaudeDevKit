# A clear flow for testing phone pushes with the owner

Status: discussion with the owner (Обговорення: Як тестувати пуші на телефоні).

## Owner's words

«потрібно чітко описати флоу тестування пуш сповіщень, бо ти спамиш якусь фігнб постійно. Запускай обговорення» (2026-11-23, P: ClaudeDevKit chat).

## Known context (to check)

- Today, 2026-11-23, P relayed step-by-step phone checks from C sessions («C: Переїзд керівника без пушів», «C: Перевірка, що Pult не будить керівників дарма»): several «+ або -» messages, a «1 чи 2?», repeated asks, test pushes the owner missed (one at 17:27 checked hours later), a test while the app was open, and a question about the Pult chat.
- Rules in force: the owner's global CLAUDE.md («A live test that needs the owner's hands ... goes one step at a time ... «+ або -»»), project-lead SKILL.md (P relays, C never asks the owner; push request form), `plans/wake-check.md`, `plans/push-noise.md` («Facts checked live»), `plugins/dev-kit/claude-facts.md` (push and Remote Control sections).
- Found today: Pult holds messages from leads (different permission mode), so pushes relayed via Pult do not arrive; whether a push shows while the app is open is unclear.

## Owner's approval

(written by the discussion session on the owner's «так»)
