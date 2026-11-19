# Launch only the project's own agents

Epic: [Run a task through the process](../epics/run-a-task.md)

## Purpose
A session in a project can start only the agents that belong to that project, so a task never runs on a
stray agent type.

## Rules
### Allowed agents
A project may launch only its own agents (`.claude/agents/*.md`), the agents of its enabled plugins
(`<plugin>:<agent>`) and the user-level `other-repo-editor` that the owner's global rules name.

### Everything else is denied
Built-in and user agent types are denied.

How the hook works: [hooks](../tech/hooks.md).

## Acceptance criteria
- A session launches `dev-kit:coder` in a project that enables dev-kit: allowed.
- A session launches an agent of the project's `.claude/agents`: allowed.
- A session launches a built-in agent type: denied.

## Built in
- `plugins/dev-kit/hooks/narrow-agents.py`
- `plugins/dev-kit/hooks/hooks.json`
- `tools/tests/test_narrow_agents.py`
