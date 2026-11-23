# Progress

## Built

- `dev-kit` 0.1.98 - the process skills, generic agents, the documentation standard and its checker, the project lead and its session tools (standard message kinds between sessions, one permission mode with hard bans), the per-project retro and the weekly docs upkeep, cost stated as a share of the weekly limit, the Windows shell-traps hook, the hook that refuses long foreground commands, the shared Claude API client with its spend log (`dev-kit-api`).
- `web-kit` 0.3.0 - browser checks and the two-stage screen design.
- `unity-kit` 0.2.1 - the Unity bridge, user check, scene sketch, GIFs.
- `pult` 0.1.21 - the hub: leads started at logon, the watcher that wakes sessions only on an event, the lead's move to a fresh session, the status page.
- Docs moved onto the documentation standard: [the docs index](docs/README.md).

## Top priorities

- Zhratva joins the shared spend log and the owner adds the API deny lines: [Open items](docs/features/log-and-reconcile-api-spend.md#open).
- Live check of the event-only wakes and of a push relayed by a lead: [Open items](docs/features/start-leads-at-logon-and-heal-them.md#open).

Open work of the features: `dev-kit-check-docs --open`.

## Open questions

- 2026-11-23 · «Ретро: ClaudeDevKit» · ❗: випускати оновлення інструментів не частіше раза на день? (менше перезапусків; виправлення на день пізніше) Рекомендую: так - найменша зміна, без нового коду.
