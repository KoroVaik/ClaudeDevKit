# Progress

## Built

- `dev-kit` 0.1.88 - the process skills, generic agents, the documentation standard and its checker, the project lead and its session tools, the Windows shell-traps hook, the shared Claude API client with its spend log (`dev-kit-api`).
- `web-kit` 0.2.2 - browser checks and the two-stage screen design.
- `unity-kit` 0.2.1 - the Unity bridge, user check, scene sketch, GIFs.
- `pult` 0.1.19 - the hub: leads started at logon, the watcher, the status page.
- Docs moved onto the documentation standard: [the docs index](docs/README.md).

## In flight

- [Token spend in the retro](plans/retro-tokens.md): built; Opus weight set to 1.5 from the /usage readings (plan, «Opus weight check»); spend trials were replaced by ordinary retro items (plans/retro-scope.md).

- [Pult idle cost](plans/pult-idle-cost.md): design in «Owner's approval», owner's «так» to the plan (2026-11-20); phase 1 build: «C: Пробудження лише на події». Phase 2 (lead self-handoff by the server watcher, plan point 12): owner's «так» 2026-11-21 to start it right after «C: Один режим для всіх сесій» merges. Live check 2026-11-21: P moved itself to a fresh session and the owner's phone chat followed it.

- [Messages between modes](plans/cross-mode-messages.md): plan approved, discussion closed (2026-11-21), owner wants the build started at once; one mode `bypassPermissions` for all dev-kit sessions (2026-11-20); ClaudeDevKit bans: `rm -rf` only; Prishch's lines added by the owner from a ready list; Pult and its sessions bypass too; bans cannot be declined; a C messages only its own P unless its brief allows more.

- [Lead sees sessions](plans/lead-sees-sessions.md): discussion; agreed: standard message kinds between all sessions; P re-reads a session before asking or a status, drops items the owner answered there; plan approved, discussion closed (2026-11-21); next: build.

- [Windows traps hook](plans/windows-traps-hook.md): built (dev-kit 0.1.86); still open: the 20-call catalogue-judge batch in Zhratva to count failed calls.

- [Shared Claude API client](plans/api-client.md): dev-kit side built (dev-kit 0.1.87); next: the deny lines for the owner and the Zhratva handoff (both in the plan).

- [Retro for project problems](plans/retro-scope.md): discussion; agreed (plan, «Owner's approval»): dev-kit projects only, agent-work problems only, per-project local item folders, a background check of every plugin change, owner sees only disputed or high-impact items in a weekly ask; the reviewer applies trivial fixes itself (weekly list, one-word revert); collection on session end and retro start on session start by dev-kit hooks, no Pult; discussion closed 2026-11-22; next: build (start with the hook check, then the scan split).

- [Cost as a share of the subscription limit](plans/cost-share.md): built (dev-kit 0.1.91): cost in % of the weekly limit, `dev-kit-retro session`, status line calibration.

Open work of the features: `dev-kit-check-docs --open`.

## Open questions

