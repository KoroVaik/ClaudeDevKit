# Stop hook: a lead's reply keeps the message form

Status: in progress (C: Перевірка форми відповіді керівника).

Source: «Ретро: ClaudeDevKit», 2026-11-25, task line: «Stop-hook, що перевіряє, що відповідь керівника порожня або починається з жирного заголовка блоку» (retro finding lead-message-form). Started by P with no owner ask (dev-kit:project-lead, «Retro of session problems»).

Caution from P: a lead's reply has named exceptions to the bold blocks (dev-kit:project-lead, «Message templates», «Exceptions»): the one line after starting an «Обговорення:» session, the push-test steps, the CAPS restart lines, and P's other replies to the owner's own questions (global caps, no blocks). The hook must not block those; prefer a narrow check (for example only turns woken by a session or event message, not by an owner message) and a soft nudge over a hard block. Find the retro's finding text in rules-kit (`rules-kit list`) for the exact problem.

Success criterion: tests show the hook passes every named exception and flags a status-like reply with free text beside the blocks; lint and tests green.
