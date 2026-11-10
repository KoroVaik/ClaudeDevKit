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

`mockup-user` and `app-user` are the same ordinary user (persona in the profile section `## mockup-user`):
one reads a drawn path, the other walks the live app. When they disagree, the live app wins.
`mockup-checker` lists every difference from the board; `app-user` reports what got in a user's way and uses
the board only to say where each fix belongs.

## Shared browser rules

- **Consent, per kind.** A browser check needs the owner's separate, explicit consent for the current
  task, under the project's rules; approval to implement a change or to preview it is not consent.
  Consent is per kind: the scenario check, the user walk and the visual check each need their own yes.
- **Scenarios come from the feature.** The scenarios and the user walk's goals come from the "Acceptance
  criteria" of the feature (found with `dev-kit-check-docs --who <path>`); a check that finds a rule the
  criteria miss reports it for the feature.
- **Always a subagent**, never the main session: it keeps screenshots out of the main context. The
  agents are the ones in the table above.
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
    browser, read-only (open a page, click a tab; nothing that saves). The selector is one block that
    shows the result (a list, a dialog, a form, a row), never the whole page. If the profile has no
    sign-in steps, the agent lists the sign-in form's selectors too.
  - **The caller captures.** The agents have no shell, so the caller writes the spec and runs
    `web-kit-shot --spec <spec.json> --out <screenshot folder>` (format at the top of
    `scripts/capture.mjs`). It renders the same URL in a throwaway headless Edge or Chrome at the
    profile's window size (4K for the Zhratva admin) with no profile of the owner's, and stops it
    afterwards. The password is typed from its file (`"@<path>"`), never put in a spec or a message.
    The command prints each PNG's path and pixel size; check that the section is not cut off and that
    its text is legible at 100%. If it fails, or a state cannot be reached from a URL, say so and send
    the agent's in-app shot marked "low resolution", never as the proof.
  - **Send** the PNGs and the in-app phone shots in one `SendUserFile` call (`display: render`, a caption
    naming the board or scenario). The chat reply stays one line per board or scenario; the screenshots
    carry the detail.
- **After the report**, clean up as above and report any record or setting left behind. If a report is
  unclear, send the agent a follow-up rather than driving the browser yourself.
