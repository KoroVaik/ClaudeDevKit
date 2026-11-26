# Plan: projects edit web-kit and unity-kit directly

Status: in discussion (2026-11-26).

Owner's words: «давай надамо проектам які юзають плагіні веб і юніті можливість редагування напряму, щоб ти не займався цим. У сесій цих проектів кращий контекст специфіки роботи. ЗАпусти обговорення» (L: ClaudeDevKit chat, 2026-11-26).

Today: agents in other projects never edit the plugins; they add BACKLOG.md entries and the plugin repo's own Lead builds them (`plugins/dev-kit/skills/manager/SKILL.md`, "A change to the plugins themselves"; `plugins/dev-kit/skills/project-lead/SKILL.md`, "Plugin backlog" and "Small rule edit"; the owner's global rule «Stay in the session's project» and the `other-repo-editor` helper). web-kit and unity-kit live in this repo under `plugins/web-kit`, `plugins/unity-kit`; releases, version bumps and release marks follow `.claude/dev-kit.md` of this repo; the Pult watcher restarts leads on bumps.

Success criterion: an «Owner's approval» section here with every agreed point in builder detail, and the owner's «так» to the short plan.
