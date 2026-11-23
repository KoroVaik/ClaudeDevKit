# Own docs of Claude quirks and workarounds across apps

Status: built by a C (2026-11-23); waits for P's merge.

Spend: ~1.1% of the weekly limit, estimate; API: 0 USD

## Owner's words

«скажи чи десь занотовуються отакі ньюанси і воркеранди роботи клода в різнизних апілікухах типу десктоп, сервер, андроід апп і тд? Бо документації офіційной майже нема, тому є сенс вести свою документацію» and «скажи керінику щоб запустив інше обговорення» (2026-11-23, in «Обговорення: Повідомлення під час перезапуску»).

## Known context (to check)

- No single place today. Such facts are scattered: plugins/dev-kit/skills/project-lead/SKILL.md (live-checked notes with dates), the owner's local `.claude/docs/tools.md`, `docs/findings/` of this repo.
- Fresh live facts (2026-11-23) in `plans/restart-notice.md` on branch `c/restart-notice`: a send to a stopped session over Remote Control fails with «HTTP 409 ... not active», not only «not reachable»; resuming without `-n` gives the session a new name; an owner message sent during a restart is not lost.

## Success criterion

The owner agrees whether to keep such docs, where they live, what goes in, who writes and updates them, and how agents find them before acting.

## Owner's approval

