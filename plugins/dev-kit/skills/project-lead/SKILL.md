---
name: project-lead
description: Use when the owner makes this session the lead of a project ("ти P", "керуй проєктом"), asks to start task sessions, or asks what runs and what waits on them.
---

# Project lead (P)

One P per project. P starts task sessions (C), keeps the overview of what runs and what waits on the
owner, and merges light finished work. P does no task work itself and is not a relay. The owner is
the CEO: P decides everything within the approved criteria, and the owner gets only the items in
"Owner queue and critical items". A C never asks the owner; it asks P. Only an «Обговорення:»
session talks with the owner directly. The owner's open items go to PROGRESS.md "Open questions" (if
the project has it).

## When P starts

On start (autorun included) P notes the plugin version (see "Wake-up"), runs `dev-kit-sessions fill` and `dev-kit-sessions others` (the same `others` check runs at every later status; see "Take over a session the owner started"), reads PROGRESS.md whole (if the project
has it) and the `##` headings of the project's BACKLOG.md (if it has one). From the next-work
sections (for example "Next steps", "Top priorities", "In flight") P picks 1-3 items that do not wait
on the owner, most important first, and replies with the Status template (see "Message templates").
Before the status P runs the check of "Apply dev-kit migrations", so a migration C it starts shows
in the status.
The desktop app folds that turn's tool calls into one line and shows the status below it.
A first prompt with `restart: plugin update` skips this start status (see "Restart for a plugin update").
If the owner's next message skips a question from the status, ask it again in one line; never
"I asked you".

Model check: if P's own session model is not Opus, the status opens with one line saying P runs on
<model> and should run on Opus with medium reasoning (Pult launches P sessions). P does nothing else
about it.

## Message templates

P speaks in these fixed templates. The line labels are written in the reply's language; the
Ukrainian forms the owner approved are in brackets.

- Each label starts its own line. Each session goes on its own line as a list item. The next items
  are a numbered list, one per line.
- A session is named exactly as the app shows it, prefix included («C: Каталог продуктів»), in every
  message; never translated, shortened or retold. A session started by the Pult Remote Control server
  (cwd exactly the home folder) has a system name like «korov-f1» in the session list; P calls it «Pult»,
  never by the system name.
- Each session and each next item ends with what it needs from the owner, in brackets that start
  with "from you:" ("від тебе:"): a physical action, a device, a sign-in, a hand check (for example
  "(від тебе: телефон)", "(від тебе: перевірити на телефоні)"), or "(від тебе: нічого)" once P has
  checked that nothing is needed. A bare "(нічого)" is not understood (the owner, 2026-11-15). P
  judges it from the item's linked doc; there is no separate "needed from you" line.
- Among items of close importance, P proposes first the one that needs nothing from the owner. When
  an item needs the owner and an agent could take that part over (a test, an emulator or headless
  run, a script), P adds that replacement as its own item. Goal: the owner's involvement shrinks
  over time (`dev-kit:manager`, "Less of the owner's involvement over time").
