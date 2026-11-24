# Plugin split inventory (read-only survey, 2026-11-24)

Repo: ClaudeDevKit worktree retro-auto. Targets: dev-kit / rules / limits / pult / unclear / SPLIT (a part that mixes
responsibilities: the pieces say where each goes). "rules" = today's retro grown into the rules plugin.
Evidence: read in code unless marked "assumed".

## 1. Skills (plugins/dev-kit/skills)

| Part | What it does | Target | Reason |
|---|---|---|---|
| skills/brainstorm | ideas for an open product direction | dev-kit | product work, part of the process |
| skills/discovery-round | numbered questions, product discussion | dev-kit | product work |
| skills/documentation | docs standard, upkeep rules, feature file format | dev-kit | docs are the process. Piece: table row "Agent rules" and the edit-rules link stay as a pointer to rules |
| skills/edit-rules | 6-step rule edit: read set, find clashes, review | rules | named in the plan as the rules plugin's skill |
| skills/fix-bug | bug flow | dev-kit | process |
| skills/maintain-project-docs | docs audit; weekly «Документація:» background run | dev-kit | docs upkeep is process; its weekly start is wired into retro (see unclear U6) |
| skills/manager | routes a task, briefs, agents, size check, cost | SPLIT: dev-kit + limits + unclear | piece "Stating the cost of work" (share of weekly limit via `dev-kit-retro session`) and "Claude API calls" go to limits (U3); piece "A change to the plugins themselves" (BACKLOG intake) unclear (U4); the rest dev-kit |
| skills/migrate-docs | move old docs to the standard | dev-kit | docs |
| skills/new-feature | feature flow | dev-kit | process |
| skills/project-lead | lead P: sessions, queue, wake-up, restarts, merge | SPLIT: dev-kit + rules + unclear | pieces "Retro of session problems" (lines 1074-1119) and the `retro: N due` line -> rules (shrinks, the plan drops the weekly ask); "Small rule edit" -> unclear (U5); "Plugin backlog" -> U4; "API credit check" (weekly Console check, `dev-kit-api reconcile`) -> limits or unclear (U3); "Weekly limit forecast push" mentions -> limits data; everything else (start C, takeover, hard bans, migrations, restart for update, wake-up) dev-kit |
| skills/prune-tests | mark old tests | dev-kit | testing |
| skills/retro | background «Ретро:» session: review findings, fix | rules | the retro itself |
| skills/showcase | public showcase repo of a private project | dev-kit | project work, no other owner fits |
| skills/test-change | test run and test marks rules | dev-kit | testing |

## 2. Agents (plugins/dev-kit/agents)

| Part | What it does | Target | Reason |
|---|---|---|---|
| agents/coder | bounded code change from a brief | dev-kit | process |
| agents/core-engineer | hard subproblem, Fable, owner yes | dev-kit | process |
| agents/facts-keeper | only writer of claude-facts.md | unclear (U1) | writes facts, fed by the retro |
| agents/investigator | read-only root-cause search | dev-kit | process; the retro also uses it (cross link) |
| agents/mechanical-editor | applies a fully specified edit | dev-kit | process; edit-rules names it (cross link) |
| agents/overlap-checker | checks other live sessions for overlap | dev-kit | sessions |
| agents/question-reader | checks lead questions read in owner's words | dev-kit | lead / owner talk |
| agents/reviewer | independent read-only review | dev-kit | process; retro and edit-rules use it (cross link, dev-kit <-> rules) |

## 3. Scripts (plugins/dev-kit/scripts)

