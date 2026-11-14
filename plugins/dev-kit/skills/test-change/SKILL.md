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

## Which tests to write

- Write a test only when you can name what breaks without it: a main user flow (`Flow`), a
  business rule (`Rule`), a fixed bug (`Bug`), or a boundary that real data reaches (`Edge`).
- Do not write: a scenario that types or the database already rule out; a second test of the
  same rule (add a data row to the existing test instead); a test of the language or framework
  (a record copy, "the constructor does not throw", constants are distinct).
- Every new test carries a "protects" mark with one of these values, written as the project's
  test rules say; a `Bug` test also carries one line on what broke. The level (unit /
  integration / E2E) is tagged as before.

## Run and report

- Build the current code; never use stale builds for a final check. Skip a rebuild only after a
  successful build of the current code in the same configuration.
- A selection with no cases is not a passed check. Report the absent coverage; add a test only
  by "Which tests to write". Prefer an isolated test when the logic can be checked without slow
  infrastructure (a database, a browser). Inspect what a selection actually matches instead of
  keeping a duplicate list of test names.
- Report the command, the actual passed, failed and skipped counts, runner time and total time.
  Verify that temporary resources the tests created are cleaned up, and preserve the owner's
  processes.

## Interface and UI order

After the final tests pass, verify a changed interface (an API, a command, a saved format) on the
single local environment; skip live checks when the interface did not change. Restart the
application with the `run-app` slot when fresh code is needed (`dev-kit-app start` when the profile lists
commands; run it in the background, it may wait in the queue while another session uses the app, and report a queue timeout (exit 3) as stuck, naming the holder). Use test data marked as the project's rules say, remove the check's own scratch records after the check; keep the app and standing test data (such as a test draft) running while the owner's work continues. Run the
`stop-app` slot (`dev-kit-app stop`) and remove the standing test data when the owner says the work is done or at a handoff. Show the command and
the actual result. Fix failed checks before any UI check. Run the project's build and lint commands
for changed frontend or other built parts.

UI and frontend tests, and browser or scene checks, need the owner's consent under the project's
rules; approval to implement or preview a change does not authorize them. A check listed as its own
line in a plan the owner approved has that consent (the owner's global rule "One yes per plan"). After
consent use the
check slots: `check-ui` for a scenario, `check-usability` for an ordinary user's walk, `check-look` for
mockups and layout. The skill filling a slot owns how its check runs. Run them in this order (owner
decision of 2026-11-10): `check-look` first, then `check-ui`, then `check-usability` last, on a page that
already matches the mockup and works; fix what one finds before the next.

The consent rule forbids running the check unasked; it does not forbid asking. Best put the checks in the
plan before the work starts. When a change has visible UI behaviour (a screen, a flow, a layout), the approved
plan did not list these checks, and you accept it or report it done, ask the owner in the same message
whether to run `check-ui`, when the change adds or reworks a flow `check-usability`, and when a mockup exists
`check-look`, with your recommendation and its reason.
Without a yes, the report says "not checked: browser scenario, user walk and look"; tests, review and "open it and tell me"
are not a substitute.
