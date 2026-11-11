---
name: design-sandbox
description: Use when the owner remarks on the look of a real screen being polished in the design sandbox (too big, clumsy corners, a screenshot with an arrow drawn on it), or asks to try or apply a look there - "зроби менше", "спробуй інакше", "бери варіант Б", "чип здоровенний", "радіуси кострубаті", an owner's screenshot with arrows - or picks a variant shown from it. Not for a structure no mockup has drawn (that is draw-mockup), not for checking that a scenario works (that is e2e-check).
---

# Design sandbox

The loop for polishing a look in the project's design sandbox: a dev-only page that renders real components
on prepared data, on its own git branch and worktree. A mockup decides which blocks a screen has and their
order; the sandbox settles only what the mockup leaves open (sizes, corners, spacing, line breaks) and what
the remark names. A structure change goes back to `web-kit:draw-mockup`.

Read the profile section `## design-sandbox` of `.claude/dev-kit.md` first: the worktree path and branch, the
sandbox URL and port, the data sets folder, the mockup folders, the app frame selector (for a whole-page
shot) and the project's own rules. It overrides the defaults here. Shot rules, the one numbered set and
the headless capture are in [browser-checks.md](${CLAUDE_PLUGIN_ROOT}/browser-checks.md) ("Screenshots go to the
owner"). The sandbox is shown with headless shots only: the loop never opens the in-app browser, and it
needs no separate consent where the project's rules allow it (its `CLAUDE.md` or profile); otherwise ask once
for the task.

## Roles

The main session decides, writes briefs, commits and writes the message to the owner. It never writes the
CSS and does not inspect every PNG: the critic's verdict is the evidence. It opens one shot of the set it
sends as a spot check (a subagent's done is not evidence). Before shooting it checks the sandbox port from
the profile and, if the dev server is down, starts it with the profile's command in the background; it stops
it only when the owner says the work is done, following the project's process rules. Agents run
one after another, with the full brief each time (they remember nothing).

- `web-kit:sandbox-builder` (sonnet): modes `try`, `fix`, `apply`, `sync-mockups`.
- `web-kit:shot-taker` (haiku): takes the shots from a list.
- `web-kit:design-critic` (sonnet): screens the variant shots.

## The loop

1. **Read** the remark, the owner's screenshot if any, and the accepted mockup board for the mark it is
   about. Decide the variants: 2-3 distinct ones, or 1 when the owner named the exact change. The
   accepted mockup's look is the starting point; a variant differs only in what the remark is about.
2. **Build:** `sandbox-builder`, mode `try`. The brief: the remark, the board and its mark, each variant in
   a line, the profile facts. It returns per variant the URL, a one-line visual description in the owner's
   words, the selectors of the piece and of its parent block, and the board region selector for the mark.
3. **Shoot:** first make sure the sandbox dev server runs (Roles). `shot-taker` gets the list of shots (name,
   URL, the piece, kind `piece|parent|page|close-up|board`, caption): today's look, every variant, and the
   board region. Every brief also passes the window size, the device scale, the app frame selector, the
   output folder (the session scratchpad) and the absolute path of `capture.mjs`
   (`${CLAUDE_PLUGIN_ROOT}/scripts/capture.mjs`, resolved by the caller). The piece is shot by the rules of
   browser-checks.md: a small piece through its parent block or with a margin of the page around it; the
   page layout itself as the app frame with `fitHeight`.
4. **Screen:** `design-critic` gets every variant shot and the board shot, the board spec, the
   standard, the deliberate differences (what the remark changes) and what is out of scope. Today's shot
   goes only as a reference labelled "today, not a variant, do not judge"; the critic judges variants only.
   The shots of one variant are one block.
5. **Fix:** a failed variant goes back to the builder, mode `fix`, with the critic's defect lines as they
   are; then shoot and screen again. At most two rounds; then drop the variant with one line. A line marked
   `board breaks it` is not a variant defect: tell the owner and send the board to `draw-mockup`.
6. **Show:** one message with one set: today's look and every passed variant, each image with a numbered
   caption naming what differs on screen. The reply text is one line per variant, one recommendation line with
   its reason and the question which to take. No process words (built, sent, committed). An image of an earlier
   message is never pointed to: send it again in the new set. When no variant passed, say so in one line and
   what you try next. When the pick would go into the real page, the set also holds one whole-page shot of
   the recommended variant (app frame, `fitHeight`), screened by the critic (owner's standing instruction: a
   build-in or merge question comes with a whole-page shot).
7. **Apply** the pick: the builder in mode `apply` moves it into the real component, removes the trial flags
   and their CSS, updates the tech doc that describes the look and runs the project's type check, lint and
   build. Shoot and screen the result as in steps 3-4, then commit to the sandbox branch.
8. **Merge:** a whole-page shot (app frame, `fitHeight`) of the result, screened by the critic, goes to the
   owner with the question to merge. If marks or structure changed, run builder mode `sync-mockups` first; the
   shot-taker shoots the redrawn boards and the critic screens them against the built look. Merge into main
   only on the owner's yes. Never push.

## Rules

- Take no variant to the owner that the critic did not pass. The critic filters; it does not choose, and
  neither does the main session: the recommendation is a reasoned line, the owner picks.
- A variant never changes a rule of the feature (a column removed, a field renamed). That needs the owner's
  yes and a `dev-kit:reviewer` check of the feature file; the sandbox's yes-free show covers looks only.
- Real components stay untouched until `apply`. A trial lives in a query flag and sandbox-only CSS.
- Leftovers: trial flags and their CSS go when the pick is applied. Scratch shots stay in the scratchpad
  and are deleted at the end; the browser and the servers follow the project's rules about processes.
- A remark that turns out to be a structure question (another block, another order) stops the loop: say it in
  one line and move to `web-kit:draw-mockup`.
- The reply to the owner follows the project's chat rules (language, length, the question with its
  recommendation and example).
