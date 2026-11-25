# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. An idea leaves the backlog when the owner agrees
it and it is built, or when the owner drops it.

Entry format: see the Backlog kind in [the documentation standard](plugins/dev-kit/skills/documentation/SKILL.md).
A reviewed entry gets a `Verdict:` line (the project lead's recommendation) and waits for the owner's yes or no.

## Pult: own remote client for agents

What: a status page that refreshes itself (the built `plugins/pult/scripts/status-page.py` page is a snapshot), built by a script from a status file per project that also keeps a history of finished tasks; then maybe an own Claude client app with grouping by project, what waits on me and health.
Why: the phone app's session list lacks grouping by project and what waits on the owner (`plugins/dev-kit/claude-facts.md`, "The phone app's session list does not group by project or show what waits on the owner"); the attached snapshot goes stale.
Cheapest test: serve the page from the PC (or publish it) and open it from the phone once; the own client waits on that answer.
Verdict (2026-11-20): keep as an idea; owner: yes. Both the live page and its task history wait on one open point: where a live page lives and how the phone opens it; the own client app is parked behind it.

## A manager (C) with its own sub-sessions

What: a task session gets more freedom inside its feature and starts its own sub-sessions (a sub-C under a C for a huge dependent part), taking over part of the lead's duties. Not supported today: dependent parts stay in one C with parallel subagents, an independent part goes to P as a new task.
Why: owner, 2026-11-15 (lead authority discussion): managers should take over part of the lead's duties with sub-managers; left unsupported for now, to revisit if a subagent's context proves too small.
Cheapest test: give a C a dependent part too big for one subagent's context and see whether the talk between C and sub-C stays away from P.
Verdict (2026-11-20): keep as an idea: `manager/SKILL.md` still bans a C's own sessions and no case since 2026-11-15 showed a subagent's context too small. Owner: yes.

## Retro: decision items reused across projects

What: every retro decision (a "no, the rule is not to blame" too) becomes a local file with a short cause key; another project's retro reads only the list of keys and opens the matching decisions; one that worked in two projects becomes a dev-kit rule and its file is deleted. Needs a way to keep the number of decision files manageable over time.
Why: owner, 2026-11-21: reuse of experience between projects; today each project's retro starts from its own items only.
Cheapest test: replay one real case, e.g. a decision of the Zhratva retro, and see whether the ClaudeDevKit retro would have found it by its cause key.
Verdict (2026-11-22): keep as an idea; moved from the finished retro plan, the owner has not agreed it; no case yet shows it missing. Owner: yes (2026-11-23).

## Project lead: event wake-ups give a status line or no text, never a free-text note

What: in `plugins/dev-kit/skills/project-lead/SKILL.md`, "Message templates" (the line "P never writes a free-text note beside the blocks") and the forced-output paragraph say it outright: an event with no change for the owner (a usage-limit line «ЛІМІТ: ...», a C freeing the shared editor, a finished retro) gets only a status line in the template, or no text. P never sends plain sentences instead of the blocks («Nothing new needs you», «Your limit is N%», «The session finished»). The usual end-of-turn pressure to write something is not the host reminder that allows the forced-output state.
Why: P: Prishch, 2026-11-24/25, answered such events with free plain-English text; owner: «Чому на англ? Чому не показуєш статистику а пишеш цей текст?». The English part is already fixed in the owner's global rules (Reply language, 2026-11-25); this entry covers only the free-text part.
Cheapest test: replay a usage-limit line and a finished retro to a lead; the reply is a status line in the template or empty, never a plain sentence.
Verdict: owner yes 2026-11-25 (P: Prishch chat); simple edit, one place.

## Clearer names for the session roles

What: rename the roles the owner meets in chat so each name points to one thing: today a task session works by the `dev-kit:manager` skill, so "менеджер" can mean it or the project lead.
Why: owner, 2026-11-25, «Обговорення: Перевірка зібраних екранів»: his «менеджер» read two ways; «дійсно неймінг кривий, треба буде подумати над адекватним потім».
Cheapest test: list every role name the owner sees in a lead's chat and session titles, and check each has one meaning.
Verdict (2026-11-25): owner «Можна зараз»: discussion started («Обговорення: Назви ролей сесій»).

## web-kit-pair: half labels under the title

What: change `web-kit-pair` (plugins web-kit, `scripts/pair.mjs`) to keep the one `--title` line on top (the state in the owner's words) and add under it a fixed label above each half, drawn inside the image: «Мокап» over the left half and «Зроблено» over the right (defaults, overridable with `--left-label` / `--right-label`). The old note that the title must not say "mockup" / "built" is dropped only for these labels; the title itself stays the state. The caller's chat caption repeats the title. Update the doc lines (the header comment and usage line in `pair.mjs`) and the callers that describe the title: `plugins/web-kit/browser-checks.md` (line 142), `skills/design-screen/SKILL.md` (line 112) and `skills/visual-check/SKILL.md` (line 51). Callers shoot the built half at the mockup's frame extent. When this ships, remove the per-half caption exception from the owner's global rules (C:/Users/korov/.claude/CLAUDE.md, bullet 'Pictures go to the owner', the sentences naming `web-kit-pair`), keeping only 'side by side' there; owner yes 2026-11-25.
Why: owner, 2026-11-25, Zhratva: «Треба над фото писати прям в картинці опис короткий фото завжди. Тобто зараз 2 фото зклеєно, тому м буть 2 описи», then «Підписи повторяють текст», then «На картинці має бути підпис!!!!!», then yes to this layout (title on top, a label over each half). A built half cropped to one block also read to him as an empty screen, so the built half must be shot at the mockup's frame extent.
Cheapest test: run `web-kit-pair` on one Zhratva board frame plus one built shot; open the PNG and check the title and both labels are legible on a phone.
