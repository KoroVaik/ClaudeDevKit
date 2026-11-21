# ClaudeDevKit

[![CI](https://github.com/KoroVaik/ClaudeDevKit/actions/workflows/ci.yml/badge.svg)](https://github.com/KoroVaik/ClaudeDevKit/actions/workflows/ci.yml)

Four plugins for [Claude Code](https://claude.com/claude-code) that give AI coding agents a fixed
development process: plan, code, review, test, update the docs. It is a personal tool for solo
developers who let agents write most of the code and want to stay in charge of the decisions.
The problem, the purpose, the plugins and their epics: [the product overview](docs/product.md). All
the docs: [the docs index](docs/README.md).

## Example

A project enables the plugins and you tell Claude: "the Save button does nothing". The `fix-bug` skill then:

1. classifies the report (a functional bug, not a layout bug), so it knows which check to run later;
2. finds the root cause in code and writes a plan, then waits for your yes;
3. writes a failing test, fixes the cause, and runs the project's test command;
4. runs a browser check of the screen, if you allowed it;
5. updates the feature description in `docs/`, runs `dev-kit-check-docs`, and asks a separate
   `reviewer` agent to read the change.

Enable it in a project:

```bash
claude plugin marketplace add <path to this folder>
claude plugin install dev-kit@korov-dev --scope project
```

The marketplace is a local folder, so it is a working setup, not a packaged release.

## Develop

Most of the repo is Markdown prompts; the code that runs as a program is listed in
[the map](docs/tech/map.md). The tests are in `tools/tests/`. Run them and the lint with:

```bash
python -X utf8 -m unittest discover tools/tests
python -X utf8 tools/lint.py
```

CI (`.github/workflows/ci.yml`) runs both on every push to `main` and on pull requests, with Python 3.13
and Node 22. The lint, the pre-commit hook and the docs check: [repo checks](docs/tech/repo-checks.md).
The rules for writing skills and agents: [plugin authoring](docs/standards/plugin-authoring.md). The
profile a project keeps for the plugins: [project profile](docs/tech/project-profile.md). The docs
standard: the `dev-kit:documentation` skill (`plugins/dev-kit/skills/documentation/SKILL.md`).

## After enabling a plugin

The install rewrites `.claude/settings.json`; check that existing hook fields (e.g. `onFailure`)
survived. Projects load the plugins in place from this folder (`claude plugin list --json` shows
`readFromFolder` and `folderVersion`), so a change reaches every project at its next session start;
no `claude plugin update` is needed. The `version` that the list and `installed_plugins.json` show only
records the install and may lag behind. A session that was already running sees a new agent or skill
only after `/reload-plugins`.