| Part | What it does | Target | Reason |
|---|---|---|---|
| scripts/api_client.py | Messages API client, spend log, reconcile, prices | unclear (U3) | money, not process; fits limits (spend) or stays |
| scripts/check_docs.py | docs structure and link check | dev-kit | docs |
| scripts/check_tests.py | test marks check, coverage report | dev-kit | testing |
| scripts/dev_kit_state.py | per-project state folder name and main checkout | unclear (U7) | shared helper used by dev-kit scripts and retro |
| scripts/hard_bans.py | add and check deny lines in settings.json | dev-kit | lead setup (Pult calls it by path) |
| scripts/migrations.py | pending project migrations, record level | dev-kit | process |
| scripts/retro.py (1980 lines) | transcript scan, findings, items, hooks, spend, limit fit | SPLIT: rules + limits + unclear | rules: Mapper/routing, findings (analyse non-token kinds, claude app, owner check, script candidate), new/seen/items files, `items`, `done`, `add`, `due`, `asked`, hook_start/hook_end, retro session start (lines 307-1090 minus tokens, 1345-1680). limits: `units_of`, `waste_of`, `spend`, `critical`, `session`, `weekly_limit`, fit_limit, window_spans, calibrate, refit (586-640, 1089-1316, 1688-1870). unclear: docs-session start/stamp (`docs_start_command`, `docs_done`, `docs-items`, 1417-1478, 1654-1676) (U6). The `analyse` pass (690-820) computes findings and token units in one loop: must be cut in two |
| scripts/run_app.py | start/stop the project's app, queue lock | dev-kit | process (slots) |
| scripts/sessions.py (1791 lines) | session registry, fill, state, watch, restart, handoff, limited | dev-kit | lead and sessions. Pieces: `size` (wake units, line 1450) uses retro.units_of -> limits link (code import); `usage_limit`/`limited` (stop on usage limit, 744-780, 930-960) stay dev-kit, Pult uses them (U8) |
| scripts/statusline.py | status line `тиждень: N%`, writes usage-log.jsonl | limits | weekly limit status line |
| scripts/usage_forecast.py | weekly-limit run-out forecast for a phone push | limits | forecast; the Pult watcher calls it |

## 4. Hooks (plugins/dev-kit/hooks)

| Part | What it does | Target | Reason |
|---|---|---|---|
| hooks/hooks.json | wires 6 hooks | SPLIT | each plugin gets its own hooks.json: narrow-agents, windows-traps, long-commands, owner-session-note (note part) stay dev-kit; retro-start, retro-end, retro-due part -> rules |
| hooks/long-commands.py | refuses long foreground commands | dev-kit | agent work guard (option: rules as an enforcer, see U9) |
| hooks/narrow-agents.py | allows only the project's own agents | dev-kit | agent work guard (U9) |
| hooks/windows-traps.py | refuses 3 known Windows shell traps | dev-kit | agent work guard (U9); long-commands.py imports it (same plugin, ok) |
| hooks/owner-session-note.py | note for owner-taken sessions; adds `retro: N due` to the lead | SPLIT: dev-kit + rules | note part uses sessions registry (dev-kit); `retro.due_line` part -> a rules hook (U10) |
| hooks/retro-start.py | SessionStart: scan, start retro session, docs session | SPLIT: rules + unclear | retro scan/start -> rules; the weekly docs session start inside `hook_start` -> U6 |
| hooks/retro-end.py | SessionEnd: scan the ended session | rules | retro |

## 5. bin (plugins/dev-kit/bin; each a sh+python launcher)

| Part | What it does | Target | Reason |
|---|---|---|---|
| bin/dev-kit-api | API client launcher | unclear (U3) | as api_client.py |
| bin/dev-kit-app | start/stop app | dev-kit | process |
| bin/dev-kit-bans | hard bans | dev-kit | process |
| bin/dev-kit-check-docs | docs check | dev-kit | docs |
| bin/dev-kit-check-tests | test marks check | dev-kit | testing |
| bin/dev-kit-migrations | migrations | dev-kit | process |
| bin/dev-kit-retro | retro CLI (scan, items, done, add, due, critical, session, calibrate) | SPLIT: rules + limits | scan/items/done/add/due/asked/hook-* -> rules; critical/session/calibrate -> a limits command |
| bin/dev-kit-sessions | session registry CLI | dev-kit | lead |
| bin/dev-kit-statusline | status line launcher | limits | weekly limit |

## 6. Top-level files and plugin data

