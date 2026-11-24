# Show C sessions in the app?

Owner's words (2026-11-24, P: Zhratva): «Переробка ядра аналізу - чому не бачу цьой сесії», then «напиши дев кіт керівнику щоб обговрив це зі мною». In P: ClaudeDevKit: «обговрення давай».

Today C sessions start with no Remote Control (`plugins/dev-kit/no-remote-control.json`, `plans/push-noise.md`), so the phone and desktop apps list only leads and «Обговорення:» sessions. Remote Control brings one «Remote control enabled» push per brand-new session (`plugins/dev-kit/claude-facts.md`).

Goal: agree with the owner whether and how he sees C sessions (all, some, on demand, another view), with the push cost weighed.

Success criterion: the owner's «так» to the short plan; the decision written in «Owner's approval» below.

## Facts checked live (2026-11-24, Claude Code 2.1.331, owner watched the phone, app closed, phone unlocked)

- A new `claude --bg` session started with no `--remote-control` and no `--settings` gets Remote Control from the
  owner's `remoteControlAtStartup: true` (job `state.json` has a `bridgeSessionId`), shows in the app, and gives
  NO «Remote control enabled» push. Seen twice («Тест 3 пушу», «Тест 5 пушу»).
- A new session started with `--remote-control "<name>"` gives the push. Seen twice («Тест 4 пушу», «Тест 6 пушу»,
  the last two started 3 s after «Тест 5»).
- So the push comes with the `--remote-control` flag, not with Remote Control itself. This corrects
  `plugins/dev-kit/claude-facts.md` ("The phone gets one push when a brand-new session first gets Remote Control",
  "`remoteControlAtStartup: true` gives every new session Remote Control...": its "and its one push" was never seen
  for a session without the flag) and `plans/push-noise.md`.
- Earlier the same day tests 1-2 showed no push while the phone was locked; pushes appeared after unlocking, not
  identified. Not used as evidence.

## Owner's approval

Owner «+» (= так) to both questions, 2026-11-24, in «Обговорення: Видимість сесій C»:

1. **Every C shows in the Claude app (phone, desktop), with no push.** In project-lead "Start a C"
   (`plugins/dev-kit/skills/project-lead/SKILL.md` ~:440) the C launch drops `--settings
   "${CLAUDE_PLUGIN_ROOT}/no-remote-control.json"` and gets no `--remote-control` either: the owner's
   `remoteControlAtStartup: true` gives it the link, and only the `--remote-control` flag pushes (facts above).
   Rewrite the "A C gets no Remote Control ... Why" text at ~:441-445 with the checked facts. Also fix the same
   claim wherever "Start a C" or the «Обговорення:» start (~:559-560) explain the push. A C keeps its rule of
   never calling `PushNotification` and never asking the owner itself.
   - «Обговорення:» sessions keep `--remote-control` and their one push (the owner must open them).
   - Not in scope: the retro and docs sessions (`plugins/dev-kit/scripts/retro.py` ~:1621, ~:1673) keep the
     `--settings` file (stay hidden); keep `no-remote-control.json` for them. Leads (P) keep their flag.
   - C sessions already running keep their stored flags (hidden until they end); nothing is restarted for this.
2. **The owner may write in a C's chat; the C relays it to its P.** When a message in a C's chat comes from the
   owner (not a cross-session message), the C follows it as an instruction for its task, as it would P's
   `ВКАЗІВКА`, and at once sends its P a `ВЛАСНИК ВІДПОВІВ` message with the owner's words verbatim, so P drops a
   matching queue item and knows the change of scope. The C answers the owner in its chat in short (owner's chat
   rules). Anything on the C's ask-P list still goes through P. Write this in project-lead "Start a C" (the C's
   rules) and in `plugins/dev-kit/messages.md` (`ВЛАСНИК ВІДПОВІВ` sender: also a C the owner wrote to).
3. **Facts and docs.** `dev-kit:facts-keeper` corrects `plugins/dev-kit/claude-facts.md` with the facts above
   (push comes with `--remote-control`, not with Remote Control; "A background session started without Remote
   Control does not show in the phone app" now: a C has the link and shows). Update
   `docs/epics/run-all-projects-from-the-phone.md` step 3 (a C shows in the app; you may write to it) and the
   "Facts checked live" claim in `plans/push-noise.md` with a pointer to this plan.

Success check for the builder: a C started by the changed rule has a `bridgeSessionId` in its job `state.json`
and shows in the app; one owner phone check (via P, "Push test with the owner") that it gave no push.

Side note for P (not in this build): «P: Prishch» runs dev-kit 0.1.105 since 2026-11-23 (`~/.claude/pult/lead-versions.json`), older than the C-without-link rule.

## Build (C: c-visible-build, 2026-11-24)

- Done in dev-kit 0.1.117: project-lead "Start a C" starts a C with no `--settings` and no `--remote-control`;
  the owner-message rule lives with the C's other rules in `dev-kit:manager`, "A task from the project lead"
  (the C reads it there; project-lead points to it and lists `ВЛАСНИК ВІДПОВІВ` in the first prompt's report rule);
  `messages.md`, `claude-facts.md` (facts-keeper), the epic, `docs/features/hand-work-to-the-project-lead.md`,
  `plans/push-noise.md` and the `retro.py` comments updated. Retro and docs sessions keep the `--settings` file.
- Not checked by the builder: a live C started by the new rule (a C starts no sessions). The next C P starts is
  the check: `bridgeSessionId` in its job `state.json`, it shows in the app, and the owner saw no push (via P).
- Spend: ~0.2% of the weekly limit, estimate; API: 0 USD
