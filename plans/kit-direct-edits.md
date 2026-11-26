# Plan: projects edit web-kit and unity-kit directly

Status: agreed, owner «так» to the short plan (2026-11-26). Next: build.

Owner's words: «давай надамо проектам які юзають плагіні веб і юніті можливість редагування напряму, щоб ти не займався цим. У сесій цих проектів кращий контекст специфіки роботи. ЗАпусти обговорення» (L: ClaudeDevKit chat, 2026-11-26).

Today: agents in other projects never edit the plugins; they add BACKLOG.md entries and the plugin repo's own Lead builds them (`plugins/dev-kit/skills/manager/SKILL.md`, "A change to the plugins themselves"; `plugins/dev-kit/skills/project-lead/SKILL.md`, "Plugin backlog" and "Small rule edit"; the owner's global rule «Stay in the session's project» and the `other-repo-editor` helper). web-kit and unity-kit live in this repo under `plugins/web-kit`, `plugins/unity-kit`; releases, version bumps and release marks follow `.claude/dev-kit.md` of this repo; the Pult watcher restarts leads on bumps.

## Agreed so far

- Direction (owner «так», 2026-11-26): a session of a project that uses web-kit or unity-kit edits and releases that plugin itself; dev-kit and the other plugins stay with L: ClaudeDevKit. Why (owner): «в обговорення тих проектів я часто потребую апдейта відразу, а сесії починають спілкуватись одна з іншой фактично втрачаючи контекст нашой розмови».
- Who edits (owner «так», 2026-11-26): the project session itself, in its own worktree of ClaudeDevKit; it runs the plugin checks (lint, tests) and merges into main. Not the `other-repo-editor` helper (it cannot run checks).
- Review before merge (owner «так», 2026-11-26): an independent helper reviews the rule diff before the merge, as the ClaudeDevKit Lead's "Small rule edit" does today. Owner added: «Чудова ідея що і девкіт перевіряє вкінці валідність апдейту»; asked «1 чи 2?», he chose (owner «так», 2026-11-26) the helper review only: L: ClaudeDevKit does not check the merged change afterwards.

## Owner's approval

Agreed 2026-11-26 in «Discuss:» on direct kit edits. Builders follow every point; rule text is edited through `rules-kit:edit-rules`.

1. Scope. Any session (Lead, Manager, «Discuss:») of a project whose `.claude/settings.json` enables `web-kit` or `unity-kit` may change that plugin (`plugins/web-kit` or `plugins/unity-kit` in `C:/Users/korov/MyRepositories/ClaudeDevKit`) and release it, without a `BACKLOG.md` entry and without L: ClaudeDevKit. Only the kit the project enables. dev-kit, pult, rules-kit, spend-kit and the repo's shared files (`.claude-plugin/marketplace.json`, `tools/`, `docs/` outside the kit's own feature text) stay with L: ClaudeDevKit.
2. How the session edits, in `plugins/dev-kit/skills/manager/SKILL.md`, "A change to the plugins themselves" (named exception to the ban at about lines 290-296), with a pointer from `project-lead/SKILL.md` "Small rule edit" (about line 1097) and "Plugin backlog":
   - a fresh worktree of ClaudeDevKit's main (never the main checkout; the host's worktree guard blocks it), one branch per change;
   - read ClaudeDevKit's `CLAUDE.md` and `.claude/dev-kit.md` first; edit via `rules-kit:edit-rules`; a script change goes to a `dev-kit:coder` (sonnet) as usual;
   - run the repo checks: `python -I tools/lint.py` and `python -I -m unittest discover tools/tests` (`docs/tech/repo-checks.md`);
   - an independent `rules-kit:rule-reviewer` (sonnet) reviews the diff (steps 5-6 of `rules-kit:edit-rules`), as L: ClaudeDevKit's "Small rule edit" does; its confident problems are fixed before merge;
   - bump `plugins/<kit>/.claude-plugin/plugin.json` and add the mark to `plugins/<kit>/releases.json` per `.claude/dev-kit.md` (routine by default; critical or `clean` by its rule);
   - merge `--ff-only` into ClaudeDevKit's main (rebase on a newer main first), push (ClaudeDevKit `Push: auto`), remove the worktree;
   - run `/reload-plugins` in the session so the change works in the same talk at once (fact status "doubtful" in `claude-facts.md`; if it does not take, say so to the owner in one line).
   - No message to L: ClaudeDevKit; it does not check the change afterwards (owner chose option 1). The Pult watcher restarts the leads that enable the kit as it does today; no watcher change.
3. dev-kit part. When the kit change needs a dev-kit change (a slot added or renamed in `plugins/dev-kit/slots.md`, a dev-kit skill, agent or bin it relies on, a profile-section doc), the kit part lands as above only if it works without it; the dev-kit part goes to `BACKLOG.md` as today.
4. The global rule «Stay in the session's project» (local file: `CLAUDE.md` in the `.claude` folder of the owner's user folder) gets a named exception: a project's own kit plugin is edited by the session itself as in point 2, not by `other-repo-editor` and not in its own session.
5. Text that names L: ClaudeDevKit as the only lander is updated: `plugins/web-kit/rules-subscription.md` and `plugins/unity-kit/rules-subscription.md` (about lines 10-11), ClaudeDevKit `CLAUDE.md` (lines 4-6), the `BACKLOG.md` header (line 3), and the feature rule «A project edits its own kit plugin» in `docs/features/hand-work-to-the-project-lead.md` (already written; add the review and dev-kit-part points).
- dev-kit part (owner «так», 2026-11-26): when a web-kit or unity-kit change needs a dev-kit change, the dev-kit part still goes to `BACKLOG.md` for L: ClaudeDevKit.
- Users today (checked `enabledPlugins`): web-kit - Zhratva, Zhratva-design-sandbox, KnowledgeBase; unity-kit - Prishch.

Success criterion: an «Owner's approval» section here with every agreed point in builder detail, and the owner's «так» to the short plan.
