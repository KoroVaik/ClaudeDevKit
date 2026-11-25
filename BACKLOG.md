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

## Project lead: event wake-ups give a status line or no text, never a free-text note

What: in `plugins/dev-kit/skills/project-lead/SKILL.md`, "Message templates" (the line "P never writes a free-text note beside the blocks") and the forced-output paragraph say it outright: an event with no change for the owner (a usage-limit line «ЛІМІТ: ...», a C freeing the shared editor, a finished retro) gets only a status line in the template, or no text. P never sends plain sentences instead of the blocks («Nothing new needs you», «Your limit is N%», «The session finished»). The usual end-of-turn pressure to write something is not the host reminder that allows the forced-output state.
Why: P: Prishch, 2026-11-24/25, answered such events with free plain-English text; owner: «Чому на англ? Чому не показуєш статистику а пишеш цей текст?». The English part is already fixed in the owner's global rules (Reply language, 2026-11-25); this entry covers only the free-text part.
Cheapest test: replay a usage-limit line and a finished retro to a lead; the reply is a status line in the template or empty, never a plain sentence.
Verdict: owner yes 2026-11-25 (P: Prishch chat); simple edit, one place.

## Claude facts: a "This PC" section for Windows machine facts

What: add a section «This PC» to `plugins/dev-kit/claude-facts.md`, kept by the `dev-kit:facts-keeper` agent like the other entries (what happens, seen date, how to re-check). Sessions record there checked facts about the owner's Windows PC that affect work, and read it before naming a machine cause (low memory, disk, a killed process). First facts to seed (checked 2026-11-25 in Zhratva, read-only): 32.6 GB RAM; fixed pagefile 48 GB initial / 64 GB max on C: (automatic management off); commit limit about 79 GB; peak pagefile use 4.5 GB. Windows does not kill processes for low RAM like the Linux OOM killer; a real shortage shows as Resource-Exhaustion-Detector event Id 2004 in the System log (none in the 4 days before 2026-11-25). Claude Code's own low-memory handling only retires idle background sessions (`daemon.log` `[low memory]`, already in the facts file). Re-check commands: `Get-CimInstance Win32_PageFileUsage`, `Get-CimInstance Win32_ComputerSystem | Select AutomaticManagedPagefile`, `Get-WinEvent -FilterHashtable @{LogName='System';Id=2004;StartTime=(Get-Date).AddDays(-3)}`.
Why: in Zhratva on 2026-11-24/25 a session told the owner a paid run «stopped for low PC memory» and asked him to close Unity; a read-only check found no memory shortage (the runner dropped the child's exit code, cause unknown). The owner asked to note such nuances the way Claude app facts are noted.
Cheapest test: facts-keeper writes the section with the seed facts; a session asked "a run died, is it low memory?" reads it and checks event 2004 before blaming memory.
Owner said (2026-11-25, Zhratva «Обговорення: Прогони і пам'ять ПК»): «Хотілось би ще десь нотувати такі ньюанси, як це робиться для клод знань»; to «Додаємо розділ «Цей ПК» у цей файл знань?» he answered «Так».
