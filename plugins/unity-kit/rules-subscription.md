# Rules subscription: unity-kit

Unity editor checks: skills, the editor operator agent, slots and the scripts that play recipes and cut GIFs. `rules-kit`
(the retro) reads this file; format: `plugins/rules-kit/scripts/subscriptions.py`.

| Setting | Value |
|---|---|
| set | unity-kit |
| reviewed by | ClaudeDevKit |
| lands by | branch merged into main by L: ClaudeDevKit or by a session of a project that enables unity-kit (dev-kit:manager, "Exception: a project's own kit plugin"); bump plugins/unity-kit version with a release mark in plugins/unity-kit/releases.json |

## Files

| Path (glob, relative to the set root) | Type | Part kinds | Section |
|---|---|---|---|
| skills/game-clip/SKILL.md | process | skill unity-kit:game-clip | |
| skills/game-view-check/SKILL.md | process | skill unity-kit:game-view-check | |
| skills/scene-sketch/SKILL.md | process | skill unity-kit:scene-sketch | |
| skills/unity-editor/SKILL.md | process | skill unity-kit:unity-editor | |
| skills/user-check/SKILL.md | process | skill unity-kit:user-check | |
| skills/user-check/blocks/*.json | technical | skill unity-kit:user-check | |
| agents/unity-operator.md | process | agent unity-kit:unity-operator | |
| slots.md | process | | |
| scripts/user_check.py | technical | skill unity-kit:user-check | |
| scripts/frames_to_gif.py | technical | skill unity-kit:game-clip | |
| scripts/*.py | technical | | |
| bin/* | technical | | |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| the editor bridge fails twice | technical | in a unity-operator part two editor bridge commands in a row return an error |

## May change itself

| Path | Changes |
|---|---|
| skills/*/SKILL.md | word, sentence, new sign |
| agents/** | word, sentence, new sign |
| slots.md | word, sentence |
