# dev-kit profile

## project-lead

| Setting | Value |
|---|---|
| migrations applied | 4 |
| hard bans | present 2026-11-21 |
| docs migration | offered 2026-11-19: yes |

## All agents

- Orientation: `docs/README.md` (index of the docs), `docs/tech/map.md` (code folders), `README.md` (install and develop commands).
- The plugins under `plugins/` are the product: their skills, agents, `slots.md` and `rules/` are edited through `rules-kit:edit-rules`.
- Never kill the running Pult servers or project leads by hand; stop or restart them only with the Pult scripts (`plugins/pult/rules/hub.md`, section "Servers").
- Checks: the commands in `README.md`, section "Develop".
- A commit that bumps a plugin's version (`dev-kit`, `pult`, `web-kit`, `unity-kit`, `rules-kit`, `spend-kit`) adds its
  release mark to that plugin's own `plugins/<plugin>/releases.json` (create it when missing):
  `"<version>": {"kind": "critical" | "routine", "date": "<YYYY-MM-DD>", "reason": "<one line>"}`, optionally with `"clean": true` (below). Critical only
  when agents cannot cope without it: messages lost, sessions stuck or looping, a Lead or Manager cannot do its job,
  harm to data; everything else is routine (a missing mark counts as routine). The Pult watcher restarts the
  leads for a routine release on a later day at a quiet moment, for a critical one the same day
  (`plugins/dev-kit/skills/project-lead/SKILL.md`, "Restart for a plugin update"). One bump, so one mark, for
  the whole merged result. Why: owner, 2026-11-23 (`plans/update-timing.md`): a restart per bump cut into
  talks with the owner several times an hour.
  The mark also gets `"clean": true` when the release renames or changes something a running Lead holds in its
  context: a session name prefix, a role or term name, a command or script name, a message or event-line format,
  a fixed line the Lead writes. Everything else (fixes, new rules that rename nothing) gets no `clean` field. A
  clean release restarts the Lead with a clean context (a handoff and `/clear`) instead of resuming its
  conversation; the timing still follows the kind. Why: owner, 2026-11-26 (`plans/lead-early-clear.md`): after
  dev-kit 0.1.135 renamed the session prefixes, a resumed Lead in Zhratva still started sessions with the old ones.

## documentation

| Setting | Value |
|---|---|
| code-root | plugins 3 |
| code-root | tools 1 |
| scan | .claude: .md |
| skills-lock | none |
| file-ext | .py .ps1 .psd1 .mjs .cs .json .css .md .sh .yml .html |
