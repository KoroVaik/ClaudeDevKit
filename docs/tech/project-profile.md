# Project profile

A project that enables the plugins keeps its facts in one file, `.claude/dev-kit.md`. The plugins hold no
project facts. Code: `plugins/dev-kit` (the profile is read by its skills, agents and scripts) and
`tools/lint.py` (which checks the profiles of the projects in `tools/projects.json`).

## Sections of dev-kit

- `## All agents` - orientation files, processes agents never touch, shared rules.
- `## Slots` - optional table `| Slot | Skill or command |` that overrides a slot for this project; only
  `run-app` and `stop-app` may have several rows (a list of commands).
- `## <agent or skill name>` - rules for one role, e.g. `## reviewer`; they override the plugin defaults.
- `## project-lead` - optional table `| Path | How |`: the git-ignored paths a fresh worktree needs, each
  `copy` or `link` (a junction to the main checkout's folder). A `| Setting | Value |` table there holds
  `migrations applied`: the last entry of `plugins/dev-kit/migrations.md` the project has applied (written
  by `dev-kit-migrations record`).
- `## documentation` - table `| Setting | Value |` for the docs check (code folders, scanned folders, size
  limits); the setting names are listed in `plugins/dev-kit/scripts/check_docs.py`.

## Sections of web-kit

- `## e2e-check` - URLs, login, screenshot folder, test-data marker; read by every browser skill and agent.
- `## ui-tester`.
- `## visual-check`.
- `## layout-checker` - sizes.
- `## design-screen` - mockups folder, palette, languages, sandbox URL, checks, shot window.
- `## user` - onboarding of the ordinary user: who you are, what the app is for, its sections.
- `## designer` - UI standard, mockup folders, report language.

## Sections of unity-kit

- `## unity-editor` - the bridge, its wrapper command, versions, scene, build targets, devices, Profiler.
- `## unity-operator`.
- `## user-check` - table `| Setting | Value |`: the bridge, recipe and report folders, scene, state command and
  "ready", click command, panel scale; the format is in `plugins/unity-kit/skills/user-check/SKILL.md`.
- `## game-view-check` - the screenshot command.
- `## game-clip` - the frame-recording command, where the frames and their time index land.
- `## scene-sketch` - subject, names, caption language.
