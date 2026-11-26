# Plan: a forced reply with nothing new is the one line «Без змін...»

Status: not started (2026-11-26).

Owner's words (L: ClaudeDevKit chat, 2026-11-26): «чому лід спамить повтори?» (screenshot of L: Prishch: the same «Статуси сесій» block after every event), then to «Замінити повтор статусів на один рядок «Без змін»?» - «Без змін....», «Без змін...», and «3 крапки додай».

Cause (checked by the Lead): after an event the Lead ends its turn with no text; the host does not accept an empty turn and demands a visible reply («Your previous response had no visible output»; 8 times in the recent tail of L: Prishch's transcript); "Message templates", "Forced output" in `plugins/dev-kit/skills/project-lead/SKILL.md` then sends the short current state, which is the same block again.

Do: in "Forced output", when nothing changed since the Lead's previous message, the forced reply is exactly the line «Без змін...» (three dots), nothing else; the full short state only when something changed. Keep the keep-warm ping and «Зараз нічого не працює і нічого не чекає на тебе.» as they are unless they clash. Make the Lead-reply Stop hook (`plugins/dev-kit/hooks/lead-reply-form.py`) accept that line. Tests.

Success criterion: a forced reply with no change is «Без змін...»; the hook passes it; tests and lint pass; dev-kit bumped with a release mark.

Spend: -
