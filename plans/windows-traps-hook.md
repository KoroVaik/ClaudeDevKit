# Hook: stop the three known Windows Python and shell traps

Owner's words: yes in the retro of 2026-11-21 (BACKLOG.md entry «Hook: stop the three known Windows Python and shell traps», `Verdict: owner yes in retro 2026-11-21`).

What, why and the cheapest test: that BACKLOG.md entry (read it whole). Gate reviewer's evidence: C:/Users/korov/.claude/dev-kit/retro/gate-2026-11-21.md, item R1. The rule's home stays the owner's C:/Users/korov/.claude/docs/tools.md (Python section).

Success criterion: replaying the failed commands from the retro evidence through the hook blocks most of them and none of the commands that worked; each refusal names the working form in one line; read-only inline Python with `-X utf8` passes. The BACKLOG entry is removed in the same branch; dev-kit version bumped; lint passes.

Paid spend: 0 USD so far.

## Result (2026-11-21)

Corpus: 7201 Bash/PowerShell calls with outcome from all transcripts modified since 2026-11-20 (scripts and data in the job tmp folder, not kept). Bash failures classified by error text.

| Class | Calls | Refused by the hook |
|---|---|---|
| encoding (UnicodeEncode/DecodeError) | 130 | 129 |
| heredoc "unexpected EOF ... matching quote" | 48 | 42 |
| /tmp failures (true /tmp paths; the classifier also counted job-tmp paths) | about 12 | 10 |
| worked | 6487 | 1399: python without `-X utf8` 1391, heredoc size 4, /tmp 4 |

- (a) is as approved: every python launch without `-X utf8` is refused, so working calls without it are refused too (about 1390 calls in about 153 transcripts; about one refusal per context, since agents adapt). P's "none of the commands that worked" cannot hold together with (a); the owner's approved wording (a) won.
- (b) narrowed by data: heredoc failures are driven by size (all over about 8000 chars), not non-ASCII (588 non-ASCII heredocs worked). `python -c` with non-ASCII: 187 worked with `-X utf8`, no failures, so that part is dropped. Rule: heredoc body over 7000 chars.
- (c) narrowed by data: `/tmp` as a shell argument works (the shell maps it, 231 working calls); it fails only inside Python code. Rule: `/tmp` in a heredoc fed to python or written to a .py file, or in a `python -c` string.
- PowerShell: 0 encoding failures in 302 calls, so the hook is on Bash only.
- Plugin docs that tell agents to run `python ...` now say `python -X utf8 ...`, so the hook does not refuse the plugin's own commands.
- Seen on the way, not fixed: the Bash tool turned `\` into `\` inside a quoted heredoc (my own extraction script); likely the cause of several "python SyntaxError" failures (18 in the corpus).
- 20-call catalogue-judge batch (second part of the BACKLOG's cheapest test): not run here; it needs a Zhratva run.
- Independent review (sonnet reviewer): its 4 confirmed findings fixed (launcher keywords, per-launcher check, quoted text, /tmp scope); tools.md left as is: its advice is stricter than the hook, not in conflict.
