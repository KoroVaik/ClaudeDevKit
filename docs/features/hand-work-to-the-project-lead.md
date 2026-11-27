# Hand work to the project lead

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
You give work to one session per project, the project lead (the Lead), and decide only what is yours: the Lead starts
the task sessions, merges their work and tells you the result. You are the CEO and do not micromanage.

## Rules
### Roles
The Lead is one session per project. It starts task sessions (Managers), each in its own worktree, merges their
finished work into main and tells you the result. It does no task work itself.

### The Lead's messages: session states and the question window
Every message from the Lead has up to two short blocks (a third when nothing works, below): «Статуси сесій» (each
session's state and name) and, last, «Питання без відповіді». That block is a window: the 2 oldest open questions,
written out in full and numbered 1 and 2 (urgent ones first, marked ❗), each after a separate cheap check that it
reads in your own words with no agent terms. Every other open question waits behind one line «і ще N питань». The
window changes only after you answer: answered questions leave and the next oldest come in; a new question only raises
the counter, and an urgent one that arrives meanwhile takes the first place in the next window. Every Lead message
that has text repeats the same window, and it also opens the Lead's first message after any restart, so your bare
«так», sent at any moment, answers the same two questions. The window ends with «Приймаєш мої поради до обох?»;
with one question open, that question itself is the last thing. A bare «так» or «ні» answers the shown questions; «1 так»
or «2 ні» answers only that one and says nothing about the other (the next oldest then takes its place). The Lead never
asks back which one you meant. A question the Lead finds already answered (in a session or in the code) is not dropped:
it stays and opens with «✅ Вирішено, закрити? (причина)», so you need not read it again; your «так» closes it.
The Lead writes to the chat only when something waits on you or there is a result you see: a new question, a merge, a
finished session, a failure or a stuck session. A session's progress or a step done sends no message; it appears in
«Статуси сесій» of the next message, and you can ask «що працює?» at any time. The other sessions still at work share
one last status line «ще працюють: «A», «B»». When Claude Code demands a reply where the Lead has nothing new, the Lead
shows the current state in this form, never a filler phrase; with nothing running and nothing waiting, it is one line
saying so.
When no session works any more (for example after the last one is merged), the message adds a block
«Стан проєкту» between the statuses and the question: 2-4 plain sentences on what was just finished, what the project
waits on and what is blocked. The Lead's proposal of the next task («Запустити нову сесію «M: ...»?» with its
`Рекомендую:` line) is an ordinary open question that takes its turn in the window; you usually start a discussion
yourself. The Lead writes the block again only when the state changed. While a session works, the message has neither.
Why: owner, 2026-11-26 ([the plan](../../plans/lead-questions.md)): a later Lead message ended with a different
question and his «так» went to the wrong one («Я написав так на попереднє повідомлення. Тут вже хаос якийсь»); a question
the Lead showed only in chat was lost when the Lead restarted, so every question is written to the queue first.
A check at the end of each Lead turn keeps this form: when a session's message, an event or a finished
helper woke the Lead (not your own message, and not while the Lead still owes you a reply), the Lead's reply must be empty,
one of the named one-line steps (a discussion start, a push test, a restart notice) or only the blocks.
On free text before, between or after the blocks, the Lead gets a note to write the next message in form; the
message you saw is not sent again.

### How a question and a state are written
An urgent question is one where a session stands and cannot move without your answer; a session that asks and goes
on, or a closed session with a leftover question, is not urgent. The window shows questions from sessions and the
Lead's own the same way (the Lead's own: start a new task session, close a session, take one over, restart a crashed
one, new plugin backlog entries (the retro asks nothing: it fixes by itself and shows a passive list in Pult's status);
the Lead never asks «Яку задачу запустити?»). A
question stands alone: a session's question starts with its name and «питає:»; it is in your words (what you
see or do on your side, never the Lead's own mechanisms), with the consequence in brackets, worded so the advice is
«так», then an indented `Рекомендую: так - <reason>` (the Lead adds one a session did not give). A question about
how a screen looks carries its shots next to the mockup every time it is shown in the window. An answered
question just leaves the window, with no confirmation line.

