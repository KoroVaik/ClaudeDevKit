# dev-kit migrations

Changes that each project with a lead must make in its own files when dev-kit moves on. Entries are numbered 1, 2, 3... in
the order they were added and are never renumbered or removed. A project's applied level is kept by `dev-kit-migrations`;
an agent applies each pending entry under the project's own rules (its CLAUDE.md), then records the level.
Who applies them and when: `dev-kit:project-lead`, "Apply dev-kit migrations". An entry is added only after the
owner's yes; a choice that differs per project goes in `Owner choice`.

## 1. Record the applied migration level in the profile

- Added: dev-kit 0.1.44
- What: The project profile `.claude/dev-kit.md` gets, in its `## project-lead` section, a `| Setting | Value |` table with the row `| migrations applied | <n> |`, so the lead knows which entries are done.
- How: Create the profile and the section if they are missing (a new profile starts with a `# dev-kit profile` heading). Write the row with `dev-kit-migrations record <n>`, where n is the number of the last entry applied; nothing else changes. The project's CLAUDE.md rules for editing rule text apply, and rule text is edited through `dev-kit:edit-rules`.
- Owner choice: none
- Done when: `dev-kit-migrations pending` prints `none` (or lists only entries above 1).
