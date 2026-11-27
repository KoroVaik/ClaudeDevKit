---
name: weekly-retro
description: Use when a session named «Retro: тиждень» starts (rules-kit starts it once a week with "/rules-kit:weekly-retro", or `rules-kit weekly --start` on the owner's request) to show the owner the week's spend by cause, the experiments and the important retro items, fixed and planned, and to answer his questions about them.
---

# Main retro of the week

The owner talks with this session. It shows where the week's tokens went and what the retros did, and answers his
questions; it asks him nothing on its own and fixes nothing itself: the service retro sessions of the projects fix by
themselves (`rules-kit:retro`), and this session does not replace them.

1. Run `rules-kit weekly` (Bash tool; where Bash cannot run it, `python -X utf8 <this plugin>/scripts/retro.py weekly`).
2. Show its output as it is, in one message: it is a fixed-format report (the owner's chat caps do not cut it). Add
   nothing before or after it, no question.
3. Then answer what the owner asks, under his chat rules. A detail he asks for comes from the same sources: `spend-kit
   stats --detail <group>`, `spend-kit experiments`, `rules-kit items`, `rules-kit list --days 7`, the item files the
   items list names.
4. A change he asks for (a rule, a helper's model, stopping an experiment) is not made here: after his explicit yes,
   send it to the Lead of the project that owns it (`L: ClaudeDevKit` for the plugins) as a `ДОРУЧЕННЯ` with his words
   verbatim in «» (dev-kit's `messages.md`), and say so in one line.

Why: owner, 2026-11-27 (`plans/limit-spend.md`, point 7): «запуск основной ретро сесії з якой я можу комунікцвать раз
на тиждень або за вимогой»; «Має вказуватись основна статистика і важливі ретроайтеми як пофікшені так і
заплановані».
