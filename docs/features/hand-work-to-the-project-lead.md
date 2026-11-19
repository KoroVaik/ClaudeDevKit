# Hand work to the project lead

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
You give work to one session per project, the project lead (P), and decide only what is yours: P starts
the task sessions, merges their work and tells you the result. You are the CEO and do not micromanage.

## Rules
### Roles
P is one session per project. It starts task sessions (C), each in its own worktree, merges their
finished work into main and tells you the result. It does no task work itself.

### The owner queue
P collects what needs you in a queue and shows each item once. Every later message ends with a count of
the questions still waiting; the status or your «які питання» lists them again.

### Critical items come at once
Only a critical item (a session cannot go on without you, a session crashed, a risk to data or money)
comes at once, also as a push to your phone.

### What P decides alone
P decides alone within the approved acceptance criteria. You get a product choice, a hard-to-undo step,
or paid spend over $1 in total per task.

### P sorts each task
P sorts each task: the C alone; P and the C (an agreed feature, technical details); or, for what you get
that is not agreed yet (a «Так» to a task title does not agree it), a question first: up to 3 text
questions through the queue. More than 3, any doubt from you, or any question about how a screen looks:
P proposes an «Обговорення:» session and opens it after your «так».

### A discussion ends in the feature file
In an «Обговорення:» session you settle the meaning and the mockup with one agent, and the feature file
ends with an «Approved design» section (acceptance criteria, the approved mockup, the user's situation).
Then P starts a C that builds the screen and shows you its shots next to the mockup.

### A C asks only P
A C never asks you in its own chat; it asks P.

### No permission prompts when hard bans hold
C and P run with no permission prompts when the project's committed settings hold the hard-ban deny rules
(push to main where it deploys, deleting data, and the like). You accept the Claude Code disclaimer once
per machine.

### No two sessions on the same task
Before a task starts, P (and any session through the manager skill) checks that no other live session of
the repository, one you started yourself included, already does it.

### P wakes only when needed
P wakes only on a task session's report, your message, or when a session ends or writes the line
"Роботу завершено".

How P does it: [project lead tools](../tech/project-lead.md).

Known limits: the plugin covers work inside one repository. Starting P, the project list, the phone flow
and the list of all your sessions live in the `pult` plugin
([Run all projects from the phone](../epics/run-all-projects-from-the-phone.md)).

Known limits: P does not limit the number of parallel task sessions or heavy steps by memory.
Why: on 2026-11-16 Claude Code stopped P's background watcher while Windows ran low on memory; the owner
decided memory is enough and Windows was the problem, so no queue or memory gate was added and the
pagefile was fixed instead (48 GB initial, 64 GB max).

## Acceptance criteria
- You give P a task whose outcome is not agreed: P asks up to 3 questions through the queue, or proposes an «Обговорення:» session when there are more or a screen is involved.
- Several questions wait: each message from P ends with the count, and «які питання» lists them.
- A task session crashes: you get it at once, also as a push to your phone.
- A task is finished: P merges it into main and tells you the result; you did not start or watch the C.
- A second session already works on the same task: P does not start another one.

## Built in
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `plugins/dev-kit/skills/manager/SKILL.md`
- `plugins/dev-kit/agents/overlap-checker.md`
- `plugins/dev-kit/scripts/sessions.py`
- `plugins/dev-kit/bin/dev-kit-sessions`
- `tools/tests/test_sessions.py`
