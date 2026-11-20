# Clean up finished plans

Owner's words: «так» to P's proposal «Запустити нову сесію «C: Прибрати завершені плани»? (у «In flight» лишаться лише живі задачі)» (2026-11-20).

## Task
PROGRESS.md «In flight» still lists finished work (docs migration, open questions, global rules vs the P format), and `plans/` holds plans whose work is built (for example docs-migration, global-rules-p, open-questions, no-filler, p-answers, p-messages, status-all, wait-push, backlog-review). Handle each finished plan as `dev-kit:documentation` says for a done plan (move what stays true into the docs, keep open items, delete the plan), and leave in «In flight» only live work.

Keep: plans/retro-tokens.md (waits on the owner's second /usage reading) and its «Open questions» item.

## Success criterion
Every plan left in `plans/` has open work; «In flight» lists only those; `dev-kit-check-docs` passes; no fact or open item from a deleted plan is lost.

## Paid spend
Total: $0

## Result
Nine finished plans deleted (all steps confirmed built). Moved to `docs/features/hand-work-to-the-project-lead.md`: two Known limits (reminder push wording and missed waits; why the five global rules stay) and one Open defect (a chat-only P question is lost on restart). BACKLOG «Track changes to the owner's global rules» marked fully built. «In flight» now lists only retro-tokens. P's own queue line about this task in «Open questions» left for P to clear. `dev-kit-check-docs`: 0 errors.
