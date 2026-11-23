# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. An idea leaves the backlog when the owner agrees
it and it is built, or when the owner drops it.

Entry format: see the Backlog kind in [the documentation standard](plugins/dev-kit/skills/documentation/SKILL.md).
A reviewed entry gets a `Verdict:` line (the project lead's recommendation) and waits for the owner's yes or no.

## Pult: own remote client for agents

What: a status page that refreshes itself (the built `plugins/pult/scripts/status-page.py` page is a snapshot), built by a script from a status file per project that also keeps a history of finished tasks; then maybe an own Claude client app with grouping by project, what waits on me and health.
Why: the phone app's session list lacks grouping by project and what waits on the owner (`plugins/dev-kit/claude-facts.md`, "The phone app's session list does not group by project or show what waits on the owner"); the attached snapshot goes stale.
Cheapest test: serve the page from the PC (or publish it) and open it from the phone once; the own client waits on that answer.
Verdict (2026-11-20): keep as an idea; owner: yes. Both the live page and its task history wait on one open point: where a live page lives and how the phone opens it; the own client app is parked behind it.

## A manager (C) with its own sub-sessions

What: a task session gets more freedom inside its feature and starts its own sub-sessions (a sub-C under a C for a huge dependent part), taking over part of the lead's duties. Not supported today: dependent parts stay in one C with parallel subagents, an independent part goes to P as a new task.
Why: owner, 2026-11-15 (lead authority discussion): managers should take over part of the lead's duties with sub-managers; left unsupported for now, to revisit if a subagent's context proves too small.
Cheapest test: give a C a dependent part too big for one subagent's context and see whether the talk between C and sub-C stays away from P.
Verdict (2026-11-20): keep as an idea: `manager/SKILL.md` still bans a C's own sessions and no case since 2026-11-15 showed a subagent's context too small. Owner: yes.

## Retro: decision items reused across projects

What: every retro decision (a "no, the rule is not to blame" too) becomes a local file with a short cause key; another project's retro reads only the list of keys and opens the matching decisions; one that worked in two projects becomes a dev-kit rule and its file is deleted. Needs a way to keep the number of decision files manageable over time.
Why: owner, 2026-11-21: reuse of experience between projects; today each project's retro starts from its own items only.
Cheapest test: replay one real case, e.g. a decision of the Zhratva retro, and see whether the ClaudeDevKit retro would have found it by its cause key.
Verdict (2026-11-22): keep as an idea; moved from the finished retro plan, the owner has not agreed it; no case yet shows it missing. Owner: yes (2026-11-23).

## Retro: one-off items expire

What: an item whose cause was seen once and not urgent expires after about 2 weeks if it does not recur (lost work is fixed at once, never waits).
Why: first sightings stay as `waiting` items with no end today; the 2-week expiry of one-off causes had no explicit yes (owner, 2026-11-21).
Cheapest test: count the `waiting` items older than 14 days in the three projects' item folders and see how many the expiry would drop.
Verdict (2026-11-22): keep as an idea; moved from the finished retro plan, the owner has not agreed it; no case yet shows it missing. Owner: yes (2026-11-23).

## Project lead: a session that waits on something shows as «чекає» with the reason

What: (1) `dev-kit:project-lead`, «Статуси сесій»: a new state for a C that waits more than 1 minute on something other than the owner (low memory on the machine, a retry timer, a store cool-off, another session): `- чекає - «<name>» (<reason in the owner's words, with the time it resumes if known>)`. Today the only waiting state is `чекає на тебе`, so P showed such a C as `працює`. (2) `dev-kit:manager`, "A task from the project lead": a C sends P a message (kind ЗАСТРЯГ or a new kind, as the messages.md design fits) whenever it will wait more than 1 minute on something, with the reason and the resume time, and another when it resumes. (3) P shows every such report at once as that status line; it never folds a C's report into `працює`.
Why: Zhratva, 2026-11-23: a C reported to P that its app start for an import failed for lack of memory and it would retry in 30 min; P showed only «працює». Owner: «Я сказав сесії щоб повідомила тобі про проблему, вона зробила це, але ти промовчав, хоча вона тебе повідомила.» and «Але ж сесія не застрягла, а просто очікує на щось, то так і писати з причиною очікування. Очікування будем вважати коли сесія тупо чекає на щось більше ніж 1хв.»
Cheapest test: a C that hits a 30-min retry wait sends P a report; P's next message has `чекає - «C: ...» (<reason>, повтор о HH:MM)`, not `працює`.
Verdict (2026-11-23): owner already said yes to the idea on 2026-11-23; waits for the plugin agent to build it. Owner: yes (2026-11-23).