(written by the discussion session on the owner's «так»)

Approved by the owner («+» to the short plan, 2026-11-23). The short plan he approved:

1. All known Claude quirks sit in one file in dev-kit, by app, with no duplicates.
2. Each fact has a date, the Claude version, how it was checked and a status checked / doubtful / outdated.
3. New facts are collected by the daily session scan; only a dedicated agent writes them, in one format.
4. Facts are re-checked weekly and after a Claude update; what only the owner can see comes as one batch a week.
5. Every session learns of the file from one line in the owner's global rules.

Agreed points in detail:

- Not a separate plugin: dev-kit is enabled in all six of the owner's projects, so a new plugin adds no reach (checked in their `.claude/settings.json`). Owner has not yet said «так» to the place itself (question 1).
- Facts are written only by one dedicated dev-kit agent, in one standard format; it checks the new fact against the existing ones for duplicates and contradictions. No owner's yes per fact (owner: «обовязково апдейт клод фактів через спец агента, щоб все було стандартищовано»; «так» to question 5).
- Every fact carries the date, the Claude Code version, how it was checked and a status: checked / doubtful / outdated («так» to question 6).
- A background run re-checks the facts weekly and after a Claude Code update; facts that need the phone or the owner's eyes are checked only by the owner («так» to question 7).
- Collecting facts runs in the background: it must not add questions for the owner, and sessions must not be made to report facts all the time (owner, 2026-11-23).
- Technical choices are left to the agent (owner: «про такі тех деталі вирішуй сам»). Decided by the discussion session:
  - Place: one file in the dev-kit plugin, `plugins/dev-kit/claude-facts.md`, grouped by app or area (desktop app, phone app, claude.ai web, Remote Control, background and cloud sessions, headless `claude -p`, plugins and hooks, Windows shell). Not the owner's local `.claude/docs/` (seen on one machine only, no history).
  - One home per fact: the fact, its date and its check live only in this file; a skill or rule keeps only what to do and a link to the fact. The existing facts (about 40, in project-lead and manager skills, `plugins/pult/rules/hub.md`, pult scripts, `docs/findings/idle-wake-cost.md`, `plans/bg-browser-checks.md`, `plugins/web-kit/browser-checks.md`, the owner's `tools.md` and `fable-subagents.md`, the branch `c/restart-notice`) are moved in once, deduplicated; contradictions (for example "not reachable" vs "HTTP 409 ... not active" for a send to a stopped session) are settled by the newest checked fact. The owner's `tools.md` stays the rule home of the Windows-traps hook; its facts link to the file.
  - Fact format: what happens, the workaround, app and Claude Code version, date, how it was checked (and a command or steps to re-check), status `checked` / `doubtful` / `outdated`, the source (project and session).
  - Writer: a new agent type in dev-kit (sonnet) that takes candidate facts, matches them against the file, writes or updates entries in the format and never writes a rule. Only it edits the file.
  - Collection, no new parser: the existing daily transcript scan (`dev-kit-retro scan`) gets one more finding kind, Claude app behaviour (host errors such as a failed SendMessage or a Remote Control HTTP error, refused launches). These findings are routed to ClaudeDevKit from every project, Pult and the home folder included (today their other findings stay in the scan log only). The weekly ClaudeDevKit retro hands them to the facts agent.
  - A quiet quirk with no error text: the agent that met it adds one line with `dev-kit-retro add --project ClaudeDevKit --text "<fact>"`, no subagent and no message; only when it actually used a workaround.
  - Re-check: weekly in the ClaudeDevKit retro and after the Claude Code version changes; the facts agent re-runs only checks that are safe (no phone push, no paid API, no owner app); a failed re-check marks the fact `doubtful`, and agents treat a doubtful fact as a hypothesis.
  - How agents find it: one line in the owner's global `C:/Users/korov/.claude/CLAUDE.md`, in its own form «Before <action>, read <path>»: before relying on how a Claude app behaves (sessions, Remote Control, background runs, hooks, desktop or phone app), read the matching section of `C:/Users/korov/MyRepositories/ClaudeDevKit/plugins/dev-kit/claude-facts.md`. Why there: it is loaded in every session and subagent on the machine, every project and the home folder included; dev-kit has no rule text loaded in every session (its hooks inject none at start, checked in `plugins/dev-kit/hooks/hooks.json`), and a skill line reaches only sessions that run that skill. The file opens with a short "how to use" part: find the section, trust `checked`, treat `doubtful` as a hypothesis, report a new quirk by the one-line command. Edited through `dev-kit:edit-rules`.
- Facts only the owner can check (phone push arrived, what the phone app shows): the project lead `P: ClaudeDevKit` brings the doubtful ones to the owner as one batch at most once a week. A doubtful fact is dropped from the batch when a session meanwhile adds a fresh observation of it (through the same collection route) and the facts agent settles it from that (owner: «або ж інша сесія внесе факт по цьом питанню, а так ок», 2026-11-23).

## Built (2026-11-23)

- `plugins/dev-kit/claude-facts.md`: 80+ entries moved in from skills, Pult rules and scripts, web-kit docs and the owner's `tools.md` / `fable-subagents.md`; each old place keeps its rule and points to the entry by exact title. `plans/` and `docs/findings/` stay as sources. The 2026-11-23 Remote Control facts of `plans/push-noise.md` are in.
- `plugins/dev-kit/agents/facts-keeper.md`: the only writer (sonnet); adds candidates, re-checks only safe checks, returns at most 5 owner-only questions.
- `retro.py`: kind `claude app` (failed SendMessage, refused Agent / session start) routed to ClaudeDevKit from every transcript; `updated <old> -> <new>` on a version rise; `weekly re-check due` once in 7 days. Tests in `tools/tests/test_retro.py`.
- `retro` skill step 4 hands these lines to the facts keeper after `EnterWorktree`; owner-only questions go to item `claude-facts-owner-check` (disputed) for P's weekly question; P passes answers back with `dev-kit-retro add ... "owner check ..."`.
- Owner's global `CLAUDE.md`: section "Claude app facts" (local git commit done). Feature doc `docs/features/keep-claude-app-facts.md`.
- Versions: dev-kit 0.1.105 (routine mark), pult 0.1.23, web-kit 0.4.1, unity-kit 0.2.2.
- Left for the push-noise C: project-lead "Start a C" still says a C without `--remote-control` gets no RC push (its Why line); the facts file already has the new behaviour.
