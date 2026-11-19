# ClaudeDevKit onto the dev-kit docs standard

<!-- docs-check: no-path-mentions -->

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

## State (C)
- Done. P's yes (2026-11-19) to rows A-H; the "Not checked" lines of deleted plans became Open items (P's change, also applied to design-flow, launch-fixes, memory-pressure, pult-version-watch).
- Checks run: `dev-kit-check-docs` 0 errors 0 warnings; `--structure` complete; `python tools/lint.py` 0 errors; `python -m unittest discover tools/tests` 548 OK.
- Reviewer (sonnet) findings fixed. Left open: those "Not checked" Open items go against the standard's line that not-yet-run checks are never written to docs; kept on P's explicit instruction.
- Glossary names wait for the owner's approval.
