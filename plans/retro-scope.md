# Retro across projects

## Owner's words
- 2026-11-21: «зараз ретро діє тіки в самом девкіт проекті?»
- P answered: the retro is started only by the lead of ClaudeDevKit, but its scan reads the sessions of every project on this machine (Zhratva, Prishch, Pult too); findings are handled here because the rules live in the plugin.
- Owner: «запускай оьговрення»; on P's two readings he chose «2»: a new discussion about the retro, for example so that it does not run only from ClaudeDevKit.
- Owner, in this discussion: «по ідеї ретро сесій це взагалі можна зробити окремим плагіном... абсолютно інший функціонал, який аналізує любі сесії навіть ті що без девкіта».
- Checked here: the scan already reads sessions without dev-kit (BlenderSandbox, the home folder, Documents among 157 project folders); dev-kit ties are who starts it (P of ClaudeDevKit) and where fixes go.
- Owner: «зараз всі ретро відбуваються тіки для покращень девкіта, але ігнорують проблеми конкретних проектів. А проблем там предостатньо які можна виправить».
- Checked: holds. `skills/retro/SKILL.md` step 1 gives the reviewer only the plugin folder and the global rules, never the project's own rules, docs or code. The project-rule route (other-repo-editor into that project's `BACKLOG.md`) exists on paper, but no `BACKLOG.md` of Zhratva, Prishch, KnowledgeBase or Zhratva-design-sandbox mentions a retro.

## Facts checked by P
- `plugins/dev-kit/scripts/retro.py`: transcripts are every `*.jsonl` under `~/.claude/projects` (or env DEV_KIT_PROJECTS_DIR), so all projects.
- `plugins/dev-kit/skills/project-lead/SKILL.md`, «Retro of session problems (plugin repo only)»: only P of ClaudeDevKit runs `dev-kit-retro check`, the gate reviewer and the retro.
- Rule fixes for the plugin go to this repo; another project's own rules (its CLAUDE.md, .claude/, docs) are that project's.
- Owner: «я думаю що ретро приноситиме мало користі в сесіях, які не структуровані як ті що запускаються з допомогою дев кіта».
- Checked: holds. The scan files of 2026-11-19..21 (`~/.claude/dev-kit/retro/scan-*.md`) name only dev-kit projects: Zhratva most (138 mentions), ClaudeDevKit 71, Pult 16, Prishch 10; none from BlenderSandbox, the home folder or Documents. So a separate plugin for non-dev-kit sessions has little to work on; the gap is the project problems of dev-kit projects.

## Success criterion
The owner approves, in an «Owner's approval» section of this file, what should change about where and by whom the retro runs and how findings about other projects reach a fix, and the short plan.

