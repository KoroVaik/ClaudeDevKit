# Retro: full automation and a rules check per plugin

Owner's words (2026-11-24, P: ClaudeDevKit chat), on BACKLOG «Retro: one-off items expire»: «Давай 4. Подумай як покращить ретро і внесеш ці зміни. Головне це максимальна автоматизація процесу, щоб юзер не звертав уваги на процес самоаналізу сесій. Також потрібно буде подумати щодо того щоб ретро проводилось для якогось конкретного скоупу правил. Тобто перевірка правил виходить, а не перевірка контексту сесії. Тобто кожен плагін матиме свого перевіряльника доцільності його правил і тд».

Links: `docs/features/fix-agent-problems-in-the-retro.md`, `plugins/dev-kit/skills/retro/SKILL.md`, `plugins/dev-kit/scripts/retro.py`, BACKLOG.md «Retro: one-off items expire» and «Retro: decision items reused across projects».

P's note: whether a rule is worth keeping shows only in how it worked in sessions, so a rules checker still needs session evidence; settle in the talk.

Success criterion: the owner's «так» to the short plan; the agreed points written in «Owner's approval» here or in the feature file.

## Agreed so far (discussion, not the approval)

- 2026-11-24, owner «Звучить ок» to: retro items are kept in one folder per rule set, not per project (web-kit has one folder although it runs in three projects); Claude app facts stay in dev-kit, the retro only passes findings there.
- 2026-11-24, owner «Ну окей»: each set's subscription names the project that reviews it, the one where its files are edited; today ClaudeDevKit reviews all four plugins and the owner's global rules.
- Open: the retro as its own plugin with subscriptions (one subscription file per rule set listing its files); each file belongs to one set, the set it lives in; findings that fit no set go to the project's own retro; splitting a session into parts by the skill, agent or hook at work, a cheap agent naming the file at fault; global rules checked only by content after an owner correction.
