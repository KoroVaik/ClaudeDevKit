---
name: e2e-check
description: Use when the owner has given separate, explicit consent in this task for a scenario check - a user scenario verified end to end in the running app (taps, saved data, server answers, what the other user sees), "перевір, що працює", "e2e", "прожени сценарій" - or for a user walk - an ordinary user goes after a goal in the running app and says what got in the way, "пройди як користувач", "чи зручно", "що заважає". Not for comparing screens with mockups or checking layout (that is visual-check).
---

# E2E check

Answers whether the app works for its user, in one of two modes (the owner's consent names which):

- **Scenario:** does the scenario do what the product says it should? `web-kit:ui-tester`, pass or fail.
- **User walk:** can an ordinary user reach the goal, and what gets in the way? `web-kit:app-user`.

How the screen looks against the mockup is `web-kit:visual-check`; who answers which question is the table
in browser-checks.md. Shared rules for every browser check (consent, the single
environment, test data, cleanup, one browser) are in [browser-checks.md](${CLAUDE_PLUGIN_ROOT}/browser-checks.md).
Read them first, then the profile sections `## e2e-check`, `## ui-tester` and `## app-user` of
`.claude/dev-kit.md` if they exist; they override the defaults here.

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

- A fail: read the evidence (console text, request and status, screen text) before calling it
  a defect. After the fix, rerun only that scenario.
- A pass: check that the report lists the steps it actually took and the values it saw. A
  bare "pass" is not evidence; send a follow-up.
- Report to the owner one line per scenario: pass or fail, and what broke. Send the
  screenshots from the report with it (browser-checks.md, "Screenshots go to the owner").
- When the change adds or reworks a flow, offer the owner a user walk of it, with your reason.

## User walk

The walk shows what the scenario check cannot: where a real user hesitates. The agent walks blind; the
mockup comes only after the walk, so it cannot bias what the user notices.

1. **Goal.** One goal per walk, taken from the feature's criteria: the situation and what the user wants,
   in plain everyday words ("you want to add tomorrow's lunch"). Never steps, screen names, button labels or
   expected results. Pick the persona the profile section `## mockup-user` gives for this app.
2. **Data.** Prepare what the situation needs through the API (browser-checks.md, "Test data through the
   API") and tell the agent only what a user would know ("you already have two dishes"). The walk reaches
   a goal that saves only on test-owned data; when the agent may not change the data it walks (the owner's
   real records), tell it the step to stop before and report the walk as partial.
3. **Walk.** Call `web-kit:app-user` (model sonnet) with the persona, situation, goal, start URL and the
   window size the profile names for this app. One goal per call, one call after another.
4. **Sort.** If the flow has a mockup board (`<mockups folder>/src/<flow>.json`, the folder from
   `## draw-mockup`, default `docs/mockups`), send the same agent a follow-up (`SendMessage`) with the spec
   path, the spec format reference (`${CLAUDE_PLUGIN_ROOT}/skills/draw-mockup/spec-format.md`) and the known
   deliberate differences, found as in visual-check, "Mockup comparison" step 2. Without `SendMessage`, call
   a fresh `web-kit:app-user` with the walk report and the same three things, saying the walk is done. No
   board: every remark goes to the owner as a design question.
5. **Report** to the owner, one line per goal (reached or not), then two short lists with the screenshots:
   - **implementation defects** (and broken steps): the app is wrong, fix in code; after the fix, rerun the
     walk for that goal only.
   - **design mistakes** and remarks not on the board: the app follows the mockup and is still awkward; the
     owner decides whether to change the rules and the mockup (`web-kit:draw-mockup`). Nothing changes
     without the owner's yes.

A remark the agent drew from the brief rather than the screen (it lists them) is weighed, not trusted.
