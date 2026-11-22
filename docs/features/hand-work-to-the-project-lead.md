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
Every status message from P has two short blocks: «Питання без відповіді» (only the counts: how many
questions from sessions, how many from P, how many urgent) and «Статуси сесій» (each session's state
and name). A message with open questions ends with «Показати всі питання?»; on your «так» P lists every
question in full, numbered, after a separate cheap check that each reads in your own words with no
agent terms. The one exception is a critical question (a session stands and cannot move without your
answer): it is shown in full as the last thing in the message, with no closing line, so a bare «так»
answers it; the next critical question is shown the same way only after you answer the first. The full
list also opens the start status of a fresh P session, but not the one after a plugin-update restart
(same chat, you saw the questions); the list ends with the question itself when it is the only one, or
«Приймаєш усі мої рекомендації?» when several are listed. A bare «так» or «ні» answers P's last line;
P never asks back which one you meant.
You can still answer by number («1 так, 3 ні»). P writes at once on each event, only
what changed; the other sessions still at work share one last line «ще працюють: «A», «B»». After a plugin-update restart, or when Claude Code demands a reply where P has nothing new,
P shows the current state in this form, never a filler phrase; with nothing running and nothing
waiting, it is one line saying so.

### How a question and a state are written
The counts are three lines: «❗ термінові» (a session stands and cannot move without your answer; a session
that asks and goes on, or a closed session with a leftover question, is not urgent), «від сесій» and «від
мене» (P's own: start a new task session, close a session, take one over, restart a crashed one, the weekly
retro, new plugin backlog entries; P never asks «Яку задачу запустити?»). A kind with zero is left out. A
question stands alone: a session's question starts with its name and «питає:»; it is in your words (what you
see or do on your side, never P's own mechanisms), with the consequence in brackets, worded so the advice is
«так», then an indented `Рекомендую: так - <reason>` (P adds one a session did not give). A question about
how a screen looks carries its shots next to the mockup every time it is written in full. An answered
question just leaves the counts, with no confirmation line.

Each line of «Статуси сесій» is the state first, then the session name exactly as the app shows it, in «»:
`працює`, `чекає на тебе` (with the reason in brackets), `стоїть, скінчився ліміт` (with the reset time),
`стоїть, сесія впала`, `готово`. The start status and your «що працює?» list every session; any other
message lists the sessions whose state changed, plus each `готово` one until you next write to P.

### P never asks what you already answered in a session
Before P asks you about a session or shows its status, it reads what you wrote in that session since
its last report. If you already answered there (for example «так» to closing a discussion), P drops its
own question silently and acts on your answer. Sessions also tell P such answers in a message that
starts with a fixed kind word: every message between sessions starts with one word from a short fixed
list (`plugins/dev-kit/messages.md`), such as «ГОТОВО», «ПИТАННЯ» or «ВЛАСНИК ВІДПОВІВ».

### Critical items reach your phone
A critical item (a session cannot go on without you, a session crashed, a risk to data or money, P's own
restart question) also comes as a push to your phone (the phone side:
[Run all projects from the phone](../epics/run-all-projects-from-the-phone.md), step 7). The queue pushes
once, when it had no question for you and gets one; later questions push nothing until you write. A status
line alone (`готово`, a usage-limit stop) never pushes, and nothing else does: no progress, merges or
event lines that need nothing. A push is one line under 200 characters: the project, then what to act on
first; it is skipped while you look at the screen.

