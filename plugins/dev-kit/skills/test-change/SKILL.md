---
name: test-change
description: Use when a change needs checking during `dev-kit:new-feature` or `dev-kit:fix-bug`, or when the owner asks directly for a test run.
---

# Test a change

Follow the owner's requested scope; a request for a focused run does not require a full run. The
project's own commands, test inventory and selection tables come from the `run-tests` slot (core
`slots.md`, the profile's `## Slots`); read the profile section `## test-change` of
`.claude/dev-kit.md` if it exists, it overrides the defaults here.

## Choose the scope by impact

- Inspect the affected consumers of the changed behaviour before choosing. Explain the concrete
  reason for broadening coverage; use the full suite if the impact across areas cannot be safely
  bounded.
- Local fixes: run targeted tests of the changed behaviour and the affected integrations. A change
  confined to one part that has its own tests (a script, a tool) runs those tests, not the whole
  suite. Rules and docs-only edits use format and consistency checks, without application builds or
  test suites.
- While editing, prefer the cheapest relevant checks; run a specific slower test when needed to verify
  the behaviour or diagnose a failure. Do not repeat the full suite after each edit.
- Run the full suite once, on final code, only for shared infrastructure, database schema or
  persistence, broad impact across areas, or an explicit request. Editing a test or reaching
  finalization alone does not trigger it. After a failure, diagnose and retry focused cases; repeat
  the full run only if the final change still meets these criteria. Once the relevant checks pass,
  stop optional testing.

## Run and report

- Build the current code; never use stale builds for a final check. Skip a rebuild only after a
  successful build of the current code in the same configuration.
- A selection with no cases is not a passed check. Report the absent coverage; do not add tests
  merely to populate a category. Add isolated tests when new logic can be checked without slow
  infrastructure (a database, a browser). Tag new tests as the project's test rules say. Inspect
  what a selection actually matches instead of keeping a duplicate list of test names.
- Report the command, the actual passed, failed and skipped counts, runner time and total time.
  Verify that temporary resources the tests created are cleaned up, and preserve the owner's
  processes.

## Interface and UI order

After the final tests pass, verify a changed interface (an API, a command, a saved format) on the
single local environment; skip live checks when the interface did not change. Restart the
application with the `run-app` slot when fresh code is needed. Use test data marked as the project's
rules say, remove it after the check and stop the processes the agent started. Show the command and
the actual result. Fix failed checks before any UI check. Run the project's build and lint commands
for changed frontend or other built parts.

UI and frontend tests, and browser or scene checks, need the owner's consent under the project's
rules; approval to implement or preview a change does not authorize them. After consent use the
check slots: `check-ui` for a scenario, `check-layout` for mockups and layout. The skill filling a slot
owns how its check runs.
