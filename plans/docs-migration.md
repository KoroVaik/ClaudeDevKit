# ClaudeDevKit onto the dev-kit docs standard

Owner's words (2026-11-19): «Так» to «Запустити нову сесію «C: Міграція документації»? (у проєкту з'являться файл прогресу й базові документи)». Approved earlier as point 5 of plans/open-questions.md («Owner's approval»).

## Checked facts
- `dev-kit-check-docs --structure` in the main checkout (2026-11-19) lists 7 missing: PROGRESS.md, docs/product.md, an epic in docs/epics/, a feature in docs/features/, docs/tech/map.md, a standard in docs/standards/, and the profile section `## All agents` in .claude/dev-kit.md.
- Without PROGRESS.md the lead's owner queue («Open questions») has no home.
- Existing docs to fold in: README.md, docs/plan.md, BACKLOG.md, plans/*.md.

## Goal
Run `dev-kit:migrate-docs` on this repo so the structure check passes, PROGRESS.md holds the lead's «Open questions» (move in the one waiting owner question: compare the usage counter one day for the Opus weight, from plans/retro-tokens.md), and nothing the existing docs say is lost.

## Success criterion
`dev-kit-check-docs --structure` reports nothing missing and `dev-kit-check-docs` passes; the waiting owner question is in PROGRESS.md «Open questions».

## Paid spend
0
