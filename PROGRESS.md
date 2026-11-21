# Progress

## Built

- `dev-kit` 0.1.80 - the process skills, generic agents, the documentation standard and its checker, the project lead and its session tools.
- `web-kit` 0.2.2 - browser checks and the two-stage screen design.
- `unity-kit` 0.2.1 - the Unity bridge, user check, scene sketch, GIFs.
- `pult` 0.1.16 - the hub: leads started at logon, the watcher, the status page.
- Docs moved onto the documentation standard: [the docs index](docs/README.md).

## In flight

- [Token spend in the retro](plans/retro-tokens.md): built; Opus weight set to 1.5 from the /usage readings (plan, «Opus weight check»); the spend trial is compared in a later retro.

- [Pult idle cost](plans/pult-idle-cost.md): design in «Owner's approval», owner's «так» to the plan (2026-11-20); phase 1 build: «C: Пробудження лише на події».

- [Messages between modes](plans/cross-mode-messages.md): plan approved, discussion closed (2026-11-21), owner wants the build started at once; one mode `bypassPermissions` for all dev-kit sessions (2026-11-20); ClaudeDevKit bans: `rm -rf` only; Prishch's lines added by the owner from a ready list; Pult and its sessions bypass too; bans cannot be declined; a C messages only its own P unless its brief allows more.

- [Lead sees sessions](plans/lead-sees-sessions.md): discussion; agreed: standard message kinds between all sessions; P re-reads a session before asking or a status, drops items the owner answered there; plan approved, discussion closed (2026-11-21); next: build.

Open work of the features: `dev-kit-check-docs --open`.

## Open questions

- 2026-11-21 · «C: Один режим для всіх сесій» · ❗: Ставимо заборони? ClaudeDevKit: агентам не можна стирати папки .git і plugins. Prishch: не можна примусово переписувати чи видаляти гілки на GitHub, стирати архів логів і правити налаштування дозволів. Рекомендую: так - лише незворотні дії, звичайна робота не зачеплена.
