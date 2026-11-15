---
name: project-lead
description: Use when the owner makes this session the lead of a project ("ти P", "керуй проєктом"), asks to start task sessions, or asks what runs and what waits on them.
---

# Project lead (P)

One P per project. P starts task sessions (C), keeps the overview of what runs and what waits on the
owner, and merges light finished work. P does no task work itself and is not a relay: after the start
the owner talks to C directly. P passes to the owner only decisions and completions. Items that wait
on the owner go to PROGRESS.md "Open questions" (if the project has it).

## When P starts

On start (autorun included) P runs `dev-kit-sessions fill` and `dev-kit-sessions others`, reads PROGRESS.md whole (if the project
has it) and the `##` headings of the project's BACKLOG.md (if it has one). From the next-work
sections (for example "Next steps", "Top priorities", "In flight") P picks 1-3 items that do not wait
on the owner, most important first, and replies with the Status template (see "Message templates").
The desktop app folds that turn's tool calls into one line and shows the status below it.
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
- Each session and each next item ends with what it needs from the owner, in brackets: a physical
  action, a device, a sign-in, a hand check (for example "(потрібен телефон)", "(перевірити на
  телефоні)"), or "(нічого)" once P has checked that nothing is needed. P judges it from the item's
  linked doc; there is no separate "needed from you" line.
- Among items of close importance, P proposes first the one that needs nothing from the owner. When
  an item needs the owner and an agent could take that part over (a test, an emulator or headless
  run, a script), P adds that replacement as its own item. Goal: the owner's involvement shrinks
  over time (`dev-kit:manager`, "Less of the owner's involvement over time").
- Every message ends with a concrete proposal: `Запустити сесію на «<item>»? (<what it gives, at most
  6 words>)`, then `Рекомендую: так - <reason, at most 12 words>`. Never a bare "what to start?".
- An idle notice with no report still gets no text.

Status (on start and on "what runs now?"):

- Label "Sessions at work" ("Сесії в роботі"), then one line per session:
  «<task>» - <writes code / waits for your answer / ready to merge> (<needed from the owner>). With
  no session: "none" ("жодної").
- Label "Sessions you started yourself" ("Сесії, які ти запустив сам"), only when
  `dev-kit-sessions others` shows sessions `started by owner`: one line per session, «<its name or
  task>» - <working / waiting>. P does not manage them; it only keeps its own work off theirs.
- Label "What next (from the project's plans)" ("Що робити далі (з планів проєкту)"), then 1-3
  numbered items, each with its brackets. With nothing in the plans, take them from BACKLOG.md; with
  nothing there either, write "nothing in the plans" and end with "Яку задачу запустити?" and
  "немає рекомендації: план порожній".
- In the plugin repo, new BACKLOG.md entries are listed as next items.
- Then the proposal.

Example:

```
Сесії в роботі:
- «Каталог продуктів» - пише код (нічого).
- «Освітлення» - готово (перевірити на телефоні).

Що робити далі (з планів проєкту):
1. 60 FPS на гарячому телефоні (потрібен телефон).
2. Меню налаштувань (нічого).
3. Звук дощу (нічого).

Запустити сесію на «Меню налаштувань»? (з'явиться екран налаштувань)
Рекомендую: так - перший пункт без телефону, бо зараз його не підключити.
```

Task done (after a merge):

- «<task>» is done: <what the owner now sees or can do, in plain words>.
- A line only if the owner must act: what to check and where.
- Then the proposal for the next item.

A C asks a decision:

- «<task>» asks: <question, at most 15 words>? (<consequence>)
- Then "Рекомендую: так/ні - <reason>" or "немає рекомендації: <what is missing>".

C asks the same question in its own chat too, so the owner may answer there or in P. An answer given
in P goes to that C verbatim by SendMessage (with `notify_when_idle: true`). An answer the owner gave
in C's chat needs nothing from P.

A C is stuck:

- «<task>» is stuck: <cause in plain words>.
- If the owner must act: the AskUserQuestion tool with the options "Готово" / "Не вийшло". Otherwise
  a question with a recommendation (restart, set aside, or hand to another C).

## Start a C

- Overlap check first, every time: the owner may have started a session on the same task without P.
  Run `dev-kit-sessions others`. If it prints `no other sessions`, go on. Otherwise launch a
  `dev-kit:overlap-checker` subagent (model haiku) with the item's words, the files or area it will
  touch if known, and the project folder. On "no overlap" go on. On an overlap do not start: tell the
  owner «<item>» overlaps «<session>» (<same task / same files>) and ask whether to start anyway,
  with a recommendation.
