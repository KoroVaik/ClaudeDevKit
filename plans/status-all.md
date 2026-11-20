# Status shows every session, unchanged ones in one line

Owner's words (2026-11-20, P: ClaudeDevKit): «Так» to «Показувати в кожному статусі всі сесії, а не лише
ті, що змінились?»; then «Проаналізуй це прохання чи не розтягне це сам репорт який повторюється»; then
«Так» to the variant: changed sessions are written as now, and all unchanged working sessions go in one
line «ще працюють: «A», «B»».

Source: BACKLOG.md entry «P's status messages hide sessions that keep working» (from P: Zhratva,
2026-11-20, owner: «Чому в статусі нема сесії аналізу?»).

## What the owner approved
In `plugins/dev-kit/skills/project-lead/SKILL.md`, «Message templates», «Which sessions a message
lists»: every message with «Статуси сесій» keeps the lines of sessions whose state changed (and
`готово` ones as now), and adds one last line `- ще працюють: «<name>», «<name>»` with every other
session P manages that still works (unchanged since the previous message). The line is left out when
there is none. The forced-output state and the start status keep listing every session as now. Update
the example if it shows the block, and the feature doc that describes it.

## Done when
The rule and example read as above; the BACKLOG entry is removed as built; dev-kit version bumped;
lint and docs check clean.