## Owner's approval
- 2026-11-21, «так»: the retro stays in dev-kit (no separate plugin) and is extended so that it fixes the problems of the projects themselves, not only the plugin's rules.
- Owner's requirements for that extension (2026-11-21, his words): «виправлятись має в контексті самих проектів з урахуванням їх нюансів»; projects must avoid fixes that will not help later because the problem «рандомно виникнені, а не через погані правила скіли чи агнети». Checked: `skills/retro/SKILL.md` has no repeat test today; its reviewer marks only noise, fixed or handed over.
- 2026-11-21, «так»: retro items live in a folder of item files, one file per item, kept locally (outside any repository, under the retro findings folder `~/.claude/dev-kit/retro/`), one subfolder per project. The scan sorts its findings into the project subfolders; any session may add an item to any project's subfolder, marked with the project it came from; the lead (P) of each project runs the retro over its own subfolder, with that project's rules, docs and code in view, and may pass an item to another project's subfolder (owner expects that to be rare). A problem in dev-kit's own rules still goes as an entry in ClaudeDevKit's `BACKLOG.md`. Why local and one file per item: writes into a project's main checkout are blocked for P (`skills/project-lead/SKILL.md`, «Small rule edit»), items on unmerged branches would be lost, the scan from ClaudeDevKit would write into other repositories, and two sessions writing one shared file can overwrite each other.
- Still open (owner, 2026-11-21): automate the retro so the owner reviews only disputed items; let retros record decision items that other projects' retros take into account (reuse of experience), with a way to keep their number manageable over time. The repeat test (a fix only when the same cause recurs in different sessions) and the 2-week expiry of one-off items (lost work fixed at once) for one-off causes has no explicit yes yet.
- 2026-11-22, «так»: scope - the retro catches every problem of agent work and only that. A bug in a project's code is not fixed by the retro; it is handed to that project as a bug (its backlog) and the retro stops there. A project's own rules or docs that make agents err (an outdated doc that sends agents to the wrong file) are agent work and stay in the retro. Example of the line: a flaky test in Zhratva is a code bug; an agent that keeps opening the wrong file because of an old doc is a retro item.
- 2026-11-22, «так», five additions:
  1. Items whose cause is the owner's global rules (`C:/Users/korov/.claude/`, chat style included) are handled only by the ClaudeDevKit lead, so two projects never ask the owner the same thing.
  2. The reviewer tells «no rule» from «the rule exists but agents ignore it»; an ignored rule is not reworded again, it needs another means (for example a hook or a check).
  3. The retro works only on dev-kit projects (owner, 2026-11-22: «ретро діє виключно на проекти з девкітом»); sessions outside them (BlenderSandbox, the home folder, Documents) are skipped by the scan. Little is lost: the scans of 2026-11-19..21 had no finding from such sessions, and global-rule problems show up in dev-kit sessions too.
  4. Every rule fix also removes or merges something, so the rules do not keep growing.
  5. The check whether a change worked looks only at sessions started after that change.
- 2026-11-22, «так» to all of the following: the simpler variant (one retro run from ClaudeDevKit that sees each project's rules, sorts items into project folders, filters one-offs); the check of every plugin change by reading later sessions (worked / did not / not met yet); the owner gets only truly disputed items, high-impact ones and anything about how sessions talk to him, the reviewer decides trivial ones; spend-trial results become ordinary retro items; the check runs daily as a separate background session started by the ClaudeDevKit lead; weekly the lead asks «розібрати N пунктів?», after a «ні» it asks again next day; urgent items reach the owner at once.
- How (rest of the design): not yet agreed.

## Proposed design (superseded 2026-11-22; the agreed points are in «Owner's approval»; kept only as history of the talk)
Reviewer's critique of this draft (2026-11-22): auto-applied fixes contradicted the owner's 2026-11-19 decision (nothing reaches a rule without his «так», `skills/retro/SKILL.md:107-109`), and the real data had almost nothing to auto-fix (2 real findings of 98 on 2026-11-21, one of them an ignored rule).
Goal (owner, 2026-11-21): a self-sufficient process with the owner's part kept to a minimum.
1. The scan runs once a day, started by any live lead (P) of any project; it reads every session on the machine (sessions the owner opens without a lead too) and sorts findings into each project's item folder.
2. Each project's P runs the retro over its own folder in the background: a reviewer decides each item with that project's rules, docs and code in view.
3. Clear items (exact cause with file:line, one-place edit, same cause in 2+ sessions) are applied at once as a trial, with no owner. A fix after which the same cause comes back is rolled back automatically and becomes disputed.
4. Always to the owner (disputed): anything that changes what the owner sees (his messages, questions), his global rules, deleting a rule, a new script, hook, agent or skill, and anything the reviewer is unsure about.
5. Priority: urgent = lost work, big token spend, blocked work, or a cause repeating the same day. An urgent clear item is fixed the same day; an urgent disputed item goes to the owner at once as one question. Ordinary items wait for one weekly message to the owner: the disputed items plus a list of the auto-fixes, each revertable with one word.
6. The fewer auto-fixes the owner reverts, the more the retro decides by itself (start strict, loosen over time).
7. Decision items: every retro decision (a «no, the rule is not to blame» too) becomes a local file with a short cause key; another project's retro reads only the list of keys and opens the matching decisions. A decision that worked in 2 projects becomes a dev-kit rule and its file is deleted. A first sighting is only recorded; a fix needs a repeat and a named rule gap; lost work and big spend are fixed on first sight.
Known weak spot: a project's retro runs only while its P is live; with P closed for days its items, urgent ones too, wait.
