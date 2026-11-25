# Clearer names for the session roles

Status: approved, to build (owner «Так» to the short plan, 2026-11-25).

Owner, 2026-11-25, «Обговорення: Перевірка зібраних екранів»: his «менеджер» read two ways; «дійсно неймінг кривий, треба буде подумати над адекватним потім». Then in P: ClaudeDevKit chat, to «Відкладаємо на потім простіші назви для сесій?»: «Можна зараз».

Backlog entry «Clearer names for the session roles» (BACKLOG.md): today a task session works by the dev-kit:manager skill, so «менеджер» can mean it or the project lead. Cheapest test there: list every role name the owner sees in a lead's chat and session titles (P, C, «Обговорення:», Ретро, Документація, Pult, керівник, менеджер, сесія, агент, помічник) and check each has one meaning.

## Talk so far

- Owner, 2026-11-25: thinks of the two sessions as «керівник» (the lead: runs the whole project, talks with him) and «менеджер» (a task session: does one job), but sees both words mean the same thing.
- Owner picked English role words, title prefix = their first Latin letter (example shown: «Lead» → «L: ClaudeDevKit», «Task» → «T: Нові іконки»). Exact words still to confirm.
- Owner on «Task»: «це фактично менеджер який курує розробку задачі» (true: the task session follows dev-kit:manager, which plans and hands work to subagents). Proposed instead: task session «Manager», title «M: <task>»; the skill keeps its name.
- Owner floated «Delivery manager» / «Task manager»; weak spot named (both shorten to «менеджер», Windows Task Manager). Accepted, owner «Так»: the lead is «Lead», title «L: <project>»; the task session is «Manager», title «M: <task>».
- Accepted, owner picked «1»: rare sessions get a full English word, no letter: «Обговорення:» → «Discuss: <topic>», «Ретро:» → «Retro: <project>», «Документація:» → «Docs: <project>». «L:» and «M:» stay one letter (owner: «Не лізь в крайнощі» to full words for all).
- Accepted, owner «8 так»: in Ukrainian chat the roles are written «Lead» and «Manager», never translated to «керівник» or «менеджер».
- Accepted, owner «Ну ок» after an example: subagents are always «помічник» in chat, and the launch line starts «помічник:» instead of «агент:».
- Checked (claude-facts.md, "Resuming without `-n` renames the session"): a resume with `-n` keeps a given name, so a running «P: X» lead can be resumed as «L: X» with its history.
- Checked (investigator, 2026-11-25): «P: » is matched in code (lead-reply-form hook, sessions.py, Pult servers.psd1, restart-leads, stop-servers, watch-servers, status-page, tests); «C:» only in rules-kit talk.py; «Ретро:»/«Документація:» in retro, fixes, docs_weekly, sessions.py. English "manager" names the main session in rule text and the skill dev-kit:manager (seen by the owner in launch lines); «помічник» already means subagents.

Success criterion: the owner's «так» to the short plan, with the agreed names written in «Owner's approval» below.

## Owner's approval

Owner «Так», 2026-11-25, to this short plan:

1. Головна сесія проєкту зветься «L: ClaudeDevKit», сесія задачі «M: Нові іконки»; Pult працює з новими назвами, а нинішні головні сесії отримують нову назву і зберігають історію.
2. Рідкі сесії звуться «Discuss: <тема>», «Retro: <проєкт>», «Docs: <проєкт>».
3. У чаті ролі пишуться тільки «Lead» і «Manager», без «керівник» і «менеджер».
4. Дрібні виконавці всюди звуться «помічник», і рядок перед їхнім запуском починається з «помічник:».

Detail for the builders:

