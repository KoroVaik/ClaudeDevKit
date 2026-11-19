# Keep docs and tests in order

Part of the [ClaudeDevKit product](../product.md).

## What it gives

A project's docs follow one standard and its tests say what they protect, checked by programs instead of
by memory. The `dev-kit:documentation` skill is the standard and `dev-kit-check-docs` checks a project's
docs against it; `--structure` lists the base docs files a project lacks. `dev-kit:migrate-docs` moves a
project's existing docs onto the standard. `dev-kit-check-tests` and the `dev-kit:test-change` and
`dev-kit:prune-tests` skills keep the tests honest.

A git pre-commit hook outside Claude Code runs the docs check before a commit (how it finds the plugin:
[repo checks](../tech/repo-checks.md)).

## Features

- [Check that a test says what it protects](../features/check-that-a-test-says-what-it-protects.md)

## Not written yet

The docs check (`plugins/dev-kit/scripts/check_docs.py`) and `migrate-docs` have no feature files; their
rules stay in `plugins/dev-kit/skills/documentation/SKILL.md` and `plugins/dev-kit/skills/migrate-docs/SKILL.md`.
