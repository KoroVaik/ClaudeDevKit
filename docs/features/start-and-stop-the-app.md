# Start and stop the app

Epic: [Run a task through the process](../epics/run-a-task.md)

## Purpose
An agent starts the project's application to check a change and stops it afterwards, with the project's
own commands run in the right order.

## Rules
### Several commands, one row each
The `run-app` and `stop-app` slots of a project's profile may list several commands, one row each, in
start order.

### The plugin only sequences the project's commands
`dev-kit-app start` runs the run-app commands in order, `dev-kit-app stop` the stop-app commands in
reverse, `dev-kit-app list` shows both. The plugin only sequences the project's commands: what may be
stopped (the owner's processes) is decided by the project's own helpers.

### Teardown when the work is done
The skills that start the application run the teardown when the owner says the work is done, or at a
handoff.

The queue between worktrees and the rest of the rules: [slots](../../plugins/dev-kit/slots.md).

## Acceptance criteria
- A profile lists three run-app rows: `dev-kit-app start` runs them in that order and `dev-kit-app list` shows them.
- The owner says the work is done: the stop-app commands run in reverse order.
- A stop-app helper refuses to stop one of the owner's processes: the plugin does not override it.

## Built in
- `plugins/dev-kit/bin/dev-kit-app`
- `plugins/dev-kit/scripts/run_app.py`
- `plugins/dev-kit/slots.md`
- `tools/tests/test_run_app.py`
