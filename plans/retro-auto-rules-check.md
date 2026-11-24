# Retro: full automation and a rules check per plugin

Owner's words (2026-11-24, P: ClaudeDevKit chat), on BACKLOG «Retro: one-off items expire»: «Давай 4. Подумай як покращить ретро і внесеш ці зміни. Головне це максимальна автоматизація процесу, щоб юзер не звертав уваги на процес самоаналізу сесій. Також потрібно буде подумати щодо того щоб ретро проводилось для якогось конкретного скоупу правил. Тобто перевірка правил виходить, а не перевірка контексту сесії. Тобто кожен плагін матиме свого перевіряльника доцільності його правил і тд».

Links: `docs/features/fix-agent-problems-in-the-retro.md`, `plugins/dev-kit/skills/retro/SKILL.md`, `plugins/dev-kit/scripts/retro.py`, BACKLOG.md «Retro: one-off items expire» and «Retro: decision items reused across projects».

P's note: whether a rule is worth keeping shows only in how it worked in sessions, so a rules checker still needs session evidence; settle in the talk.

Success criterion: the owner's «так» to the short plan; the agreed points written in «Owner's approval» here or in the feature file.

## Agreed so far (discussion, not the approval)

- 2026-11-24, owner «Звучить ок» to: retro items are kept in one folder per rule set, not per project (web-kit has one folder although it runs in three projects); Claude app facts stay in dev-kit, the retro only passes findings there.
- 2026-11-24, owner «Ну окей»: each set's subscription names the project that reviews it, the one where its files are edited; today ClaudeDevKit reviews all four plugins and the owner's global rules.
- 2026-11-24, owner «Ок» (reverses the 2026-11-21/22 «retro stays in dev-kit»): the retro becomes its own plugin; dev-kit, web-kit, unity-kit, pult and the owner's global rules subscribe; one subscription file per set lists its files, what to look for in sessions and what the agent may change itself; each file belongs to one set, the one it lives in, other sets' files are read only for context; a finding that fits no set goes to the project's own retro.
- 2026-11-24, owner «Так»: a subscription file is a file of its set and is reviewed with it. A rule that caught nothing for weeks: an agent reads a few sessions and decides whether the rule is unneeded or the tracking is blind. A problem found by the general signs (owner correction, failed command) and laid to a file of a set the subscription missed: the agent adds a new sign to the subscription itself.
- 2026-11-24, owner «Так»: the subscription marks each rule with a type (talk with the owner, technical, process), each tracked its own way. Talk rules are checked by the script in every reply to the owner with no model and no owner correction needed (length, dashes, language, «так»/«ні» first); technical rules by tool traces (calls, failures, repeats); process rules by an agent reading the session part.
- 2026-11-24, owner «Так»: the script with no model splits a session into parts by the skill, agent or hook at work then (a problem after a discovery-round call has dev-kit as a candidate); a cheap agent, shown only that part and the candidate sets' files, names the file and line at fault or «not a rule».
- 2026-11-24, owner «Так»: no weekly «розібрати N пунктів?» question; the retro applies fixes itself and reverts a fix that later sessions show did not work; the owner is asked only about deleting a rule file or changing how sessions talk to him.
- 2026-11-24, owner «Так»: a finding seen once, not urgent, that does not recur in 2 weeks expires by itself (closes BACKLOG «Retro: one-off items expire»). The owner's global rules are checked in the sessions of every project, those without a lead too. Token spend counting stays in dev-kit (it is shared with the status line); the retro takes its numbers only as evidence.
- Checked 2026-11-24 in the last 30 ClaudeDevKit transcripts: skill calls (skill name), agent calls (`subagent_type`) and hook events are recorded, so the script can split a session by them; a hook event names its event type, the hook's plugin comes from its command path.
- Kept from today's retro: a fix needs a repeat (lost work and critical token problems are fixed at once); every fix also removes or merges something; each fix is checked by later sessions.
