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
- How (rest of the design): not yet agreed.
