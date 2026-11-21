# The lead does not know what happened in a session

Owner's words (2026-11-21): «Чому ти питаєш? Я ж закрив обговорення вже», then «Запускай обговорення цьой проблеми, що ти не знаєш про статус сесії».

## Cases seen
- 2026-11-21: «Обговорення: Повідомлення між сесіями» asked the owner «Закриваю цю сесію обговорення?»; he said «Так» there. P did not read that transcript and asked him again in P's chat («закриваємо обговорення і запускаємо будову?»).
- 2026-11-20: P merged and closed «Обговорення: Токени Pult у простої» while the owner was still writing there (fixed in dev-kit 0.1.73: P reads the transcript before merge).
- P's status lines come from `dev-kit-sessions state` / `claude agents` (busy, idle, waiting) and the session's reports by SendMessage; what the owner answered inside a session reaches P only if that session reports it.
- The phase-1 server watcher (pult 0.1.16, dev-kit 0.1.78) now wakes leads on session events; see plans/pult-idle-cost.md.

## Cause of the 2026-11-21 case (checked in both transcripts)
- 12:11 D sent P its done report and asked the owner «Закриваю цю сесію обговорення?»; P read D's tail once and queued «закриваємо обговорення і запускаємо будову?».
- 12:19:16 the owner said «Так» in D; D sent P nothing after it. 12:19:37 P showed its stale queue item without re-reading D.
- So: a queue item outlives the owner's answer in the session; no rule makes P re-read a session before asking about it, and none makes D report the closing «Так».
- `dev-kit-sessions state` gives only the last assistant text; no command prints the owner's messages after a session's last question (pieces exist: `tail_entries`, `message_text` in sessions.py).

## Goal
Agree with the owner how P learns a session's real state and the owner's answers there before it writes a status or asks him anything; write it in «Owner's approval» here.

## Owner's approval
- 2026-11-21, owner's «так»: standard message kinds between all session types (P, Обговорення, C, other projects' leads). A short fixed list, each kind with its own first word (for example «ГОТОВО», «ПИТАННЯ», «ВЛАСНИК ВІДПОВІВ», «ЗАКРИТО», «ЗАСТРЯГ»); each session type's rules say which kinds it sends, so a receiver knows what to expect. Replaces «Обговорення sends P one line after the closing «Так»» (that becomes the «ЗАКРИТО» kind). Still open: P re-reads a session before asking or writing its status; P drops a queue item the owner already answered in the session. Touches the same skill texts as plans/cross-mode-messages.md (who may message whom), not against it.
- 2026-11-21, owner's «так» (to both open points): before any question to the owner or status line about a session, P reads what the owner wrote in that session after its last question or report (a new `dev-kit-sessions` command prints it; pieces `tail_entries`, `message_text` exist). If the owner already answered there, P drops that queue item silently and never asks him again.
- 2026-11-21: owner's «так» to the short plan; discussion closed.
