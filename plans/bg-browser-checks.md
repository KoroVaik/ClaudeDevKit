# Screen checks in background task sessions

Owner's words: none in chat; the owner said «так» on 2026-11-23 to «Запустити нову сесію «C: Перевірки екрана у фонових сесіях»? (зараз перевірку екрана тихо пропускають)».

Source: BACKLOG.md entry «A background task session cannot run check-ui or check-usability» (read it first: the facts, the places in web-kit and project-lead, the cheapest test).

Goal: a C that the project lead starts with `claude --bg` can run the owner-approved check-ui and check-usability of a web screen (web-kit e2e-check and user-walk), or the flow hands them to a place that can, with nothing skipped silently.

Success criterion: in one live test, a background session runs (or correctly hands off) the check-ui of a small web page and the result reaches P; the rules in web-kit and dev-kit project-lead / test-change name that route; the backlog entry is removed.

Notes: pick the route yourself after the cheapest test (headless browser route in web-kit, or a documented hand-off); a choice that changes what the owner sees or does goes to P as a question. Bump plugin versions as the repo rules say.

## Work log

- Cheapest test (2026-11-23): this C (a `claude --bg` session) has no `mcp__Claude_Browser__*` tools; confirmed.
- Route picked: headless browser shipped with web-kit (`plugins/web-kit/.mcp.json`, server `headless`,
  `@playwright/mcp@0.0.84`, installed Edge, isolated profile, output in `%TEMP%/web-kit-headless`).
  Checked in `claude -p --plugin-dir`: tools appear as `mcp__plugin_web-kit_headless__browser_*`; navigate,
  click, snapshot and screenshot work; a phone window shot is full size (375x812). A screenshot `filename`
  lands in the session's working folder (the repo), so agents never pass one.
- Agents use the in-app browser when the session has it, else the headless one; with neither, the C reports
  ПИТАННЯ to P naming the check. Also covers `layout-checker` (check-look), same cause.

Spend: ~0.3% of the weekly limit, estimate (plus two short test sessions on the subscription); API: 0 USD

## Live test (2026-11-23)

- `claude --bg` in this worktree with the edited web-kit: no in-app browser tools, headless tools present;
  the caller followed "Two browsers". Its `web-kit:ui-tester` launch was refused by dev-kit's narrow-agents
  hook, because a plugin loaded with `--plugin-dir` is not in the project's enabled plugins (test set-up
  only: real projects enable web-kit).
- `claude -p` (no in-app browser either) in a scratch folder: the caller briefed `web-kit:ui-tester` with
  the headless lines; scenario "tap Add one twice, Count: 2" passed with steps, console check and one
  375x812 PNG under `%TEMP%/web-kit-headless`; no files left in the working folder.

## Notes

- Accepted: the headless server also starts in desktop sessions with web-kit enabled (its tools load
  deferred, so the cost is small); it pins Edge, which every machine of the owner has.
- Review (sonnet) fixed: dialog handling, `browser_evaluate` for layout-checker, in-app-only lines that do
  not apply, wide shots still go to the owner through `web-kit-shot`, dev-kit version bump, `ПИТАННЯ` (not
  `ЗАСТРЯГ`) for a check with no browser, since P can still choose.