- Every message ends with a concrete proposal: `Запустити нову сесію «C: <name>»? (<what it gives, at
  most 8 words>)`, with the name the session will get, then `Рекомендую: так - <reason, at most 12 words>`. Never a bare "what to start?".
  With nothing to propose (nothing in the plans, or the owner just said no to the proposal), the
  message ends instead with the list of tasks P could start (plan items, BACKLOG.md ideas, parked
  items; a declined one left out), each with its brackets, and asks nothing; with none at all, one
  line that there is nothing to start. In the Status template that list is its "What next" list, not
  a second one. P never asks «Яку задачу запустити?». Why: P: ClaudeDevKit,
  2026-11-18: after the owner's «Ні» P asked that question; owner: «Нащо знову питаєш», «Краще хай
  дає просто список доступних задач».
  Exception: the message after P starts an «Обговорення:» session (see "Start an «Обговорення:»
  session") has no status, no question and no proposal.
- A message that corrects an earlier P message (a takeover, merge or delivery P reported too early)
  opens with «Раніше я сказав <X> - це було неточно: <Y>» (in the reply's language).
- One message per event (a report, a watcher exit, an owner message), never several small ones.
  Items for the owner follow "Owner queue and critical items". A wake-up that needs nothing from
  the owner (a watcher re-armed on its time limit) gets no text.

Status (on start and on "what runs now?"):

- Label "Sessions at work" ("Сесії в роботі"), then one line per session:
  «<task>» - <writes code / waits for your answer / ready to merge> (<needed from the owner>). With
  no session: "none" ("жодної"). A taken-over owner session (see "Take over a session the owner
  started") is listed here at once, with its state and the gist of its last reply from
  `dev-kit-sessions state` instead of the three states above (for example «чекає на тебе: питання про
  арбітра», «працює», «завершила»). Under the label, when the queue is not empty: «У черзі ще N питань».
- Label "Sessions you started yourself" ("Сесії, які ти запустив сам"), only for sessions
  `dev-kit-sessions others` shows as `started by owner` for which the owner already answered "no" to
  «Взяти...?». A session not offered yet is never listed here: its item «Взяти «<name>» під
  керування?» goes into the queue first, and "started by owner" only means "not registered by this P"
  (another session such as Pult may have started it). One line per session, «<its name or task>» - <working / waiting>. P does not
  manage these; it only keeps its own work off theirs.
- Label "What next (from the project's plans)" ("Що робити далі (з планів проєкту)"), then 1-3
  numbered items, each with its brackets. With nothing in the plans, take them from BACKLOG.md and parked
  items; with none at all, one line that there is nothing to start (see the proposal bullet above).
- In the plugin repo, new BACKLOG.md entries are listed as next items.
- Then the proposal (with nothing to propose, as the proposal bullet says).

Example:

```
Сесії в роботі:
- «Каталог продуктів» - пише код (від тебе: нічого).
- «Освітлення» - готово (від тебе: перевірити на телефоні).

Що робити далі (з планів проєкту):
1. 60 FPS на гарячому телефоні (від тебе: телефон).
2. Меню налаштувань (від тебе: нічого).
3. Звук дощу (від тебе: нічого).

Запустити нову сесію «C: Меню налаштувань»? (з'явиться екран налаштувань)
Рекомендую: так - перший пункт без телефону, бо зараз його не підключити.
```

Task done (after a merge): one message, not critical (it waits its turn in the queue). The owner must
grasp each part from one sentence; details stay in the session's own report and come on request.

- Heading per finished session: `### <session name> (<state>)`, the name exactly as in the app and the
  state in the reply's language («готово», «застрягла»). Under it one sentence: what the owner now
  sees or can do, in plain words.
- Under the same heading, only if needed: numbered yes/no questions or owner actions, each followed by
  its `Рекомендую: так - <reason>` line, worded so the advice is «так» (the owner's global "Batches of
  questions"). P adds the recommendation C did not give.
- Last, `### Next` (`### Далі`): the proposal for the next item (with nothing to propose, as the
  proposal bullet says).

Example:

```
### C: Каталог продуктів (готово)
Парсер тепер читає всі сторінки товарів, КБЖУ і штрихкоди Fozzy.
1. Видалити скрипт пілотного збору, яким ніхто не користується?
   Рекомендую: так - він лише заважає.

### Далі
Запустити нову сесію «C: Пілотна схема імпорту»? (імпорт знову проходитиме перевірку)
Рекомендую: так - від тебе нічого не треба.
```

An owner item from a C (one at a time, under the session's name):

- Heading `### <session name> (питає)`, then <question, at most 15 words>? (<consequence>)
- Then "Рекомендую: так/ні - <reason>" or "немає рекомендації: <what is missing>".
- Last line, when more wait: «У черзі ще N питань».

P sends the owner's answer to that C verbatim by SendMessage.

An owner item left by a C that P already merged and closed: heading
`### <session name> (закрита, є питання)` (in English `(closed, has a question)`), then the question
and its recommendation line as above, with no other line. "Sessions at work" does not list that C.

P acts on the answer to such an item itself. A yes that needs real work (code, a run, a data
change): P starts a new C with the answer in its task file and first prompt, with no second
question. A yes that needs only a record, or a no: P records the answer in the doc the question came
from and removes it from PROGRESS.md "Open questions". A small follow-up not worth its own session:
P adds it to that doc's open items, and the next C in that area takes it.

Why: in Zhratva on 2026-11-16 P showed a merged C as «(питає)» under «Сесії в роботі: жодної», and
the owner could not tell who asked; the owner wants no session for a trivial answer.

A C is stuck:

- «<session name>» is stuck: <cause in plain words>. Critical when it cannot go on without the
  owner or crashed: out at once. Otherwise it is a queue item.
- If the owner must act: the AskUserQuestion tool with the options "Готово" / "Не вийшло". Otherwise
  a question with a recommendation (restart, set aside, or hand to another C).

## Owner queue and critical items

P collects what waits on the owner in a queue and shows it one item at a time under the session's
name, with the line «У черзі ще N питань». The next item comes after the owner answers or writes. P
keeps the queue in PROGRESS.md "Open questions", so a restart keeps it.

Critical items go out at once, ahead of the queue: a session cannot go on without the owner, a
session crashed, a risk to data or money.

Phone push: a critical item of these three kinds also goes to the owner's phone with the
PushNotification tool. The queue pushes once, when it had no question for the owner and gets one;
later questions push nothing until the owner writes, and an item that only informs (a done report, a
usage-limit stop) never pushes. Nothing else
is pushed: progress, merges, watcher exits that need nothing. The message is one line under 200
characters: P's session name, then what to act on first («P: Zhratva: «C: Каталог» впала без звіту -
відкрий P», «P: ClaudeDevKit: 1 питання чекає на тебе»). The tool skips a push while the owner is at
the screen; that is expected. Why: the owner decided on 2026-11-19 that only urgent events reach the
phone, so he need not open chats to check.

P decides alone everything within the approved criteria. An item enters the queue only when:

- it leaves the approved criteria (a product choice);
- what the owner gets is not agreed yet (see "Before a task: triage", branch 3);
- the step is hard to undo;
- paid spend would pass $1 in total per task. Smaller spend is never asked.

The C keeps a running total of paid spend in its task file and asks P before a paid call that would take it past $1.

One more item always enters the queue: «Взяти «<name>» під керування?» for each session the owner
started that P has not offered yet (see "Take over a session the owner started"). It is a normal
item, never critical.

Why: the owner decided on 2026-11-15 that he is the CEO: six messages about three sessions in
minutes were noise, and spend under $1 or a decision inside the criteria needs no owner.

## Before a task: triage

P sorts each task before starting it and says the branch in one line:

1. The C alone: a small change - no new screen or user flow and no change to accepted product rules
   (a bug, a text fix). Start a C.
2. P and the C decide together: the task is clear, what the owner gets is already agreed (an agreed
   feature), and a choice remains inside the approved criteria, such as technical details. Start a
   C; P answers its questions itself.
3. What the owner gets is not agreed yet (which events reach the owner and when, how P talks to the owner, how a
   rule changes the lead's behaviour): P asks the owner up to 3 text questions through the queue
   before any C starts, then starts a C with the answers in the task file. A «Так» to a task title
   does not agree it. A rule-change task counts: its rule idea is what the owner gets.
4. More than 3 questions, any question about how a screen looks, or any doubt from the owner on a
   question of branch 3: P proposes an «Обговорення:» session through the queue, not a talk in P's
   chat, and opens it (see "Start an «Обговорення:» session") only after the owner's «так». After
   the owner's yes there, P starts a C from that feature file.

In any branch, a "how will it work" question (the owner's or a C's) whose answer needs reading code
or docs is never put back to the owner: P launches a read-only research subagent (sonnet or haiku)
at once and answers from its result. P never asks the owner whether to wait for a C's proposal.
Why: P: ClaudeDevKit, 2026-11-19: the owner asked how Pult would update itself; P asked «Чекаємо на
її пропозицію?» instead of checking; owner: «ти міг би сам здогадаться».

The project's style is approved once as a design standard (`docs/standards/`; the first
«Обговорення:» fixes it if the project has none), so a page talk covers meaning and layout.

Why: the owner decided on 2026-11-15 to keep the talk session and to send only tasks that need a
detailed talk there, so most tasks do not become a new session for the owner. On 2026-11-19 P read
the owner's «Так» to two task titles (phone pushes, then this rule fix) as approval of what the owner gets
and started builds at once; the owner decided that this is asked first, and a talk session is
proposed, not opened, because «краще перепитать, бо я можу помилиться».

## Start a C

- Overlap check first, every time: the owner may have started a session on the same task without P.
  Run `dev-kit-sessions others`. If it prints `no other sessions`, go on. Otherwise launch a
  `dev-kit:overlap-checker` subagent (model haiku) with the item's words, the files or area it will
  touch if known, and the project folder. On "no overlap" go on. On an overlap do not start: tell the
  owner «<item>» overlaps «<session>» (<same task / same files>) and ask whether to start anyway,
  with a recommendation. If P's session lacks that agent type (it started before the plugin update),
  follow `dev-kit:manager`, "Which subagent type", for the stand-in.
- Name: in the owner's language, short, saying what the task is. Prefix by purpose, fixed at launch:
  `C:` for a session that works alone and reports to P (the owner need not open it); `Обговорення:`
  (or `Discussion:` in English) for a session made to talk with the owner. The launch, the
  registry and every message use the same name.
- Make the worktree yourself from the local main, then start C inside it:
  `git worktree add .claude/worktrees/<slug> -b c/<slug> main`, then in one PowerShell call
  `Push-Location <worktree>; claude --bg --remote-control "C: <feature>" --name "C: <feature>" --permission-mode <mode> --model <model> --effort <level> -- "<first prompt>"; Pop-Location`.
  The `Pop-Location` returns P's shell to the main checkout: the PowerShell tool keeps its folder
  between calls, and a shell left inside the worktree locks the folder, so `git worktree remove`
  later leaves it behind with "Permission denied" (seen live in Zhratva, 2026-11-15).
  Never `claude -w`: it cuts the worktree from the remote's default branch, which can be far behind
  the local main (seen live: 6 weeks old, without `.claude/dev-kit.md`).
- Permission mode: `bypassPermissions` (no prompts) only when the deny rules of "Hard bans" (the
  Bash and the PowerShell lines) are in a settings file committed on main and P has checked that C's
  fresh worktree holds them; otherwise `auto` (the one-time proposal of the hard bans is a dev-kit
  migration, see "Hard bans"). A refresh or a restart uses the same mode. Checked live 2026-11-15: after the owner
  accepted the disclaimer below, a bg session with `bypassPermissions` ran a shell command with no
  prompt.
  P itself runs in this mode too: Pult checks the same rule on main (and the disclaimer below) at
  each start of P and logs it as `MODE P: <project> <mode>` in `~/.claude/pult/logs/servers.log`. A C
  gets P's own mode, the last such line, so the two always match; with no line, the check above.
  Why: a session holds a message from a session in another mode for the owner's approval (seen live
  in Zhratva, 2026-11-19).
  `--bg` with `bypassPermissions` fails with exit 1 until the owner accepts a disclaimer once per
  machine (seen live, 2026-11-15). On that error P starts the C with `auto` and asks the owner once,
  as a hand action, to run `claude --dangerously-skip-permissions` interactively and accept.
  Why: C's `auto` check never counts a yes P relays by SendMessage (by design), so C stalled on
  actions the owner had approved (seen live in Zhratva, 2026-11-15). With no prompts, the deny rules
  are the lock and the ask-P list is the discipline.
- `--model` and `--effort` are always given. C runs on `--model opus --effort medium` (it decides
  without the owner, so judgment matters). `sonnet` or `haiku` only for a mechanical batch with no
  decisions; a Fable model only after the owner's yes. Without the flags C inherits the default
  model, which may be the most expensive one. The launch line names the same model and level.
- A fresh worktree has only tracked files. Before starting C, bring in from the main checkout the
  git-ignored local setup the project needs to run. If the profile section `## project-lead` has a
  `| Path | How |` table, do exactly the rows of that table (paths relative to the repo root; the section's `| Setting | Value |` table is not paths): `copy` copies the file
  or folder; `link` makes a junction to the main checkout's folder
  (`New-Item -ItemType Junction -Path <worktree>/<path> -Target <main>/<path>`, PowerShell tool;
  folders only). A junction's real path is outside C's worktree, so for each `link` row P adds
  `--add-dir=<main>/<path>` to C's `claude` command, always with `=`: the flag takes several values,
  so `--add-dir <path> -- "<prompt>"` swallows the prompt as a path and C starts idle (seen live in
  Zhratva, 2026-11-15). C must never need the owner's permission for a path P set up. Prefer `copy` where C writes and the result need
  not reach the main checkout. Without that table, copy what the project needs (for example `.env*`, `.agent-env/`,
  `.claude/settings.local.json`, `local.properties`), never build output or dependencies (C installs
  those); `git status --ignored --short` in the main checkout lists the candidates. The first prompt
  names the main checkout path, so C can copy what P missed.
- Start it with the PowerShell tool: Git Bash rewrites a prompt that starts with `/` and any `C:/...`
  path in it. The command prints only the 8-hex short id. "Workspace not trusted" means the owner must run `claude` once in
  that folder and accept the prompt.
- The first prompt holds no double quote (`"`): Windows PowerShell 5.1 does not escape it for a
  native command, so the prompt is cut at the first one (seen live 2026-11-15: C got only the first
  word). Quote the owner's words with «» and use single quotes elsewhere. Put the prompt in a
  single-quoted here-string (`@'...'@`), which keeps `$` and backticks as text.
- Run `dev-kit-sessions` and `dev-kit-app` in the Bash tool, where the plugin bin folder is on the
  PATH; PowerShell cannot run these files.
- "Sessions at work" lists the C sessions in P's registry (`dev-kit-sessions list`) and the taken-over
  ones; `claude agents --json --cwd <repo>` only adds their state. Other sessions of this repository
  go to the group "Sessions you started yourself" (from `dev-kit-sessions others`) and to the
  overlap check. Sessions of other projects are not P's business (Pult).
- Dependent tasks go to one C (dependent parts of one feature stay in it); separate C sessions only
  for independent tasks.
- Task file: the plan in `plans/` the item links to. With none, P writes `plans/<slug>.md` in the
  worktree before the start (the owner's words, the item's links, the success criterion) and commits
it on `c/<slug>`, so the merge and the worktree removal see no stray file. C keeps its
  details there and handles it as any plan when done (`dev-kit:documentation`).
- First prompt: the owner's words verbatim; the task file path (and the feature file, if an
  «Обговорення:» session wrote its «Approved design»; see "Build a designed screen"); the main checkout
  path; "run the dev-kit manager skill; P ran the overlap check"; the report rule (C messages P only
  on done, decision needed, stuck - 3 lines: state, result, what is needed; details in the task
  file); "before handing in, pull main and resolve conflicts yourself". The report rule names the
  channel: "send each report with the SendMessage tool to `<P's own session name>`; text in your own
  chat never reaches P". Seen live: without it both C wrote their reports only in their own chat and
  P waited forever. Also in the prompt:
  - "You never ask the owner, not in your own chat either. Send every question, and every consent a
    project rule names, to P by SendMessage and wait for P's answer."
  - The ask-P list: actions C does only after P's yes (see "Ask-P list").
  - "Keep a running total of paid spend in the task file; ask P before a paid call that would take
    the total past $1. Spend below $1 is never asked."
  - On done, C ends its own chat with «Готово, керівник зіллє роботу й закриє цю сесію» and no
    question (`dev-kit:manager`, "A task from the project lead").
- Right after registering a C, arm the watcher (see "Wake-up"); if one already runs, the new C is
  picked up by it and the second one exits at once with `already watching`.
- Register every C at once. Take its full `sessionId` from `claude agents --json` (match by `name` or
  `cwd`; the transcript needs the full id, not the 8-hex short id), then
  `dev-kit-sessions add --id <sessionId> --name "C: <feature>" --worktree <path> --task <file> [--parent <P's own session id, if known>]`.
  The registry, not the session list, is P's source for which C it owns; the session list only adds state.

## Apply dev-kit migrations

dev-kit keeps a numbered list of changes every project with a lead makes in its own files (the
plugin's `migrations.md`); the project records the last applied number in its profile (section
`## project-lead`, row `migrations applied`; no row means 0). P checks it on start and after a
plugin-update restart: `dev-kit-migrations pending` (Bash tool, main checkout). It prints `none`, or
the pending entries and the list's path. Exit 2 (a broken list or level): P tells the owner in one
line, as a critical item, and starts nothing.

- Pending entries and no migration C registered (`dev-kit-sessions list`): P starts one C for all of
  them, as in "Start a C", named «C: Міграції dev-kit» (or «C: dev-kit migrations» in English). The
  task file lists the entry numbers and says: apply the entries in order; for each, follow its `How`
  under this project's rules, check its `Done when`, then run `dev-kit-migrations record <n>` in the
  worktree. An entry with an `Owner choice` goes to P as a question before it is applied, and the C
  waits for the answer (it never records past an entry it has not applied). P puts that choice in the
  owner queue and passes the answer back; a hand action the entry gives the owner on a yes, P puts
  in the queue too. With a migration C registered, P starts no second one.
- The C's edits of rule text run steps 1-2 and 5-6 of `dev-kit:edit-rules`: the owner's yes to the
  entry, given when it was added to the list, is their approval (as in `dev-kit:migrate-docs`). P does
  not apply entries itself.
- The recorded number reaches main with P's merge (see "Acceptance and merge"); until then `pending`
  still lists the entries.
- Urgent edits needed in every project at once are not entries: Pult starts a session in each project
  for them (the `pult` plugin's hub rules).

Why: the owner agreed on 2026-11-16 that a change every project needs is written once in dev-kit and
each lead applies it under its own project's rules, with no agent editing other projects.

## Start an «Обговорення:» session

For a task of branch 4 in "Before a task: triage", after the owner's «так» to the proposal. Start it as a C (overlap check, worktree, folder
setup, registration) with these differences:

- Name `Обговорення: <feature>` (no guillemets in the name) (flag `--name` and `--remote-control`), `--permission-mode auto`
  (the owner answers its prompts), `--model opus --effort medium` (the owner talks with it).
- The owner's «сабсесія», «саб-сесія», «сесія для обговорення», or «саб» to talk something over,
  means this session, never a helper agent. When the owner's words point at a log, file or session
  («нехай прочитає лог тієї сесії»), P adds its path to the first prompt.
  Why: on 2026-11-16 the owner asked P: ClaudeDevKit for «саба для обговорення» and P started an
  internal helper the owner could not talk to.
- The owner talks with it directly. One session plays analyst and mockup designer. First prompt: the
  owner's words, the task file path, a feature file path, "run `dev-kit:discovery-round` for the
  meaning and the show-idea slot for the look; on the owner's «так» to the mockup, in the same turn,
  write the «Approved design» section in the feature file (`dev-kit:documentation`, "Feature file")
  and a next-step line in PROGRESS.md, then send P a done report by SendMessage; without that section
  you may not report done".
- It ends with the owner's «так» to the criteria and the mockup. P merges its branch as in
  "Acceptance and merge", but never a branch whose feature file lacks the «Approved design» section:
  P sends it back. Then P starts a C from that feature file (see "Build a designed screen").
- After the launch P writes exactly one line and nothing else: `Відкрий сесію «Обговорення:
  <feature>» - там обговориш усе по задачі.`, with the exact name from the launch. No question, no
  button, no status, no recommendation; the owner's global rules name this exception. When the owner
  answers «так» or similar, P writes nothing more about opening it.

Why: the owner decided on 2026-11-15 that what the owner approves must be written down before the
build, so the C builds without him and what the lead accepts is what he accepted.

## Build a designed screen

For a feature whose file has an «Approved design» section in state `approved, not built`. The steps
run one after another; nothing unfinished is merged.

1. P starts a C as in "Start a C", from the feature file. Its first prompt adds: the owner's «так» to
   the mockup is consent for `check-look`, `check-ui` and `check-usability` of that screen
   (`dev-kit:test-change`); build the screen on your own branch and check it yourself in the
   test-change order (`check-look`: in web-kit the designer compares headless shots with the mockup
   and layout-checker checks the widths; then `check-ui`, then `check-usability`); the done report
   carries shots of the built screen next to the mockup.
2. On C's done report P shows the owner the shots next to the mockup, as a queue item with the
   choice «так» / «є питання».
3. «так»: P merges as in "Acceptance and merge", then sets the section's state to `built` in the main
   checkout and commits it.
4. «є питання»: P stops the C (`dev-kit-sessions end --id <id> --status stopped`, then
   `claude stop <id>`) and starts an «Обговорення: <feature>» session for the polish (the show-idea
   slot's polish stage; in web-kit, `web-kit:design-screen` stage 2) on C's branch, in its worktree as
   in "Refresh an overfull C"; if the session cannot continue that branch, on a branch made from it.
   Its first prompt holds the owner's questions and the feature file path. It reports done to P after
   the owner's «так» in it; then P does step 3.

Why: the owner wants the design flow to go one step after another, with nothing lost (owner,
2026-11-18).

## Ask-P list

Actions a C does only after P's yes (the same list is in the first prompt and in `dev-kit:manager`):

- starting the owner's app in the main checkout;
- loosening a validation or safety guard;
- deleting tracked files;
- a paid call that would take the task's total past $1 (spend below $1 is never asked);
- any step a project rule says needs consent (check-ui, check-usability, check-look and similar),
  except the checks a screen's approved mockup already allows (`dev-kit:test-change`).

P answers these itself. It asks the owner only for money over the threshold, a hard-to-undo step or
a product choice (see "Owner queue and critical items").

## Hard bans

Hard bans are deny rules in a settings file committed on main (`.claude/settings.json`), so every
fresh worktree has them. Neither P nor C may add, change or lift them; the owner adds the lines by
hand after his yes, and neither P nor C writes them. The set is proposed once per project, as one
yes/no with the exact lines, by entry 3 of the plugin's `migrations.md` (see "Apply dev-kit
migrations"); the profile's `hard bans` row records the answer, so P does not ask again. The set: push to
main where main deploys; deleting data folders or the owner's database; stopping the owner's
containers; editing permission settings.
Every Bash line has a PowerShell twin of the same shape (Claude Code docs: PowerShell rules use the
same shape as Bash rules), because C may run either shell.

```json
{
  "permissions": {
    "deny": [
      "Bash(git push*main*)",
      "PowerShell(git push*main*)",
      "Bash(rm -rf <data-folder>*)",
      "PowerShell(Remove-Item*<data-folder>*)",
      "Edit(<owner-database-file>)",
      "Bash(docker stop *)",
      "PowerShell(docker stop *)",
      "Bash(docker compose down*)",
      "PowerShell(docker compose down*)",
      "Edit(.claude/settings.json)",
      "Edit(.claude/settings.local.json)"
    ]
  }
}
```

The settings lines hold for most projects, but only best-effort: a shell command can still write the
file. The push lines are for projects where main deploys. `<data-folder>`, `<owner-database-file>`
and the docker lines are project-specific placeholders: P fills them from the project or drops them.

## Take over a session the owner started

Offer: at every status (on start, on "what runs now?", at every status after a wake-up), not only at
start, P runs `dev-kit-sessions others`. Each session `started by owner` that P has not yet offered
becomes one owner-queue item `Взяти «<name>» під керування?` with its `Рекомендую:` line. P offers each
session once: the answer, a "no" included, is written into the item's record in the queue
(PROGRESS.md "Open questions"), so a session the owner declined is never offered again. It stays
under «Сесії, які ти запустив сам».

Idle session, never taken over: when `others` shows such a session idle and its last reply (read
with `dev-kit-sessions state`) reports finished work, or P received its FYI, the queue item is
«Закрити «<name>»? (роботу завершено)» instead of the takeover item. On yes P runs
`claude stop <id>`. If a session of a declined offer is idle, P asks the same closing question once.
Why: on 2026-11-16 «C: Pult як плагін», started by Pult, finished and hung idle; P only listed it
and never offered it, so nobody closed it.

On yes: `dev-kit-sessions add --id <sessionId> --name "<its name>" --worktree <path> --task <text> --owner`
(full id from `claude agents --json`; `--worktree` is the session's `cwd` from that list, the main checkout
for a session on main; `--task` holds the session's first owner message in short).
P sends the session no message: a message to a session in another permission mode is held for the
owner's approval and may expire. The session goes under «Сесії в роботі» at once. The plugin itself
adds a note at each owner message to it: it is watched, it ends with the line «Роботу завершено» when
fully done, and on main it commits its own work to main after each finished step, so P does not merge
it. Right after `add --owner` P arms the watcher (see "Wake-up"). Known limit: the hook note reaches the
session only at the owner's next message to it, so a session already idle at takeover may never write
«Роботу завершено»; P then shows it as waiting.

Watching: at every status P runs `dev-kit-sessions state` for these sessions (it reads the state and
the last reply without messaging) and shows the state plus the gist in «Сесії в роботі». The owner
keeps talking to the session directly; P never answers for it and never relays its questions. P keeps
new tasks off its changed files (the overlap check in "Start a C" covers it).

Finished: when `state` or the watcher (`finished: <name> | <id>`) says finished, P runs
`dev-kit-sessions end --id <id>` and tries `claude stop <id>`. If the stop fails (the session is open
in the app window), P just stops counting it as active and asks the owner nothing. No merge, no
worktree removal.

Why: owner decided 2026-11-15 that P watches sessions he started so they do not get in the way of
others, closes them only so P stops counting them, and never messages them (mode mismatch).

## Wake-up

P does not wake by itself, and it never uses `notify_when_idle` for a C: every idle notice woke P, and
the host forced a visible reply each time, so the owner got many repeated small messages (seen in
P: Zhratva, 2026-11-15). P wakes only on a C report (SendMessage), an owner message, or an exit of the
session watcher. P speaks to the owner at once only for a critical item; otherwise it shows the next
queue item after the owner answers or writes.

Watcher: `dev-kit-sessions watch` in the Bash tool with `run_in_background`, run in the project's
main checkout. It reads the registry's active sessions (C and taken-over owner sessions) every minute, stays silent
while they live, and exits when one is gone, stopped on the usage limit or, for an owner session, finished; its own limit is 2 hours. Never run it in the foreground: the Bash tool kills
a foreground command at its 10-minute timeout with no exit line, while a background one is not bound
by the timeout (checked 2026-11-15: background runs of 150 seconds with a 60-second timeout and of
12 minutes both finished). Arm it after `add` of a C, after `add --owner`, and after every
exit below, while the registry has an active session. On its exit:

- `gone: <name> | <id> | <state>` (exit 0): that C ended. If it sent a "done" report, go on with the
  merge and re-arm only after its clean-up (`end` first, or the watcher fires on it again). Otherwise it crashed or quit: run `dev-kit-sessions end --id <id> --status stopped` (so the
  re-armed watcher does not fire on it again), send the "stuck" template (critical, out at once;
  cause: the session ended without a report) and re-arm. Recommend a fresh C in the same worktree,
  same name and flags, whose
  first prompt adds: "a previous C left unfinished work here; read `git status`, `git log main..` and
  the task file first". Register it with `--predecessor <old id>`. For a taken-over owner session
  `gone` only means it ended: run `end --id <id>`, no "stuck" template, re-arm.
- `finished: <name> | <id>` (exit 0): a taken-over owner session wrote «Роботу завершено» (a C never
  reports `finished`; its end is `gone` plus its "done" report). Do the
  "Finished" step of "Take over a session the owner started" (`end --id`, try `claude stop`, ask
  nothing), re-arm, and show it in the next status; no separate message.
- `limited: <name> | <id> | resets <time>` (exit 0): that C stopped on the usage limit; it is alive and
  goes on after the reset. Tell the owner in one line the session name and the reset time (a queue
  item, not critical), re-arm, and never `end` or stop that C. Each stop is reported once.
- `time limit` (exit 4): run the skill update check below, then re-arm; no text, no other checks.
- `restart requested: <version>` (exit 7): the handshake of "Restart for a plugin update".
- `nothing to watch` (exit 5: no active session, also at the time limit when the last session ended meanwhile) or
  `already watching` (exit 6: another watcher runs): do not re-arm; no text.
- "No text" for exits 4, 5 and 6 holds even when the host then demands visible output: end the turn
  empty again (seen in P: Zhratva, 2026-11-15: text on watcher exits confused the owner).
- Any other exit (3: the registry or session list unreadable for several minutes): the "stuck" template
  for P itself, in one line, then re-arm.
- The host stopped the watcher itself (its note says the system ran low on memory and not to start it
  again on your own): re-arm it at once, with no text and no owner yes; this rule is the owner's standing
  ask, so it wins over the note. Why: on 2026-11-16 a reaped watcher left every C unwatched until the
  owner, who did not know what it was, said yes.
- A C still in the session list but with no process (Claude Code closed it, or it crashed) is reported
  `gone` only after 5 minutes: meanwhile the Pult watcher brings it back with `claude respawn`. Such a
  `gone` means that failed; handle it as above.

Skill update check, on every wake-up: read `version` from
`.claude-plugin/plugin.json` two folders above this skill's base directory and compare it with the
version P noted when it last read this skill (note it in the first status turn's tool output). If it
changed, read this SKILL.md whole with the Read tool (the Skill tool only answers "already loaded")
and follow the new text from then on; P's process still runs the old hooks and agents, so P also runs
the handshake of "Restart for a plugin update". No message to the owner about it.

On an owner message or a C report run `dev-kit-sessions fill`.

The fill limit is 0.5 (half the context window). The script takes the window from C's model as Claude Code runs it
(1M for Fable, Sonnet 5+, Haiku 5.5, Opus 4.7+; 200K for older ones); `--window` overrides it. For each
line marked OVER, refresh that C.

## Refresh an overfull C

1. Message C: reach the nearest checkpoint between steps (never mid-step), run
   `continue-work-in-another-context save`, reply with the handoff file name.
2. Start a fresh C from inside the SAME worktree folder (no `-w`), same name, model, effort and
   permission mode; first prompt: `/continue-work-in-another-context load <file>`, then "once loaded,
   send P «picked up» by SendMessage".
3. Only after the new C's «picked up» reaches P, register it with `dev-kit-sessions add ...
   --predecessor <old id>` (this ends the old record as `replaced`), then run `claude stop <old id>`.

Checked live 2026-11-14: a fresh bg C started in an existing worktree loads the handoff from its first
prompt and can write there. If a step fails, tell the owner and keep the old C running.
Two C sessions share one name during a refresh; message the new one by its `[ref]` from ListAgents.
Why: without the «picked up» check P could stop the old C before the new one held the work (owner,
2026-11-18).

## Shared app

C runs `dev-kit-app start` in the background after P's yes (see "Ask-P list"): it may wait in a
queue while another C uses the app (up to 15 minutes). A queue timeout reaches P as "stuck"; P tells
the owner which worktree holds the app.

## Acceptance and merge

C owns all doc updates. On "done", P checks only the list of changed doc files (a reviewer subagent if
there are many). Then, in the main checkout: if it is not on `main` or `git status --porcelain` is not
empty, P does not merge and tells the owner. P commits its own edits in the main checkout (PROGRESS.md,
BACKLOG.md `Verdict:` lines) right after making them, so a dirty checkout is never P's own (that is the owner's work in progress, not C's conflict).
Otherwise `git merge --ff-only c/<slug>`. If it refuses (main moved since C pulled it), P sends it back
("main moved, pull main") and does not resolve anything itself.

When P edits a file in the main checkout from outside its own worktree (PROGRESS.md, a feature's
design state), it re-reads the file after each edit and checks that the edit fully applied before
committing it. This is a stopgap: the cause, the host's worktree guard that blocks such edits, is out
of reach (seen in P: Zhratva, 2026-11-18: shell edits half-applied).

After a merge, without asking the owner, run `dev-kit-sessions end --id <id>` (the short id works),
`dev-kit-app stop --project <that C's worktree>` (releases the app lock if C left the app running),
`claude rm <id>` (the session's job state), then removes each `link` row's junction without following
it (`cmd /c rmdir "<worktree>\<path>"`, PowerShell tool, no `/s`; never `Remove-Item`, `rm -r` or
`--force` while a junction is there: they may delete the main checkout's data), then, from the main
checkout (`Set-Location <main>` first if the PowerShell tool's folder is anywhere inside the worktree,
or the folder stays behind locked), `git worktree remove <worktree>` and
`git branch -d c/<slug>`: `claude rm` does not remove a worktree P made by hand. If `git worktree
remove` refuses over untracked files, P looks at them: nothing from the task, `--force`; otherwise it
asks the owner. A C that ended without a merge gets `dev-kit-sessions end --id <id> --status stopped`,
then `claude stop <id>` (in this order, so the watcher does not report it), and its worktree and branch stay.

A taken-over owner session working on main (no worktree) commits its own work to main after each
finished step. P does not merge it and removes no worktree for it. When it finishes P follows
"Take over a session the owner started", step "Finished" (`dev-kit-sessions end --id`, try
`claude stop <id>`; if the stop fails, no question to the owner). Why: the owner decided on
2026-11-15 that main stays clean, so P's merges of other C sessions do not wait on it.

After the clean-up P re-reads the next-work sections of PROGRESS.md and sends the Task done
template, ending with the proposal for the next item.

## Restart P

`continue-work-in-another-context save`, then the owner types `/clear`, then `load`. State lives in
project files and the registry; the queue lives in PROGRESS.md "Open questions". After `load`, P runs
the wake-up checks (fill, registry against the session list) and sends the status. C reports reach P
by name; a background watcher may not survive `/clear`, so P arms it again.

## Restart for a plugin update

The Pult watcher restarts the leads after a dev-kit version bump so they load the new skills, agents
and hooks (the owner's request of 2026-11-16). It notices the bump itself: it compares the version P's
process started on with `plugin.json` of the main checkout. An idle P (no turn, no background task) is
restarted at once. A busy P is never woken for it: it finds the new version itself at its next wake-up
(the skill update check in "Wake-up"; the watcher's time limit wakes it at least every 2 hours). Only
when the owner asks Pult to update the leads does the session watcher wake P at once, with
`restart requested: <version>` (exit 7). The restart resumes the same conversation; only the session
process is new. Why: the owner chose on 2026-11-16 no extra paid turns by default, at the cost of up to
2 hours on the old hooks and agents.

- Handshake (a new version found at a wake-up, or exit 7): from then P
  starts no new step (no new C, no merge, no new subagent). A step already running is brought
  to a point where a stop breaks nothing: a merge and its clean-up are finished, an edit P began is
  committed, a running subagent is waited for. C sessions keep working on their own. Then P runs
  `dev-kit-sessions restart ready --version <the new version>`, re-arms the watcher if the registry has
  an active session, and ends the turn with no text to the owner. An owner message that arrives before
  the restart is answered after it. The hold ends by itself 10 minutes after `ready` with no restart
  (the watcher drops an older `ready` too); P then works as usual and says nothing about it.
- First prompt after the restart: `/dev-kit:project-lead restart: plugin update`. P skips the start
  status and goes on where it stopped: it reads this SKILL.md whole, notes the new version (see
  "Wake-up") and runs `dev-kit-sessions fill`, `dev-kit-sessions others` and `dev-kit-sessions state`.
  If the registry has an active session, P re-arms the watcher (see "Wake-up"). If that watcher exits at
  once with `already watching`, the old one may have outlived the stop: P reads the holder's pid in
  `watch.lock` next to the registry, stops that process and arms again. Then P sends each active C one SendMessage: «P перезапущено після
  оновлення плагіна. Якщо твій звіт до P не дійшов (помилка "not reachable"), надішли його ще раз.»
  An unfinished step from before the stop is finished now. Then P runs the check of "Apply dev-kit
  migrations"; a migration C it starts shows in the next status, with no message now. P writes to the owner only what was
  already due to them (a C report that waits, a critical item), in the usual templates; no message
  about the restart itself.
- A message to a stopped session fails at the sender with "No agent named ... is reachable" and is
  not queued (checked live 2026-11-16 with a throwaway session); after the resume the same name
  receives messages again. So a C report sent during the stop is not lost in silence: the C sees the
  error, and P's resend request above catches it. A C that ended during the stop shows as `gone` to the
  re-armed watcher; before the "stuck" template P checks its task file and branch for a finished
  result, since its "done" report may have failed.

## Plugin backlog (plugin repo only)

In the plugin repo (ClaudeDevKit) P also handles `BACKLOG.md`: agents in other projects add plugin
changes there and message `P: ClaudeDevKit` (`dev-kit:manager`, "A change to the plugins themselves").
P has no timer. On start and on every wake-up, a new entry is one with no `Verdict:` line; P names the
new entries in its status.

After merging work that bumps the `dev-kit` version, P sends nothing about it: the Pult watcher sees
the new version in the main checkout and restarts every lead, this P included (see "Restart for a
plugin update"). Why: on 2026-11-16 the hub got that message but restarted nobody: it acts only when
someone writes in its chat.

- Up to 3 new entries, all simple (one place in one skill, agent or doc, no clash with other rules):
  one `dev-kit:reviewer`, whose brief carries steps 1-2 of `dev-kit:edit-rules`, reviews them together
  and returns, per entry, a recommendation with its reason, the idea in one plain line and the exact
  edit. P writes each recommendation as a `Verdict:` line under its entry and asks the owner a yes/no
  batch on the ideas, not the wording. On "так" one `dev-kit:coder` applies the edits, bumps the plugin
  version, runs the lint and removes the built entries; P runs steps 5-6 of `dev-kit:edit-rules` on the
  diff and commits. On "ні" P removes the entry. This is P's one exception to "no task work"; any other
  rule edit P makes follows `dev-kit:edit-rules` too.
- A complex entry (several files, the P/C flow, a new skill or script), more than 3 new entries, or
  an entry the owner wants to discuss rather than answer yes/no: one C for the whole batch, started
  as in "Start a C".

Why: the owner decided on 2026-11-14 that a C for every simple rule edit is too much, and a timer
costs tokens while nothing is new.

## Not supported yet

A C that starts its own C (P-P-C). The registry has a `parent` field for it; do not use this flow yet.
An independent part a C finds mid-work comes to P as a new task. Dependent parts stay in one C,
which fixes how they fit in the task file and runs parallel subagents.
