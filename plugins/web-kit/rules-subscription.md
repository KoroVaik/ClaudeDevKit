# Rules subscription: web-kit

Browser checks of a web app: skills, agents, slots, shared browser rules and the screenshot scripts. `rules-kit` (the
retro) reads this file; format: `plugins/rules-kit/scripts/subscriptions.py`.

| Setting | Value |
|---|---|
| set | web-kit |
| reviewed by | ClaudeDevKit |
| lands by | branch merged into main by L: ClaudeDevKit or by a session of a project that enables web-kit (dev-kit:manager, "Exception: a project's own kit plugin"); bump plugins/web-kit version with a release mark in plugins/web-kit/releases.json |

## Files

| Path (glob, relative to the set root) | Type | Part kinds | Section |
|---|---|---|---|
| skills/design-screen/SKILL.md | process | skill web-kit:design-screen | |
| skills/design-screen/*.md | process | skill web-kit:design-screen | |
| skills/e2e-check/SKILL.md | process | skill web-kit:e2e-check | |
| skills/user-walk/SKILL.md | process | skill web-kit:user-walk | |
| skills/visual-check/SKILL.md | process | skill web-kit:visual-check | |
| agents/designer.md | process | agent web-kit:designer | |
| agents/layout-checker.md | process | agent web-kit:layout-checker | |
| agents/sandbox-builder.md | process | agent web-kit:sandbox-builder | |
| agents/shot-taker.md | process | agent web-kit:shot-taker | |
| agents/ui-tester.md | process | agent web-kit:ui-tester | |
| agents/user.md | process | agent web-kit:user | |
| slots.md | process | | |
| browser-checks.md | process | skill web-kit:e2e-check, skill web-kit:visual-check | |
| scripts/capture.mjs | technical | skill web-kit:visual-check, agent web-kit:shot-taker | |
| scripts/pair.mjs | technical | skill web-kit:design-screen | |
| scripts/build-mockups.mjs | technical | skill web-kit:design-screen | |
| scripts/*.mjs | technical | | |
| bin/* | technical | | |
| .mcp.json | technical | | |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| a screenshot run fails | technical | a `web-kit-shot` call returns an error and a shot-taker part follows it |
| the main session drives the in-app browser | process | outside a web-kit agent part, a call of an `mcp__Claude_Browser__*` tool in a session that is not a subagent |

## May change itself

| Path | Changes |
|---|---|
| skills/** | word, sentence, new sign |
| agents/** | word, sentence, new sign |
| slots.md | word, sentence |
| browser-checks.md | word, sentence |
