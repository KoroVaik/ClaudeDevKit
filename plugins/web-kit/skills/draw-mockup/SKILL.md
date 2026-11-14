---
name: draw-mockup
description: Use when the owner asks to draw, sketch or mock up a screen or flow - "намалюй мокап / флоу / екран" - or when the owner proposes or asks about a visual change that adds a new block, order or flow (polishing the look of an existing real screen is `design-sandbox`), or when discovery or brainstorming needs a visual of a flow (the `show-idea` slot), or when the agent itself is about to put a visual proposal, a restored piece or a choice between looks to the owner during mockup work. Not for building real UI in the project's frontend.
---

# Draw mockup

Low-fidelity wireframes: phone frames (or, for a desktop admin, wide screens, see "Desktop boards" in
[spec-format.md](spec-format.md)) connected by arrows, written as a JSON spec and generated
into HTML, so dozens of them stay consistent and nothing gets lost in chat. They are drafts for
discussion, not accepted UI and not frontend code. Read the profile section `## draw-mockup` of
`.claude/dev-kit.md` if it exists: it gives the mockups folder (default `docs/mockups`), the reference
spec, the design standard, the language of the screen text and the project's other specifics, and
overrides the defaults here.

## Sources (read before drawing)

- The feature file of the flow (the project's docs) - what each screen contains and which rules apply
  (cite its rules).
- [spec-format.md](spec-format.md) - the spec format: fields, block types, layout cells.
- The reference spec named in the profile, if any.
- The project's design standard named in the profile. The palette is already encoded in the mockups
  folder's `mockups.css` (the project's own file wins; without one the generator writes the plugin's
  neutral default on the first build), but read the standard's rules on controls: pick each button `kind` by its meaning
  there (`save` for an intermediate step, `approve` for submitting data), not by how prominent it should
  look.

Do not invent product behavior. If the flow is not described yet, draw the minimum, say in the
spec `authorNotes` which parts are placeholders, and list the open questions at the end of the reply
as a numbered block.

## Steps

1. Pick the flow and its screens (3-5 phones per board, 2-3 desktop screens; split a long flow into several specs).
   Happy path in layout row 1, branches (rejection, errors, empty states) in the rows below.
2. Check `<mockups folder>/src/` first: extend an existing spec instead of duplicating a flow. Set
   `group` so the index stays organized (reuse an existing group name when one fits).
3. Write `<mockups folder>/src/<flow-name>.json` using only the block types in the spec format. Screen
   text is the UI copy from the feature file, in the UI language the profile names; everything else is
   in the docs language. Photos and names are obvious placeholders. A piece that repeats in two or more
   mockups (a table, a page header, a menu) goes to `<mockups folder>/parts/<name>.json` in its normal state
   and the specs reference it with a `part` block ("Parts" in the spec format); a changed state is drawn
   inline in the flow, never as a part option.
4. Run `web-kit-mockups` (add `--dir <mockups folder>` when it is not `docs/mockups`). It validates the
   spec (unknown blocks, unplaced phones, bad fields fail with a message), writes `<flow-name>.html` and
   regenerates `index.html`. Fix spec errors; never edit generated HTML.
5. If the block list lacks something you need and two or more mockups would use it, add the block to the
   generator (`scripts/build-mockups.mjs` in the web-kit plugin repo) and its class to the project's
   `mockups.css`, document it in `spec-format.md`, and rebuild. Otherwise compose with existing blocks.
