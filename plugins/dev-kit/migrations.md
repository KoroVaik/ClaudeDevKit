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

## 2. Rename the design profile sections (projects that enable web-kit)

- Added: dev-kit 0.1.49
- What: web-kit 0.2.0 merged its design skills and agents: `web-kit:design-screen` replaces draw-mockup and design-sandbox, the agent `web-kit:user` replaces mockup-user and app-user, the agent `web-kit:designer` replaces design-critic and mockup-checker. Their sections in the project profile `.claude/dev-kit.md` move to the new names.
- How: In a project that enables web-kit, merge `## mockup-user` and `## app-user` into one `## user` section and add to it, written once per project, the onboarding text the user agent reads: who the user is, what the app is for, its sections (taken from `docs/product.md` and the epics). Merge `## draw-mockup` and `## design-sandbox` into `## design-screen`. Move any `## design-critic` or `## mockup-checker` section to `## designer`. Keep each section's content; drop only exact repeats. Elsewhere in the profile (the `## manager` table, other sections' text), replace the old skill and agent names with the new ones. A project without web-kit changes nothing and only records the level. The project's CLAUDE.md rules for editing rule text apply, and rule text is edited through `dev-kit:edit-rules`.
- Owner choice: none
- Done when: the profile has no `## mockup-user`, `## app-user`, `## draw-mockup`, `## design-sandbox`, `## design-critic` or `## mockup-checker` section, and no old skill or agent name is left in it (`python tools/lint.py` in the plugin repo shows no error for the project).

## 3. Propose the hard bans once

- Added: dev-kit 0.1.50
- What: The owner is asked once per project whether to add the deny rules of `dev-kit:project-lead` "Hard bans", so the one-time proposal is tracked by the applied level instead of a promise nobody checks.
- How: Read the project's committed `.claude/settings.json` on main. If it already holds the deny lines of "Hard bans" that fit this project (each Bash line with its PowerShell twin), nothing is asked. Otherwise fill the set for this project: keep the push lines only where main deploys, put the real data folders and the owner's database file in place of the placeholders or drop those lines, drop the docker lines where the owner runs no containers. The filled lines go to P as the owner choice. No agent writes them: on a yes P gives the owner the hand action to add them to `.claude/settings.json` on main, and the C does not wait for it. Either way the C writes the answer in the profile's `## project-lead` table, row `| hard bans | accepted <date> / declined <date> / already present |`, then records the level. The project's CLAUDE.md rules for editing rule text apply, and rule text is edited through `dev-kit:edit-rules`.
- Owner choice: yes or no to the exact deny lines filled for this project.
- Done when: the profile has the `hard bans` row and `dev-kit-migrations pending` prints `none` (or lists only entries above 3).
