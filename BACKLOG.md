# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. An idea leaves the backlog when the owner agrees
it and it is built, or when the owner drops it.

Entry: a `##` title, then `What:`, `Why:` (the concrete case that showed the need: project, date) and
`Cheapest test:`, 2-4 lines in all. A reviewed entry gets a `Verdict:` line (the project lead's
recommendation) and waits for the owner's yes or no.

## Pult: own remote client for agents

What: a custom remote interface for agents, maybe an own Claude client app without the extra features and with the missing ones (grouping by project, what waits on me, health). A self-updating status page instead of a chat list is the first step.
Why: idea from the Pult repo, 2026-11; the phone app's session list does not group by project or show what waits on the owner.
Cheapest test: one static page that reads `claude agents --json` and the projects' PROGRESS.md files and shows them grouped by project.
Built (2026-11-16): first step, `plugins/pult/scripts/status-page.py`; the Pult session sends the page on "статус". Still an idea: a page that refreshes itself, and the own client app. Deferred by the owner (2026-11-19): the attached HTML is a snapshot and cannot refresh itself; first decide where a live page lives (served by the PC or published) and how the owner opens it from the phone.

## Pult: watcher that fixes mechanical issues

What: merge the watcher with server autorun so it fixes mechanical issues itself (dead server, stale queue locks) and keeps a health log the hub reads; the hub fixes the rest within its competence.
Why: idea from the Pult repo, 2026-11; today the watcher only logs and the owner restarts by hand.
Cheapest test: let the watcher restart one dead lead after the owner's yes and check the log lines.
Built (2026-11-16, pult 0.1.4): `plugins/pult/scripts/watch-servers.ps1` restarts a dead lead or server of `servers.psd1` (HEAL, at most 3 an hour, paused by a hold file from `stop-servers.ps1` / `restart-leads.ps1`) and removes dev-kit locks whose owner is gone (UNLOCK); `rules/hub.md` says what Pult shows from the log. Tested on a throwaway lead; not yet seen on a real lead crash.

## Pult: phone notification from a script

What: a script sends a notification to the owner's phone (a dead server, a question that waits).
Why: idea from the Pult repo, 2026-11; not checked how Claude's phone app can be notified from a script.
Cheapest test: find out whether the Remote Control app or another channel accepts a message from a script.
Tried (2026-11-19): two PushNotification calls from P: ClaudeDevKit (a Remote Control bg session) returned «Mobile push requested», but nothing reached the owner's phone. With the Claude app fully closed on the phone, a third push arrived: a session's PushNotification works, it is just not shown while the app is open. Next: let Pult (or a lead) push the owner's critical items instead of a script.

## Check all sessions before a machine-wide action (idea, home not chosen)

What: before any session recommends an action that stops or restarts more than its own work (a PC reboot, restarting Pult or its watcher, stopping servers), it lists every session on the machine (`claude agents --json` with no `--cwd` lists all projects; checked live) and does not recommend the action while one is busy, naming it. Only the idea is agreed; where the rule lives is open (owner's global rules, project-lead skill, Pult hub rules, or several).
Why: P: ClaudeDevKit, 2026-11-16: after a merge it advised the owner to reboot the PC «зараз», reasoning «жодна сесія зараз не працює» from its own registry only, while P: Zhratva and its C were working. The project-lead line «Sessions of other projects are not P's business (Pult)» pulled that way.
Cheapest test: in a session with no sessions of its own, ask whether a reboot is safe while another project's session works; it must name that session and advise against.

## Sequential UI design flow, plus P/C flow fixes (from P: Zhratva)

What: one chain for a screen design, so nothing is lost: mockup approved -> approval recorded in the feature file -> a next-step item where P reads its plans -> build C -> design-sandbox talk; the owner wants a proposal first. Also: 4) the watcher treats a C stalled on the usage limit (blocked, pid present) as alive; 5) dev-kit:overlap-checker fails with «the claude command is not on PATH» (exit 3) and gives no verdict; 6) in a background P the host's worktree guard rejects Edit on PROGRESS.md in the main checkout, so P edits through a shell script and a half-applied edit reached a commit; 7) refreshing an overfull C has no built-in «picked up» confirmation before the old C is stopped.
Why: Zhratva, 2026-11-18: the approved mockup docs/mockups/admin/review-newcomer.html (approved about 2026-11-14) was recorded nowhere, so P never planned it; owner: «треба попрацювати над цим флоу, щоб нічого не губилось. І все ішло одне за одним, а не хаотично». The mockup title «для новачка» misled both P and the owner.
Cheapest test: replay the Zhratva case on paper: after a mockup approval, the next status of P lists the build step without anyone adding it by hand.
