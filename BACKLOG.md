# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. An idea leaves the backlog when the owner agrees
it and it is built, or when the owner drops it.

Entry format: see the Backlog kind in [the documentation standard](plugins/dev-kit/skills/documentation/SKILL.md).
A reviewed entry gets a `Verdict:` line (the project lead's recommendation) and waits for the owner's yes or no.

## Pult: own remote client for agents

What: a status page that refreshes itself (the built `plugins/pult/scripts/status-page.py` page is a snapshot), built by a script from a status file per project that also keeps a history of finished tasks; then maybe an own Claude client app with grouping by project, what waits on me and health.
Why: the phone app's session list does not group by project or show what waits on the owner; the attached snapshot goes stale.
Cheapest test: serve the page from the PC (or publish it) and open it from the phone once; the own client waits on that answer.
Verdict (2026-11-20): keep as an idea; owner: yes. Both the live page and its task history wait on one open point: where a live page lives and how the phone opens it; the own client app is parked behind it.

## A manager (C) with its own sub-sessions

What: a task session gets more freedom inside its feature and starts its own sub-sessions (a sub-C under a C for a huge dependent part), taking over part of the lead's duties. Not supported today: dependent parts stay in one C with parallel subagents, an independent part goes to P as a new task.
Why: owner, 2026-11-15 (lead authority discussion): managers should take over part of the lead's duties with sub-managers; left unsupported for now, to revisit if a subagent's context proves too small.
Cheapest test: give a C a dependent part too big for one subagent's context and see whether the talk between C and sub-C stays away from P.
Verdict (2026-11-20): keep as an idea: `manager/SKILL.md` still bans a C's own sessions and no case since 2026-11-15 showed a subagent's context too small. Owner: yes.

## A background task session cannot run check-ui or check-usability

What: sessions the project lead starts with `claude --bg` have no `mcp__Claude_Browser__*` tools, so the web-kit `ui-tester` and `user` subagents (web-kit:e2e-check, web-kit:user-walk) cannot run there. No route is documented: `web-kit/browser-checks.md:14-15` and `38-43` require the in-app browser; dev-kit project-lead SKILL.md "Build a designed screen" (around lines 534-541) tells the C to run check-ui and check-usability itself. Seen live in Zhratva on 2026-11-21 («C: Обід на справжніх акаунтах») and 2026-11-22 («C: Огляд телефонного застосунку»): both had to skip the owner-approved walk and e2e check.
Why: owner-approved checks are silently skipped; the lead has no way to run them.
Cheapest test: start one `claude --bg` session and list its tools for `mcp__Claude_Browser__*`; then decide between a headless scenario route (e.g. Playwright via a web-kit command) or a documented hand-off to a session that has the browser pane.
Verdict (2026-11-22): complex (web-kit browser route and the lead flow): one C after the owner's yes.

## Retro: decision items reused across projects

What: every retro decision (a "no, the rule is not to blame" too) becomes a local file with a short cause key; another project's retro reads only the list of keys and opens the matching decisions; one that worked in two projects becomes a dev-kit rule and its file is deleted. Needs a way to keep the number of decision files manageable over time.
Why: owner, 2026-11-21: reuse of experience between projects; today each project's retro starts from its own items only.
Cheapest test: replay one real case, e.g. a decision of the Zhratva retro, and see whether the ClaudeDevKit retro would have found it by its cause key.

## Retro: one-off items expire

What: an item whose cause was seen once and not urgent expires after about 2 weeks if it does not recur (lost work is fixed at once, never waits).
Why: first sightings stay as `waiting` items with no end today; the 2-week expiry of one-off causes had no explicit yes (owner, 2026-11-21).
Cheapest test: count the `waiting` items older than 14 days in the three projects' item folders and see how many the expiry would drop.