A reminder push is the one time-based push. A session that has waited on you 20 minutes (a question from
it in P's queue, a taken-over session of yours that shows `чекає на тебе`, or an «Обговорення:» session)
gets one, before its cache runs out after about an hour and the next answer costs its whole context again.
Several such sessions in one wake-up make one push that names the first and adds «і ще <N>». One push per
wait, also across restarts; a new wait may push again. A C that waits on P pushes nothing, and sessions
outside P's registry are not covered.

### What P decides alone
P decides alone within the approved acceptance criteria. An item reaches your queue only when it leaves
those criteria (a product choice), what you get is not agreed yet (see "P sorts each task"), the step is
hard to undo, or API spend (real money through `dev-kit-api`) would pass 1 USD in total per task. Smaller
API spend and subscription use (sessions, subagents, `claude -p`) never ask you. The C keeps the task's
spend line in its task file and asks P before a paid call that would pass the limit. The weekly retro ask
and an offer to take over a session you started
([Take over a session I started](take-over-a-session-i-started.md)) always enter the queue. A question a C put to you, unanswered
since before today, whose answer lies in P's own rights (a step the C may ask P, a choice inside the
criteria), P decides by its recommendation, records in the doc it came from and drops from the queue.

### P sorts each task
P sorts each task and says the branch in one line: the C alone (a small change with no new screen or user
flow); P and the C (an agreed feature, technical details); or, for what you get that is not agreed yet (a
«Так» to a task title does not agree it; a task that changes a rule's effect on you counts), a question
first: up to 3 text questions through the queue. More than 3, any doubt from you, or any question about
how a screen looks: P proposes an «Обговорення:» session and opens it after your «так». A small rule edit
is no task: P does it itself. A "how will it work" question whose answer needs reading code or docs P
researches with a read-only subagent and never puts to you.

### A discussion ends in the feature file
In an «Обговорення:» session you settle the meaning and the mockup with one agent, and the feature file
ends with an «Approved design» section (acceptance criteria, the approved mockup, the user's situation).
Then P starts a C that builds the screen and shows you its shots next to the mockup.

### A C asks only P
A C never asks you in its own chat; it asks P, and it messages no other session unless P's brief for it
names one (sessions, not its own subagents). Only P and an «Обговорення:» session message other sessions
freely; none of them messages a session you started yourself. Nothing blocks the tool: it is a rule of the skills.
Why: owner, 2026-11-21 (his «так»): only leads and discussion sessions message other sessions freely.

### No permission prompts in any session
Every session a project starts, P included, runs with no permission prompts, so a message between two
sessions is never held for your approval. A project whose committed main has no hard-ban deny rules (push
to main where it deploys, deleting data, and the like) starts no sessions. P shows you the exact lines
and, on your «так», writes them to `.claude/hard-bans.json` and adds them on main itself; you cannot
decline them and type nothing. Removing a ban stays yours: you type the undo (`! dev-kit-bans undo`, only
the latest addition), and only you remove an older ban. You accept the Claude
Code disclaimer once per machine. The Pult hub and the sessions Pult starts run the same way; a session you
start by hand from the app keeps your own mode. ClaudeDevKit's own bans are `rm -rf` lines only (no push ban,
since its P pushes main): a ticket for Pult's check more than real protection.
Why: owner, 2026-11-20 and 2026-11-21: a question between two projects' sessions in different modes was held for
approval and never delivered, since a background session cannot show the approval; one mode for all removes
the hold, and the hard bans are what keeps it safe.

### No two sessions on the same task
Before a task starts, P (and any session through the manager skill) checks that no other live session of
the repository, one you started yourself included, already does it.

### P wakes only when needed
P wakes only on a task session's report, your message, or a message from the Pult watcher when a session
ends, writes the line "Роботу завершено", stops on the usage limit, waits 20 minutes or passes half its
context, or when a plugin update waits for a safe point to restart P; P keeps no watcher of its own. While
a task session (not one you started) works and P has been silent 50 minutes, the Pult watcher pings P; P
then shows its short status.
Why: owner, 2026-11-20: P and Pult were woken every 2 hours only to re-arm a watcher
([measured](../findings/idle-wake-cost.md)); the ping keeps P's cache warm, since a warm read costs about
1/20 of a cold rewrite and P's next task report would otherwise find it cold.

### P moves itself to a fresh session
When P's own context is half full, P saves its notes and asks you «Перезапустити мене зараз?» (a phone
push). The Pult watcher moves P to a fresh session of the same name when P is quiet, or at once when
you answer «так» or write «перезапускай» ([the wait](start-leads-at-logon-and-heal-them.md)); you type nothing else.

