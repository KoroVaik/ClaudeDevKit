# Sequential UI design flow, plus P/C flow fixes

Source: request from P: Zhratva, 2026-11-18 (BACKLOG.md entry «Sequential UI design flow, plus P/C flow fixes (from P: Zhratva)» holds the full case).

Owner's words (via P: Zhratva): «треба попрацювати над цим флоу, щоб нічого не губилось. І все ішло одне за одним, а не хаотично». The owner asked P: ClaudeDevKit to run it as a discussion («Це обговорення буде»).

## Goal
1. A sequential flow for screen design: mockup approved -> approval recorded in the feature file -> a next-step item where the project lead reads its plans -> build C -> design-sandbox talk. Nothing approved may stay recorded nowhere.
2. Fixes, as the discussion decides, for: a C stalled on the usage limit looks alive to the watcher; dev-kit:overlap-checker fails with «claude not on PATH»; a background P cannot Edit PROGRESS.md in the main checkout (worktree guard) and edits half-apply via shell; no built-in «picked up» confirmation when refreshing an overfull C.
3. Related idea, home not chosen: check all sessions on the machine before advising a machine-wide action (BACKLOG.md entry «Check all sessions before a machine-wide action»). Include only if the owner wants it in this talk.

## Success criterion
The owner approves, in this file, a written proposal: the flow steps, which plugin files change, and the fixes chosen. Building happens after that, in a C started by P from this file.

## Proposal (discussion with the owner, 2026-11-18)

### Flow, as the owner sees it
1. The owner wants a screen -> P starts an «Обговорення: <feature>» session (the analyst).
2. Stage 1, structure: numbered questions with recommendations, a mockup drawn and redrawn. Before each show to the owner: a fresh «користувач» walks it, the «дизайнер» reviews it and turns the user's questions into fixes, the session applies them; at most 2 such iterations, what remains goes to the owner.
3. On the owner's «так» to the mockup, in the same turn (not a step for the owner): the feature file gets a section «Approved design» (mockup link, acceptance criteria, user situation, state «approved, not built») and PROGRESS.md gets a next-step line; then a done report to P. Without that section the session may not report done and P does not merge its branch.
4. P starts C from the feature file. C builds the screen on its own branch and checks it itself: the designer compares headless shots with the mockup, layout-checker checks widths, then the scenario and user checks (test-change order). The owner's «так» to the mockup counts as consent for these checks on that screen.
5. C reports to P with shots of the built screen next to the mockup; P shows the owner.
6. Owner «так» -> P merges, the feature's state becomes «built». Owner «є питання» -> stage 2 (polish of the look on real components) in a separate session on the same branch, the same designer/user loop; merge after the owner's «так». If structure or marks changed, the mockup is redrawn to match what was built.
Nothing unfinished is merged.

### Structure after the change
- Skill `design-screen` (web-kit) replaces draw-mockup and design-sandbox: one loop and one set of show rules, two stages; stage-specific text in side files read only when that stage runs (spec format for stage 1, sandbox for stage 2).
- Agent «користувач» (UX) replaces mockup-user and app-user: one text, two entry modes (mockup: reads PNGs only, no browser; live app: browser). Blind, fresh each run.
  - Context: (1) onboarding written once per project (who you are, what the app is for, its sections), like a new employee shown the app; (2) majority browser/phone habits (back, logo to home), live app only; (3) a real-life situation per feature from the feature file (what just happened, where you are, what you want), same for mockup and built screen, no screen names or button labels. The feature only as a one-line announcement naming neither the screen nor the control. The previous version of the app only when the feature changes an existing screen.
  - Walk: no steps given. On each screen it first says what it expects to see, then what it taps and why, with a mark «певен / вгадав / загубився»; a lucky right tap is a finding. Off the intended path on a static mockup: the choice is a finding, then «ти на потрібному екрані, продовжуй» (also its only help when fully stuck). It does not talk with the designer: it writes the questions it would ask into the report; each is a finding.
  - Keep from the current files: one hand, short text, unclear/extra/awkward marks, max 3 points per screen, the one change that would help most; problems are the main result; broken only with evidence; no deletes; sorting against the mockup stays a separate later step.
