# Pult takes new rules by itself

Owner's words: «Так» to «Запустити нову сесію «C: Pult бере нові правила»? (зміни Pult доходитимуть до нього самі)» (2026-11-19).

## Problem (checked 2026-11-19, see plans/push-notifications.md, Built)
- Nobody runs `claude plugin update pult@korov-dev`: Pult ran pult 0.1.0 from the plugin cache from 2026-11-15 to 2026-11-19.
- A resumed Pult keeps its old rules, so pult rule changes never reach it.
- Now installed: pult 0.1.10 (updated by P 2026-11-19); the running Pult has not restarted on it yet.

## Goal
After a pult change is merged into main of ClaudeDevKit, the installed pult is updated and Pult runs on the new rules and scripts, with no hand step from the owner. Same check for dev-kit, web-kit and unity-kit if they have the same gap.

## Success criterion
A pult version bump merged into main reaches the installed plugin and the running Pult (its rules and watchers) within the existing restart flow, shown on one live bump.

## Paid spend
0