6. Run `web-kit-mockups --check`: it must report OK.
7. Cut text: walk every screen and remove each word the screen stays clear without (section
   "Less text"). Then call the `web-kit:mockup-user` subagent (model sonnet) once per branch, each a fresh
   run (a tool without subagents skips this and says so). Hand it only what the user sees: the
   persona and the report language from the profile section `## mockup-user` (the agent reads no files
   at this stage), the branch's `given`
   in plain words as the situation, then each screen's visible text from top to bottom (photos as
   "photo of the item") and the arrow label that leads on. Never pass captions, notes, decisions, file
   paths or reasons. Show the owner its points in short; change the mockup only for the points the
   owner accepts. A point that changes how a screen looks is shown as the board with that change drawn
  (Rules: "This holds for every visual proposal"); only a point with no visual side is a text line.
  A point that comes back from a second fresh run is never closed with "the docs
   require it": before the next round find in the code or data what the thing does and who uses it
   (for a field: where its value goes), and give the owner that result with the point. If no reason
   is found, the point goes to the owner as an open question, not as a decision to keep. Once the flow is built, the live app is walked by `web-kit:app-user` (`web-kit:user-walk`); its remarks outrank this one.
   The checks run in this order: nothing lost (step 7c), words (the text run above), usability (step
   7b), colours (step 7a).
   7c. Nothing lost, when the board redesigns a screen that exists (in the app or on a `-current`
   board): a read-only `dev-kit:reviewer` (sonnet) gets the current screen's board spec (or the page's
   component and its feature doc) and the new spec, lists every piece of information and every action
   the current screen gives, and says for each whether the new board keeps it in view, keeps it behind
   one click, or drops it. Each dropped piece is drawn back on the temporary board (or on a variants board:
   kept against dropped) and goes to the owner as the screenshots plus one line: "these pieces were lost, keep
   them?". It is never listed in text and never dropped silently. Fresh readers cannot catch this: they never
   saw the old screen.
   7b. Usability, once the words hold: a fresh `web-kit:mockup-user` per branch gets the same situation
   and, for each screen, a headless shot of the screen frame alone (no board title, caption, note or
   arrow) as a PNG path, plus the action that leads on. It judges what the eye finds first, what is far
   or hidden, what looks clickable and whether the order of blocks fits the task. The shots are the
   ones step 7a takes: you run `web-kit-shot --board <board.html> --out <folder> --profile <profile path>`
   yourself after every rebuild (one PNG per screen id, no selectors; `--screens d1,u3` for some), and call
   `web-kit:shot-taker` only when the command fails or a shot comes out wrong. Fix as in step 7, then the colour check.
   7a. Screen the look, before the owner sees the board: shoot the board headless with
   `web-kit-shot --board <board.html> --out <folder> --profile <profile path>` (you run it yourself after every
   rebuild; the profile gives the window size and scale, the generator's `data-screen` ids give the crops, so
   no selector is written; `web-kit:shot-taker` is called only when the command fails or a shot comes out wrong,
   and it fixes or reports) and call `web-kit:design-critic`
   (sonnet) with those PNGs, the board spec JSON, the design standard from the profile and the reference
   "no mockup" (checks 2 and 3 only). Say in the brief: "a mockup board, not a variant; report every
   tone, button kind and marker that contradicts its meaning in the standard (selection, confirmed,
   warning, error, button colours), including ones copied from an older board". mockup-user judges words
   and layout, not colour, so this is the only colour check of the loop. Fix every defect line in the
   spec, rebuild and screen again. Later, run it again only when a new element appears (a block, a
   tone or a button kind the board did not have). While the owner tunes a look round by round (a
   shade, a size, a spacing), skip the critic and run it once when the series ends, before the
   commit. A tool
   without subagents or headless shots skips the step and says so in the hand-over.
8. Hand the mockup to the owner as a file attachment in the chat (in Claude Code: `SendUserFile` with
   `display: render`); one click opens it in the built-in browser. The generated page carries its
   styles inside, so send the file from the mockups folder as it is. Do not open the browser pane
   yourself.
9. Commit the finished series as the project's rules say about commits: the spec, the generated
   HTML, `index.html` and any `mockups.css` or config change. Nothing else. A series still being
   iterated on with the owner is not finished work; commit it when the owner accepts it or ends the
   session.

## Less text

Screen text is the least that keeps the screen clear; explanations go in the board's note.

- Every word on a screen tells the user where they are or what to do. Anything else goes.
- No label that repeats what an icon, a number, a photo or a position already says (a trophy icon with
  "gold" next to it, "1." with "favourite").
- Plain everyday words, never internal or technical terms (no "round of 16"): if the user would have
  to work something out, say it another way ("places 9-16").
- A title is a few words; a hint is one short line, and only where the action is not obvious.
- One way to say a thing: the same word for the same action on every screen.

## Rules

- Show, do not describe: while a screen or a visual idea is being discussed, draw a temporary
  mockup and send it as a file attachment instead of explaining the change in text. The chat around
  the attachment is a line or two: what changed and one question. A temporary mockup is not a code or doc edit,
  so the global "yes before edit" does not apply to drawing it: when the owner proposes a visual change, draw it at
  once, never ask "redraw?". Put the verdict's weak spots in that one or two line note, and keep the reply cap.
