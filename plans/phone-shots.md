# Phone shots: one screen each

Owner's words (Zhratva, 2026-11-20): «Нащо знімати таку довгу сторінку?», «На майбутнє так не має бути»; owner said «так» to the idea in the Zhratva lead's chat.

## Task
Build the BACKLOG.md entry «web-kit: phone shots are one screen each, never a stitched page» (all three parts: browser-checks.md bullet, shot-taker kind `screen`, capture.mjs scroll steps / `screens` option / `captureBeyondViewport` only for a selector or `fullPage` / `click` scrolls into view). Check whether a phone page needs `mobile: true`. Bump web-kit version. Remove the built entry from BACKLOG.md. After the build, the Zhratva stopgap (its `.claude/dev-kit.md` «Phone app shots») can shrink to a link: do not edit Zhratva; tell P in the done report.

## Success criterion
The entry's cheapest test passes: a spec with `"size":"375x812","scale":2` and two shots of one page, the second after `{"scroll":800}`; both PNGs are 750x1624 and differ. Lint and tests pass.

## Paid spend
Total: 0 USD

## Result (2026-11-20)
Built: capture.mjs (`scroll`, `scrollTo`, `"screens": true`, one-window plain shots, `click` scrolls into view, windows under 768 px emulated as a phone in spec mode, scrolling falls back to the app's inner scroll container), browser-checks.md bullet, shot-taker kind `screen` (with its own PNG check), restatements in visual-check and design-screen stage 2, feature doc rule and criterion, web-kit 0.2.1, backlog entry removed.
Decisions: phone means under 768 px (768 stays tablet, as layout-checker and browser-checks already say); a `piece` or `parent` shot at a phone width keeps its selector (small, not a stitched page); `mobile: true` (checked: overlay scrollbars no longer take width, 750 px wide PNGs).
Checks: cheapest test passes (two 750x1624 PNGs that differ); screens on a long page and on an inner-scroll app correct; lint and 553 tests pass; reviewer findings fixed.
Follow-up for P: the Zhratva stopgap (its `.claude/dev-kit.md`, "Phone app shots") can shrink to a link to browser-checks.md; not edited here.
