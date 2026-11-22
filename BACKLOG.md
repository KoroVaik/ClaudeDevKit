# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. An idea leaves the backlog when the owner agrees
it and it is built, or when the owner drops it.

Entry format: see the Backlog kind in [the documentation standard](plugins/dev-kit/skills/documentation/SKILL.md).
A reviewed entry gets a `Verdict:` line (the project lead's recommendation) and waits for the owner's yes or no.

## Pult: own remote client for agents

What: a custom remote interface for agents, maybe an own Claude client app without the extra features and with the missing ones (grouping by project, what waits on me, health). A self-updating status page instead of a chat list is the first step.
Why: idea from the Pult repo, 2026-11; the phone app's session list does not group by project or show what waits on the owner.
Cheapest test: one static page that reads `claude agents --json` and the projects' PROGRESS.md files and shows them grouped by project.
Built (2026-11-16): first step, `plugins/pult/scripts/status-page.py`; the Pult session sends the page on "статус". Still an idea: a page that refreshes itself, and the own client app. Deferred by the owner (2026-11-19): the attached HTML is a snapshot and cannot refresh itself; first decide where a live page lives (served by the PC or published) and how the owner opens it from the phone.
Merged (2026-11-20, owner's yes): «P status built by a script, with a history of finished tasks»: `dev-kit-sessions` (or the watcher) keeps a status file per project (live sessions, open questions by kind, finished tasks); P pastes its ready lines, and the history is a page. Owner, 2026-11-19: «Чи можна написати скрипт який формуватиме хтмл статус? Відповідно буде видно історію готових задач».
Verdict (2026-11-20): keep as an idea; owner: yes. Both wait on one open point: where a live page lives and how the phone opens it; the own client app is parked behind that.

## A manager (C) with its own sub-sessions

What: a task session gets more freedom inside its feature and starts its own sub-sessions (a sub-C under a C for a huge dependent part), taking over part of the lead's duties. Not supported today: dependent parts stay in one C with parallel subagents, an independent part goes to P as a new task.
Why: owner, 2026-11-15 (lead authority discussion): managers should take over part of the lead's duties with sub-managers; left unsupported for now, to revisit if a subagent's context proves too small.
Cheapest test: give a C a dependent part too big for one subagent's context and see whether the talk between C and sub-C stays away from P.
Verdict (2026-11-20): keep as an idea: `manager/SKILL.md` still bans a C's own sessions and no case since 2026-11-15 showed a subagent's context too small. Owner: yes.

## A background task session cannot run check-ui or check-usability

What: sessions the project lead starts with `claude --bg` have no `mcp__Claude_Browser__*` tools, so the web-kit `ui-tester` and `user` subagents (web-kit:e2e-check, web-kit:user-walk) cannot run there. No route is documented: `web-kit/browser-checks.md:14-15` and `38-43` require the in-app browser; dev-kit project-lead SKILL.md "Build a designed screen" (around lines 534-541) tells the C to run check-ui and check-usability itself. Seen live in Zhratva on 2026-11-21 («C: Обід на справжніх акаунтах») and 2026-11-22 («C: Огляд телефонного застосунку»): both had to skip the owner-approved walk and e2e check.
Why: owner-approved checks are silently skipped; the lead has no way to run them.
Cheapest test: start one `claude --bg` session and list its tools for `mcp__Claude_Browser__*`; then decide between a headless scenario route (e.g. Playwright via a web-kit command) or a documented hand-off to a session that has the browser pane.
