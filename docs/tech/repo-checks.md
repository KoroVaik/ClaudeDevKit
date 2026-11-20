# Repo checks

Code: `tools/lint.py`, `.githooks/pre-commit`, `.github/workflows/ci.yml`, `plugins/dev-kit/scripts/check_docs.py`.

## Lint

`python tools/lint.py` checks manifests, skills, agents, slot tables and the profiles of the projects in
`tools/projects.json` (local, not in git: `{"name": "folder"}`). It also fails on `$<digit>` or `$ARGUMENTS` in a
skill or agent body: Claude Code replaces them with the call's arguments, so a sum is written as `1 USD`.

## Pre-commit

`.githooks/pre-commit` runs the lint before every commit, together with `claude plugin validate .`;
it is enabled with `git config core.hooksPath .githooks`. The validate step needs the Claude Code CLI, so
CI runs only the lint.

## CI

`.github/workflows/ci.yml` runs the tests and the lint on every push to `main` and on pull requests, with
Python 3.13 and Node 22.

## Docs check

`dev-kit-check-docs` lives in `plugins/dev-kit/bin` and is on the Bash tool PATH while dev-kit is enabled.
A git pre-commit hook outside Claude Code runs `plugins/dev-kit/scripts/check_docs.py --pre-commit`,
finding this folder through `~/.claude/plugins/known_marketplaces.json`. The rules of the check are in the
`dev-kit:documentation` skill.
