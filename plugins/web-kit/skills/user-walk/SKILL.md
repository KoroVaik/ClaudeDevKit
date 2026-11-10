---
name: user-walk
description: Use when an ordinary user should go after a goal in the running app and say what got in the way (unclear, extra words, awkward steps, where they got lost), and the owner has given separate, explicit consent for a user walk in this task - "пройди як користувач", "чи зручно", "що заважає", "подивись очима користувача", or the `check-usability` slot. Not for checking that a scenario does what the feature says (that is e2e-check) or comparing screens with mockups (that is visual-check).
---

# User walk

Answers one question: can an ordinary user reach the goal, what gets in the way, and how should the design
change so it would not? The recommendations are the result; the mockup only shows where each fix belongs. It shows what a
scenario check cannot: where a real user hesitates. The agent `web-kit:app-user` walks blind; the mockup
comes only after the walk, so it cannot bias what the user notices, and the live app outranks the mockup.
Whether the scenario does what the feature says is `web-kit:e2e-check`; who answers which question is the
table in browser-checks.md. Shared rules for every browser check (consent, the single environment, test
data, cleanup, one browser) are in [browser-checks.md](${CLAUDE_PLUGIN_ROOT}/browser-checks.md). Read them
first, then the profile sections `## e2e-check`, `## mockup-user` and `## app-user` of `.claude/dev-kit.md`
if they exist; they override the defaults here.

## Steps

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
   deliberate differences, found as in `web-kit:visual-check`, "Mockup comparison" step 2. Without `SendMessage`, call
   a fresh `web-kit:app-user` with the walk report and the same three things, saying the walk is done. No
   board: every remark goes to the owner as a design question.
5. **Report** to the owner, one line per goal (reached or not), then the agent's recommendations, most
   useful first, in two short lists with the screenshots:
   - **fix in code** (and broken steps): the app strays from the mockup; after the fix, rerun the walk for
     that goal only.
   - **design changes** (and recommendations not on the board): the app follows the mockup and is still in
     the way; the owner decides whether to change the rules and the mockup (`web-kit:draw-mockup`). Nothing
     changes without the owner's yes.

A remark the agent drew from the brief rather than the screen (it lists them) is weighed, not trusted.
