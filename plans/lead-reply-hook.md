# Stop hook: a lead's reply keeps the message form

Status: done (C: Перевірка форми відповіді керівника), dev-kit 0.1.128.

Source: «Ретро: ClaudeDevKit», 2026-11-25, task line: «Stop-hook, що перевіряє, що відповідь керівника порожня або починається з жирного заголовка блоку» (retro finding lead-message-form). Started by P with no owner ask (dev-kit:project-lead, «Retro of session problems»).

Caution from P: a lead's reply has named exceptions to the bold blocks (dev-kit:project-lead, «Message templates», «Exceptions»): the one line after starting an «Обговорення:» session, the push-test steps, the CAPS restart lines, and P's other replies to the owner's own questions (global caps, no blocks). The hook must not block those; prefer a narrow check (for example only turns woken by a session or event message, not by an owner message) and a soft nudge over a hard block. Find the retro's finding text in rules-kit (`rules-kit list`) for the exact problem.

Success criterion: tests show the hook passes every named exception and flags a status-like reply with free text beside the blocks; lint and tests green.

## Result

- `plugins/dev-kit/hooks/lead-reply-form.py`, a Stop hook in `plugins/dev-kit/hooks/hooks.json`. Lead only (title «P: »). Checks only a turn woken by a session message, a Pult event, a subagent notice or a timer, and not while the owner's last message still has no reply (P's answer to the owner keeps the global caps). Passes an empty reply, the named one-liners (discussion start and close, push test steps, the restart lines, the forced-output «Зараз нічого не працює...» line) and the bold blocks; flags text before, between or after the blocks, except a last paragraph that ends with a question, «+ або -» or a `Рекомендую:` line.
- Soft nudge: `decision: block` with a reason telling P not to resend or correct the message and to end the step with no text; never twice in a row (`stop_hook_active`); any error exits 0 silently.
- Replay on 8 recent real lead transcripts: the flagged replies were free notes («Готую питання...», English status notes, notes after the blocks), i.e. the retro's problem; no flagged reply was a named exception after the «+ або -» fix.
- Risk to watch: if the host demands visible text after the hook's extra step (`claude-facts.md`, "The host forces a visible reply on some wake-ups"), P sends the forced-output state once. Stop hook input fields are taken from official plugins, not from a dump here; the hook reads only `transcript_path` and `stop_hook_active`.
- Tests: `tools/tests/test_lead_reply_form.py`.

Spend: ~0.3% of the weekly limit, estimate; API: 0 USD
