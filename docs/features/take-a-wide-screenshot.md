# Take a wide screenshot

Epic: [Check and design screens in the browser](../epics/check-and-design-screens-in-the-browser.md)

## Purpose
The owner gets readable evidence screenshots of wide screens.

## Rules
### Wide screens are shot headless at full resolution
Readable evidence screenshots of wide screens come from `web-kit-shot`, a headless full-resolution
capture.
Why: the in-app browser's screenshot is too small to read ([Claude facts](../../plugins/dev-kit/claude-facts.md), "The in-app browser screenshot is at most about 800 px wide").

The window size comes from the project's profile ([sections](../tech/project-profile.md)).

### A phone shot is one window
At a phone width (under 768 px) each PNG is exactly one window, emulated as a phone; a long page is
several shots taken after scrolling (`scroll`, `scrollTo` steps or `"screens": true`), never one
stitched image.
Why: owner, Zhratva, 2026-11-20: a mobile page came out as one tall image with the tab bar in its middle.

## Acceptance criteria
- A wide screen is shot with `web-kit-shot`: the picture has the full resolution of the window, not the capped size of the in-app browser's shot.
- A spec at `"size":"375x812","scale":2` with two shots of one page, the second after `{"scroll":800}`,
  gives two different 750x1624 PNGs.

## Built in
- `plugins/web-kit/scripts/capture.mjs`
- `plugins/web-kit/bin/web-kit-shot`
