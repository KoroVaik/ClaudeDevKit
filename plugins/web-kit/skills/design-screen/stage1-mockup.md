# Stage 1: structure on a mockup

Low-fidelity wireframes: phone frames (or, for a desktop admin, wide screens, see "Desktop boards" in
[spec-format.md](spec-format.md)) connected by arrows, written as a JSON spec and generated into HTML, so
dozens of them stay consistent and nothing gets lost in chat. They are drafts for discussion, not built UI
and not frontend code. The loop, the shots and the show rules are in [SKILL.md](SKILL.md).

## Sources (read before drawing)

- The feature file of the flow (the project's docs) - what each screen contains and which rules apply
  (cite its rules).
- [spec-format.md](spec-format.md) - the spec format: fields, block types, layout cells.
- The reference spec named in the profile, if any.
- The project's design standard named in the profile. The palette is already encoded in the mockups
  folder's `mockups.css` (the project's own file wins; without one the generator writes the plugin's
  neutral default on the first build), but read the standard's rules on controls: pick each button `kind` by
  its meaning there (`save` for an intermediate step, `approve` for submitting data), not by how prominent
  it should look.

Do not invent product behavior. If the flow is not described yet, draw the minimum, say in the spec
`authorNotes` which parts are placeholders, and list the open questions at the end of the reply as a
numbered block.

## Steps

1. Pick the flow and its screens (3-5 phones per board, 2-3 desktop screens; split a long flow into several
   specs). Happy path in layout row 1, branches (rejection, errors, empty states) in the rows below.
2. Check `<mockups folder>/src/` first: extend an existing spec instead of duplicating a flow. Set `group`
   so the index stays organized (reuse an existing group name when one fits).
3. Write `<mockups folder>/src/<name>.json` using only the block types in the spec format. The name and the
   `title` are the feature's name; with several screens, the feature's name plus the screen (rule:
   `dev-kit:documentation`, "Kinds of content"). Screen text is the UI copy from the
   feature file, in the UI language the profile names; everything else is in the docs language. Photos and
   names are obvious placeholders. A piece that repeats in two or more mockups (a table, a page header, a
   menu) goes to `<mockups folder>/parts/<name>.json` in its normal state and the specs reference it with a
   `part` block ("Parts" in the spec format); a changed state is drawn inline in the flow, never as a part
   option.
4. Run `web-kit-mockups` (add `--dir <mockups folder>` when it is not `docs/mockups`). It validates the spec
   (unknown blocks, unplaced phones, bad fields fail with a message), writes `<name>.html` and regenerates
   `index.html`. Fix spec errors; never edit generated HTML.
5. If the block list lacks something you need and two or more mockups would use it, add the block to the
   generator (`scripts/build-mockups.mjs` in the web-kit plugin repo) and its class to the project's
   `mockups.css`, document it in `spec-format.md`, and rebuild. Otherwise compose with existing blocks.
6. Run `web-kit-mockups --check`: it must report OK.
7. **Cut text:** walk every screen and remove each word the screen stays clear without ("Less text").
8. **Facts, before the first show:** a read-only `dev-kit:investigator` (haiku or sonnet) gets the spec and
   lists every claim the screens make about how the app works (where a value comes from, which step or
   link leads where, what a button does, which data is shown), and checks each in the code or data, with
   file:line. A claim it cannot confirm is fixed or marked as a placeholder in `authorNotes` before the owner
   sees the board. Run it again only when a later change adds a new claim.
9. **Nothing lost,** when the board redesigns a screen that exists (in the app or on a `-current` board): a
   read-only `dev-kit:reviewer` (sonnet) gets the current screen's board spec (or the page's component and
   its feature doc) and the new spec, lists every piece of information and every action the current screen
   gives, and says for each whether the new board keeps it in view, keeps it behind one click, or drops it.
   Each dropped piece is drawn back on the temporary board (or on a variants board: kept against dropped) and
   goes to the owner as the screenshots plus one line: "these pieces were lost, keep them?". It is never
   listed in text and never dropped silently. Fresh users cannot catch this: they never saw the old screen.
10. **The loop** ([SKILL.md](SKILL.md), "The loop before each show"): shoot the board, a fresh user per
    branch, the designer with the brief "a mockup board, not a variant; report every tone, button kind and
    marker that contradicts its meaning in the standard (selection, confirmed, warning, error, button
    colours), including ones copied from an older board". The designer is the only colour check of the loop.
