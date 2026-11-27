# Progress

## Built

- `dev-kit` 0.1.104 - the process skills, generic agents, the documentation standard and its checker, the project lead and its session tools (standard message kinds between sessions, one permission mode with hard bans), the per-project retro and the weekly docs upkeep, cost stated as a share of the weekly limit, plugin updates timed by a critical or routine mark, the Windows shell-traps hook, the hook that refuses long foreground commands, the shared Claude API client with its spend log (`dev-kit-api`).
- `web-kit` 0.3.0 - browser checks and the two-stage screen design.
- `unity-kit` 0.2.1 - the Unity bridge, user check, scene sketch, GIFs.
- `pult` 0.1.22 - the hub: leads started at logon, the watcher that wakes sessions only on an event, the lead's move to a fresh session, the status page.
- Docs moved onto the documentation standard: [the docs index](docs/README.md).

## Top priorities

- Statistics of where the weekly limit goes (owner «Ну ок. Непогано» to the chat table, 2026-11-25, «Обговорення: Статистика витрат ліміту»): P shows a table by projects, tasks, agents and skills for the limit week; weekly totals kept forever. Built (`spend-kit stats`, spend-kit 0.1.3, dev-kit 0.1.130). Feature: [docs/features/limit-usage-stats.md](docs/features/limit-usage-stats.md).
- Live check of the event-only wakes and of a push relayed by a lead: [Open items](docs/features/start-leads-at-logon-and-heal-them.md#open).

- P moves itself like a release (owner «так», 2026-11-23, P: ClaudeDevKit chat): no «Перезапустити мене зараз?» question and no push; quiet (owner silent 5 min, no open question) -> silent move; otherwise the CAPS warning, then the move 30 s later, as in «Restart for a plugin update». Weak spot accepted: while the owner keeps writing, the move waits. Built and merged (dev-kit 0.1.106).

- Restart notice (owner «все так», 2026-11-23): no warning to child sessions; a C retries a failed send to P itself, P drops its «resend» message. Plan: `plans/restart-notice.md` «Owner's approval». Built and merged (dev-kit 0.1.104).

- Own docs of Claude app quirks (owner «так» to the plan, 2026-11-23, «Обговорення: Нюанси Claude у різних застосунках»): one facts file in dev-kit, a facts agent, collection through the retro scan, weekly re-checks. Built and merged (dev-kit 0.1.105), [plan](plans/claude-quirks-docs.md).

- No "session started" push on P self-move and from C sessions (owner «+», 2026-11-23): self-move resumes the same session with `/clear`, a C starts with no phone link. Built and merged (dev-kit 0.1.106, pult 0.1.24); retro and docs sessions too. Plan: [plans/push-noise.md](plans/push-noise.md).

- Weekly limit forecast push (owner «+», 2026-11-23, «Обговорення: Відстеження лімітів»): one phone push per week when, at the current pace, the weekly limit runs out over 6 hours before its reset and tasks are open. Built and merged (dev-kit 0.1.112, pult 0.1.30). Removed by the owner 2026-11-25 («Прибирай»: the same work costs the same limit in parallel or one by one; dev-kit 0.1.131, pult 0.1.36, spend-kit 0.1.4). Plans: [plans/limit-tracking.md](plans/limit-tracking.md), [plans/drop-forecast-push.md](plans/drop-forecast-push.md).

- Push test flow with the owner (owner «так» to the plan, 2026-11-24, «Обговорення: Як тестувати пуші на телефоні»): one readiness step, one push 5 s after «+» with text starting «Тест», one result question, no re-asks after 10 min, pushes 3 s apart; new push facts to the facts file. Built (dev-kit 0.1.115); first phone run passed 2026-11-24 («Тест 1» reached the phone). Plan: [plans/push-test-flow.md](plans/push-test-flow.md) «Owner's approval».

- C sessions shown in the app with no push (owner «+», 2026-11-24, «Обговорення: Видимість сесій C»): a C starts with no `--settings` file and no `--remote-control`; the owner may write in a C, it relays his words to P. Next: build. Plan: [plans/c-session-visibility.md](plans/c-session-visibility.md) «Owner's approval».

- Retro becomes rules-kit, Claude spend moves to spend-kit (owner «Так» to the plan, 2026-11-24, «Обговорення» on retro automation): rules checked per subscribed rule set, no owner questions, independent agent checks instead; dev-kit keeps only the development process. Next: build, large, in steps. Plan: [plans/retro-auto-rules-check.md](plans/retro-auto-rules-check.md) «Owner's approval», map [plans/retro-auto-plugin-split-map.md](plans/retro-auto-plugin-split-map.md).

- Pult stays part of dev-kit (owner «Так», 2026-11-24, «Обговорення: Відокремлення пульта від dev-kit»): no split, nothing to build; the unseen C sessions are covered by [plans/c-session-visibility.md](plans/c-session-visibility.md). Plan: [plans/pult-split-from-dev-kit.md](plans/pult-split-from-dev-kit.md) «Owner's approval».

- Wind down near a usage limit (owner «так» to the plan, 2026-11-25, «Обговорення: Плавна зупинка при вичерпанні ліміту»): leads get notices at 90%/95% weekly and 90% 5-hour, stop only sessions with a listed sign, wake them after the reset; the watcher's missed limit stop fixed. Built and merged (dev-kit 0.1.125, pult 0.1.34); gap: a notice is lost when no lead is alive. Plan: [plans/limit-wind-down.md](plans/limit-wind-down.md) «Owner's approval».

- Review of a built screen in its own discussion (owner «Так», 2026-11-25, «Обговорення: Перевірка зібраних екранів»): P only starts an «Обговорення:» session, which shows the shots and passes the owner's remarks to the C that built the screen. Built (dev-kit 0.1.132, web-kit 0.4.3); not yet run on a real screen. Plan: [plans/screen-review.md](plans/screen-review.md) «Owner's approval».

- Clearer session role names (owner «Так» to the plan, 2026-11-25, «Обговорення: Назви ролей сесій»): lead `L: <project>` («Lead»), task session `M: <task>` («Manager»), `Discuss:`, `Retro:`, `Docs:`; subagents «помічник». Built and merged (dev-kit 0.1.134, pult 0.1.37); running leads are renamed at their next restart. Plan: [plans/role-names.md](plans/role-names.md) «Owner's approval».

- Clean restart of a lead on a renaming release (owner «Так», 2026-11-26, «Discuss:» on lead context clearing): a release that renames terms or formats gets the mark `"clean": true`; the watcher then restarts the Lead with a fresh context via handoff + /clear; small fixes keep the plain resume. Next: build. Plan: [plans/lead-early-clear.md](plans/lead-early-clear.md) «Owner's approval».

- The Lead's questions are not lost or misdirected (owner «уже даю так» to the plan, 2026-11-26, «Discuss: Питання Lead не губляться»): every question written to PROGRESS.md first; the chat shows a stable window of the 2 oldest questions (critical first) with «і ще N питань», changed only by the owner's answer; the Lead never closes an item itself but marks it «✅ Вирішено, закрити?»; the Lead writes only when something waits on the owner or a result is ready; the handoff skill gets a verbatim section «Дослівно». Next: build. Plan: [plans/lead-questions.md](plans/lead-questions.md) «Owner's approval».

- Projects edit web-kit and unity-kit themselves (owner «так», 2026-11-26, «Discuss:» on direct kit edits): a session of a project that enables the kit edits it in its own ClaudeDevKit worktree, runs the checks, gets a helper review, bumps and merges; the dev-kit part still goes to the backlog. Next: build. Plan: [plans/kit-direct-edits.md](plans/kit-direct-edits.md) «Owner's approval».

Open work of the features: `dev-kit-check-docs --open`.

## Open questions


