# Design a screen

Epic: [Check and design screens in the browser](../epics/check-and-design-screens-in-the-browser.md)

## Purpose
A screen is designed in two stages, so the owner approves how it looks before it is built and the built
screen is polished on real components.

## Rules
### Stage 1: a mockup the owner approves
The `design-screen` skill first makes a mockup that the owner approves. The approval is recorded in the
feature file.

### Stage 2: polish in the design sandbox
Then the screen is polished on real components in the design sandbox. Each show is prepared by
a fresh `web-kit:user` and `web-kit:designer`, with `web-kit:sandbox-builder` and `web-kit:shot-taker` in
stage 2.

### Mockup pages come from JSON specs
`web-kit-mockups` builds the mockup pages from JSON specs; the format is in
[the spec format](../../plugins/web-kit/skills/design-screen/spec-format.md).

The project's facts (mockups folder, palette, languages, sandbox URL, checks, shot window) go in its
profile ([sections](../tech/project-profile.md)).

## Acceptance criteria
- The owner is shown a mockup of the screen before any build and approves it; the approval is in the feature file.
- Then the owner is shown shots of the screen on real components from the design sandbox.
- A mockup page is built from a JSON spec with `web-kit-mockups`.

## Built in
- `plugins/web-kit/skills/design-screen`
- `plugins/web-kit/scripts/build-mockups.mjs`
- `plugins/web-kit/bin/web-kit-mockups`
- `plugins/web-kit/agents/designer.md`
- `plugins/web-kit/agents/user.md`
- `plugins/web-kit/agents/sandbox-builder.md`
- `plugins/web-kit/agents/shot-taker.md`
- `tools/tests/test_build_mockups.py`