Each line of «Статуси сесій» is the state first, then the session name exactly as the app shows it, in «»:
`працює`, `чекає на тебе` (with the reason in brackets), `чекає` (a session waits more than a minute on
something other than you, such as low memory or a retry timer; with the reason and the resume time), `стоїть, скінчився ліміт` (with the reset time),
`стоїть, сесія впала`, `готово`. The start status and your «що працює?» list every session; any other
message lists the sessions whose state changed, plus each `готово` one until you next write to the Lead.

### The Lead never asks what you already answered in a session
Before the Lead asks you about a session or shows its status, it reads what you wrote in that session since
its last report. If you already answered there (for example «так» to closing a discussion), the Lead drops its
own question silently and acts on your answer. Sessions also tell the Lead such answers in a message that
starts with a fixed kind word: every message between sessions starts with one word from a short fixed
list (`plugins/dev-kit/messages.md`), such as «ГОТОВО», «ПИТАННЯ» or «ВЛАСНИК ВІДПОВІВ».

### Critical items reach your phone
A critical item (a session cannot go on without you, a session crashed, a risk to data or money) also comes as a push to your phone (the phone side:
[Run all projects from the phone](../epics/run-all-projects-from-the-phone.md), step 7). The queue pushes
once, when it had no question for you and gets one; later questions push nothing until you write. A status
line alone (`готово`, a usage-limit stop) never pushes, and nothing else does: no progress, merges or
event lines that need nothing. A push is one line under 200 characters: the project, then what to act on
first; it is skipped while you look at the screen.

A reminder push is the one time-based push. A session that has waited on you 20 minutes (a question from
it in the Lead's queue, a taken-over session of yours that shows `чекає на тебе`, or a «Discuss:» session)
gets one, before its cache runs out and the next answer costs its whole context again ([Claude facts](../../plugins/dev-kit/claude-facts.md), "A main session's prompt cache lives about one hour").
Several such sessions in one wake-up make one push that names the first and adds «і ще <N>». One push per
wait, also across restarts; a new wait may push again. A Manager that waits on the Lead pushes nothing, and sessions
outside the Lead's registry are not covered.

### A push test asks you twice at most
When a check needs a push on your phone, the Lead writes one line: «Тест пушу: напиши + і одразу закрий застосунок.
Через 5 секунд прийде пуш «Тест N · HH:MM».». Your «+» there means "ready". Five seconds later one push comes,
its text starting with «Тест», and the Lead asks once: «Пуш «Тест N» надіслано. Прийшов? + або -». Nothing else stops
during a test. With no answer in 10 minutes nobody asks about that push again; if the check is still needed, it
starts over with a new push. Several pushes in one test come at least 3 seconds apart.

### What the Lead decides alone
The Lead decides alone within the approved acceptance criteria. An item reaches your queue only when it leaves
those criteria (a product choice), what you get is not agreed yet (see "The Lead sorts each task"), the step is
hard to undo, or API spend (real money through `spend-kit-api`) would pass 1 USD in total per task. Smaller
API spend and subscription use (sessions, subagents, `claude -p`) never ask you. The Manager keeps the task's
spend line in its task file and asks the Lead before a paid call that would pass the limit. An offer to take over a
session you started
([Take over a session I started](take-over-a-session-i-started.md)) always enters the queue. A question a Manager put to you, unanswered
since before today, whose answer lies in the Lead's own rights (a step the Manager may ask the Lead, a choice inside the
criteria), the Lead no longer decides itself: it stays open with «✅ Вирішено, закрити? (причина)» and the Lead
records the decision in the doc it came from after your «так».

