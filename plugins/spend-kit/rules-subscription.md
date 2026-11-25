# Rules subscription: spend-kit

The spend plugin: the weekly-limit status line, the per-session spend files, the Claude API client and its price
table. It has no rule text of its own, only code and data, so the retro never edits it itself: a finding goes to a
session as a code change. Format: `plugins/rules-kit/scripts/subscriptions.py`.

| Setting | Value |
|---|---|
| set | spend-kit |
| reviewed by | ClaudeDevKit |
| lands by | branch merged by L: ClaudeDevKit; bump plugins/spend-kit version with a release mark in plugins/spend-kit/releases.json |

## Files

| Path (glob, relative to the set root) | Type | Part kinds | Section |
|---|---|---|---|
| hooks/hooks.json | technical | hook spend-kit | |
| hooks/*.py | technical | hook spend-kit | |
| scripts/*.py | technical | | |
| bin/* | technical | | |
| api-prices.json | technical | | |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| a spend command fails | technical | a Bash call of `spend-kit`, `spend-kit-api` or `spend-kit-statusline` returns an error |
