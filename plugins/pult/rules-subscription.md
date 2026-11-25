# Rules subscription: pult

The hub for the owner's phone: its rules (added to the home folder by the SessionStart hook), the status page and the
scripts that start, watch and restart the servers and the leads. `rules-kit` (the retro) reads this file; format:
`plugins/rules-kit/scripts/subscriptions.py`.

| Setting | Value |
|---|---|
| set | pult |
| reviewed by | ClaudeDevKit |
| lands by | branch merged by L: ClaudeDevKit; bump plugins/pult version with a release mark in plugins/pult/releases.json |

## Files

| Path (glob, relative to the set root) | Type | Part kinds | Section |
|---|---|---|---|
| rules/hub.md | talk | hook pult | Answering "статус" |
| rules/hub.md | talk | hook pult | Phone push |
| rules/hub.md | process | hook pult | |
| README.md | process | | |
| hooks/hooks.json | technical | hook pult | |
| hooks/*.py | technical | hook pult | |
| scripts/*.ps1 | technical | | |
| scripts/*.psd1 | technical | | |
| scripts/*.py | technical | | |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| a lead or a server restarted outside the scripts | process | a Bash or PowerShell call that stops or starts a lead or a Pult server (`Stop-Process`, `taskkill`, `claude stop`, `claude --bg`) and does not run a script of `plugins/pult/scripts` |

## May change itself

| Path | Changes |
|---|---|
| rules/** | word, sentence, new sign |
| README.md | word, sentence |
