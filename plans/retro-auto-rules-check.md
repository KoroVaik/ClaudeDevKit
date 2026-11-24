# Retro: full automation and a rules check per plugin

Owner's words (2026-11-24, P: ClaudeDevKit chat), on BACKLOG «Retro: one-off items expire»: «Давай 4. Подумай як покращить ретро і внесеш ці зміни. Головне це максимальна автоматизація процесу, щоб юзер не звертав уваги на процес самоаналізу сесій. Також потрібно буде подумати щодо того щоб ретро проводилось для якогось конкретного скоупу правил. Тобто перевірка правил виходить, а не перевірка контексту сесії. Тобто кожен плагін матиме свого перевіряльника доцільності його правил і тд».

Links: `docs/features/fix-agent-problems-in-the-retro.md`, `plugins/dev-kit/skills/retro/SKILL.md`, `plugins/dev-kit/scripts/retro.py`, BACKLOG.md «Retro: one-off items expire» and «Retro: decision items reused across projects».

P's note: whether a rule is worth keeping shows only in how it worked in sessions, so a rules checker still needs session evidence; settle in the talk.

Success criterion: the owner's «так» to the short plan; the agreed points written in «Owner's approval» here or in the feature file.

## Owner's approval

2026-11-24, «Обговорення» session, owner «Так» to the short plan «Плагіни rules-kit і spend-kit»:
1. The retro becomes the plugin rules-kit, responsible for everything about rules: how to write them and how to improve them. dev-kit, web-kit, unity-kit, pult, the owner's global rules and each project's own rules subscribe to it.
2. rules-kit splits sessions into parts, finds the rule line behind a problem and checks each rule type its own way; subscriptions add signs themselves when they miss a problem.
3. The owner is asked nothing: an independent agent approves every change, it is replayed on past sessions, a failed change is reverted by the retro itself, and everything done is a list in Pult's «статус».
4. The new plugin spend-kit takes everything about Claude spend: weekly limit, per-session spend, API money and all their clients; other plugins only read its files.
5. dev-kit stays the development-process plugin, and no plugin imports another's code.

The points below are the agreed detail for the builders; a later line wins over an earlier one where they differ (e.g. token counting moves to spend-kit, not dev-kit). The BACKLOG entry «Retro: one-off items expire» is covered by the 2-week expiry below and is removed when built; «Retro: decision items reused across projects» stays an idea.