- Names. Project lead: role word «Lead», session title `L: <project>` (was `P: `). Task session: role word «Manager», title `M: <task>` (was `C: `). Discussion: `Discuss: <topic>` (was `Обговорення: `). Retro: `Retro: <project folder>` (was `Ретро: `). Docs upkeep: `Docs: <project folder>` (was `Документація: `). All five prefixes differ; no one-letter prefix for the three rare ones (owner rejected `D:`/`R:` and full words for all).
- Chat wording. In owner-facing text (Ukrainian too) the two roles are written «Lead» and «Manager», never «керівник», «менеджер», «P» or «C». Fixed lines change too, e.g. the C closing line «Готово, керівник зіллє роботу й закриє цю сесію» (`plugins/dev-kit/skills/manager/SKILL.md`), the discussion closing line «Обговорення закрите, будову запускає керівник.» and P's «Відкрий сесію «Обговорення: ...»» line (`plugins/dev-kit/skills/project-lead/SKILL.md`), the nudge text in `plugins/dev-kit/hooks/lead-reply-form.py`. The skill `dev-kit:manager` keeps its name (the task session is the Manager).
- Subagents. Owner-facing word is «помічник» only, never «агент». The launch line becomes `помічник: <type> · модель: <model> · reasoning: <level> · скіл: <skill | немає>`; it is defined in the owner's global rules (local file `CLAUDE.md` in the user's `.claude` folder, section "Subagents: model, Fable approval, launch line", plus its English form under "Reply language"), so that edit is local, via `rules-kit:edit-rules`.
- Code that matches the old titles (from the investigator sweep, 2026-11-25): `plugins/dev-kit/hooks/lead-reply-form.py` (`P: ` gate, `Обговорення:` lines); `plugins/dev-kit/scripts/sessions.py` (lead/retro/docs skip prefixes); `plugins/pult/scripts/servers.psd1`, `start-servers.ps1`, `restart-leads.ps1`, `stop-servers.ps1` (`-like 'P: *'`), `watch-servers.ps1`, `status-page.py`; `plugins/rules-kit/scripts/talk.py` (`STARTED_BY_SESSION`), `retro.py`, `fixes.py` (`SKIP_TITLES`); `plugins/dev-kit/scripts/docs_weekly.py`; tests `tools/tests/test_lead_permission_mode.py`, `test_lead_reply_form.py`, `test_docs_weekly.py`. Matchers should accept the old prefixes too for one transition period, so sessions already running under old titles keep working until they end.
- Rule text. Every rule, skill, agent file and `messages.md` that names P, C, «Обговорення:», «Ретро:», «Документація:» moves to the new names (about 40 files say a bare P or C; plans/ history is left as is). Sender/receiver names in `messages.md` change; the message kinds (`ЗАКРИТО`, `ГОТОВО`...) stay. The Pult repo's own `CLAUDE.md` lookup of "P: <project>" changes too (other repo: through `other-repo-editor`).
- Switch-over of running leads. Each running `P: <project>` lead is resumed once with `-n "L: <project>"` so its history stays (claude-facts.md, "Resuming without `-n` renames the session": `-n` keeps the given name); `servers.psd1` gets the new names in the same step, so the watcher does not start a second lead.
- Success: in a lead's chat and the session list the owner sees only `L:`, `M:`, `Discuss:`, `Retro:`, `Docs:`, «Lead», «Manager» and «помічник»; Pult starts, restarts and stops leads under `L:` names; the hook, retro and docs scripts skip and gate on the new titles; tests pass.

## Build steps

Manager session «C: Назви ролей» (this build), 2026-11-25. Doers: M = this session; coder = `dev-kit:coder` sonnet.

1. Pult code (coder): one helper maps a lead name to its old name (`L: X` -> `P: X`); every match of a running
   lead by name (stop-servers, restart-leads, watch-servers skips and heal check, start-servers resume look-up,
   status-page) accepts both. Resume look-up falls back to the old `P: X` session, and the saved options in the
   job's `state.json` (`name`, `--name`) are rewritten to `L: X` before the resume (same place as
   Set-LeadRespawnModel), so the lead keeps its history under the new name. `servers.psd1` gets `L:` names.
   Tests in `tools/tests` updated and extended for the fallback.
2. dev-kit and rules-kit scripts (coder): `lead-reply-form.py`, `docs-start.py`, `docs_weekly.py`, `sessions.py`,
   `talk.py`, `retro.py`, `fixes.py`, `subscriptions.py`: new titles are made, both old and new are matched;
   owner-facing hook text says «Lead»/«Manager»/«Discuss:». Tests updated.
3. Rule text (coder, then M reads the diff): skills, agents, `messages.md`, rules, docs, README in `plugins/` and
   `docs/`; P -> Lead (`L: <project>`), C -> Manager (`M: <task>`), «Обговорення:» -> `Discuss:`, «Ретро:» ->
   `Retro:`, «Документація:» -> `Docs:`; «керівник»/«менеджер» in owner-facing lines -> «Lead»/«Manager»;
   «агент:» launch line -> «помічник:». `plans/` history left as is. Via `rules-kit:edit-rules`.
4. Owner's global rules (M, local git in the user's `.claude` folder): launch line `помічник:`, P/C/керівник
   words -> Lead/Manager. Via `rules-kit:edit-rules` steps 1-2, 5-6.
5. Pult repo `CLAUDE.md` lookup of "P: <project>" (other repo: `other-repo-editor`, haiku).
6. Live check (M): a throwaway background session renamed through its `state.json`, then resumed, shows the
   new name in `claude agents`. Decides whether step 1's rename works.
7. Versions: dev-kit, pult, rules-kit bumped; routine marks in `releases.json` (the watcher restarts leads at
   a quiet moment, and that restart does the rename). Full test run, pull main, report to P.

Spend: see the line at the end of this file.
