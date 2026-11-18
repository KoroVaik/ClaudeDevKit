# Lead: task list instead of a question, one-time hard-ban proposal, migration 2 here

Owner's words and yeses (P: ClaudeDevKit chat, 2026-11-18):
- After P asked «Яку задачу запустити?» right after the owner's «Ні»: «Нащо знову питаєш»; to the idea «коли план порожній, керівник не ставить питання» the owner said «Так. Краще хай дає просто список доступних задач».
- From P: Zhratva: relayed owner yeses do not count in auto mode, because no P ever proposed the hard bans. To «записати як одноразову зміну для всіх проєктів, а не перевірку на кожному старті» the owner said «Так».

## Work
1. BACKLOG.md entry «Project lead: no repeated «Яку задачу запустити?» with an empty plan»: in plugins/dev-kit/skills/project-lead/SKILL.md, "Message templates" (the proposal bullet and the Status template's empty-plan line): with nothing to propose, P lists the tasks it could start (plans, BACKLOG ideas, parked items) with their «(від тебе: ...)» brackets and asks nothing; with none at all, one line that there is nothing. No proposal line and no «Яку задачу запустити?». Remove the built entry from BACKLOG.md.
2. A new entry in plugins/dev-kit/migrations.md: propose the hard bans once. How: if the project's committed .claude/settings.json lacks the deny lines of project-lead "Hard bans", P puts one owner-queue item with the exact lines filled for this project (Owner choice); the owner adds them by hand on yes; either answer is recorded and the entry is applied. Update project-lead "Hard bans" / "Permission mode" so «once per project» points at this migration instead of a promise nobody tracks.
3. Apply pending migration 2 in this repo (it enables no web-kit, so likely a record only) and record the level.

Every rule edit runs dev-kit:edit-rules steps 1-2 and 5-6; the owner approved the ideas above. Bump the dev-kit version, run python tools/lint.py and the tests.

## Success criterion
Lint and tests pass; project-lead has no instruction that makes P ask «Яку задачу запустити?»; migrations.md has the hard-ban entry; `dev-kit-migrations pending` in this repo prints only the new entry (or none once applied here).
