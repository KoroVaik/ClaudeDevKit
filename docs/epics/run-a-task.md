# Run a task through the process

Part of the [ClaudeDevKit product](../product.md).

## What it gives

An agent given a task follows a fixed development process instead of skipping steps: plan, code, review,
test, update the docs. The `dev-kit` manager and task skills (`fix-bug`, `new-feature` and the others)
run the process; generic agents (coder, reviewer, investigator) do the steps.

Example: you tell Claude "the Save button does nothing". The `fix-bug` skill classifies the report (a
functional bug, not a layout bug), finds the root cause in code and writes a plan, then waits for your
yes. It writes a failing test, fixes the cause and runs the project's test command; runs a browser check
of the screen, if you allowed it; then updates the feature description in `docs/`, runs
`dev-kit-check-docs` and asks a separate `reviewer` agent to read the change.

## Slots

The core lists the process steps in [slots](../../plugins/dev-kit/slots.md). An extension plugin fills
slots in its own `slots.md` (`| Slot | Skill |`, skill as `<plugin>:<skill>`). The manager reads these
tables, not skill descriptions. A project may override a slot in its profile
([sections](../tech/project-profile.md)).

## Features

- [Start and stop the app](../features/start-and-stop-the-app.md)
- [Launch only the project's own agents](../features/launch-only-the-projects-own-agents.md)
- [Stop the known Windows shell traps](../features/stop-the-known-windows-shell-traps.md)

## Not written yet

The skills of the manager, `fix-bug`, `new-feature`, `brainstorm`, `discovery-round`, `showcase`,
`maintain-project-docs`, `edit-rules` and the generic agents have no feature files. Their rules stay in
the skill files (`plugins/dev-kit/skills`) until a feature is written from them.
