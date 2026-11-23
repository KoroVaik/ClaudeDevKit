# Fewer "session started" pushes on restarts

Status: discussion with the owner (Обговорення: Пуш-повідомлення про запуск сесій).

## Owner's words

«запусти обговорення стосовно пуш повідомлень. Зараз мені іде купа повідомлень про те що сесія запущена, хоча це просто перезапуск існуючой. Треба думати над воркераундом» (2026-11-23, P: ClaudeDevKit chat).

## Known context (from the lead, to check)

- Every launch with `--remote-control` pushes «Remote control enabled» to the owner's phone, and no setting turns it off (project-lead SKILL.md, "Start a C", 2026-11-20). That is why a C gets no `--remote-control`.
- Sessions that still launch with it: leads (P) started by Pult, «Обговорення:» sessions, and their restarts (Pult watcher: plugin-update restarts, self-move of P, `claude respawn` of a crashed session).
- With releases marked routine/critical (dev-kit 0.1.103) leads restart less often, but each restart still pushes.

## Success criterion

The owner no longer gets a "session started" push when an existing session is only restarted or moved; a push for a truly new session the owner must open stays only where the owner agrees it is useful.

## Owner's approval

(written by the discussion session on the owner's «так»)