- Agent «дизайнер» (UI) replaces design-critic and mockup-checker: knows the design standard, the feature's rules and the approved mockup; finds defects and mismatches with business; turns the user's questions into concrete fixes; screens polish variants before the owner; compares headless shots of the built screen with the mockup. Never edits.
- Stay: sandbox-builder (stage 2 edits), shot-taker, layout-checker, ui-tester; skills visual-check, e2e-check, user-walk re-pointed to the new agents.
- Mockup name = the feature's name; with several screens, the feature name plus the screen (Zhratva: «для новачка» misled both P and the owner).

### Files to change
- web-kit: skills/draw-mockup and skills/design-sandbox -> skills/design-screen (+ side files); agents mockup-user, app-user -> one user agent; design-critic, mockup-checker -> one designer agent; skills visual-check, user-walk, e2e-check; browser-checks.md; slots.md; README.md; version bump.
- dev-kit: skills/documentation (feature template: «Approved design» section, state, user situation; mockup naming), skills/project-lead («Обговорення:» end and P's merge gate, C's first prompt for a screen, owner show of shots, polish session, refresh confirmation, PROGRESS edit check), skills/discovery-round, skills/manager, skills/new-feature, skills/test-change (mockup approval = check consent), skills/brainstorm, slots.md; version bump.
- Scripts: dev-kit/scripts/sessions.py (find claude outside PATH; usage-limit state), pult/scripts/watch-servers.ps1 (usage-limit state).
- Project profiles: sections `## mockup-user` / `## app-user` / `## draw-mockup` / `## design-sandbox` move to the new names, plus the onboarding text; a migration note for projects that use web-kit.

### Fixes chosen
- Watcher: a session stopped on the usage limit is not «alive»; first look at what `claude agents --json` shows for such a session, then teach sessions.py and the Pult watcher.
- overlap-checker: sessions.py looks for claude in the usual install places when it is not on PATH.
- P's PROGRESS.md edit outside its worktree: a stopgap - check the file after each edit before saving it in git (the cause, the host's worktree guard, is out of reach).
- Refresh of an overfull C: the new C's first prompt makes it send P «picked up»; only then P stops the old C (and ends its record).
- Not in this work: checking all sessions before a machine-wide action stays a separate BACKLOG entry.

### Unchecked
- Whether the stage 2 session can continue C's branch.
- What `claude agents --json` shows for a session stopped on the usage limit.

## Owner's approval
2026-11-18: «Так» to the whole proposal above, including one design-screen skill with two stages and the mockup's «так» counting as consent for C's checks of that screen.

## Build (C: design-screen, 2026-11-18)
- Done: web-kit 0.2.0 - skill `design-screen` (SKILL.md, stage1-mockup.md, spec-format.md, stage2-sandbox.md), agents `user` and `designer`; the six old files removed (P's yes); visual-check, user-walk, e2e-check, browser-checks.md, slots.md, sandbox-builder, shot-taker, capture.mjs, README re-pointed. capture.mjs reads the window size from `## design-screen`, or the older `## design-sandbox`.
- Done: dev-kit - documentation («Approved design», mockup naming), project-lead («Обговорення:» end and merge gate, "Build a designed screen", refresh «picked up», main-checkout edit check, watcher `limited:` exit at P's ask), test-change (mockup «так» = check consent), manager, discovery-round, new-feature, slots.md, migrations entry 2 (profile sections and names).
- Lint loosened at P's yes: a project below the newest migration level gets its profile findings as warnings marked «migration N pending»; tests cover pending -> warning and applied -> error.
- Decisions not fixed by the plan: the polish session is an «Обговорення:» session that P starts after stopping the done C; the new C on a refresh is registered only after «picked up»; the designer has no browser and works from headless shots.
- Open: Zhratva's profile must apply migration 2 (its lint findings show as pending warnings until then).
- Paid spend: none (no paid calls).
