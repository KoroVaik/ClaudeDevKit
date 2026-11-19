# Check that a test says what it protects

Epic: [Keep docs and tests in order](../epics/keep-docs-and-tests-in-order.md)

## Purpose
Every test added to a project carries a mark that says what it protects, so tests that protect nothing
stand out. Old tests get their marks in one pass and the clearly low-value ones are removed.

## Rules
### Every new test has a valid mark
`dev-kit-check-tests` checks that every test added since `HEAD` (or `--base REF`) carries a valid
"protects" mark (`Flow`, `Rule`, `Bug`, `Edge`) in xUnit, Vitest or Python unittest syntax, as the
`dev-kit:test-change` skill requires.

### The report shows marks and uncovered endpoints
`--report` prints marks per domain and the API endpoints that no integration test mentions (a
path-mention measure); `--json` gives the same for showcases.

### Suspect tests are listed
`--suspects` lists the tests marked `Suspect: <why>`: they may protect nothing. An agent that changes their
code verifies them.

### Old tests get marks in one pass
The `dev-kit:prune-tests` skill gives old tests their marks in one pass, domain by domain. It also deletes
clear low-value tests and duplicates.

## Acceptance criteria
- A test is added without a mark: `dev-kit-check-tests` names it and the check fails.
- A test is added with a valid mark in the project's test syntax: the check passes.
- `dev-kit-check-tests --report` shows the marks of each domain and the endpoints no integration test mentions.
- `dev-kit-check-tests --suspects` lists every test marked `Suspect: <why>`.
- After a `dev-kit:prune-tests` pass a domain's old tests have marks and its duplicates are gone.

## Built in
- `plugins/dev-kit/scripts/check_tests.py`
- `plugins/dev-kit/bin/dev-kit-check-tests`
- `plugins/dev-kit/skills/test-change`
- `plugins/dev-kit/skills/prune-tests`
- `tools/tests/test_check_tests.py`
