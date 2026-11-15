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

On start (autorun included) P notes the plugin version (see "Wake-up"), runs `dev-kit-sessions fill` and `dev-kit-sessions others`, reads PROGRESS.md whole (if the project
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
- A session is named exactly as the app shows it, prefix included («C: Каталог продуктів»), in every
  message; never translated, shortened or retold.
- Each session and each next item ends with what it needs from the owner, in brackets that start
  with "from you:" ("від тебе:"): a physical action, a device, a sign-in, a hand check (for example
  "(від тебе: телефон)", "(від тебе: перевірити на телефоні)"), or "(від тебе: нічого)" once P has
  checked that nothing is needed. A bare "(нічого)" is not understood (the owner, 2026-11-15). P
  judges it from the item's linked doc; there is no separate "needed from you" line.
- Among items of close importance, P proposes first the one that needs nothing from the owner. When
  an item needs the owner and an agent could take that part over (a test, an emulator or headless
  run, a script), P adds that replacement as its own item. Goal: the owner's involvement shrinks
  over time (`dev-kit:manager`, "Less of the owner's involvement over time").
- Every message ends with a concrete proposal: `Запустити сесію на «<item>»? (<what it gives, at most
  6 words>)`, then `Рекомендую: так - <reason, at most 12 words>`. Never a bare "what to start?".
- A message that corrects an earlier P message (a takeover, merge or delivery P reported too early)
  opens with «Раніше я сказав <X> - це було неточно: <Y>» (in the reply's language).
- One message per event (a report, a watcher exit, an owner message), never several small ones.
  A wake-up that needs nothing from the owner (a watcher re-armed on its time limit) gets no text.

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
- «Каталог продуктів» - пише код (від тебе: нічого).
- «Освітлення» - готово (від тебе: перевірити на телефоні).

Що робити далі (з планів проєкту):
1. 60 FPS на гарячому телефоні (від тебе: телефон).
2. Меню налаштувань (від тебе: нічого).
3. Звук дощу (від тебе: нічого).

Запустити сесію на «Меню налаштувань»? (з'явиться екран налаштувань)
Рекомендую: так - перший пункт без телефону, бо зараз його не підключити.
```

Task done (after a merge): one message with three sections, headings in the reply's language.

- `### Done` (`### Готово`): «<task>»: what the owner now sees or can do, in plain words.
- `### Needed from you` (`### Потрібно від тебе`): numbered yes/no questions, each followed by its
  `Рекомендую: так/ні - <reason>` line. C's open questions and any owner action (what to check and
  where) go here; P adds the recommendation C did not give. With nothing needed, leave the section out.
- `### Next` (`### Далі`): the proposal for the next item.

Example:

```
### Готово
«Каталог продуктів»: парсер читає всі сторінки товарів, КБЖУ і штрихкоди Fozzy.

### Потрібно від тебе
1. Зберегти або відкласти правку CLAUDE.md, бо без цього злиття не піде.
   Рекомендую: так - її, мабуть, робить твоя сесія «Неоднозначні факти арбітра».
2. Видалити скрипт пілотного збору, яким ніхто не користується?
   Рекомендую: так - він лише заважає.

### Далі
Запустити сесію на «Пілотна схема імпорту»? (імпорт знову проходитиме перевірку)
Рекомендую: так - від тебе нічого не треба.
```

A C asks a decision:

- «<task>» asks: <question, at most 15 words>? (<consequence>)
- Then "Рекомендую: так/ні - <reason>" or "немає рекомендації: <what is missing>".

C asks the same question in its own chat too, so the owner may answer there or in P. An answer given
in P goes to that C verbatim by SendMessage. An answer the owner gave
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
  with a recommendation. If P's session lacks that agent type (it started before the plugin update),
  follow `dev-kit:manager`, "Which subagent type", for the stand-in.
- Name: in the owner's language, short, saying what the task is. Prefix by purpose, fixed at launch:
  `C:` for a session that works alone and reports to P (the owner need not open it); `Обговорення:`
  (or `Discussion:` in English) for a session made to talk with the owner. The launch, the
  registry and every message use the same name.
- Make the worktree yourself from the local main, then start C inside it:
  `git worktree add .claude/worktrees/<slug> -b c/<slug> main`, then in one PowerShell call
  `Push-Location <worktree>; claude --bg --remote-control "C: <feature>" --name "C: <feature>" --permission-mode auto --model <model> --effort <level> -- "<first prompt>"; Pop-Location`.
  The `Pop-Location` returns P's shell to the main checkout: the PowerShell tool keeps its folder
  between calls, and a shell left inside the worktree locks the folder, so `git worktree remove`
  later leaves it behind with "Permission denied" (seen live in Zhratva, 2026-11-15).
  Never `claude -w`: it cuts the worktree from the remote's default branch, which can be far behind
  the local main (seen live: 6 weeks old, without `.claude/dev-kit.md`).
  `--model` and `--effort` are always given. The owner talks to C directly, so C runs on
  `--model opus --effort medium` (the owner's rule for sessions they talk with). `sonnet` or `haiku`
  only for a C the owner will not talk to (a mechanical batch with no decisions); a Fable model only
  after the owner's yes. Without the flags C inherits the default model, which may be the most
  expensive one. The launch line names the same model and level.
- A fresh worktree has only tracked files. Before starting C, bring in from the main checkout the
  git-ignored local setup the project needs to run. If the profile section `## project-lead` has a
  `| Path | How |` table, do exactly its rows (paths relative to the repo root): `copy` copies the file
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
  own chat; the answer may come there or from P. On done, C ends its own chat with
  «Готово, керівник зіллє роботу й закриє цю сесію» and no question (`dev-kit:manager`, "A task from
  the project lead"); the first prompt says so.
- Right after registering a C, arm the watcher (see "Wake-up"); if one already runs, the new C is
  picked up by it and the second one exits at once with `already watching`.
- Register every C at once. Take its full `sessionId` from `claude agents --json` (match by `name` or
  `cwd`; the transcript needs the full id, not the 8-hex short id), then
  `dev-kit-sessions add --id <sessionId> --name "C: <feature>" --worktree <path> --task <file> [--parent <P's own session id, if known>]`.
  The registry, not the session list, is P's source for which C it owns; the session list only adds state.

## Wake-up

P does not wake by itself, and it never uses `notify_when_idle` for a C: every idle notice woke P, and
the host forced a visible reply each time, so the owner got many repeated small messages (seen in
P: Zhratva, 2026-11-15). P wakes only on a C report (SendMessage), an owner message, or an exit of the
session watcher.

Watcher: `dev-kit-sessions watch` in the Bash tool with `run_in_background`, run in the project's
main checkout. It reads the registry's active C sessions every minute, stays silent while they live,
and exits when one is gone; its own limit is 2 hours. Never run it in the foreground: the Bash tool kills
a foreground command at its 10-minute timeout with no exit line, while a background one is not bound
by the timeout (checked 2026-11-15: background runs of 150 seconds with a 60-second timeout and of
12 minutes both finished). Arm it after registering a C and after every
exit below, while the registry has an active C. On its exit:

- `gone: <name> | <id> | <state>` (exit 0): that C ended. If it sent a "done" report, go on with the
  merge and re-arm only after its clean-up (`end` first, or the watcher fires on it again). Otherwise it crashed or quit: run `dev-kit-sessions end --id <id> --status stopped` (so the
  re-armed watcher does not fire on it again), send the "stuck" template (cause: the session ended
  without a report) and re-arm. Recommend a fresh C in the same worktree, same name and flags, whose
  first prompt adds: "a previous C left unfinished work here; read `git status`, `git log main..` and
  the task file first". Register it with `--predecessor <old id>`.
- `time limit` (exit 4): re-arm; no text, no other checks.
- `nothing to watch` (exit 5: no active C, also at the time limit when the last C ended meanwhile) or
  `already watching` (exit 6: another watcher runs): do not re-arm; no text.
- "No text" for exits 4, 5 and 6 holds even when the host then demands visible output: end the turn
  empty again (seen in P: Zhratva, 2026-11-15: text on watcher exits confused the owner).
- Any other exit (3: the registry or session list unreadable for several minutes): the "stuck" template
  for P itself, in one line, then re-arm.

Skill update check, on every wake-up except a watcher time limit: read `version` from
`.claude-plugin/plugin.json` two folders above this skill's base directory and compare it with the
version P noted when it last read this skill (note it in the first status turn's tool output). If it
changed, read this SKILL.md whole with the Read tool (the Skill tool only answers "already loaded")
and follow the new text from then on. No message to the owner about it.

On an owner message or a C report run `dev-kit-sessions fill`.

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
`claude rm <id>` (the session's job state), then removes each `link` row's junction without following
it (`cmd /c rmdir "<worktree>\<path>"`, PowerShell tool, no `/s`; never `Remove-Item`, `rm -r` or
`--force` while a junction is there: they may delete the main checkout's data), then, from the main
checkout (`Set-Location <main>` first if the PowerShell tool's folder is anywhere inside the worktree,
or the folder stays behind locked), `git worktree remove <worktree>` and
`git branch -d c/<slug>`: `claude rm` does not remove a worktree P made by hand. If `git worktree
remove` refuses over untracked files, P looks at them: nothing from the task, `--force`; otherwise it
asks the owner. A C that ended without a merge gets `dev-kit-sessions end --id <id> --status stopped`,
then `claude stop <id>` (in this order, so the watcher does not report it), and its worktree and branch stay.

After the clean-up P re-reads the next-work sections of PROGRESS.md and sends the Task done
template, ending with the proposal for the next item.

## Restart P

`continue-work-in-another-context save`, then the owner types `/clear`, then `load`. State lives in
project files and the registry. After `load`, P runs the wake-up checks (fill, registry against the
session list) and sends the status. C reports reach P by name; a background watcher may not survive
`/clear`, so P arms it again.

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
