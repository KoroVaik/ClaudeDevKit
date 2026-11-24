# Rules subscription: rules-kit

The rules plugin: the retro, the edit-rules skill, its checker agent, the templates and the scripts and hooks that
serve them. It subscribes itself, reviewed by ClaudeDevKit. Format:
`plugins/rules-kit/scripts/subscriptions.py`.

| Setting | Value |
|---|---|
| set | rules-kit |
| reviewed by | ClaudeDevKit |
| lands by | branch merged by P: ClaudeDevKit; bump plugins/rules-kit version with a release mark in plugins/rules-kit/releases.json |

## Files

| Path (glob, relative to the set root) | Type | Part kinds | Section |
|---|---|---|---|
| skills/retro/SKILL.md | process | skill rules-kit:retro | |
| skills/edit-rules/SKILL.md | process | skill rules-kit:edit-rules | |
| agents/rule-reviewer.md | process | agent rules-kit:rule-reviewer | |
| agents/part-reader.md | process | agent rules-kit:part-reader | |
| templates/global-rules-subscription.md | process | skill rules-kit:retro | |
| hooks/hooks.json | technical | hook rules-kit | |
| hooks/*.py | technical | hook rules-kit | |
| scripts/retro.py | technical | skill rules-kit:retro, hook rules-kit | |
| scripts/subscriptions.py | technical | skill rules-kit:retro, hook rules-kit | |
| scripts/*.py | technical | | |
| bin/* | technical | | |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| a retro session writes into a main checkout | technical | in a «Ретро: » session an Edit or Write call fails because its path is in the main checkout (the session must call EnterWorktree first) |
| a fix with one sighting | process | an item file has a `- fix:` line, one `- seen:` line and a status other than `urgent` |

## May change itself

| Path | Changes |
|---|---|
| skills/** | word, sentence, new sign |
| agents/** | word, sentence, new sign |
