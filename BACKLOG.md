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

## Check all sessions before a machine-wide action (idea, home not chosen)

What: before any session recommends an action that stops or restarts more than its own work (a PC reboot, restarting Pult or its watcher, stopping servers), it lists every session on the machine (`claude agents --json` with no `--cwd` lists all projects; checked live) and does not recommend the action while one is busy, naming it. Only the idea is agreed; where the rule lives is open (owner's global rules, project-lead skill, Pult hub rules, or several).
Why: P: ClaudeDevKit, 2026-11-16: after a merge it advised the owner to reboot the PC «зараз», reasoning «жодна сесія зараз не працює» from its own registry only, while P: Zhratva and its C were working. The project-lead line «Sessions of other projects are not P's business (Pult)» pulled that way.
Cheapest test: in a session with no sessions of its own, ask whether a reboot is safe while another project's session works; it must name that session and advise against.

## P/C flow fixes (from P: Zhratva)

What: 5) dev-kit:overlap-checker fails with «the claude command is not on PATH» (exit 3) and gives no verdict; 6) in a background P the host's worktree guard rejects Edit on PROGRESS.md in the main checkout, so P edits through a shell script and a half-applied edit reached a commit.
Why: Zhratva, 2026-11-18, in the same case as the approved Zhratva mockup «review-newcomer», which was recorded nowhere, so P never planned it (the design flow, the watcher on the usage limit and the «picked up» check for a refreshed C are built since then).
Cheapest test: run overlap-checker with `claude` off PATH and expect a verdict; edit PROGRESS.md from a background P and expect no half-applied edit.

## Idle session the owner started that finished its task

What: when a session the owner started has finished its task and hangs idle, P offers the owner once to close it, or to take over its open question as a new task session.
Why: Zhratva, 2026-11-15: «Неоднозначні факти арбітра» finished and hung idle; P could neither reach it (messages held, permission mode mismatch) nor close it. P: Zhratva proposed the offer; it was not in the approved build of lead authority.
Cheapest test: first check how far the «Роботу завершено» line (dev-kit 0.1.36) already covers it; then end a throwaway owner session and see that P offers once.

## A manager (C) with its own sub-sessions

What: a task session gets more freedom inside its feature and starts its own sub-sessions (a sub-C under a C for a huge dependent part), taking over part of the lead's duties. Not supported today: dependent parts stay in one C with parallel subagents, an independent part goes to P as a new task.
Why: owner, 2026-11-15 (lead authority discussion): managers should take over part of the lead's duties with sub-managers; left unsupported for now, to revisit if a subagent's context proves too small.
Cheapest test: give a C a dependent part too big for one subagent's context and see whether the talk between C and sub-C stays away from P.


## P status built by a script, with a history of finished tasks

What: `dev-kit-sessions` (or a background watcher) keeps a status file per project: live sessions with their state, open questions by kind, and a history of finished tasks; P pastes its ready lines into its status message instead of composing them, and the history is viewable as a page. Close to the Pult status-page entry above: where a live page lives and how the owner opens it from the phone is the same open point.
Why: P: ClaudeDevKit, 2026-11-19, discussion «Повідомлення керівника»: a «готово» line in a mid-day update is lost once the next update comes; owner: «Чи можна написати скрипт який формуватиме хтмл статус? Відповідно буде видно історію готових задач».
Cheapest test: run the script on the current registry and compare its lines with a status P wrote by hand the same minute.

## Track changes to the owner's global rules

What: a manager or another agent that keeps a record of every change to the owner's global rules (`C:/Users/korov/.claude/CLAUDE.md` and its `docs/`): what changed, when, and why (the incident or the owner's decision). A simpler first step: keep that folder in a local git repo, with the reason in each commit message, which `dev-kit:edit-rules` writes when it edits the global rules.
Why: owner, 2026-11-19, discussion «global rules vs the new P format»: asked why five global rules exist, and no reason was found anywhere (the folder has no history, no notes give a reason), so nobody can say whether a rule is still needed.
Cheapest test: after one global rule edit through `dev-kit:edit-rules`, ask a fresh session why that line exists; it must find the date and the reason.
