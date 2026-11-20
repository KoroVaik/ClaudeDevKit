# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. An idea leaves the backlog when the owner agrees
it and it is built, or when the owner drops it.

Entry format: see the Backlog kind in [the documentation standard](plugins/dev-kit/skills/documentation/SKILL.md).
A reviewed entry gets a `Verdict:` line (the project lead's recommendation) and waits for the owner's yes or no.

## Pult: own remote client for agents

What: a custom remote interface for agents, maybe an own Claude client app without the extra features and with the missing ones (grouping by project, what waits on me, health). A self-updating status page instead of a chat list is the first step.
Why: idea from the Pult repo, 2026-11; the phone app's session list does not group by project or show what waits on the owner.
Cheapest test: one static page that reads `claude agents --json` and the projects' PROGRESS.md files and shows them grouped by project.
Built (2026-11-16): first step, `plugins/pult/scripts/status-page.py`; the Pult session sends the page on "статус". Still an idea: a page that refreshes itself, and the own client app. Deferred by the owner (2026-11-19): the attached HTML is a snapshot and cannot refresh itself; first decide where a live page lives (served by the PC or published) and how the owner opens it from the phone.
Merged (2026-11-20, owner's yes): «P status built by a script, with a history of finished tasks»: `dev-kit-sessions` (or the watcher) keeps a status file per project (live sessions, open questions by kind, finished tasks); P pastes its ready lines, and the history is a page. Owner, 2026-11-19: «Чи можна написати скрипт який формуватиме хтмл статус? Відповідно буде видно історію готових задач».
Verdict (2026-11-20): keep as an idea; owner: yes. Both wait on one open point: where a live page lives and how the phone opens it; the own client app is parked behind that.

## Check all sessions before a machine-wide action (idea, home not chosen)

What: before any session recommends an action that stops or restarts more than its own work (a PC reboot, restarting Pult or its watcher, stopping servers), it lists every session on the machine (`claude agents --json` with no `--cwd` lists all projects; checked live) and does not recommend the action while one is busy, naming it. Only the idea is agreed; where the rule lives is open (owner's global rules, project-lead skill, Pult hub rules, or several).
Why: P: ClaudeDevKit, 2026-11-16: after a merge it advised the owner to reboot the PC «зараз», reasoning «жодна сесія зараз не працює» from its own registry only, while P: Zhratva and its C were working. The project-lead line «Sessions of other projects are not P's business (Pult)» pulled that way.
Cheapest test: in a session with no sessions of its own, ask whether a reboot is safe while another project's session works; it must name that session and advise against.
Verdict (2026-11-20): build now: one sentence in the owner's global rules, section «Machine hygiene» (the only home every session loads); nothing covers it today, `stop-servers.ps1` guards only its own server folders.
Owner's yes (2026-11-20); handed to P to write, since the home is the owner's global rules outside this repo.

## A manager (C) with its own sub-sessions

What: a task session gets more freedom inside its feature and starts its own sub-sessions (a sub-C under a C for a huge dependent part), taking over part of the lead's duties. Not supported today: dependent parts stay in one C with parallel subagents, an independent part goes to P as a new task.
Why: owner, 2026-11-15 (lead authority discussion): managers should take over part of the lead's duties with sub-managers; left unsupported for now, to revisit if a subagent's context proves too small.
Cheapest test: give a C a dependent part too big for one subagent's context and see whether the talk between C and sub-C stays away from P.
Verdict (2026-11-20): keep as an idea: `manager/SKILL.md` still bans a C's own sessions and no case since 2026-11-15 showed a subagent's context too small. Owner: yes.

## Track changes to the owner's global rules

What: a manager or another agent that keeps a record of every change to the owner's global rules (`C:/Users/korov/.claude/CLAUDE.md` and its `docs/`): what changed, when, and why (the incident or the owner's decision). A simpler first step: keep that folder in a local git repo, with the reason in each commit message, which `dev-kit:edit-rules` writes when it edits the global rules.
Why: owner, 2026-11-19, discussion «global rules vs the new P format»: asked why five global rules exist, and no reason was found anywhere (the folder has no history, no notes give a reason), so nobody can say whether a rule is still needed.
Cheapest test: after one global rule edit through `dev-kit:edit-rules`, ask a fresh session why that line exists; it must find the date and the reason.
Verdict (2026-11-20): build now: a local git repo in the owner's `.claude` folder tracking only `CLAUDE.md` and `docs/` (allow-list `.gitignore`), and one `dev-kit:edit-rules` line to commit each global-rule edit with its reason.
Built (2026-11-20, owner's yes): the `dev-kit:edit-rules` line (step 6, dev-kit 0.1.67) and the local git repo in the owner's `.claude` folder.

## Design-screen spot check leaks into the owner's chat

What: in `web-kit:design-screen` (SKILL.md, "Roles"), the main session no longer opens a shot itself as the spot check of a set it sends; a cheap subagent (haiku) opens the shots and reports cut-off, empty or illegible ones, or the session relies on the size `web-kit-shot` prints. Only the numbered `SendUserFile` pictures reach the owner.
Why: Zhratva, «Обговорення: Смаки партнера», 2026-11-20: in the phone app every image the main session reads with Read shows in the owner's chat, so a spot-check picture arrived unnumbered next to the numbered set and the owner asked why there were three pictures for two cases. Owner: «пофіксим ці картинки спочатку», «Запиши».
Cheapest test: run one design-screen show from the phone app; the chat must show only the numbered pictures.

## Design-screen: no new picture reaches the owner without the designer

What: in `web-kit:design-screen` (SKILL.md, "The loop before each show"), the skip clause «While the owner tunes a look round by round (a shade, a size, a spacing), skip the loop» covers only shades, sizes and spacing of elements the designer already passed. Any new screen, popup, state or control drawn mid-discussion goes to `web-kit:designer` before the owner sees it, even when the loop's user walk is skipped.
Why: Zhratva, «Обговорення: Смаки партнера», 2026-11-20: mid-discussion the session sent new popups, an empty state and a tab switcher without the designer; the switcher rendered as one word «МоїОлі». Owner: «це має буть флоу де дизайнер апрувить а потім мені дається».
Cheapest test: in a design discussion, ask for a new control mid-round; the session must run the designer before sending the picture.

## project-lead: a look question carries its shots every time

What: in `plugins/dev-kit/skills/project-lead/SKILL.md` (section "Message templates", paragraph "The full list"), add one sentence: a question about how a screen looks (the «так» / «є питання» check of "Build a designed screen", step 2) carries its shots next to the mockup every time it is shown, in the full list and when asked again, even if they were sent before.
Why: Zhratva, 2026-11-20: P showed the full question list for the built «Смаки» tab without the shots because it had sent them one message earlier; owner: «Чому сюди не продублювались фінальні фото?». The owner's global rules were sharpened the same day (a look question carries its picture every time it is shown; this wins over the no-re-send ban).
Cheapest test: in a P chat, a built-screen question shown twice (new, then in the full list) has the shots both times.
Verdict (2026-11-20): owner yes to the idea in the Zhratva lead's chat.

## web-kit: pictures for the owner in blocks, mockup and result side by side

What: the owner's global rule (2026-11-20) now says pictures go as separate files in logical blocks (one send per block with its caption), never a stitched sheet of many screens, and a mockup and its result of one state are one picture side by side with a very short line on top saying what the frame shows. Align web-kit: `plugins/web-kit/browser-checks.md` (about lines 100-119) and `plugins/web-kit/skills/design-screen/SKILL.md` (about lines 104-106, "one SendUserFile call per image", "more than two items: one message per item") name the side-by-side pair as one image and allow one send per block, with numbering reconciled to per-block captions. Add a small command (for example `web-kit-pair`) that joins a mockup PNG and an app PNG side by side at equal height with a short title line on top, so no agent writes a one-off Pillow script; the check-look flow (`browser-checks.md`, about lines 93-99, and the check-look row about line 16) uses it for owner-facing comparisons. Each half stays one full phone window (the one-screen rule).
Why: Zhratva, 2026-11-20: the built «Смаки» tab went to the owner as three wide contact sheets; owner: «Фото потрібно розбивати на логічні блоки і постити не склейками, бо їх незручно на телефоні переглядать», then «Склей мокапи і результат», then «Замість мокап і збудовано описуй дуже стисло суть фото». Owner yes to the idea in the Zhratva lead's chat, 2026-11-20.
Cheapest test: a check-look report of 4 states reaches the owner as one block of 4 side-by-side pictures, each with a short title line, readable on a phone.
