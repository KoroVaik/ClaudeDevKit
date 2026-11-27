# Clean up scripts made for the owner

Epic: [Run a task through the process](../epics/run-a-task.md)

## Purpose
When a step needs the console, an agent writes a ready `.cmd` file for the owner to run (the owner's global rules,
«Chat replies»). The agent deletes it after the owner's «Готово», but a session that ends first leaves the file
behind, and an old file confuses the owner when he looks for a new one. Such files land in one folder and vanish by
themselves a day later; the owner never cleans them up.

## Rules
### Only the folder Claude on the desktop
A `.cmd` or `.bat` file written with the Write tool anywhere on the desktop (the usual one or OneDrive's) outside the
folder `Claude` is refused, and the reason names that folder. Files elsewhere (a project's own `build.cmd`) pass.
Why: L: Zhratva, 2026-11-26: `Zhratva - allow push main.cmd` lay on the desktop itself, outside the folder, for four
days; the owner: «там тіки старий файл який ти н прибрав схоже».

### A left file goes after a day
Each `.cmd` or `.bat` file written into the folder `Claude` is recorded with its time and the hash of its text. At
the start of any session on the machine, a recorded file older than a day is deleted if its text is unchanged. The
agent still deletes the file after «Готово»; this is the backstop for a session that ended first. Owner's «Так»,
2026-11-27: «старі файли на робочому столі зникатимуть самі».

### The owner's files stay
A file the hook did not record (one the owner put there himself) is never deleted. A recorded file whose text
changed counts as the owner's and stays.

How the hook works: [hooks](../tech/hooks.md).

## Acceptance criteria
- An agent writes `Claude/x.cmd`, its session ends with no «Готово»: a session started a day later deletes it.
- The owner's own `Claude/mine.cmd` next to it stays.
- A recorded file the owner edited stays.
- A Write of `Desktop/x.cmd`: refused, the reason names the folder `Claude`.

## Built in
- `plugins/pult/hooks/owner-scripts.py`
- `plugins/pult/hooks/hooks.json`
- `tools/tests/test_owner_scripts.py`
