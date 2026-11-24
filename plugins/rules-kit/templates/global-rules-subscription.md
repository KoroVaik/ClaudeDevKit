# Rules subscription: global

The owner's global rules: `CLAUDE.md` and `docs/*.md` in the user's `.claude` folder. The `rules-kit` retro writes this
file from its template on its first run when it is missing, and commits it in this folder's local git repository (no
push). Format: `plugins/rules-kit/scripts/subscriptions.py` in the rules-kit plugin.

| Setting | Value |
|---|---|
| set | global |
| reviewed by | ClaudeDevKit |
| lands by | commit in this folder's local git repository (no push), after rules-kit:edit-rules |

## Files

| Path (glob, relative to the set root) | Type | Part kinds | Section |
|---|---|---|---|
| CLAUDE.md | talk | | Chat replies |
| CLAUDE.md | talk | | Reply language |
| CLAUDE.md | process | | |
| docs/jargon.md | talk | | |
| docs/*.md | process | | |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| em dash in a reply to the owner | talk | an assistant reply to the owner contains an em dash or an en dash: «[—–]» |
| a process mistake was noted | process | a line for the session is added to `notes.md` in the rules-kit data folder |

## May change itself

| Path | Changes |
|---|---|
| docs/*.md | word, sentence |
