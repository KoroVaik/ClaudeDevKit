# Hand work to the project lead

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
You give work to one session per project, the project lead (P), and decide only what is yours: P starts
the task sessions, merges their work and tells you the result. You are the CEO and do not micromanage.

## Rules
### Roles
P is one session per project. It starts task sessions (C), each in its own worktree, merges their
finished work into main and tells you the result. It does no task work itself.

### P's messages: session states and question counts
Every status message from P has two short blocks: «Питання без відповіді» (a new question written in
full once, older ones only counted, urgent ones always named) and «Статуси сесій» (each session's state
and name). A message with an open question always ends with one question you can answer with a bare «так»:
«Показати всі питання?» when some question is not written out (on «так» P lists every question in full,
numbered), the question itself when it is the only one, or «Приймаєш усі мої рекомендації?» when several
are written out. A bare «так» or «ні» answers that last line; P never asks back which one you meant.
You can still answer by number («1 так, 3 ні»). P writes at once on each event, only
what changed; the other sessions still at work share one last line «ще працюють: «A», «B»». After a plugin-update restart, or when Claude Code demands a reply where P has nothing new,
P shows the current state in this form, never a filler phrase; with nothing running and nothing
waiting, it is one line saying so.

### P never asks what you already answered in a session
Before P asks you about a session or shows its status, it reads what you wrote in that session since
its last report. If you already answered there (for example «так» to closing a discussion), P drops its
own question silently and acts on your answer. Sessions also tell P such answers in a message that
starts with a fixed kind word: every message between sessions starts with one word from a short fixed
list (`plugins/dev-kit/messages.md`), such as «ГОТОВО», «ПИТАННЯ» or «ВЛАСНИК ВІДПОВІВ».

### Critical items reach your phone
A critical item (a session cannot go on without you, a session crashed, a risk to data or money) also
comes as a push to your phone. A session that has waited on you 20 minutes (a question from it in P's
queue, or an «Обговорення:» session) gets one reminder push, before its cache runs out after about an
hour and the next answer costs its whole context again; one push per wait.

### What P decides alone
P decides alone within the approved acceptance criteria. You get a product choice, a hard-to-undo step,
or API spend (real money through `dev-kit-api`) over $1 in total per task; sessions and subagents on your
subscription never ask you.

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
A C never asks you in its own chat; it asks P, and it messages no other session unless P's brief for it
names one.

### No permission prompts in any session
Every session a project starts, P included, runs with no permission prompts, so a message between two
sessions is never held for your approval. A project whose committed main has no hard-ban deny rules (push
to main where it deploys, deleting data, and the like) starts no sessions. P shows you the exact lines
and, on your «так», writes them to `.claude/hard-bans.json` and adds them on main itself; you cannot
decline them and type nothing. Removing a ban stays yours: you type the undo (`! dev-kit-bans undo`, only
the latest addition), and only you remove an older ban. You accept the Claude
Code disclaimer once per machine.

### No two sessions on the same task
Before a task starts, P (and any session through the manager skill) checks that no other live session of
the repository, one you started yourself included, already does it.

### P wakes only when needed
P wakes only on a task session's report, your message, or a message from the Pult watcher when a session
ends, writes the line "Роботу завершено", stops on the usage limit, waits 20 minutes or passes half its
context; P keeps no watcher of its own. While a task session works and P has been silent 50 minutes, the
Pult watcher pings P; P then shows its short status.

### P moves itself to a fresh session
When P's own context is half full, P saves its notes and asks you «Перезапустити мене зараз?» (a phone
push). The Pult watcher moves P to a fresh session of the same name after 5 quiet minutes, or at once when
you answer «так» or write «перезапускай»; you type nothing else.

How P does it: [project lead tools](../tech/project-lead.md).

Known limits: the plugin covers work inside one repository. Starting P, the project list, the phone flow
and the list of all your sessions live in the `pult` plugin
([Run all projects from the phone](../epics/run-all-projects-from-the-phone.md)).

Known limits: P does not limit the number of parallel task sessions or heavy steps by memory.
Why: on 2026-11-16 Claude Code stopped P's background watcher while Windows ran low on memory; the owner
decided memory is enough and Windows was the problem, so no queue or memory gate was added and the
pagefile was fixed instead (48 GB initial, 64 GB max).

Known limits: the reminder push always says "20 хв ... ~40 хв", even for a longer wait found after a P
restart. A wait whose question is not yet in your queue when the watcher's message arrives gets no reminder.

Known limits: your global rules keep five lines that P messages override (no headings or bold labels,
deferring a result mid-discussion, no relay of a started session, every question written out, the
closing next-step question); they still guard ordinary sessions, so a one-line exception names P's
format instead of removing them. Those rules live outside this repo and change only through
`dev-kit:edit-rules`.

## Acceptance criteria
- You give P a task whose outcome is not agreed: P asks up to 3 questions through the queue, or proposes an «Обговорення:» session when there are more or a screen is involved.
- A new question arrives: P writes it in full once; later messages only count it and ask «Показати всі питання?», and on «так» all are listed, numbered.
- You answer a P message with a bare «так»: P takes it as the answer to the message's last line and acts, never asking «1 чи 2?».
- A session finishes while you are away: P writes at once, and its message lists the session as «готово».
- A task session crashes: you get it at once, also as a push to your phone.
- A session waits on your answer for 20 minutes: you get one reminder push for that wait; a session waiting on P pushes nothing.
- You answer a session's question inside that session: P never asks you the same thing in its own chat.
- A task is finished: P merges it into main and tells you the result; you did not start or watch the C.
- A second session already works on the same task: P does not start another one.

## Built in
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `plugins/dev-kit/skills/manager/SKILL.md`
- `plugins/dev-kit/agents/overlap-checker.md`
- `plugins/dev-kit/messages.md`
- `plugins/dev-kit/scripts/sessions.py`
- `plugins/dev-kit/bin/dev-kit-sessions`
- `tools/tests/test_sessions.py`
- `plugins/dev-kit/scripts/hard_bans.py`
- `plugins/dev-kit/bin/dev-kit-bans`
- `tools/tests/test_hard_bans.py`

## Open
- [ ] Defect: a question P shows only in chat, not in PROGRESS.md "Open questions", is lost when P restarts; `plugins/dev-kit/skills/project-lead/SKILL.md`
