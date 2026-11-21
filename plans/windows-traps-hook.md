# Hook: stop the three known Windows Python and shell traps

Owner's words: yes in the retro of 2026-11-21 (BACKLOG.md entry «Hook: stop the three known Windows Python and shell traps», `Verdict: owner yes in retro 2026-11-21`).

What, why and the cheapest test: that BACKLOG.md entry (read it whole). Gate reviewer's evidence: C:/Users/korov/.claude/dev-kit/retro/gate-2026-11-21.md, item R1. The rule's home stays the owner's C:/Users/korov/.claude/docs/tools.md (Python section).

Success criterion: replaying the failed commands from the retro evidence through the hook blocks most of them and none of the commands that worked; each refusal names the working form in one line; read-only inline Python with `-X utf8` passes. The BACKLOG entry is removed in the same branch; dev-kit version bumped; lint passes.

Paid spend: 0 USD so far.