- This holds for every visual proposal or choice in mockup work, whoever raises it: the agent's own idea, a
  finding of a check (nothing lost, mockup-user, design-critic), a piece to restore, a choice between options
  (save flow, button tone, marker colour, a yes/no on how something looks). Draw the change on the board, or the
  options on a variants board (a yes/no becomes "as now" against "changed"), and send the screenshots with a
  one-line question. Never put such a proposal or question as text, a bullet list or a words-only option list
  ("Варіант 1 / Варіант 2", "зробити X жовтим?", "повернути ці п'ять речей?"). For this case this rule wins over
  the global question format (no bracket example, no batch of text questions, no "Рекомендую" list) and over
  every no-resend rule (the global "never re-send", "One set per answer" in browser-checks.md): the
  recommendation is one clause in the one-line note. The question always carries its own picture in the same
  message, even when the owner saw that picture earlier; no-resend covers only re-delivering a finished
  result, never a new question. Never write "you saw", "як ти бачив" or "on the earlier shots" about anything
  not on screen in this message: show it or do not mention it. Only a question with no visual side (a rule, a
  scope, a name) is asked in text.
- One board, one theme: a board covers a single flow or a single idea family. A new idea on
  another theme gets its own board; an idea that replaces an earlier one updates or removes the
  old screens. Temporary boards whose outcome is settled are deleted before the commit (step 9).
- Variants board: to choose between designs of one screen or piece, draw 2-3 variants on one
  temporary board, each a `branch` row titled with the variant («Варіант А: ...») and the same
  `given`, its screens below it. Variants differ in structure (which blocks, their order, where an
  action sits), not only in color or wording, and each stays within the project's design standard.
  Exact sizes, line breaks and spacing are not decided on a mockup. Once the owner picks, the chosen
  variant goes into the flow's board and the variants board is deleted.
- Low fidelity: grey boxes, bars, placeholder photos. A value may show which kind of mark it gets (plain text,
  a chip, an icon, a tone by meaning); sizes, fonts, spacing and exact shades are left to the real components.
  No final typography or pixel polish; where the
  project's typography for the app is not defined yet (the profile says), the mockup does not define it.
- A desktop screen board (`"frame": "desktop"`) lives in its own mockups folder, set in the profile; never mix it
  with phone boards. Its arrows go down, one screen per row.
- Phone size is fixed in `mockups.css` (the project's own file wins over the generated default); mockups
  are not responsive.
- The board reads as a story: caption above each frame, an arrow to the next screen labelled
  with the action. Number screens with `step`.
- The caption says where the user is ("Picks an item", "A request came from A"), not what changed in
  the design. An arrow label is exactly one user action, written as a verb and the exact element on
  the screen ("tap on the photo of the item «Name»", "tap on the button «Ask»", "tap on ☰ at the top
  right"), so it is clear where the tap lands; never a bare button name or a vague target like "tap on
  an item"; a second action needs its own screen and arrow. Labels are plain words: the generator
  draws the arrow, so no → or ↓.
- Every screen is reached by an arrow with the action that led to it. Each path of the flow,
  the first one included, starts with a `branch` row: a title and `given` with the precondition
  ("**Precondition:** an item is already chosen"). A popup or warning is never the first screen of a
  branch: draw the screen it opens from.
- Service text never shows on the page: sources, what is approximated or left out, design changes and their reasons go
  in the spec's `authorNotes`. The viewer sees at most one short `notes` line under the title.
- In a flow with two people, set `user` (`A` or `B`) on every phone: the frame color and the
  "A1"/"B4" tag (letters set in `mockups.config.json`) show whose phone it is, so the caption does not repeat the name.
- A mockup never changes rules. A new product rule goes to its feature or standard
  only after the owner accepts it (see the `dev-kit:documentation` skill, section "Where things go").
- A copy is not a source: a block, tone or button kind taken from another board is checked against the
  design standard like a new one. An older board only shows how a piece is built, never which colour
  means what.
- Who edits the spec: a small change (a word, a tone, a spacing, one block moved, in a few known
  places) is made by the caller with Edit. A bigger change (new screens or branches, a redesign, a new
  generator block) goes to a fresh `dev-kit:coder` (sonnet) with a short brief: the spec path, the
  change and the success check. Never keep one coder through a whole session: its context grows and
  it slows down.
