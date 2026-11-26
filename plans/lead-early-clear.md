# Plan: a lead clears its context earlier

Status: built (2026-11-26), dev-kit 0.1.137 and pult 0.1.38.

Spend: ~1% of the weekly limit, estimate; API: 0 USD

Owner's words (via L: Zhratva, 2026-11-26): «Напиши щоб очищення відбувалось раніше ніж ліміт токенів для лідів. Нехай запустить дев кіт обговорення для мене».

Source: BACKLOG.md entry «A lead clears its context earlier than the fill limit, and on plugin updates that rename things» (case, cause, cheapest test). Current behaviour: `plugins/dev-kit/skills/project-lead/SKILL.md`, sections "Restart the Lead" (fill limit 0.33, self-move with /clear) and "Restart for a plugin update" (resumes the same conversation); owner's view: `docs/features/hand-work-to-the-project-lead.md`, «P moves itself to a fresh session».

Success criterion: an «Owner's approval» section here with every agreed point in builder detail, and the owner's «так» to the short plan.

## Owner's approval

Owner «Так», 2026-11-26, in this «Discuss:» session, to: «коли виходить нова версія плагіна, яка перейменовує назви чи змінює формат повідомлень, помічник, що її випускає, ставить на неї позначку «потрібен чистий старт». Lead, перезапускаючись на таку версію, починає з чистого контексту і вже не пам'ятає старих назв. Дрібні виправлення таку позначку не отримують, тож для них Lead, як і зараз, продовжує стару розмову.» The owner's reason: the plugin itself must tell whether an update needs a clean restart, since minor fixes come all the time and must not reload sessions from scratch.

Agreed points, for the builders:

1. Release mark. A release mark in `plugins/<plugin>/releases.json` gets an optional field `"clean": true`. A missing field means false. The kind (critical / routine) and its timing stay as they are.
2. Who sets it. The agent that bumps the version sets `"clean": true` when the release renames or changes something a running Lead holds in its context: a session name prefix, a role or term name, a command or script name, a message or event-line format, a fixed line the Lead writes. Everything else (fixes, new rules that rename nothing) gets no field. Rule text: `.claude/dev-kit.md` of this repo, next to the critical/routine rule, with this list.
3. What the watcher does. When the pending versions of a Lead's restart include one with `"clean": true` (any plugin the Lead loads), the restart takes the self-move route of "Restart the Lead" instead of a plain resume: the Lead saves a handoff, the watcher resumes it with `/clear`, then with `/dev-kit:project-lead handoff: <file>`. Timing stays by the kind (routine: a later day, at a quiet moment; critical: the same day).
4. The handoff step. A clean restart needs the Lead to save a handoff first, so the watcher sends the Lead the event line `restart requested: <version> clean` also when the Lead is quiet. The Lead does the handshake of "Restart for a plugin update" plus step 1 of "Restart the Lead" (`continue-work-in-another-context save`, `dev-kit-sessions handoff save --file <file>`), writes exactly «⚠ ЧЕРЕЗ 30 СЕК БУДЕ ПЕРЕЗАВАНТАЖЕННЯ (ОНОВЛЕННЯ ІНСТРУМЕНТІВ)», runs `dev-kit-sessions handoff go` and ends the turn. The watcher then does the move 30 seconds later, as in step 3 of "Restart the Lead".
5. After the move the Lead follows step 4 of "Restart the Lead": it loads the handoff, then runs the plugin-update first-prompt steps (reads SKILL.md whole, notes the new version, fill, others, state, the migrations check, the full start status).
6. A failed clean move falls back as step 5 of "Restart the Lead" (HANDOFF-FAILED, the old Lead back); the plain update restart is then done as today, so the Lead is never worse off than now.
7. Docs and code to change: the skill sections "Restart for a plugin update" and "Restart the Lead", the feature `docs/features/hand-work-to-the-project-lead.md` (owner's view: an update that renames things starts the Lead with a clean context; small fixes keep the conversation), the Pult watcher and its tests.

Weak spot accepted: the mark is set by the releasing agent, not detected from the code; a forgotten mark gives today's behaviour.

8. The ordinary fill limit of a Lead stays 0.33 (owner «Так», 2026-11-26, to «Лишаємо звичайне очищення Lead на третині, бо чистий старт після оновлень уже закриває випадок у Zhratva?»). Reason: the Lead mixed up names at about a fifth of the window, so a lower limit would not have helped.
9. A change to `dev-kit:discovery-round`, step 4 (owner «Так», 2026-11-26, to «Записуємо в правило обговорення: перша відповідь - мій здогад тобі на підтвердження?»; his words: «ти маєш з контексту зрозуміть що я хочу, щоб я просто підтвердив»). The first reply of a «Discuss:» session, and of a talk on an idea the owner still weighs, states in one concrete sentence what the owner wants, read from his words, the task file and the backlog entry, and asks him to confirm it with a yes/no question. An open question stays only when those sources do not say what he wants. This replaces the 2026-11-25 rule that the first reply is always an open question with no recommendation; the ban on a stream of numbered questions in the first reply stays. Weak spot accepted: a wrong guess may get a quick «так»; so the guess is one concrete sentence, never a vague one. Apply it through `rules-kit:edit-rules`.
