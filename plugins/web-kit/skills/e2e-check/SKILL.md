---
name: e2e-check
description: Use when a user scenario must be verified end to end in the running app (taps, saved data, server answers, what the other user sees) and the owner has given separate, explicit consent for a scenario check in this task - "перевір, що працює", "e2e", "прожени сценарій". Not for an ordinary user's walk (that is user-walk), comparing screens with mockups or checking layout (that is visual-check).
---

# E2E check

Answers one question: does the scenario do what the product says it should? Whether an ordinary user
gets there easily is `web-kit:user-walk`; how the screen looks is `web-kit:visual-check`; who answers which
question is the table in browser-checks.md. Shared rules for every browser check (consent, the single
environment, test data, cleanup, one browser) are in [browser-checks.md](${CLAUDE_PLUGIN_ROOT}/browser-checks.md).
Read them first, then the profile sections `## e2e-check` and `## ui-tester` of `.claude/dev-kit.md`
if they exist; they override the defaults here.

## Write the scenarios

- One scenario is one user goal: the start state, numbered steps, and the expected result of
  each step.
- The scenarios come from the feature (browser-checks.md, "Scenarios come from the feature"). Take each
  expected result from a source, not from the code just written: those criteria and the feature's rules,
  the plan step or the bug report. Name the source next to the result. An expectation copied from the
  implementation only confirms the implementation.
- Cover the branches the source names: rejection, empty list, error, undo, the second user's
  view. List what you leave out and why.
- The window size preset for each app of the project (phone app, admin) is in the profile.
- A step done by the partner is prepared by the caller through the API between calls, or the
  agent is given both users' entry links. Say which one in the scenario.

## Run the scenarios

Call `web-kit:ui-tester` (model sonnet) once per scenario, one call after another. Each call gets:

- the start URL and the prepared IDs;
- the steps and the expected result of each, with its source;
- that any record it creates carries the project's test-data marker.

## After a scenario report

- A fail, or a pass with an observation that needs a code fix: read the evidence (console text,
  request and status, screen text) before calling it a defect. After the fix, rerun only that scenario
  through `web-kit:ui-tester`, never in the main session.
- A pass: check that the report lists the steps it actually took and the values it saw. A
  bare "pass" is not evidence; send a follow-up.
- Report to the owner one line per scenario: pass or fail, and what broke. Send the
  screenshots from the report with it (browser-checks.md, "Screenshots go to the owner").
