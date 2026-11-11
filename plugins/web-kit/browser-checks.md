# UI checks - who answers what, and shared browser rules

Read first by `web-kit:e2e-check` and `web-kit:visual-check`. The project's facts (URLs, ports, login,
screenshot folder, test-data marker, screen sizes) are in the profile `.claude/dev-kit.md`, section
`## e2e-check`; the skills and agents read it too.

## Who answers which question

The one table of web-kit's UI roles. The manager reaches the skills through the slots; the skills call
the agents.

| Question | Looks at | Skill (slot) | Agent | Answer |
|---|---|---|---|---|
| Does the scenario do what the feature says? | the running app, steps and expected results from the criteria | `web-kit:e2e-check`, scenario (`check-ui`) | `web-kit:ui-tester` | pass or fail per scenario |
| Can an ordinary user reach the goal, and what gets in the way? | the running app, the goal only; the mockup only after the walk | `web-kit:user-walk` (`check-usability`) | `web-kit:app-user` | goal reached or not, problems met with the user's hints, each marked fix in code or design change |
| Do the screens match the mockup? | the running app and one mockup board | `web-kit:visual-check`, mockup comparison (`check-look`) | `web-kit:mockup-checker` | matches or differs per phone |
| Does the layout hold up at the screen sizes? | the running app at the profile's widths | `web-kit:visual-check`, layout (`check-look`) | `web-kit:layout-checker` | defects per width |
| Is a freshly drawn path clear to an ordinary user? | the drawn mockup's text only, no app | `web-kit:draw-mockup` (`show-idea`) | `web-kit:mockup-user` | remarks for the owner |
| May a look variant be shown to the owner (matches the accepted mockup, no visible defects)? | the caller's headless screenshots, a headless shot of the mockup board, the UI design standard; no browser | none: the project's design-sandbox rule calls it before variant shots are sent | `web-kit:design-critic` | pass or fail per variant, each defect with its reference |

`mockup-user` and `app-user` are the same ordinary user (persona in the profile section `## mockup-user`):
one reads a drawn path, the other walks the live app. When they disagree, the live app wins.
`mockup-checker` lists every difference from the board; `app-user` reports what got in a user's way and uses
the board only to say where each fix belongs.

## Shared browser rules

