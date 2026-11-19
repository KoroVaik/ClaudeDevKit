# Take a wide screenshot

Epic: [Check and design screens in the browser](../epics/check-and-design-screens-in-the-browser.md)

## Purpose
The owner gets readable evidence screenshots of wide screens.

## Rules
### Wide screens are shot headless at full resolution
Readable evidence screenshots of wide screens come from `web-kit-shot`, a headless full-resolution
capture.
Why: the in-app browser's screenshot tool returns at most about 800 px wide.

The window size comes from the project's profile ([sections](../tech/project-profile.md)).

## Acceptance criteria
- A wide screen is shot with `web-kit-shot`: the picture has the full resolution of the window, not 800 px.

## Built in
- `plugins/web-kit/scripts/capture.mjs`
- `plugins/web-kit/bin/web-kit-shot`
