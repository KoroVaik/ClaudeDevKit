# Watcher that fixes mechanical issues (Pult)

## Owner's words (2026-11-16)

Owner's «так» to P's proposal: «Запустити нову сесію «C: Сторож, що сам лагодить збої»? (мертвий сервер
піднімається без тебе)».

Source, BACKLOG.md entry «Pult: watcher that fixes mechanical issues»:
- What: merge the watcher with server autorun so it fixes mechanical issues itself (dead server, stale queue
  locks) and keeps a health log the hub reads; the hub fixes the rest within its competence.
- Why: today the watcher only logs and the owner restarts by hand.
- Cheapest test: let the watcher restart one dead lead after the owner's yes and check the log lines.

## Scope

- plugins/pult/scripts/watch-servers.ps1 (and start-servers.ps1 / resume-lib.ps1 where needed): when a lead or
  the Pult server is dead, restart it the same way start-servers.ps1 does (resume the same conversation, same
  flags), with a limit on retries, and write each action to the health log the hub already reads.
- Stale locks the plugins leave (for example dev-kit-app queue locks, the sessions watcher lock) only when the
  owning process is gone.
- Never restart a session that is alive, and never touch task sessions (C) or owner sessions.
- The Pult rules (rules/hub.md) say what the hub shows from the log.

## Success criterion

- A test with a throwaway lead-like session (not a real lead): kill it, the watcher brings it back on its next
  round, the log has the lines. A test on a real lead only after P's yes (P asks the owner).
- README and BACKLOG entry updated; pult version bumped.
