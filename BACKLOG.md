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

## web-kit: phone shots are one screen each, never a stitched page

What: a phone-width headless shot (up to 768 px) is one viewport per PNG; a long page is several screens taken after scrolling. (1) `plugins/web-kit/browser-checks.md`, after the whole-page / app-frame bullets (about line 75): add a bullet «Phone widths: viewport shots - each PNG is one window (for example 375x812), no selector, no `fullPage`, no `fitHeight`; a long page is several shots, each after a scroll step; never a stitched page, fixed bars must sit at the window edge.» (2) `plugins/web-kit/agents/shot-taker.md`: add a kind `screen` for phone briefs (no selector, no `fullPage`, one viewport, scrolled by steps; a phone brief never gets `page`). (3) `plugins/web-kit/scripts/capture.mjs`: add steps `{"scroll": <px>}` and `{"scrollTo": "<css>"}` (each followed by a short wait) in `run()`, and a shot option `"screens": true` that scrolls the window by its height and writes `<name>-1.png ... -n.png`; update the spec header. Today a selector clip uses `captureBeyondViewport: true` (about lines 327-337), so a page-wrapping selector gives a tall stitched image. Checked live 2026-11-20 (Zhratva): even a shot with no selector saves the whole page height, because `capture.mjs` passes `captureBeyondViewport: true` always; it must be false unless a selector or `fullPage` is given. The `click` step is a JS `.click()` that does not scroll; it should scroll the element into view first. A temporary copy with both fixes produced correct 750x1624 phone screens. Also check whether a phone page needs `mobile: true` (lines ~188, ~328 set `mobile: false`), and that scrolling targets the right element if the app scrolls an inner container.
Why: owner, Zhratva, 2026-11-20: a shot-taker shot the mobile recipe page as 726x2441 stitched images with the fixed tab bar mid-image; owner: «Нащо знімати таку довгу сторінку?», «На майбутнє так не має бути». Verdict: owner yes to the idea in the Zhratva lead's chat, 2026-11-20. Zhratva already has a stopgap in its profile `.claude/dev-kit.md` (Phone app shots).
Cheapest test: a spec with `"size":"375x812","scale":2` and two shots of the same page, the second after `{"scroll":800}`; both PNGs are 750x1624 and differ.
