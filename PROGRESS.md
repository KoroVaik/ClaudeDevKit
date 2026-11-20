# Progress

## Built

- `dev-kit` 0.1.72 - the process skills, generic agents, the documentation standard and its checker, the project lead and its session tools.
- `web-kit` 0.2.1 - browser checks and the two-stage screen design.
- `unity-kit` 0.2.1 - the Unity bridge, user check, scene sketch, GIFs.
- `pult` 0.1.15 - the hub: leads started at logon, the watcher, the status page.
- Docs moved onto the documentation standard: [the docs index](docs/README.md).

## In flight

- [Token spend in the retro](plans/retro-tokens.md): built; Opus weight set to 1.5 from the /usage readings (plan, «Opus weight check»); the spend trial is compared in a later retro.

Open work of the features: `dev-kit-check-docs --open`.

## Open questions

- 2026-11-20 · «P»: Записати правило: перед новим нагадуванням після перезапуску я перевіряю, чи старе ще живе? (сьогодні нагадування спрацювало 4 рази) Рекомендую: так - старі нагадування пережили перезапуски, тож я їх дублював.
- 2026-11-20 · «Pult» питає: починати розмову Pult з чистого аркуша раз на день? (старі повідомлення в його чаті зникнуть) Рекомендую: так - кожне пробудження Pult зараз перечитує дні розмови за повну ціну. Context: Pult wakes about every 2 h on its log watcher time limit (watch-log.py --max-minutes default 120, self-imposed) and re-reads a 1.5 MB conversation with a cold cache. P will also lengthen the watcher limit (no visible change), asked or not.
