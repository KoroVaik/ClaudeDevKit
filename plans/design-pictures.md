# Pictures in design shows and P questions

Owner's words (Zhratva, 2026-11-20): «Чому сюди не продублювались фінальні фото?», «Фото потрібно розбивати на логічні блоки і постити не склеєними»; the owner said «так» to these ideas in the Zhratva lead's chat (see the entries' Why lines).

## Task
Build the four BACKLOG.md entries: «Design-screen spot check leaks into the owner's chat», «Design-screen: no new picture reaches the owner without the designer», «project-lead: a look question carries its shots every time», «web-kit: pictures for the owner in blocks, mockup and result side by side». Run `dev-kit:edit-rules` steps 1-2 for each and check that the entry's claim holds in the current files first (web-kit 0.2.2 just added «one question at a time with a counter» to design-screen «The text»; the owner's global CLAUDE.md now has a «Pictures go to the owner» bullet). Do not apply an entry blindly: if one is already covered, clashes or looks wrong, report it to P with the fact. Bump plugin versions, remove built entries.

## Success criterion
Each entry's cheapest test is met by the rule text (no live run needed); lint and tests pass; no duplicate of the global pictures rule.

## Paid spend
Total: 0 USD

## Result (2026-11-20)
All four entries held against the current files (no duplicate of the global pictures rule: plugin text links to it) and are built: web-kit 0.3.0 (design-screen: no spot check by the main session, designer before any new drawn element; browser-checks: PNG check by an agent, blocks, `web-kit-pair` for mockup and result; visual-check report uses it), dev-kit 0.1.77 (project-lead full list: a look question carries its shots every time). `web-kit-pair` checked on two real PNGs (title, equal height, no cut-off, seen by a haiku agent). Lint 0 errors, 556+3 tests pass. Reviewer findings on call/number wording fixed.
