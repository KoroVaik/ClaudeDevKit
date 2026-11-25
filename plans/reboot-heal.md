# Plan: task sessions survive a PC reboot

Status: not started (2026-11-25).

Owner's words: «Так» to «Запустити нову сесію «C: Сесії після перезапуску ПК»? (після перезапуску ПК фонові сесії підніматимуться самі)» (P: ClaudeDevKit, 2026-11-25).

Source: BACKLOG.md entry «Lead: do not end a task whose session died in a reboot» (cause with file:line, fix, cheapest test). Remove the entry when built.

Success criterion: a registry with one active C whose process is gone; a fresh lead runs its start steps; the record stays `active`, `state` does not report a plain `gone` inside the grace, and the Pult watcher respawns the C (or sends `gone:` after it fails). The lead skill says a lead never ends a C on `state` alone.

Spend: -
