# The other-repo helper works again

Owner's words (2026-11-19): «Так» to «Запустити нову сесію «C: Помічник для інших репозиторіїв»? (помічник для чужих репозиторіїв знову працюватиме)».

## Checked facts
- The owner's global rules (C:/Users/korov/.claude/CLAUDE.md, "Stay in the session's project") send every edit in another repository that runs no code to the `other-repo-editor` subagent; that agent lives in the owner's user agents, not in a plugin.
- dev-kit's hook plugins/dev-kit/hooks/narrow-agents.py (wired in plugins/dev-kit/hooks/hooks.json, test tools/tests/test_narrow_agents.py) refused it on 2026-11-19 in P: ClaudeDevKit: «subagent type 'other-repo-editor' is not a narrow project or enabled plugin agent; use one of: brag:*, dev-kit:coder, ...».
- So the global rule and the hook contradict each other; P then had to commit an entry in Zhratva itself.

## Goal
A session in a dev-kit project can launch `other-repo-editor` again, while the hook still blocks the broad agents it was made to block. Keep the global rule and the hook consistent (README.md line for the hook too).

## Success criterion
The hook lets `other-repo-editor` through and still refuses the agents it refused before (tests), and a live launch of `other-repo-editor` from a dev-kit project session is not refused.

## Paid spend
0

## Done (dev-kit 0.1.60)
- narrow-agents.py: a `USER_AGENTS` list (`other-repo-editor`) is allowed while `~/.claude/agents/<name>.md` exists; it is also named in the deny reason. Other user-level agents, built-ins and unknown plugin agents stay refused.
- Tests: 4 new (allowed, listed in reason, refused without its file, another user agent refused); all 37 pass.
- Hook run from the worktree against the real home: `other-repo-editor` allowed, `general-purpose` refused.
- README hook line updated. The global rule already sends work to `other-repo-editor`, so no rule text changed.
- Not checked yet: a live launch. The korov-dev marketplace is a directory one at the main checkout, so sessions run the hook from main; the live check is possible only after the merge.
