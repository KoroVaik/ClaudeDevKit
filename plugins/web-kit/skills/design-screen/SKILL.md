---
name: design-screen
description: Use when a screen or flow is designed with the owner, in two stages. Stage 1, structure - the owner asks to draw, sketch or mock up a screen or flow ("намалюй мокап / флоу / екран"), proposes or asks about a visual change that adds a new block, order or flow, discovery or brainstorming needs a visual of a flow (the `show-idea` slot), or the agent itself is about to put a visual proposal, a restored piece or a choice between looks to the owner. Stage 2, polish - the owner remarks on the look of a built screen polished on real components in the design sandbox (too big, clumsy corners, a screenshot with an arrow drawn on it - "зроби менше", "спробуй інакше", "бери варіант Б", "чип здоровенний", "радіуси кострубаті"), or picks a variant shown from it. Not for building the screen itself (a build session does that from the approved design) and not for checking that a scenario works (that is e2e-check).
---

# Design screen

One loop for designing a screen with the owner, in two stages:

- **Stage 1, structure:** a low-fidelity mockup board decides which blocks a screen has, their order, the
  words and the kind of each mark. It ends with the owner's «так» to the mockup, recorded in the feature
  file. Read [stage1-mockup.md](stage1-mockup.md) and the spec format [spec-format.md](spec-format.md).
- **Stage 2, polish:** after the screen is built, the look is settled on real components in the project's
  design sandbox: only what the mockup leaves open (sizes, corners, spacing, line breaks) and what the
  owner's remark names. Read [stage2-sandbox.md](stage2-sandbox.md). A remark that turns out to be a
  structure question (another block, another order) stops stage 2: say it in one line and go back to
  stage 1.

Read only the side files of the stage that runs. Read the profile section `## design-screen` of
`.claude/dev-kit.md` if it exists: the mockups folder (default `docs/mockups`), the reference spec, the
design standard, the language of the screen text, the sandbox (URL, port, data sets, checks), the app frame
selector, the window size and device scale of the shots, and the project's other specifics. It overrides
the defaults here.

## Roles

The main session (the one the owner talks with) decides, writes briefs, makes small spec edits, commits and
writes the message to the owner. It never opens a PNG itself: in the phone app every image it reads shows in
the owner's chat, unnumbered next to the set. The evidence is the designer's verdict and the size `web-kit-shot`
prints; a shot that may be cut off, empty or illegible goes to `web-kit:shot-taker`, which opens it and reports.
Why: owner, Zhratva, 2026-11-20: a spot-check picture reached the chat beside a numbered set of two. Agents
run one after another, with the full brief each time (they remember nothing).

- `web-kit:user` (sonnet), «користувач»: a fresh ordinary user, mode mockup (PNGs only, no browser).
- `web-kit:designer` (sonnet), «дизайнер»: the design standard, the feature's rules and the mockup; never
  edits.
- `web-kit:shot-taker` (haiku): stage 1, only when `web-kit-shot` fails or a shot comes out wrong; stage 2,
  takes the sandbox shots from a list.
- Stage 1: `dev-kit:coder` (sonnet) for bigger spec changes, `dev-kit:investigator` and `dev-kit:reviewer`
  for the facts and nothing-lost checks (stage1-mockup.md).
- Stage 2: `web-kit:sandbox-builder` (sonnet), modes `try`, `fix`, `apply`, `sync-mockups`.

A tool without subagents or headless shots skips the loop and says so in the hand-over.

## Shots

Headless only; the loop never opens the in-app browser. A board is shot with
`web-kit-shot --board <board.html> --out <folder> --profile <profile path>` (one PNG per screen id, no
selectors; `--screens d1,u3` for some), run by the session itself after every rebuild. Sandbox pages are
shot from a spec (`web-kit-shot --spec`, stage2-sandbox.md). The rules for selectors, size and
sending are in [browser-checks.md](${CLAUDE_PLUGIN_ROOT}/browser-checks.md), "Screenshots go to the
owner"; the format is at the top of `scripts/capture.mjs`.

## The loop before each show

Before the owner sees a board or a set of variants:

1. **User walk.** A fresh `web-kit:user`, mode mockup, once per branch of the board (stage 1) or per
   variant (stage 2), each a fresh run. The brief holds only what the user would know: the onboarding
   text and the report language from the profile section `## user`, the one-line feature announcement
   (it names neither the screen nor the control), the real-life situation (what just happened, where you
   are, what you want; no screen names or button labels; the same text the feature's «Approved design»
   keeps), and the PNG paths of the screens in path order: each screen frame alone, no board title,
   caption, note or arrow. Add the shots of today's screen only when the feature changes an existing
   screen. Never pass captions, notes, decisions, file paths of specs or reasons.