| Part | What it does | Target | Reason |
|---|---|---|---|
| .claude-plugin/plugin.json | dev-kit manifest, version 0.1.117 | dev-kit | one manifest per plugin; marketplace.json at repo root gets 2 new entries |
| claude-facts.md (774 lines) | facts about Claude apps; cited by almost every skill, script, Pult | unclear (U1) | shared reference, one writer |
| messages.md | kinds of messages between sessions | dev-kit | session protocol; the rules plugin's retro sends ГОТОВО/ПИТАННЯ (file read cross link) |
| slots.md | fixed process steps and slot table | dev-kit | process |
| migrations.md | project-level change list | dev-kit | process |
| releases.json | critical/routine mark per dev-kit version | dev-kit | Pult restarts leads by it; rules/limits need own marks (U11) |
| no-remote-control.json | settings file for background sessions started without Remote Control | unclear (U12) | used by retro.py to start retro/docs sessions and by dev-kit leads |
| api-prices.json | price table for the API client | unclear (U3) | goes with api_client.py |
| README (repo README.md, "Develop" commands) | install and check commands | dev-kit | repo level; needs the new plugins listed. No README inside plugins/dev-kit |
| docs/standards/plugin-authoring.md | how skills and agents are written | rules | a rule on writing rules |
| docs/tech/hooks.md | hooks description | SPLIT | each hook's section to its plugin |
| docs/tech/api-spend.md and features log-and-reconcile-api-spend.md | API spend log rules | unclear (U3) | as api_client |
| docs/features/state-cost-as-a-share-of-the-weekly-limit.md, docs/findings/token-weights-and-weekly-limit.md, idle-wake-cost.md | spend as share of limit; weights | limits | limits topic |
| docs/features/fix-agent-problems-in-the-retro.md | retro rules | rules | retro |
| docs/features/keep-claude-app-facts.md | facts file rules | unclear (U1) | as facts |
| docs/features/tidy-the-docs-once-a-week.md | weekly docs session | dev-kit | docs upkeep (U6) |
| tools/lint.py, tools/tests/* | repo lint and tests of all plugins | SPLIT | tests move with their scripts (test_retro: rules+limits, test_usage_forecast: limits); lint stays repo-level but imports dev-kit code (see code imports) |

## 7. Pult parts that touch limits or rules

| Part | What it does | Target | Reason |
|---|---|---|---|
| pult/rules/hub.md, "Answering статус", line 27 and 220 | runs `dev-kit-retro critical` for token problems | SPLIT: pult + limits | pult keeps the status page; the command becomes a limits command. New line wanted: list of retro fixes from rules (plan, passive list) |
| pult/rules/hub.md as a rule file | the hub's own rules | pult (subscriber of rules) | its rules are reviewed by the rules plugin |
| pult/scripts/watch-servers.ps1, weekly forecast block (header 119-125, code 1288-1310) | runs `usage_forecast.py check`, sends one push | SPLIT: pult + limits | watcher and push stay pult; the script it calls and the log it reads are limits |
| pult/scripts/watch-servers.ps1, LIMIT stop/resume block, plugin update restart block | resumes sessions after a usage-limit stop; restarts leads on a new version | pult | monitoring; uses dev-kit `sessions.py limited`, releases.json |
| pult/scripts/plugin-versions.ps1, restart-leads.ps1 | read plugin versions, restart leads | pult | monitoring; must learn rules and limits versions (U11) |
| pult/scripts/resume-lib.ps1, start-servers.ps1, start-session.ps1, stop-servers.ps1, servers.psd1 | start/stop leads and sessions | pult | monitoring; resume-lib calls dev-kit `dev-kit-bans` by path |
| pult/scripts/list-sessions.py, status-page.py | list desktop sessions, status page | pult | monitoring |
| pult/hooks/hub-rules.py + hooks.json | gives hub.md to a session in the home folder; resolves `{DEVKIT}` | pult | needs a similar `{LIMITS}` / `{RULES}` placeholder if hub.md calls their commands |
| pult/README.md, .claude-plugin/plugin.json | docs and manifest | pult | own plugin |

## 8. Unclear parts and options

- U1 Claude app facts (claude-facts.md, facts-keeper, keep-claude-app-facts.md). (a) stay in dev-kit (agreed 2026-11-24 in the plan; 53+ references by path, Pult rules and scripts cite `{DEVKIT}/claude-facts.md`); (b) move to rules: the retro feeds it and the keeper is an agent that edits a rule-like file, but the file holds facts, not rules, and moving breaks all those paths; (c) own tiny plugin: clean but a fifth plugin. Retro only passes findings in (a).
- U3 API money client (api_client.py, dev-kit-api, api-prices.json, api-spend docs, lead's weekly "API credit check", manager "Claude API calls"). (a) limits (spend of any kind in one place; owner's words "limits plugin: weekly limit and per-session token spend" do not name API money); (b) stay dev-kit (used by agents' own calls, other projects append the same log line); (c) limits renamed to "spend". Needs the owner's pick.
- U4 BACKLOG intake of plugin changes from other projects (manager "A change to the plugins themselves", lead "Plugin backlog"). (a) dev-kit (it is how agents reach the plugin repo); (b) rules (plugins' rules are the rules plugin's subject; but it also covers code defects).
- U5 Small rule edit by P and process-mistake fixes (no dedicated file; they run lead + edit-rules, project-lead 1045-1073, manager 281, owner's global process-mistakes doc outside the repo). (a) dev-kit lead flow calls rules:edit-rules; (b) fully rules.
- U6 Docs upkeep session («Документація:»): skill is dev-kit, but its start, state (`docs_started`, `docs_done`, `docs-items/`) and "wait for the retro's merge" live in retro.py. (a) dev-kit gets its own small start hook and state, loses the wait on the retro (or reads a rules data file); (b) docs session stays started by rules (keeps the order, keeps the coupling).
- U7 dev_kit_state.py (64 lines, project state folder name, main checkout). Used by sessions, run_app, retro. (a) copy into each plugin that needs it (same hash rule, the Pult watcher already reproduces the folder name by convention); (b) rules plugin computes its own folder by git; (c) dev-kit exposes `dev-kit-sessions state-dir` for others to call.
- U8 Usage-limit stop detection and resume (sessions.py `usage_limit`/`limited`, watcher LIMIT block). (a) dev-kit + pult (it is session health); (b) limits (it reads the same Claude limit notice). Recommended (a).
- U9 Guard hooks (narrow-agents, long-commands, windows-traps). (a) dev-kit (guards of agent work); (b) rules (they enforce rules; retro says "ignored rule: use a hook"). Recommended (a).
- U10 owner-session-note hook: one hook, two jobs. Split into two hooks (dev-kit note, rules due-line). Not really open, a required split.
- U11 releases.json and plugin version restart logic. (a) each plugin has its own releases.json and Pult watches all; (b) rules and limits releases never restart leads (cannot hurt a lead) so no marks.
- U12 no-remote-control.json: copy into rules (it starts retro sessions) or a call to dev-kit. Smallest: copy.

## 9. Cross-plugin links after the split

Code imports today that cross the new borders (must become none):

1. `retro.py:227` `import statusline` (SAME_WINDOW_S, log_file, number; lines 291, 1715-1738): becomes limits-internal once fit code moves with it. Not a problem if the fit code goes to limits. Remaining link: rules reads spend numbers as evidence: use limits' data file or CLI, not import.
2. `retro.py:226` `import dev_kit_state` (folder_name, main_checkout; lines 476-490): rules -> dev-kit. Flag: stays a code import unless copied (U7).
3. `retro.py:1613` and `retro.py:1665` `import sessions` (`find_claude`, to start retro and docs sessions): rules -> dev-kit code import. Flag: copy `find_claude` (~25 lines, `claude_candidates`) or call a dev-kit command.
4. `sessions.py:1453` `import retro` (`read_new_lines`, `units_of` in `size`, lines 1450-1472): dev-kit -> retro/limits code import. Flag: must go through a limits CLI or a copy of the weights; weights also live in `retro.WEIGHTS`.
5. `owner-session-note.py:46` `import retro` (`due_line`) in a dev-kit hook: dissolves by splitting the hook (U10).
6. `usage_forecast.py:33` `from statusline import ...`: limits-internal after the split, fine.
7. `tools/lint.py:10-12` imports `check_docs`, `migrations`, `run_app` from dev-kit scripts: repo tool -> dev-kit code import. Flag: stays an import unless lint calls the bin commands or lives in dev-kit.
8. `tools/tests/test_retro.py`, `test_sessions.py`, `test_usage_forecast.py`, `test_run_app.py`: import modules; they follow their scripts, but test_sessions touching `size` crosses (link 4).
9. Inside dev-kit only, stays fine: `long-commands.py` loads `windows-traps.py`; `run_app.py`, `sessions.py` import `dev_kit_state`; `hooks` add `scripts/` to sys.path.
10. Inside retro the single `analyse` pass mixes findings and token units (lines 690-820): cutting it makes either a double read of transcripts or a shared data file. Design point, not an import.

File reads and data files shared across plugins:

- `usage-log.jsonl` (limits writes via statusline; limits forecast and fit read; the Pult watcher reads path `~/.claude/dev-kit/usage-log.jsonl`, watch-servers.ps1:1291). Folder name `dev-kit` in `~/.claude` stays or moves; Pult hardcodes it.
- Retro state folder `~/.claude/dev-kit/retro` holds `state.json` with token stats, the fit and `critical` shown shares: split into a rules state and a limits state.
- Per-project folder `<repo>-<10 hex>` (sessions.json, app.lock, retro items): same naming rule in three places (dev_kit_state.py, retro, Pult PowerShell).
- `messages.md`: the retro skill reads `${CLAUDE_PLUGIN_ROOT}/messages.md`; in the rules plugin that path points to the wrong plugin. Fix: path to dev-kit or a copy of the kinds the retro sends.
- `releases.json` read by watch-servers.ps1 and `sessions.py release`; `plugin.json` versions read by Pult (`DevKitDir` sibling layout, `..\..\dev-kit`, plugin-versions.ps1 already handles extensions).
- `claude-facts.md` read by hub rules, cited in comments of Pult scripts, in skills and in hooks docs (path `{DEVKIT}/claude-facts.md`, found by hub-rules.py as a sibling folder or newest cache version with `bin/dev-kit-sessions`).
- `no-remote-control.json` (U12), `.claude/dev-kit.md` project profile (read by dev-kit scripts, retro for project detection `## project-lead`, check_docs, run_app): the profile is a shared data file; rules plugin reads its `## project-lead` section to know a retro project. Keep the file name or add subscription files.
- Pult watcher state folder read by dev-kit `sessions.py restart` (request files) and written by Pult: existing dev-kit <-> pult data link, unchanged.

Skill and command calls:

- dev-kit -> rules: `dev-kit:edit-rules` (documentation, project-lead, manager, migrate-docs, maintain-project-docs, coder, mechanical-editor), plus pointer to `dev-kit-retro add`. Instruction text will name `rules:edit-rules`.
- rules -> dev-kit (cycle dev-kit <-> rules): retro skill and edit-rules call `dev-kit:reviewer`, `dev-kit:investigator`, `dev-kit:coder`/`mechanical-editor`; the retro's session follows the lead's "Acceptance and merge" and the `ГОТОВО` message of messages.md; `/dev-kit:maintain-project-docs weekly` started from the rules hook. dev-kit uses rules and rules uses dev-kit agents: one directional dependency is cleaner (agents stay in dev-kit, rules depends on dev-kit; dev-kit only names `edit-rules` in text).
- pult -> dev-kit: `dev-kit-sessions`, `sessions.py`, `dev-kit-bans`, `releases.json` by path. pult -> limits: `usage_forecast.py check` by path, `critical` command. pult -> rules (new): list of retro fixes for «статус».
- dev-kit -> limits: lead's "Stating the cost" and task spend lines call the `session` command; `sessions size` (link 4).
- Any project session -> rules: `retro add --project ClaudeDevKit` (facts, findings) from claude-facts.md and the retro skill.
- Every project settings file points the status line at `dev-kit-statusline` (user settings, assumed; grep of README found no `statusLine` entry): path changes to the limits plugin.
