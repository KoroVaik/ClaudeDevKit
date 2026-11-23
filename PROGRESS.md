# Progress

## Built

- `dev-kit` 0.1.104 - the process skills, generic agents, the documentation standard and its checker, the project lead and its session tools (standard message kinds between sessions, one permission mode with hard bans), the per-project retro and the weekly docs upkeep, cost stated as a share of the weekly limit, plugin updates timed by a critical or routine mark, the Windows shell-traps hook, the hook that refuses long foreground commands, the shared Claude API client with its spend log (`dev-kit-api`).
- `web-kit` 0.3.0 - browser checks and the two-stage screen design.
- `unity-kit` 0.2.1 - the Unity bridge, user check, scene sketch, GIFs.
- `pult` 0.1.22 - the hub: leads started at logon, the watcher that wakes sessions only on an event, the lead's move to a fresh session, the status page.
- Docs moved onto the documentation standard: [the docs index](docs/README.md).

## Top priorities

- Zhratva joins the shared spend log and the owner adds the API deny lines: [Open items](docs/features/log-and-reconcile-api-spend.md#open).
- Live check of the event-only wakes and of a push relayed by a lead: [Open items](docs/features/start-leads-at-logon-and-heal-them.md#open).

- P moves itself like a release (owner «так», 2026-11-23, P: ClaudeDevKit chat): no «Перезапустити мене зараз?» question and no push; quiet (owner silent 5 min, no open question) -> silent move; otherwise the CAPS warning, then the move 30 s later, as in «Restart for a plugin update». Weak spot accepted: while the owner keeps writing, the move waits. Built and merged (dev-kit 0.1.106).

- Restart notice (owner «все так», 2026-11-23): no warning to child sessions; a C retries a failed send to P itself, P drops its «resend» message. Plan: `plans/restart-notice.md` «Owner's approval». Built and merged (dev-kit 0.1.104).

- Own docs of Claude app quirks (owner «так» to the plan, 2026-11-23, «Обговорення: Нюанси Claude у різних застосунках»): one facts file in dev-kit, a facts agent, collection through the retro scan, weekly re-checks. Built and merged (dev-kit 0.1.105), [plan](plans/claude-quirks-docs.md).

- No "session started" push on P self-move and from C sessions (owner «+», 2026-11-23): self-move resumes the same session with `/clear`, a C starts with no phone link. Built and merged (dev-kit 0.1.106, pult 0.1.24); retro and docs sessions too. Plan: [plans/push-noise.md](plans/push-noise.md).

Open work of the features: `dev-kit-check-docs --open`.

## Open questions