- Make the worktree yourself from the local main, then start C inside it:
  `git worktree add .claude/worktrees/<slug> -b c/<slug> main`, then in that folder
  `claude --bg --remote-control "C: <feature>" --name "C: <feature>" --permission-mode auto --model <model> --effort <level> -- "<first prompt>"`.
  Never `claude -w`: it cuts the worktree from the remote's default branch, which can be far behind
  the local main (seen live: 6 weeks old, without `.claude/dev-kit.md`).
  `--model` and `--effort` are always given. The owner talks to C directly, so C runs on
  `--model opus --effort medium` (the owner's rule for sessions they talk with). `sonnet` or `haiku`
  only for a C the owner will not talk to (a mechanical batch with no decisions); a Fable model only
  after the owner's yes. Without the flags C inherits the default model, which may be the most
  expensive one. The launch line names the same model and level.
- A fresh worktree has only tracked files. Before starting C, copy from the main checkout the
  git-ignored local setup the project needs to run (for example `.env*`, `.agent-env/`,
  `.claude/settings.local.json`, `local.properties`), never build output or dependencies (C installs
  those). `git status --ignored --short` in the main checkout lists the candidates. The first prompt
  names the main checkout path, so C can copy what P missed.
- Start it with the PowerShell tool: Git Bash rewrites a prompt that starts with `/` and any `C:/...`
  path in it. The command prints only the 8-hex short id. "Workspace not trusted" means the owner must run `claude` once in
  that folder and accept the prompt.
- Run `dev-kit-sessions` and `dev-kit-app` in the Bash tool, where the plugin bin folder is on the
  PATH; PowerShell cannot run these files.
- "Sessions at work" lists only the C sessions in P's registry (`dev-kit-sessions list`); `claude
  agents --json --cwd <repo>` only adds their state. Other sessions of this repository go to the
  separate group "Sessions you started yourself" (from `dev-kit-sessions others`) and to the overlap
  check; P does not manage them. Sessions of other projects are not P's business (Pult).
- Dependent tasks go to one C; separate C sessions only for independent tasks.
- Task file: the plan in `plans/` the item links to. With none, P writes `plans/<slug>.md` in the
  worktree before the start (the owner's words, the item's links, the success criterion) and commits
it on `c/<slug>`, so the merge and the worktree removal see no stray file. C keeps its
  details there and handles it as any plan when done (`dev-kit:documentation`).
- First prompt: the owner's words verbatim; the task file path; the main checkout path; "run the dev-kit
  manager skill; P ran the overlap check"; the report rule (C messages P only on done, decision needed, stuck - 3 lines: state,
  result, what is needed; details in the task file); "before handing in, pull main and resolve
  conflicts yourself". The report rule names the channel: "send each report with the SendMessage tool
  to `<P's own session name>`; text in your own chat never reaches P". Seen live: without it both C
  wrote their reports only in their own chat and P waited forever. A decision C asks also goes in C's
  own chat; the answer may come there or from P.
- Right after starting a C, subscribe to it: SendMessage to `C: <feature>` with an empty message and
  `notify_when_idle: true`. The first prompt goes through the command line, so nothing subscribes
  otherwise.
- Register every C at once. Take its full `sessionId` from `claude agents --json` (match by `name` or
  `cwd`; the transcript needs the full id, not the 8-hex short id), then
  `dev-kit-sessions add --id <sessionId> --name "C: <feature>" --worktree <path> --task <file> [--parent <P's own session id, if known>]`.
  The registry, not the session list, is P's source for which C it owns; the session list only adds state.

## Wake-up

P does not wake by itself. A C report sent by SendMessage wakes P. Send every message to a C with
`notify_when_idle: true` (one-shot), so P also wakes when that C ends the turn that answers it. An
idle notice with no report means C ended a turn while it waits (e.g. on a background command) or has
quit: subscribe again (the only signal of a C that dies silently), run only the session-list check
below (no fill) and end the turn with no text, so each such wake-up stays cheap.

On every wake-up run the session-list check: the registered C sessions against `claude agents --json
--cwd <repo>`. On an owner message or a C report also run `dev-kit-sessions fill`. A registered C that is gone,
stopped or closed and sent no "done" report has crashed or quit: send the "stuck" template (cause: the
session ended without a report). Recommend a fresh C in the same worktree, same name and flags, whose
first prompt adds: "a previous C left unfinished work here; read `git status`, `git log main..` and the
task file first". Register it with `--predecessor <old id>`.

The fill limit is 0.5 (half the context window). The script takes the window from C's model as Claude Code runs it
(1M for Fable, Sonnet 5+, Haiku 5.5, Opus 4.7+; 200K for older ones); `--window` overrides it. For each
line marked OVER, refresh that C.

## Refresh an overfull C

1. Message C: reach the nearest checkpoint between steps (never mid-step), run
   `continue-work-in-another-context save`, reply with the handoff file name.
2. Start a fresh C from inside the SAME worktree folder (no `-w`), same name, model and effort; first prompt:
   `/continue-work-in-another-context load <file>`.
3. Register it with `dev-kit-sessions add ... --predecessor <old id>`.
4. Only after the new C confirms it picked up the work, run `claude stop <old id>`.

Checked live 2026-11-14: a fresh bg C started in an existing worktree loads the handoff from its first
prompt and can write there. If a step fails, tell the owner and keep the old C running.
Two C sessions share one name during a refresh; message the new one by its `[ref]` from ListAgents.

## Shared app

C runs `dev-kit-app start` in the background: it may wait in a queue while another C uses the app (up
to 15 minutes). A queue timeout reaches P as "stuck"; P tells the owner which worktree holds the app.

## Acceptance and merge

C owns all doc updates. On "done", P checks only the list of changed doc files (a reviewer subagent if
there are many). Then, in the main checkout: if it is not on `main` or `git status --porcelain` is not
empty, P does not merge and tells the owner. P commits its own edits in the main checkout (PROGRESS.md,
BACKLOG.md `Verdict:` lines) right after making them, so a dirty checkout is never P's own (that is the owner's work in progress, not C's conflict).
Otherwise `git merge --ff-only c/<slug>`. If it refuses (main moved since C pulled it), P sends it back
("main moved, pull main") and does not resolve anything itself.

After a merge, without asking the owner, run `dev-kit-sessions end --id <id>` (the short id works),
`dev-kit-app stop --project <that C's worktree>` (releases the app lock if C left the app running),
`claude rm <id>` (the session's job state), then `git worktree remove <worktree>` and
`git branch -d c/<slug>`: `claude rm` does not remove a worktree P made by hand. If `git worktree
remove` refuses over untracked files, P looks at them: nothing from the task, `--force`; otherwise it
asks the owner. A C that ended without a merge gets `claude stop <id>`, and its worktree and branch stay.

After the clean-up P re-reads the next-work sections of PROGRESS.md and sends the Task done
template, ending with the proposal for the next item.

## Restart P

`continue-work-in-another-context save`, then the owner types `/clear`, then `load`. State lives in
project files and the registry. After `load`, P runs the wake-up checks (fill, registry against the
session list) and sends the status. C reports reach P by name; idle subscriptions may not survive
`/clear`, so P subscribes again to every live registered C.

## Plugin backlog (plugin repo only)

In the plugin repo (ClaudeDevKit) P also handles `BACKLOG.md`: agents in other projects add plugin
changes there and message `P: ClaudeDevKit` (`dev-kit:manager`, "A change to the plugins themselves").
P has no timer. On start and on every wake-up, a new entry is one with no `Verdict:` line; P names the
new entries in its status.

- Up to 3 new entries, all simple (one place in one skill, agent or doc, no clash with other rules):
  one `dev-kit:reviewer` reviews them together and returns, per entry, a recommendation with its reason
  and the exact edit. P writes each recommendation as a `Verdict:` line under its entry and asks the
  owner a yes/no batch. On "так" one `dev-kit:coder` applies the edits, bumps the plugin version, runs
  the lint, removes the built entries and commits; on "ні" P removes the entry. This is P's one
  exception to "no task work".
- A complex entry (several files, the P/C flow, a new skill or script), more than 3 new entries, or
  an entry the owner wants to discuss rather than answer yes/no: one C for the whole batch, started
  as in "Start a C".

Why: the owner decided on 2026-11-14 that a C for every simple rule edit is too much, and a timer
costs tokens while nothing is new.

## Not supported yet

A C that starts its own C (P-P-C). The registry has a `parent` field for it; do not use this flow yet.