How P does it: [project lead tools](../tech/project-lead.md).

Known limits: what the plugin covers and what lives in the `pult` plugin: see the epics
[Work through a project lead](../epics/work-through-a-project-lead.md) and
[Run all projects from the phone](../epics/run-all-projects-from-the-phone.md).

Known limits: P does not limit the number of parallel task sessions or heavy steps by memory.
Why: on 2026-11-16 Claude Code stopped P's background watcher while Windows ran low on memory; the owner
decided memory is enough and Windows was the problem, so no queue or memory gate was added and the
pagefile was fixed instead (48 GB initial, 64 GB max).

Known limits: the reader check covers only P's questions, its own and those it relays from sessions, each once
when first written in full; sessions that talk with you directly are not checked. It counts developer words (a
branch name like «main») as unclear, which fits a non-developer reader.
Why: owner, 2026-11-22: the rule «every question in your words» alone did not stop «USD-еквівалент за цінами
API» in a question; a separate cheap reader checks them (agent `question-reader`, model haiku, sees only the
question text and your list of terms in learning).

Known limits: the reminder push always says "20 хв ... ~40 хв", even for a longer wait found after a P
restart. A wait whose question is not yet in your queue when the watcher's message arrives gets no reminder.

Known limits: your global rules keep five lines that P messages override (no headings or bold labels,
deferring a result mid-discussion, no relay of a started session, every question written out, the
closing next-step question); they still guard ordinary sessions, so a one-line exception names P's
format instead of removing them. Those rules live outside this repo and change only through
`dev-kit:edit-rules`.

## Acceptance criteria
- You give P a task whose outcome is not agreed: P asks up to 3 questions through the queue, or proposes an «Обговорення:» session when there are more or a screen is involved.
- A new question arrives: P's message only counts it and ends with «Показати всі питання?»; on «так» all are listed in full, numbered, in your own words with no agent terms (a separate checker rewrites them first). A critical question is the exception: it is shown in full as the last message line with no closing line, and the next one only after you answer it.
- You answer a P message with a bare «так»: P takes it as the answer to the message's last line and acts, never asking «1 чи 2?».
- A session finishes while you are away: P writes at once, and its message lists the session as «готово».
- A task session crashes: you get it at once, also as a push to your phone.
- A session waits on your answer for 20 minutes: you get one reminder push for that wait; a session waiting on P pushes nothing.
- A second question arrives while one already waits on you: no second push until you write.
- A session needs a paid API call that would take the task past 1 USD: it asks P, and P asks you; below 1 USD and on your subscription nobody asks.
- You answer a session's question inside that session: P never asks you the same thing in its own chat.
- A task is finished: P merges it into main and tells you the result; you did not start or watch the C.
- A second session already works on the same task: P does not start another one.

## Built in
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `plugins/dev-kit/skills/manager/SKILL.md`
- `plugins/dev-kit/agents/overlap-checker.md`
- `plugins/dev-kit/agents/question-reader.md`
- `plugins/dev-kit/messages.md`
- `plugins/dev-kit/scripts/sessions.py`
- `plugins/dev-kit/bin/dev-kit-sessions`
- `tools/tests/test_sessions.py`
- `plugins/dev-kit/scripts/hard_bans.py`
- `plugins/dev-kit/bin/dev-kit-bans`
- `tools/tests/test_hard_bans.py`
- `plugins/pult/scripts/watch-servers.ps1`

## Open
- [ ] Defect: a question P shows only in chat, not in PROGRESS.md "Open questions", is lost when P restarts; `plugins/dev-kit/skills/project-lead/SKILL.md`
