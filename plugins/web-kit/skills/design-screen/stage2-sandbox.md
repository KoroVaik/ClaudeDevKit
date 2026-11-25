# Stage 2: polish on real components

The look of a built screen is polished in the project's design sandbox: a dev-only page that renders real
components on prepared data. A mockup decides which blocks a screen has and their order; the sandbox settles
only what the mockup leaves open (sizes, corners, spacing, line breaks) and what the remark names. The loop,
the shots and the show rules are in [SKILL.md](SKILL.md).

Stage 2 starts when the owner, shown the built screen next to its mockup, has remarks («є питання»), or
remarks on the look of a screen later. At a review session's remarks it runs in the build session, on its
branch (`dev-kit:project-lead`, "Build a designed screen"): every set or shot that steps 5 and 8 show the owner goes
to the review session in a `ВІДПОВІДЬ` instead, the review session shows it, and P merges on its `ЗАКРИТО`. A later
remark on a merged screen runs in a separate session, on a branch made from main. The profile section `## design-screen` gives
the sandbox URL and port, the data sets folder, the mockup folders, the app frame selector (for a whole-page
shot), the frontend's type check, lint and build commands, and the project's own rules. The sandbox needs no
separate consent where the project's rules allow it (its `CLAUDE.md` or profile); otherwise ask once for the
task.

Before shooting the session checks the sandbox port from the profile and, if the dev server is down, starts
it with the profile's command in the background; it stops it only when the owner says the work is done,
following the project's process rules. The session never writes the CSS: `web-kit:sandbox-builder` does.

## Steps

1. **Read** the remark, the owner's screenshot if any, and the approved mockup board for the mark it is
   about. Decide the variants: variant 1 is always the approved look with only the named defect fixed, at its
   cause where one is visible (a wrap, a width), never by restyling the mark. Other variants differ from it
   only in how that defect is fixed. A change to an approved mark (shape, fill, colour, divider, separator)
   appears only when the owner asks for that mark to change in their own words, and then as a separate
   variant next to variant 1. A remark that contradicts the standard is checked against it; variant 1 keeps
   the standard.
2. **Build:** `sandbox-builder`, mode `try`. The brief: the remark, the board and its mark, each variant in a
   line, the profile facts. It returns per variant the URL, a one-line visual description in the owner's
   words, the selectors of the piece and of its parent block, and the board region selector for the mark.
3. **Shoot:** first make sure the sandbox dev server runs. `web-kit:shot-taker` gets the list of shots (name,
   URL, the piece, kind `piece|parent|page|close-up|board|screen`, caption): today's look, every variant, and the
   board region. Every brief passes the window size, the device scale, the app frame
   selector, the output folder (the session scratchpad) and the absolute path of `capture.mjs`
   (`${CLAUDE_PLUGIN_ROOT}/scripts/capture.mjs`, resolved by the caller). The piece is shot by the rules of
   browser-checks.md: a small piece through its parent block or with a margin of the page around it; the
   page layout itself as the app frame with `fitHeight`, at a phone width as kind `screen` (one window per PNG).
4. **The loop** ([SKILL.md](SKILL.md), "The loop before each show"): a fresh `web-kit:user` per variant with
   that variant's shots; then `web-kit:designer` gets every variant shot and the board shot, the board spec,
   the standard, the deliberate differences (what the remark changes; fail any variant that differs from the
   board in a mark the remark does not name), what is out of scope and the user reports. Today's shot goes
   only as a reference labelled "today, not a variant, do not judge"; the designer judges variants only. The
   shots of one variant are one block. A failed variant goes back to the builder, mode `fix`, with the
   designer's defect lines as they are; then shoot and review again. After two rounds drop the variant with
   one line. A line marked `board breaks it` is not a variant defect: tell the owner and redraw the board in
   stage 1.
5. **Show:** one turn with one set: today's look and every passed variant ([SKILL.md](SKILL.md), "Show to the
   owner"). An image of an earlier message is never pointed to: send it again in the new set. When no variant
   passed, say so in one line and what you try next. When the pick would go into the real page, the set also
   holds one whole-page shot of the recommended variant (app frame, `fitHeight`; at a phone width `screen` shots), passed by the designer
   (owner's standing instruction: a build-in or merge question comes with a whole-page shot).
6. **Apply** the pick: the builder in mode `apply` moves it into the real component, removes the trial flags
   and their CSS, updates the tech doc that describes the look and runs the project's type check, lint and
   build. Shoot and review the result as in steps 3-4, then commit to the branch.
7. **Redraw the mockup:** if marks or structure changed, the builder in mode `sync-mockups` redraws the boards
   to match what was built; the session shoots the redrawn boards and the designer compares them with the
   built look.
8. **Merge:** a whole-page shot (app frame, `fitHeight`; at a phone width `screen` shots) of the result, passed by the designer, goes to the
   owner with the question to merge. Merge only after the owner's «так»: in a project with a lead, report
   done to the lead, which merges; without one, merge into main from the main checkout. Never push.

## Rules

- A variant never changes a rule of the feature (a column removed, a field renamed). That needs the owner's
  yes and a `dev-kit:reviewer` check of the feature file; the sandbox's yes-free show covers looks only.
- Real components stay untouched until `apply`. A trial lives in a query flag and sandbox-only CSS.
- Leftovers: trial flags and their CSS go when the pick is applied. Scratch shots stay in the scratchpad and
  are deleted at the end; the browser and the servers follow the project's rules about processes.
- Nothing unfinished is merged.
