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

## Clearer names for the session roles

What: rename the roles the owner meets in chat so each name points to one thing: today a task session works by the `dev-kit:manager` skill, so "менеджер" can mean it or the project lead.
Why: owner, 2026-11-25, «Обговорення: Перевірка зібраних екранів»: his «менеджер» read two ways; «дійсно неймінг кривий, треба буде подумати над адекватним потім».
Cheapest test: list every role name the owner sees in a lead's chat and session titles, and check each has one meaning.
Verdict (2026-11-25): owner «Можна зараз»: discussion started («Обговорення: Назви ролей сесій»).

## Lead: an open question list is not replaced by a later message

What: while a full list or a written-out question waits for the owner, a later Lead message (a merge, a forced-output state, a start proposal of "The project state") ends with a different closing line, and the owner's bare «так» goes to that line. Reviewer's proposal (L: Prishch): a case 6 of the closing line: the open shown items stay the last thing, with the same closing question, until answered; a start proposal stays counted meanwhile; the critical question still wins; an exception in forced output for this list. Doubts: repeats may become spam in forced output (alternative: repeat only in messages with a change); whether «Стан проєкту» stays; a partial answer «1 так».
Why: owner, 2026-11-26, L: Prishch: he answered «Так» to a list of 2 questions, but a later message ended with a «Discuss:» proposal and the Lead started it: «Я написав так на попереднє повідомлення. Тут вже хаос якийсь». Causes in `plugins/dev-kit/skills/project-lead/SKILL.md`: closing-line cases 1-5, forced output, «Reading the owner's answer». The owner wants to discuss it.
Cheapest test: replay that sequence (full list, then a ЗАКРИТО and a merge) to a Lead; the owner's «так» still answers the list.
Verdict (2026-11-26): the owner wants a talk; proposed as a «Discuss:» session.