11. **Show** the board to the owner ([SKILL.md](SKILL.md), "Show to the owner").
12. **Approval.** On the owner's «так» to the mockup, in the same turn, with no step for the owner:
    - the feature file gets its «Approved design» section (template: `dev-kit:documentation`, "Feature file"),
      state `approved, not built`, with the user situation the loop used;
    - `PROGRESS.md` gets a next-step line: the screen is approved and waits for its build;
    - the finished series is committed as the project's rules say about commits: the spec, the generated
      HTML, `index.html`, any `mockups.css` or config change and the two doc edits above. Temporary boards
      whose outcome is settled are deleted first;
    - then the done report to the project lead, or to the owner where the project has no lead.
    Without the «Approved design» section the session does not report done. The owner's «так» to the mockup
    is also consent for the build session's checks of that screen (`check-look`, `check-ui`,
    `check-usability`; rule: `dev-kit:test-change`). A series still being iterated on with the owner is not
    finished work: commit it when the owner accepts it or ends the session.

## Less text

Screen text is the least that keeps the screen clear; explanations go in the board's note.

- Every word on a screen tells the user where they are or what to do. Anything else goes.
- No label that repeats what an icon, a number, a photo or a position already says (a trophy icon with
  "gold" next to it, "1." with "favourite").
- Plain everyday words, never internal or technical terms (no "round of 16"): if the user would have to
  work something out, say it another way ("places 9-16").
- A title is a few words; a hint is one short line, and only where the action is not obvious.
- One way to say a thing: the same word for the same action on every screen.

## Board rules

- One board, one theme: a board covers a single flow or a single idea family. A new idea on another theme
  gets its own board; an idea that replaces an earlier one updates or removes the old screens.
- Variants board: to choose between designs of one screen or piece, draw 2-3 variants on one temporary
  board, each a `branch` row titled with the variant («Варіант А: ...») and the same `given`, its screens
  below it. Variants differ in structure (which blocks, their order, where an action sits), not only in
  color or wording, and each stays within the project's design standard. Exact sizes, line breaks and
  spacing are not decided on a mockup. Once the owner picks, the chosen variant goes into the flow's board
  and the variants board is deleted.
- Low fidelity: grey boxes, bars, placeholder photos. A value may show which kind of mark it gets (plain
  text, a chip, an icon, a tone by meaning); sizes, fonts, spacing and exact shades are left to the real
  components (stage 2). No final typography or pixel polish; where the project's typography for the app is
  not defined yet (the profile says), the mockup does not define it.
- A desktop screen board (`"frame": "desktop"`) lives in its own mockups folder, set in the profile; never
  mix it with phone boards. Its arrows go down, one screen per row.
- Phone size is fixed in `mockups.css` (the project's own file wins over the generated default); mockups are
  not responsive.
- The board reads as a story: caption above each frame, an arrow to the next screen labelled with the
  action. Number screens with `step`.
- The caption says where the user is ("Picks an item", "A request came from A"), not what changed in the
  design. An arrow label is exactly one user action, written as a verb and the exact element on the screen
  ("tap on the photo of the item «Name»", "tap on the button «Ask»", "tap on ☰ at the top right"), so it is
  clear where the tap lands; never a bare button name or a vague target like "tap on an item"; a second
  action needs its own screen and arrow. Labels are plain words: the generator draws the arrow, so no → or ↓.
- Every screen is reached by an arrow with the action that led to it. Each path of the flow, the first one
  included, starts with a `branch` row: a title and `given` with the precondition ("**Precondition:** an
  item is already chosen"). A popup or warning is never the first screen of a branch: draw the screen it
  opens from.
- Service text never shows on the page: sources, what is approximated or left out, design changes and their
  reasons go in the spec's `authorNotes`. The viewer sees at most one short `notes` line under the title.
- In a flow with two people, set `user` (`A` or `B`) on every phone: the frame color and the "A1"/"B4" tag
  (letters set in `mockups.config.json`) show whose phone it is, so the caption does not repeat the name.
- A mockup never changes rules. A new product rule goes to its feature or standard only after the owner
  accepts it (see the `dev-kit:documentation` skill, section "Where things go").
- A copy is not a source: a block, tone or button kind taken from another board is checked against the
  design standard like a new one. An older board only shows how a piece is built, never which colour means
  what.
- Who edits the spec: a small change (a word, a tone, a spacing, one block moved, in a few known places) is
  made by the session with Edit. A bigger change (new screens or branches, a redesign, a new generator
  block) goes to a fresh `dev-kit:coder` (sonnet) with a short brief: the spec path, the change and the
  success check. Never keep one coder through a whole session: its context grows and it slows down.
