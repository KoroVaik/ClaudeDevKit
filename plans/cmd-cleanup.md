# Clean up `.cmd` files made for the owner

Status: started 2026-11-27 by L: ClaudeDevKit.

## Task

From BACKLOG.md, entry «A `.cmd` file made for the owner was left on the desktop after use» (read it whole; remove the
entry when built).

Owner's words (L: Zhratva, 2026-11-26): «там тіки старий файл який ти н прибрав схоже», then «видалити і написати
девкіту що ти не видалив його сам». Owner's «Так» to the Lead's question (2026-11-27): «запустити сесію «M: Прибирання
файлів для запуску»? (старі файли на робочому столі зникатимуть самі)».

What: make the clean-up of an agent-written `.cmd` survive the session that wrote it (a Lead or Pult check, or a record of
written files that a later Lead start cleans up), and keep such files only in `Desktop/Claude`.

## Success criterion

A `.cmd` written by a session that ended without the owner's «Готово» is removed (or reported) by a later check with no
owner action; an agent never writes such a file outside `Desktop/Claude`; a file the owner made is never deleted.

## Notes

The owner's global rule on these files lives in his local `.claude/CLAUDE.md` («Chat replies», the `.cmd` bullet); a
change there is a rule edit of the owner's global files (`rules-kit:edit-rules`), asked through the Lead.
