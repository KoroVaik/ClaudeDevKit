# Tracking the usage limits

Status: discussion with the owner (Обговорення: Відстеження лімітів).

Owner's words (2026-11-23, P: ClaudeDevKit chat): «Також потрібно поговорить про відслідковування лімітів».

Known context (to check): sessions stop on the usage limit; the Pult watcher logs `LIMIT ... (resets <time>)` and P shows `стоїть, скінчився ліміт (до <time>)`; the subscription spend line per task is an estimate (dev-kit:manager, «Stating the cost of work»); API spend has its own log and weekly Console check (`docs/features/log-and-reconcile-api-spend.md`). A separate build «C: Сесії самі продовжують після ліміту» (plans/limit-resume.md) makes sessions resume after the reset; this discussion is about tracking, not resuming.

## Owner's approval

(written by the discussion session on the owner's «так»)
