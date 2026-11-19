# A lead restart never loses its mode

Owner's words (2026-11-19): «Так» to «Запустити нову сесію «C: Перезапуск без втрати режиму»? (керівник після перезапуску не втратить режим)».

## Problem
BACKLOG.md entry «A resume right after a stop can start a flag-less copy»: `claude --bg --resume` right after `claude stop`, even once `claude agents` shows `stopped`, can say «already running» and start a copy with the default model and mode (seen twice in the live check of plans/lead-bypass-mode.md; a wait of about 15 s avoided it).

## Goal
Every Pult restart or resume of a lead (and any P refresh of a C that resumes) starts the session with its own flags, never a flag-less copy. Remove the BACKLOG entry when built.

## Success criterion
A loop of 5 stop-then-resume runs on a throwaway bg session (cheap model, temp state) starts no copy without the flags; the restart code waits or retries until the old process is gone.

## Paid spend
0
