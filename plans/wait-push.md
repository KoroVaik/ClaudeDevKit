# Phone push when a session waits on the owner too long

Owner's words (2026-11-20, P: ClaudeDevKit): «Чи можем кидать пуш нотифікацію якщо якійсь сесії треба моя
відповідь і пройшло уже більше ніж 20хв? Щоб уникнуть ситуації, що кеш запишеться заново і відповідно
згорять токени. Здаєтся там дається година... запусти обговорення».

## Facts
- The prompt cache of these sessions lives about one hour (the host states a 1-hour TTL for session
  requests); after it runs out, the next turn of a waiting session re-reads its whole context at the
  full price.
- Today P pushes only critical items, once, when the queue had no question and gets one
  (`plugins/dev-kit/skills/project-lead/SKILL.md`, "Owner queue and critical items", "Phone push").
  Nothing reminds the owner later. P wakes only on a C report, an owner message or a watcher exit;
  the watcher (`dev-kit-sessions watch`) checks the registry every minute.
- A discussion session («Обговорення:») waits on the owner in its own chat; P sees it as
  `чекає на тебе` only through `dev-kit-sessions state`.

## To agree with the owner
Which waits trigger a reminder push (C waiting on P's question to the owner, a discussion waiting in
its own chat, both), after how long (20 minutes or another time before the cache runs out), how many
times, and what the push says.

## Success criterion
The owner approves a short plan; the «Owner's approval» section here holds every agreed point in the
detail a builder needs.