- 2026-11-24, owner «Звучить ок» to: retro items are kept in one folder per rule set, not per project (web-kit has one folder although it runs in three projects); Claude app facts stay in dev-kit, the retro only passes findings there.
- 2026-11-24, owner «Ну окей»: each set's subscription names the project that reviews it, the one where its files are edited; today ClaudeDevKit reviews all four plugins and the owner's global rules.
- 2026-11-24, owner «Ок» (reverses the 2026-11-21/22 «retro stays in dev-kit»): the retro becomes its own plugin; dev-kit, web-kit, unity-kit, pult and the owner's global rules subscribe; one subscription file per set lists its files, what to look for in sessions and what the agent may change itself; each file belongs to one set, the one it lives in, other sets' files are read only for context; a finding that fits no set goes to the project's own retro.
- 2026-11-24, owner «Так»: a subscription file is a file of its set and is reviewed with it. A rule that caught nothing for weeks: an agent reads a few sessions and decides whether the rule is unneeded or the tracking is blind. A problem found by the general signs (owner correction, failed command) and laid to a file of a set the subscription missed: the agent adds a new sign to the subscription itself.
- 2026-11-24, owner «Так»: the subscription marks each rule with a type (talk with the owner, technical, process), each tracked its own way. Talk rules are checked by the script in every reply to the owner with no model and no owner correction needed (length, dashes, language, «так»/«ні» first); technical rules by tool traces (calls, failures, repeats); process rules by an agent reading the session part.
- 2026-11-24, owner «Так»: the script with no model splits a session into parts by the skill, agent or hook at work then (a problem after a discovery-round call has dev-kit as a candidate); a cheap agent, shown only that part and the candidate sets' files, names the file and line at fault or «not a rule».
- 2026-11-24, owner «Так»: no weekly «розібрати N пунктів?» question; the retro applies fixes itself and reverts a fix that later sessions show did not work; the owner is asked only about deleting a rule file or changing how sessions talk to him.
- 2026-11-24, owner «Так»: a finding seen once, not urgent, that does not recur in 2 weeks expires by itself (closes BACKLOG «Retro: one-off items expire»). The owner's global rules are checked in the sessions of every project, those without a lead too. Token spend counting stays in dev-kit (it is shared with the status line); the retro takes its numbers only as evidence.
- Checked 2026-11-24 in the last 30 ClaudeDevKit transcripts: skill calls (skill name), agent calls (`subagent_type`) and hook events are recorded, so the script can split a session by them; a hook event names its event type, the hook's plugin comes from its command path.
- Kept from today's retro: a fix needs a repeat (lost work and critical token problems are fixed at once); every fix also removes or merges something; each fix is checked by later sessions.
- 2026-11-24, owner «Ок» to the reviewer's (opus investigator) points: after a revert one more try by another means (a hook, a script), then the cause goes to the owner; a repeat counts only in sessions started after the fix's merge into main (running sessions keep old rules); only the owner changes the «may change itself» part of a subscription, the agent may still add signs; the agent reads only session parts with a sign and each run's spend is capped as a share of the weekly limit; fixes the retro made are listed in Pult's «статус», with no question.
- Builder notes (method, from the same review): each fix is its own commit so a revert is one `git revert`, and new findings in the edited files are linked to that fix as possible breakage; a skill started by a slash command counts as at work like a Skill call; the cheap agent gets the matching rule lines, not whole files; fix the `retro.py:798` defect (subagents summed by type) before splitting by agent; keep from today's retro: the retro's and docs sessions' own findings are skipped, at most 5 trivial fixes a week per set, a second reviewer for unsure lines, the noise classes, new hooks/scripts/agents/skills always to the owner, code bugs handed over as defects, urgent items at once, the docs session waits for the retro's merge; the retro plugin subscribes itself, reviewed by ClaudeDevKit.
- 2026-11-24, owner «Так» («Мінімізуй мою участь, я всеодно буду бездумно апрувать. Краще додай більш надійні верифікації»): the retro asks the owner nothing; this replaces every owner ask above (deleting a rule file or a rule, changes to how sessions talk to him, the «may change itself» part of a subscription, a cause after the second failed try, always-loaded files). In their place three checks: (1) an independent agent on another model approves every change before it lands, rule deletions and subscription permissions included; (2) before it lands the change is replayed on past sessions where the problem was (does it cover it) and on sessions that went well (does it break them); (3) a change that later sessions show did not work is reverted by the retro itself, after the second failed try the cause is parked and shown in Pult's «статус». Everything the retro did is in that passive list; the owner may say «поверни» any time. Weak spot accepted: an agent checking an agent may share its blind spots; a bad change to talk rules shows only in chat.
- 2026-11-24, owner (principle): every part goes to its place with one clear responsibility now, nothing left in a plugin only to save rework. The retro plugin is the rules plugin: writing and improving rules (retro, the edit-rules skill, checkers, subscriptions); dev-kit uses it.
- 2026-11-24, owner «Давай так» (replaces «token counting stays in dev-kit» above): the weekly limit (status line, usage log, forecast) and per-session token spend move into a separate plugin for Claude spend; the Claude API money client (`dev-kit-api`, its spend log, prices) moves there too; dev-kit, pult and the rules plugin only read its data files. Project rules (a project's CLAUDE.md and its agent docs) are a set of their own, reviewed by that project.
- Placement by the principle (both reviewers agree, 2026-11-24): the rules plugin owns its checker agents and calls no dev-kit agents; each subscription says how a change lands in its set (who merges, version bump, release mark, a special editor agent such as facts-keeper), so the dependency runs one way, dev-kit to rules. Spend findings (long session, opus coder) are rule findings in the rules plugin; the spend plugin only counts. Claude app facts and facts-keeper stay in dev-kit; BACKLOG intake and process-mistake flow stay in dev-kit and call the rules plugin's edit-rules; the weekly docs upkeep stays in dev-kit with its own start hook and state. No plugin imports another's code: a per-session spend file written by the spend plugin replaces `sessions.py` and `owner-session-note.py` imports of `retro`; `owner-session-note` splits in two; each plugin has its own `releases.json`; the rules plugin is enabled at user scope and finds projects by subscriptions, not by `.claude/dev-kit.md`; Pult's usage-log path follows the spend plugin. Full map (first agent; the placement line above wins where they differ): plans/retro-auto-plugin-split-map.md.
- 2026-11-24, owner «Так»: names spend-kit (Claude spend: weekly limit, per-session spend, API money, every client and price table of it) and rules-kit (writing and improving rules, the retro). «Нехай переїдуть туди всякі клієнти, короче все що цього стосується»: anything about Claude spend found in any plugin moves to spend-kit.

## Build steps

Builder: C «rules-spend-kit» (branch `c/rules-spend-kit`). Each step is one or more commits that leave lint and
tests green; doers are `dev-kit:coder` (sonnet; opus for step 4-5 engine) with the manager checking the diff and
rerunning the checks. Rule text goes through `dev-kit:edit-rules` (step 3 of that skill: the owner's approval above
covers the behaviour lines; anything beyond it goes to P).

Spend: ~0% of the weekly limit, estimate; API: 0 USD (updated at each step).

Design choices (manager, within the approval):
- Folders `plugins/spend-kit`, `plugins/rules-kit`, each with its own manifest, `releases.json`, `bin/`, hooks and
  tests; both enabled at user scope (bins on PATH in every project). Data folders `~/.claude/spend-kit/` and
  `~/.claude/rules-kit/`; each moves its old files out of `~/.claude/dev-kit/` once, on first run.
- Commands: `spend-kit` (session, critical, calibrate, forecast, per-session spend file), `spend-kit-api` (was
  `dev-kit-api`, same subcommands and log line), `spend-kit-statusline`; `rules-kit` (was `dev-kit-retro`: scan,
  items, done, add, list for Pult, revert bookkeeping).
- No code import across plugins: other plugins read spend-kit's per-session spend file
  (`~/.claude/spend-kit/sessions/<session id>.json`) or run its command; rules-kit keeps its own copies of the
  state-folder naming, `find_claude` and `no-remote-control.json`.
- Subscription file `rules-subscription.md` at the root of each set: each plugin folder, the owner's global folder
  (`C:/Users/korov/.claude/`, a local git repo, so a revert is `git revert` there too) and, optionally, a project's
  `.claude/` (a project with a dev-kit profile and no file gets the default project set: `CLAUDE.md`, `.claude/`
  rule files, its agent docs).
- The weekly «Документація:» start and state move to a dev-kit hook; it waits for the retro by reading rules-kit's
  run file, not its code. The `retro: N due` line of the lead's prompt hook goes away (no owner asks).
- After merge, P runs `python -X utf8 tools/enable-rules-spend-kit.py` once (enables both plugins at user scope,
  points the status line at spend-kit); the status line and the retro stop until it runs, so it is part of the
  merge.

1. spend-kit: plugin skeleton; move `statusline.py`, `usage_forecast.py`, `api_client.py`, `api-prices.json`, their
   bins, docs and tests; move token units, waste, session spend, `critical`, weekly-limit fit and calibrate out of
   `retro.py`; write the per-session spend file; `sessions.py size`, `retro.py` and Pult (watcher forecast, hub
   `critical`, usage-log path) read spend-kit; rename `dev-kit-api` / `dev-kit-retro session|critical` in all text.
2. rules-kit move: plugin skeleton; move the retro (script minus spend, skill, start/end hooks, feature doc) and
   `edit-rules`; own checker agents (reviewer sonnet, approver opus, part reader haiku); docs-session start to
   dev-kit; rename `dev-kit:edit-rules` to `rules-kit:edit-rules` everywhere; fix the `retro.py:798` defect.
3. Subscriptions and per-set items: file format and parser; files for dev-kit, web-kit, unity-kit, pult,
   rules-kit, spend-kit, global rules, default project set; items in one folder per set; old items migrated by the
   set of the files they name, else the project's set.
4. Session parts and rule-type checks: split a transcript by skill, agent, hook (slash-command skills included);
   talk rules checked by script on every reply to the owner; technical rules by tool traces; process rules by the
   part reader on parts with a sign; a missed problem laid to a set adds a sign to its subscription.
5. The autonomous fix loop: approver on another model, replay on past problem and good sessions, one commit per
   fix, revert by `git revert` when later sessions show it failed, a second try by other means, then parked;
   2-week expiry of one-offs; spend cap per run; done list for Pult «статус»; lead and Pult rules lose every
   retro ask.
6. Wiring: marketplace, README, map and feature docs, version bumps with release marks, the enable script,
   BACKLOG «Retro: one-off items expire» removed, pull main, final review.

### Subscription file format (step 3)

`rules-subscription.md` at a set's root, Markdown the script parses (tables only; prose is for readers):

    # Rules subscription: <set name>

    | Setting | Value |
    |---|---|
    | set | dev-kit |
    | reviewed by | ClaudeDevKit |
    | lands by | branch merged by P: ClaudeDevKit; bump plugins/dev-kit version with a release mark |
    | special editor | plugins/dev-kit/claude-facts.md: dev-kit:facts-keeper (the retro passes findings, never edits) |

    ## Files

    | Path (glob, relative to the set root) | Type | Part kinds |
    |---|---|---|
    | skills/project-lead/SKILL.md | process | skill dev-kit:project-lead |
    | hooks/*.py | technical | hook dev-kit |

    ## Signs

    | Sign | Kind | Pattern |
    |---|---|---|
    | owner corrects | talk | owner message matches «не так|я ж казав|\?\?\?» |

    ## May change itself

    | Path | Changes |
    |---|---|
    | skills/** | word, sentence, new sign |

Types: `talk` (how sessions talk to the owner; script checks every reply), `technical` (tool traces: calls,
failures, repeats), `process` (part reader on parts with a sign). Part kinds name the skill, agent or hook whose
part of a session makes the set a candidate. The general signs (owner correction, failed command, repeat) live in
rules-kit itself and apply to every set; a set's own signs add to them. The global set's root is
`C:/Users/korov/.claude/` (`CLAUDE.md`, `docs/*.md`); a project's root is its repo (`CLAUDE.md`, `.claude/**/*.md`).

### Progress

- Step 1 built (spend-kit). Left for step 6: `api-calls.jsonl` and `credits.md` still live in `~/.claude/dev-kit/`
  (other projects' programs append to that log by path); move them with a read of both paths during the switch.
- Step 2 built (rules-kit move; dev-kit owns the weekly docs start, reads `~/.claude/rules-kit/runs/<folder>.json`).
  At merge, through `rules-kit:edit-rules`: the owner's global `docs/process-mistakes.md` lines 11, 13, 15 still
  name `dev-kit:edit-rules`, `~/.claude/dev-kit/retro/notes.md` and `dev-kit:retro` (the notes path matters: the
  retro now reads `~/.claude/rules-kit/notes.md`). Step 5 removes the lead's retro ask text in `project-lead` and
  the feature doc.