- **Consent, per kind.** A browser check needs the owner's separate, explicit consent for the current
  task, under the project's rules; approval to implement a change or to preview it is not consent.
  Consent is per kind: the scenario check, the user walk and the visual check each need their own yes,
  or their own line in a plan the owner approved (the owner's global rule "One yes per plan").
- **Scenarios come from the feature.** The scenarios and the user walk's goals come from the "Acceptance
  criteria" of the feature (found with `dev-kit-check-docs --who <path>`); a check that finds a rule the
  criteria miss reports it for the feature.
- **Always a subagent**, never the main session: it keeps screenshots out of the main context. The
  agents are the ones in the table above. This covers every in-app browser action: a first check, a
  re-check after a fix (also when the report was a pass with an observation), and reaching a state for a
  screenshot (selecting text, clicking, saving, `javascript_tool`). It wins over the host's "do small
  checks inline"; a one-click check is still a subagent call. The caller only prepares data through the
  API or scripts and runs headless `web-kit-shot`; it never opens or drives the in-app browser.
- **One browser.** All agents share the one browser pane, so calls run one after another, never in
  parallel. One scenario, goal, board or profile per call.
- **One environment.** The project's frontend and API addresses are in the profile. For fresh API or
  worker code restart through the `run-app` slot, after the project's rules about processes the owner
  started. If the restart fails, report its output and stop.
- **Test data through the API.** Use the UI only for the behavior under test. The caller prepares
  fixtures, restores settings and removes test data through the authenticated API and passes the IDs to
  the agent; no page scripts around browser limits, no direct database writes. Record a baseline and the
  exact IDs created; mark records with the project's test-data marker where the scenario allows, and tie
  generated records without the marker to the exact id of the job or action that created them (the
  profile names the field). Delete only proven test-owned IDs, restore only settings the check changed,
  verify the API result. Data the owner asked to keep is not test data. Never expose credentials.
- **Screenshots go to the owner, and they must be readable.** The in-app browser's screenshot tool
  returns an image at most about 800 px wide whatever the viewport (measured 2026-11-10: a 3840x2160
  window comes back 800x452, 1024 px wide 800 px, a phone 375 px wide 657 px, which is its real size),
  and `zoom` only crops that already small image. So an in-app shot of a wide window is for the agent's
  own reading (`scale` about 0.5 there), never for the owner. For a phone width the in-app shot is
  readable and goes to the owner as it is.
  - **Wide screens (tablet and up): headless capture.** Agent shots of a wide window are not sent. The
    agent ends its report with a **Shots** list, one line per shot: `name | URL | steps | CSS selector of
    the section | caption`. The URL and the steps are only what reaches that state again from a fresh
    browser, read-only (open a page, click a tab; nothing that saves). The selector is the smallest block
    that holds the result (a section, a dialog, a form, an open item, a row), never the whole page and
    never a column, pane or card that wraps other sections. A small piece (a chip, a badge, a button, one
    cell) is never shot alone: shoot its parent block (its row, field or card), so its size against its
    neighbours shows; when that parent is too big to read the piece, shoot the piece with a `margin` of the
    page around it (about its own height, at least 16 px). The one exception: when the difference shown is
    the page layout itself (a variant changes column widths or the order of panes), the shot is the app's own
    frame (the selector the profile names), never the bare browser window with its empty side margins, and the
    spec sets `"fitHeight": true`, so a page shorter than the window ends where its content ends instead of
    showing tall empty panes. The Shots line says "whole page: layout differs". This holds for every spec,
    the caller's own included. If the profile has no sign-in steps, the agent lists the sign-in form's selectors too.
  - **The caller captures** (headless only, never the in-app browser). The agents have no shell, so the
    caller writes the spec and runs `web-kit-shot --spec <spec.json> --out <screenshot folder>` (format
    at the top of `scripts/capture.mjs`). It renders the same URL in a throwaway headless Edge or Chrome at the
    profile's window size and device scale (the screen's OS display scaling; the window size is in CSS pixels, not the monitor's physical pixels) with no profile of the owner's, and stops it
    afterwards. The password is typed from its file (`"@<path>"`), never put in a spec or a message.
    The command prints each PNG's path and pixel size; open the PNG and check that the section is not
    cut off, that its text is legible at 100%, and that the content fills most of the image: a shot that
    is mostly empty background gets a smaller selector and is captured again before sending. If it
    fails, or a state cannot be reached from a URL, say so and send the agent's in-app shot marked
    "low resolution", never as the proof.
  - **Send** every image so it can be told apart on its own (`display: render`). Images that are
    alternatives of each other (variants A/B/C, today against a candidate, states of one screen) go one
    `SendUserFile` call per image, each caption naming its variant or state ("Variant A: component on a
    second line under the ingredient"), never one shared caption over several of them; a close-up also
    names what it zooms on and its variant. Steps of one scenario may share one call, the caption naming
    the scenario and the order. The chat reply stays one line per board or scenario; the screenshots
    carry the detail.
  - **One set per answer.** Every image has a caption. All images of one answer go together in that
    answer's turn, after every one of them is ready (and screened, where a critic applies), never one now
    and another later. Captions are numbered in the order the reply names them ("1. Table close-up"). The
    reply never points to an image from an earlier message: it sends that image again in the new set.
- **After the report**, clean up what the check itself created, as above, and report any record or setting left behind. A standing fixture the owner's ongoing work still uses (the running app, the project's test draft) stays until the owner says the work is done. If a report is
  unclear, or you fixed code because of it (a fail or an observation), send the agent a follow-up or a
  rerun of that scenario rather than driving the browser yourself. If a state for a shot cannot be
  reached from a URL and read-only steps, prepare it through the API or ask a subagent to reach it, or
  send the agent's in-app shot marked "low resolution"; never drive the page yourself.
