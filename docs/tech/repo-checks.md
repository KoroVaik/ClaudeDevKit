# Repo checks

Code: `tools/lint.py`, `.githooks/pre-commit`, `.github/workflows/ci.yml`, `plugins/dev-kit/scripts/check_docs.py`.

## Lint

`python -X utf8 tools/lint.py` checks manifests, skills, agents, slot tables and the profiles of the projects in
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
No git hook runs it: this repo's `.githooks/pre-commit` runs only the lint and `claude plugin validate`, and no
plugin installs a hook in other projects. Agents run it on demand, and the skills `fix-bug`, `new-feature` and
`maintain-project-docs` run `dev-kit-check-docs --pre-commit` before finishing (the flag adds the advisory
lists for staged code files). The rules of the check are in the `dev-kit:documentation` skill. The check skips files that `.gitignore` ignores (all files are read outside a
git repository), so local untracked drafts raise no errors.
