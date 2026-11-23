# Long commands do not block the chat

Owner's words: «+» (yes, 2026-11-23) to «Запустити нову сесію «C: Довгі команди не блокують чат»? (агент не зможе зайняти чат довгою командою)».

Source: BACKLOG.md entry «Stop long commands from blocking the chat» (read it first: what, why, cheapest test).

Goal: an agent cannot start a known long command in the foreground; it must run it in the background, so the owner can still talk to the session.

Success criterion: in one live check, a foreground `sleep 120` (and one long pattern from the list) is refused with a message that says to run it in the background, and the same command with run_in_background passes; tests cover the matcher; the backlog entry is removed.

Notes: prefer a hook shipped in the dev-kit plugin (it reaches every project with dev-kit) over the owner's own settings files; any edit to the owner's own settings (the local .claude folder) goes to P first. Start small (the cheapest test), the duration recorder is optional and only if cheap. Bump plugin versions as the repo rules say.
