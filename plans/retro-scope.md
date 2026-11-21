# Retro across projects

## Owner's words
- 2026-11-21: «зараз ретро діє тіки в самом девкіт проекті?»
- P answered: the retro is started only by the lead of ClaudeDevKit, but its scan reads the sessions of every project on this machine (Zhratva, Prishch, Pult too); findings are handled here because the rules live in the plugin.
- Owner: «запускай оьговрення»; on P's two readings he chose «2»: a new discussion about the retro, for example so that it does not run only from ClaudeDevKit.

## Facts checked by P
- `plugins/dev-kit/scripts/retro.py`: transcripts are every `*.jsonl` under `~/.claude/projects` (or env DEV_KIT_PROJECTS_DIR), so all projects.
- `plugins/dev-kit/skills/project-lead/SKILL.md`, «Retro of session problems (plugin repo only)»: only P of ClaudeDevKit runs `dev-kit-retro check`, the gate reviewer and the retro.
- Rule fixes for the plugin go to this repo; another project's own rules (its CLAUDE.md, .claude/, docs) are that project's.

## Success criterion
The owner approves, in an «Owner's approval» section of this file, what should change about where and by whom the retro runs and how findings about other projects reach a fix, and the short plan.

## Owner's approval
(not yet)
