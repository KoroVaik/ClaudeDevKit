# Session watcher and the lead's task report

Owner's yes, 2026-11-15 (P: ClaudeDevKit chat).

## Problem (seen in P: Zhratva, 2026-11-15)
- Every idle notice from a C ("turn ended", also when all is fine) wakes P; the host then forces a
  visible reply, so the owner gets many small repeated messages ("Чекаю на підтвердження").
- The Task done report mixes the result, C's open questions with no recommendations, an owner action
  and no next proposal, in one block with no sections.

## What to build
1. A generic watcher command in `plugins/dev-kit/scripts/sessions.py` (e.g. `dev-kit-sessions watch`):
   given session ids (or the registry's active C sessions), it polls `claude agents --json --all`
   about once a minute, stays silent while they live, and exits with a clear line when one is gone,
   stopped or closed (that exit wakes the caller). Hard time limit (e.g. `--max-minutes`, default about
   2 h); on the limit it exits with a distinct line so P just re-arms it silently. Generic: Pult may later
   call it for the leads instead of its own polling in Pult `scripts/watch-servers.ps1` (read it for the
   approach; never edit Pult).
2. project-lead SKILL.md: P no longer uses `notify_when_idle` for C sessions; it runs the watcher in the
   background (Bash tool, run_in_background) and wakes only on a C report (SendMessage) or a watcher exit.
   A watcher exit on the time limit: re-arm, no text. A watcher exit on a gone C: the stuck template.
3. Task done template becomes one message with three sections: `### Готово` (result in plain words),
   `### Потрібно від тебе` (numbered yes/no questions, each with `Рекомендую: так/ні - <reason>`; the
   C's open questions and any owner action go here), `### Далі` (the next proposal). One message per event;
   never several small ones.
4. Tests, lint, dev-kit version bump, README if it describes this.

Example (Task done):
### Готово
«Каталог продуктів»: парсер читає всі сторінки товарів, КБЖУ і штрихкоди Fozzy.

### Потрібно від тебе
1. Зберегти або відкласти правку CLAUDE.md, бо без цього злиття не піде.
   Рекомендую: так - її, мабуть, робить твоя сесія «Неоднозначні факти арбітра».
2. Видалити скрипт пілотного збору, яким ніхто не користується?
   Рекомендую: так - він лише заважає.

### Далі
Запустити сесію на «Пілотна схема імпорту»? (імпорт знову проходитиме перевірку)
Рекомендую: так - від тебе нічого не треба.

## Success criterion
A live run: P with a running C gets no idle wake-ups; killing the C (`claude stop`) wakes P within
about 2 minutes via the watcher.

Also in this task (P's message, owner's yes): the brackets after each session and next item start with
«від тебе:» (e.g. «(від тебе: нічого)»).

## Status (2026-11-15): built in dev-kit 0.1.29
- `dev-kit-sessions watch` (registry or `--id`), one watcher per project (heartbeat lock; a killed
  watcher's lock is taken over after 3 intervals), quiet when the last C ends, unit tests in
  `tools/tests/test_sessions.py`.
- Checked live: a haiku test P ran the watcher in the background and ended its turn; `claude stop` of a
  test C woke it 11 s later with `gone: test: watcher C | 29cee214 | done`. An idle C keeps its `pid`,
  so a C waiting on the owner is not reported as gone.
- Not checked yet: the full success criterion with a real P on the new skill (needs a P restart after
  the merge). Seen in that test: a session with a background shell shows `working busy` in
  `claude agents`, so a P with a running watcher looks busy there (Pult reads that state).