2. **Designer review.** `web-kit:designer` gets the same PNGs, the board spec (stage 2: the board region
   shot too), the design standard, the feature file, the deliberate differences and every user report.
   It returns the defects (standard, visible flaws, mismatches with the feature's rules) and one
   concrete fix for each user finding and question, or "owner's call" with the reason.
3. **Apply.** The session applies the fixes: a small change with Edit, a bigger one through a fresh
   `dev-kit:coder` (stage 1) or `sandbox-builder` mode `fix` (stage 2). Rebuild, shoot again.
4. At most **2 iterations** of steps 1-3. What remains (open defects, "owner's call" points, user
   questions without a fix) goes to the owner with the show, each by the show rules below.

A point that comes back from a second fresh run is never closed with "the docs require it": before the next
round find in the code or data what the thing does and who uses it (for a field: where its value goes), and
give the owner that result with the point. If no reason is found, the point goes to the owner as an open
question, not as a decision to keep. A fix that would change a feature rule (a column removed, a field
renamed) is never applied in the loop: it is an "owner's call".

While the owner tunes a look round by round (a shade, a size, a spacing of elements the designer already
passed), skip the loop and run it once when the series ends, before the commit. Anything new drawn mid-discussion
(a screen, a popup, a state, a control, a block, a tone or a button kind the board did not have) goes to
`web-kit:designer` before the owner sees it, even when the user walk is skipped. Why: owner, Zhratva,
2026-11-20: new popups and a tab switcher went out without the designer and the switcher read «МоїОлі» («це
має буть флоу де дизайнер апрувить а потім мені дається»).

Once the screen is built, the live app is walked by `web-kit:user` in mode live (`web-kit:user-walk`); its
remarks outrank the mockup walk.

## Show to the owner

- **Show, do not describe.** While a screen or a visual idea is discussed, draw it (a temporary board, a
  variants board or sandbox variants) and send the pictures instead of explaining the change in text. A
  temporary mockup is not a code or doc edit, so the global "yes before edit" does not apply to drawing it:
  when the owner proposes a visual change, draw it at once, never ask "redraw?".
- **Every visual proposal or choice is drawn**, whoever raises it: the agent's own idea, a point of the
  loop, a piece to restore, a choice between options (save flow, button tone, marker colour, a yes/no on
  how something looks). A yes/no becomes "as now" against "changed". Never put it as text, a bullet list or
  a words-only option list ("Варіант 1 / Варіант 2", "зробити X жовтим?", "повернути ці п'ять речей?"). Only
  a question with no visual side (a rule, a scope, a name) is asked in text.
- **The question carries its picture** in the same message, even when the owner saw that picture earlier:
  no-resend covers only re-delivering a finished result, never a new question. Never write "you saw", "як ти
  бачив" or "on the earlier shots" about anything not on screen in this message. For this case the rule wins
  over the global question format (no bracket example, no batch of text questions, no "Рекомендую" list) and
  over every no-resend rule (the global "never re-send", "One set per answer" in browser-checks.md).
- **Delivery.** A board goes as a file attachment (in Claude Code: `SendUserFile` with `display: render`);
  one click opens it in the built-in browser, and the page carries its styles inside, so send the file from
  the mockups folder as it is. Do not open the browser pane yourself. Shots go **one `SendUserFile` call
  per image**, each with its own numbered caption naming what differs on screen; never one call or one
  shared caption over several images (close-ups and whole-page shots too). The one exception: a mockup and
  its built result of one state are one picture (`web-kit-pair`) with its title drawn on it, and such
  pictures go one call per block. Sending, blocks and numbering follow browser-checks.md,
  "Screenshots go to the owner".
- **The text** is exactly one line per variant or change, one recommendation line (at most 15 words) with
  its reason, and one question. Weak spots of the recommendation go into that line; a note that the pick
  changes a feature rule goes into the question's brackets. This is stricter than the global report list
  and wins over it: no other items, notes or arguments, no process words (built, sent, committed).
  A show asks one question, with its own pictures, and opens with a counter «Питання N/M» (M may grow when
  a new question comes up). When several visual questions are open, ask the first; ask the next only after
  the owner answers. This wins over `dev-kit:discovery-round`'s «at most 3 numbered questions per round».
  Why: owner, 2026-11-20: three questions with eight pictures in one message, so he could not tell which
  picture went with which question («По черзі!!!!!!»); the counter shows how many are left.
- Take no variant to the owner that the designer did not pass. The designer filters; it does not choose,
  and neither does the session: the recommendation is a reasoned line, the owner picks.
- The reply follows the project's chat rules (language, length).
