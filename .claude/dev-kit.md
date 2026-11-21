# dev-kit profile

## project-lead

| Setting | Value |
|---|---|
| migrations applied | 4 |
| hard bans | present 2026-11-21 |
| docs migration | offered 2026-11-19: yes |

## All agents

- Orientation: `docs/README.md` (index of the docs), `docs/tech/map.md` (code folders), `README.md` (install and develop commands).
- The plugins under `plugins/` are the product: their skills, agents, `slots.md` and `rules/` are edited through `dev-kit:edit-rules`.
- Never kill the running Pult servers or project leads by hand; stop or restart them only with the Pult scripts (`plugins/pult/rules/hub.md`, section "Servers").
- Checks: the commands in `README.md`, section "Develop".

## documentation

| Setting | Value |
|---|---|
| code-root | plugins 3 |
| code-root | tools 1 |
| scan | .claude: .md |
| skills-lock | none |
| file-ext | .py .ps1 .psd1 .mjs .cs .json .css .md .sh .yml .html |