### The Lead sorts each task
The Lead sorts each task and says the branch in one line: the Manager alone (a small change with no new screen or user
flow); the Lead and the Manager (an agreed feature, technical details); or, for what you get that is not agreed yet (a
«Так» to a task title does not agree it; a task that changes a rule's effect on you counts), a question
first: up to 3 text questions through the queue. More than 3, any doubt from you, or any question about
how a screen looks: the Lead proposes a «Discuss:» session and opens it after your «так». A small rule edit
is no task: the Lead does it itself. A "how will it work" question whose answer needs reading code or docs the Lead
researches with a read-only subagent and never puts to you.

### Pult passes your task to the Lead
You can ask Pult for work in a project (a plugin change belongs to ClaudeDevKit): Pult sends your words verbatim to
that project's Lead and says in one line that it passed them on. The Lead sorts the task as above and its line starts
«Від Pult:». Only a new task goes this way: an answer or a «так» you give Pult reaches no Lead, so you give it in the
Lead's chat. With the Lead down, Pult says so and offers to start a session as before.

### A discussion ends in the feature file
In a «Discuss:» session you settle the meaning and the mockup with one agent, and the feature file
ends with an «Approved design» section (acceptance criteria, the approved mockup, the user's situation).
Then the Lead starts a Manager that builds the screen and checks its look against photos of the real thing
first, and a new «Discuss:» session shows you its shots (and a clip of each moving state) next to the
mockup and passes your remarks to that Manager.
Each question there names the screen it is about in its own words, with no block of facts before it.

### A project edits its own kit plugin
A session of a project that uses web-kit or unity-kit changes that plugin itself and releases the new version,
so a change you need during a talk there lands at once, with that talk's context; it no longer goes through the
plugin backlog and the ClaudeDevKit Lead. Before the change lands, the repo checks pass and an independent helper reviews
it; the ClaudeDevKit Lead does not check it afterwards. A part that needs a dev-kit change still goes to the plugin
backlog. dev-kit, pult, rules-kit and spend-kit stay with the ClaudeDevKit Lead
(owner «так», 2026-11-26, «Discuss:» on direct kit edits; details: [plans/kit-direct-edits.md](../../plans/kit-direct-edits.md)).

### A Manager asks only the Lead
A Manager never asks you in its own chat; it asks the Lead. Every Manager shows in the Claude app with no push, and you may
write in its chat: it follows your words, answers you in short and tells the Lead at once with your words. It messages no other session unless the Lead's brief for it
or a later Lead instruction names one (sessions, not its own subagents). Only the Lead and a «Discuss:» session message other sessions
freely; none of them messages a session you started yourself. Nothing blocks the tool: it is a rule of the skills.
Why: owner, 2026-11-21 (his «так»): only leads and discussion sessions message other sessions freely.

### No permission prompts in any session
Every session a project starts, the Lead included, runs with no permission prompts, so a message between two
sessions is never held for your approval. A project whose committed main has no hard-ban deny rules (push
to main where it deploys, deleting data, and the like) starts no sessions. The Lead shows you the exact lines
and, on your «так», writes them to `.claude/hard-bans.json` and adds them on main itself; you cannot
decline them and type nothing. Removing a ban stays yours: you run the undo from a file the lead puts in the folder `Claude` on your desktop (only
the latest addition), and only you remove an older ban. You accept the Claude
Code disclaimer once per machine. The Pult hub and the sessions Pult starts run the same way; a session you
start by hand from the app keeps your own mode. ClaudeDevKit's own bans are `rm -rf` lines only (no push ban,
since its Lead pushes main): a ticket for Pult's check more than real protection.
Why: owner, 2026-11-20 and 2026-11-21: a question between two projects' sessions in different modes was held for
approval and never delivered ([Claude facts](../../plugins/dev-kit/claude-facts.md), "A message between sessions
in different permission modes may be held"); one mode for all removes the hold, and the hard bans are what keeps it safe.

### No two sessions on the same task
Before a task starts, the Lead (and any session through the manager skill) checks that no other live session of
the repository, one you started yourself included, already does it.

### The Lead wakes only when needed
The Lead wakes only on a task session's report, your message, or a message from the Pult watcher when a session
ends, writes the line "Роботу завершено", stops on the usage limit, waits 20 minutes or passes a third of its
context, or when a plugin update or the Lead's own move waits for a safe point to restart the Lead; the Lead keeps no watcher of its own. While
a task session (not one you started) works and the Lead has been silent 50 minutes, the Pult watcher pings the Lead; the Lead
then shows its short status.
Why: owner, 2026-11-20: the Lead and Pult were woken every 2 hours only to re-arm a watcher
([measured](../findings/idle-wake-cost.md); [Claude facts](../../plugins/dev-kit/claude-facts.md), "The host kills a
background Bash run after 2 hours"); the ping keeps the Lead's cache warm, since the Lead's next task report would otherwise find
it cold ([Claude facts](../../plugins/dev-kit/claude-facts.md), "A main session's prompt cache lives about one hour").

### A report sent while the Lead restarts
A report a task session sends while the Lead restarts (about 10 seconds) is not lost: the session sends it
again by itself about a minute later, up to three times, then before its next message to the Lead or when the Lead
next writes to it. Task sessions
get no warning before a restart and the Lead sends them nothing after it.
Why: owner, 2026-11-23 ([the talk](../../plans/restart-notice.md)): a warning misses the silent restart
and costs the Lead and every task session a turn.

### The Lead moves itself to a fresh session
When the Lead's own context is a third full, the Lead saves its notes and the Pult watcher moves it to a fresh context, the
way a plugin update restarts it: no question to you and no phone push. When you and the Lead are quiet, it happens
silently; when the Lead is in a talk with you, it writes «⚠ ЧЕРЕЗ 30 СЕК БУДЕ ПЕРЕЗАВАНТАЖЕННЯ (СВІЖИЙ КОНТЕКСТ)» at a
safe point and is moved 30 seconds later. While you keep writing, the move waits. «перезапускай» moves it at
any time ([the wait](start-leads-at-logon-and-heal-them.md)); you type nothing else. It stays the same session
in the phone app.
Why: owner, 2026-11-23 ([the plan](../../plans/lead-self-move.md), [the pushes](../../plans/push-noise.md)): the
restart question and the push of a new session were noise.

A plugin update that renames things (a session prefix, a role, a command, a message format) restarts the Lead the
same way, with a clean context, so it forgets the old names: it writes «⚠ ЧЕРЕЗ 30 СЕК БУДЕ ПЕРЕЗАВАНТАЖЕННЯ
(ОНОВЛЕННЯ ІНСТРУМЕНТІВ)» and is moved 30 seconds later. Small fixes keep the Lead's conversation, as before. The
plugin itself tells which update needs it: the agent that releases it marks it. If the clean move fails, the Lead
is restarted the old way.
Why: owner, 2026-11-26 ([the plan](../../plans/lead-early-clear.md)): after an update renamed the session
prefixes, a resumed Lead still used the old ones; small fixes come all the time and must not start a Lead from scratch.

How the Lead does it: [project lead tools](../tech/project-lead.md).

Known limits: what the plugin covers and what lives in the `pult` plugin: see the epics
[Work through a project lead](../epics/work-through-a-project-lead.md) and
[Run all projects from the phone](../epics/run-all-projects-from-the-phone.md).

Known limits: the Lead does not limit the number of parallel task sessions or heavy steps by memory.
Why: on 2026-11-16 Claude Code closed idle sessions while Windows ran low on memory ([Claude facts](../../plugins/dev-kit/claude-facts.md), "A low-memory spell closes idle background sessions"); the owner
decided memory is enough and Windows was the problem, so no queue or memory gate was added and the
pagefile was fixed instead (48 GB initial, 64 GB max).

Known limits: the reader check covers only the Lead's questions, its own and those it relays from sessions, each once
when first written in full; sessions that talk with you directly are not checked. It counts developer words (a
branch name like «main») as unclear, which fits a non-developer reader.
Why: owner, 2026-11-22: the rule «every question in your words» alone did not stop «USD-еквівалент за цінами
API» in a question; a separate cheap reader checks them (agent `question-reader`, model haiku, sees only the
question text and your list of terms in learning).

Known limits: the reminder push always says "20 хв ... ~40 хв", even for a longer wait found after a Lead
restart. A wait whose question is not yet in your queue when the watcher's message arrives gets no reminder.

Known limits: your global rules keep five lines that Lead messages override (no headings or bold labels,
deferring a result mid-discussion, no relay of a started session, every question written out, the
closing next-step question); they still guard ordinary sessions, so a one-line exception names the Lead's
format instead of removing them. Those rules live outside this repo and change only through
`rules-kit:edit-rules`.

## Acceptance criteria
- You give the Lead a task whose outcome is not agreed: the Lead asks up to 3 questions through the queue, or proposes a «Discuss:» session when there are more or a screen is involved.
- A new question arrives: the Lead's message shows the 2 oldest open questions in full, numbered, in your own words with no agent terms (a separate checker rewrites them first), and «і ще N питань» for the rest; the new question only raises the counter, unless it is urgent (then it takes the first place after your next answer).
- You answer a Lead message with a bare «так»: the Lead takes it as the answer to the questions shown in the window, whatever it wrote since, and acts, never asking «1 чи 2?». «1 так» answers only the first.
- Several Lead messages come one after another (a merge, a finished session): each repeats the same two questions, so your «так» is never taken for another line.
- The Lead restarts: its first message shows the two oldest open questions again, read from PROGRESS.md "Open questions"; none was kept only in the chat.
- The Lead finds a question already answered: it stays in the window with «✅ Вирішено, закрити? (причина)» and leaves only on your «так».
- A session's progress changes, nothing else: the Lead sends no message; the change is in the next one, or on your «що працює?».
- A session finishes while you are away: the Lead writes at once, and its message lists the session as «готово».
- The last working session finishes: the Lead's message adds 2-4 sentences on the project's state and queues one proposal of the next task, which shows in the window in its turn; while a session still works, it has neither.
- A task session crashes: you get it at once, also as a push to your phone.
- A session waits on your answer for 20 minutes: you get one reminder push for that wait; a session waiting on the Lead pushes nothing.
- A second question arrives while one already waits on you: no second push until you write.
- A check needs a push on your phone: you get one ready line, one push starting «Тест» and one «Прийшов? + або -»; with no answer in 10 minutes nobody asks about it again.
- A session needs a paid API call that would take the task past 1 USD: it asks the Lead, and the Lead asks you; below 1 USD and on your subscription nobody asks.
- You answer a session's question inside that session: the Lead never asks you the same thing in its own chat.
- A task is finished: the Lead merges it into main and tells you the result; you need not start or watch the Manager.
- You write in a Manager's chat: it follows your words and the Lead is told at once; it asks you nothing there.
- You ask Pult for work in a project: the Lead gets your words verbatim and sorts the task, with no copying by hand; a «так» you give Pult answers no Lead question.
- A second session already works on the same task: the Lead does not start another one.
- A plugin update renames a session prefix: the restarted Lead starts its next session with the new prefix; after a small fix the Lead keeps its conversation.
- A session's message wakes the Lead and the Lead writes a note beside the blocks: the Lead gets a reminder of the form and you do not get the message twice; the Lead's answer to your own question is not checked.

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
- `plugins/pult/scripts/restart-leads.ps1`
- `plugins/pult/rules/hub.md`
- `plugins/pult/scripts/send-to-lead.ps1`
- `plugins/pult/scripts/send-lib.ps1`
- `tools/tests/test_watch_servers_handoff.py`
- `tools/tests/test_watch_servers_restart.py`
- `plugins/dev-kit/hooks/lead-reply-form.py`
- `tools/tests/test_lead_reply_form.py`

## Open
- [ ] Run the first phone push test in the form of «A push test asks you twice at most» with the owner and confirm the steps read clearly (`plans/push-test-flow.md`)
