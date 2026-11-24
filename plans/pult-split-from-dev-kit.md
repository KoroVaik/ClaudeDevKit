# Separate Pult from dev-kit

Owner's words (2026-11-24, P: ClaudeDevKit chat): «Я ще думаю над тим щоб відокремить пульт від дев кіт лпагіна. Обговорення».

Pult is already its own plugin (`plugins/pult/`), but its watcher and hub use dev-kit parts (the sessions registry `dev-kit-sessions`, lead rules, events to leads). Same principle as the rules-kit / spend-kit split (`plans/retro-auto-rules-check.md`, «Owner's approval»: one clear responsibility per plugin, no plugin imports another's code).

Goal: agree with the owner what «separate» means (what Pult owns, what dev-kit owns, how they talk) and whether it is worth doing.

Success criterion: the owner's «так» to the short plan; the agreed points in «Owner's approval» here.

## Owner's approval

Owner «Так», 2026-11-24, «Обговорення: Відокремлення пульта від dev-kit», to «Лишаємо пульт розширенням dev-kit, без розділення? (будувати нічого не треба)».

1. **Pult is not separated from dev-kit.** Pult stays an extension of dev-kit, not a standalone plugin for
   projects without dev-kit: it starts and heals dev-kit project leads, runs `sessions.py` /
   `dev-kit-sessions` / `dev-kit-bans`, imports `dev_kit_state` (`watch-servers.ps1:973`) and reads
   `~/.claude/dev-kit/<repo>-<hash>/sessions.json`. These links stay as they are; the rules-kit / spend-kit
   "no plugin imports another's code" rule does not apply between Pult and dev-kit. Nothing is built.
2. **The owner's one problem has its own plan.** His reason to think of a split was that he does not see a
   project's background (C) sessions. That comes from how dev-kit starts a C (no Remote Control), not from
   Pult; it is decided in [plans/c-session-visibility.md](c-session-visibility.md) «Owner's approval».

Checked: a read-only map of every Pult - dev-kit link (both directions) found no owner-visible problem caused
by the coupling; the cost is only that the two plugins are released together.
