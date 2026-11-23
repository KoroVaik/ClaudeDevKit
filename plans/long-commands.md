# Long commands do not block the chat

Owner's words: «+» (yes, 2026-11-23) to «Запустити нову сесію «C: Довгі команди не блокують чат»? (агент не зможе зайняти чат довгою командою)».

Source: BACKLOG.md entry «Stop long commands from blocking the chat» (read it first: what, why, cheapest test).

Goal: an agent cannot start a known long command in the foreground; it must run it in the background, so the owner can still talk to the session.

Success criterion: in one live check, a foreground `sleep 120` (and one long pattern from the list) is refused with a message that says to run it in the background, and the same command with run_in_background passes; tests cover the matcher; the backlog entry is removed.

Notes: prefer a hook shipped in the dev-kit plugin (it reaches every project with dev-kit) over the owner's own settings files; any edit to the owner's own settings (the local .claude folder) goes to P first. Start small (the cheapest test), the duration recorder is optional and only if cheap. Bump plugin versions as the repo rules say.

Result (2026-11-23): hook `plugins/dev-kit/hooks/long-commands.py` (dev-kit 0.1.101) on Bash and PowerShell refuses a foreground wait of 60 s or more and the rows of the profile's `## long commands`; `run_in_background` passes. Live check with `claude -p --plugin-dir` (haiku): `echo start; sleep 70; echo end` and a listed pattern refused by the hook, the listed pattern in the background ran; a lone `sleep 120` / `Start-Sleep 120` is already blocked by Claude Code itself. Tests: `tools/tests/test_long_commands.py`; all 725 tests and the lint pass. Backlog entry removed. Not done: the duration recorder (optional) and Zhratva's own `## long commands` rows (Open items in the feature doc). No edit to the owner's settings.

Spend: <0.1% of the weekly limit, estimate; API: 0 USD
