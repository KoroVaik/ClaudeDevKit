# Plugin authoring

How the skills and agents of the plugins are written. Edits of them follow `dev-kit:edit-rules`.

## Rules

- A skill description says only when to use it and starts with "Use when"; it never summarizes the steps
  (an agent that reads a summary follows it instead of the skill).
- An agent sets `name`, `description` and `model` explicitly.
- Agents and skills are addressed as `<plugin>:<name>`, e.g. `dev-kit:coder`.
- Some skill descriptions contain Ukrainian phrases. They are trigger phrases the author types to start a
  skill, so they are meant to stay.
