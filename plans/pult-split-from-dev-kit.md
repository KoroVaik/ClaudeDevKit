# Separate Pult from dev-kit

Owner's words (2026-11-24, P: ClaudeDevKit chat): «Я ще думаю над тим щоб відокремить пульт від дев кіт лпагіна. Обговорення».

Pult is already its own plugin (`plugins/pult/`), but its watcher and hub use dev-kit parts (the sessions registry `dev-kit-sessions`, lead rules, events to leads). Same principle as the rules-kit / spend-kit split (`plans/retro-auto-rules-check.md`, «Owner's approval»: one clear responsibility per plugin, no plugin imports another's code).

Goal: agree with the owner what «separate» means (what Pult owns, what dev-kit owns, how they talk) and whether it is worth doing.

Success criterion: the owner's «так» to the short plan; the agreed points in «Owner's approval» here.
