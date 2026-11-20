---
name: visual-check
description: Use when the owner has consented (a separate yes or its own line in an approved plan) to a visual check in this task and the running app must be compared with a mockup board or its layout checked at a set of screen sizes - "перевір по мокапах", "чи схоже на мокап", "чи не їде верстка", "як на телефоні". Not for checking that a scenario works (that is e2e-check).
---

# Visual check

Answers how the screens look. Whether the scenario works is `web-kit:e2e-check`. Shared rules for every
browser check (consent, the single environment, test data, cleanup, one browser) are in
[browser-checks.md](${CLAUDE_PLUGIN_ROOT}/browser-checks.md). Read them first, then the profile sections
`## e2e-check` and `## visual-check` of `.claude/dev-kit.md` if they exist; they override the defaults here.

## Which agent

Two agents, model sonnet (the table in browser-checks.md): `web-kit:designer` for the mockup comparison,
from headless shots, and `web-kit:layout-checker` for the layout, with the layout profile the project names
for the app (phone app or admin). Whether the screens are clear to a user is `web-kit:user-walk`.

They are separate calls: one mockup board or one layout profile per call, one call after another. When
both are asked for, run the mockup comparison first.

## Mockup comparison

1. Find the board: `<mockups folder>/src/<flow>.json` is the source the agent reads (texts, blocks,
   arrows and notes); the HTML next to it is generated from it. The mockups folder is in the profile
   (`## design-screen`, default `docs/mockups`); the feature's «Approved design» section links it.
2. Read the rules made after the mockup was drawn: the rule named in its `source`, the rule in its
   feature or in the project's design standard, and the owner answers in the plan. List each known
   deliberate difference for the agent ("the back link sits on its own line, rule X").
3. For each phone of the board, prepare the state through the API and shoot it headless with
   `web-kit-shot --spec` at the app's window size (the URL and read-only steps that reach it, the app
   frame or the screen's section as selector, at a phone width no selector and one window per PNG;
   browser-checks.md, "Screenshots go to the owner"), named
   after the phone. Shoot the board with `web-kit-shot --board`. `web-kit:shot-taker` writes and runs the
   spec when that is quicker or a shot fails. A phone no URL and read-only steps reach goes into the
   report as not checked, with the reason.
4. Call `web-kit:designer`, subject "built", with the shots of the app and of the board, the spec path,
   the spec format reference (`${CLAUDE_PLUGIN_ROOT}/skills/design-screen/spec-format.md`), the path of the
   project's design standard, the feature file and the known differences.
5. Check every difference it reports against the feature rules and the standard before calling it a
   defect: a newer rule wins over the mockup. A deviation from the standard is a defect of the app, and
   also of the mockup when the mockup draws it (redraw it with `web-kit:design-screen`, stage 1). Unclear whether the app or the mockup is right → ask the owner.

## Layout

Call `web-kit:layout-checker` with the profile, the screens and what to watch this time.

## Report

To the owner: one line per board or profile with matched, defects and not checked, and the
screenshots (for a mockup comparison, each app shot next to its board shot) (browser-checks.md, "Screenshots go to the owner"). A
difference that follows a newer rule is not a defect; mention it only if the mockup should
be redrawn.
