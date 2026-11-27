# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. A project's own web-kit or unity-kit change needs no entry:
that project's session lands it (`dev-kit:manager`, "Exception: a project's own kit plugin"). An idea leaves the backlog when the owner agrees
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

## Review session: the screen question alone, in its own message

What: in `plugins/dev-kit/skills/project-lead/SKILL.md`, the first prompt of a review «Discuss:» session of a built screen (the «так» / «є питання» ask) should say: ask «екран прийнято?» in a message of its own with only the screen pictures and no other question; the user-walk design questions come in later messages, one at a time (`web-kit:design-screen`, "Show to the owner"), never as a batch beside it.
Why: owner, 2026-11-27 (Zhratva review session «Discuss: Огляд картки типу страви»): the session put the screen question, a defect note and a 5-question batch in one message; the owner's bare «Так» was ambiguous, the session asked «1 чи 2?», owner: «Знову каша з питань». Idea approved by the owner 2026-11-27.
Cheapest test: replay that review prompt; the first owner-facing message holds the pictures and only the screen question.
