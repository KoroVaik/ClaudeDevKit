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
Built (2026-11-16): first step, `plugins/pult/scripts/status-page.py`; the Pult session sends the page on "статус". Still an idea: a page that refreshes itself, and the own client app.

## Pult: watcher that fixes mechanical issues

What: merge the watcher with server autorun so it fixes mechanical issues itself (dead server, stale queue locks) and keeps a health log the hub reads; the hub fixes the rest within its competence.
Why: idea from the Pult repo, 2026-11; today the watcher only logs and the owner restarts by hand.
Cheapest test: let the watcher restart one dead lead after the owner's yes and check the log lines.
Built (2026-11-16, pult 0.1.4): `plugins/pult/scripts/watch-servers.ps1` restarts a dead lead or server of `servers.psd1` (HEAL, at most 3 an hour, paused by a hold file from `stop-servers.ps1` / `restart-leads.ps1`) and removes dev-kit locks whose owner is gone (UNLOCK); `rules/hub.md` says what Pult shows from the log. Tested on a throwaway lead; not yet seen on a real lead crash.

## Pult: phone notification from a script

What: a script sends a notification to the owner's phone (a dead server, a question that waits).
Why: idea from the Pult repo, 2026-11; not checked how Claude's phone app can be notified from a script.
Cheapest test: find out whether the Remote Control app or another channel accepts a message from a script.

## Pult: rule edits go through dev-kit:edit-rules

What: add one line to `plugins/pult/rules/hub.md`: every edit of Pult's rules (`rules/hub.md`, the Pult repo's `CLAUDE.md` and `.claude/`) goes through `dev-kit:edit-rules`.
Why: Pult, 2026-11-16: the owner enabled dev-kit in the Pult repo (project scope) so that Pult's rule edits run through edit-rules; the rule itself lives in this plugin.
Cheapest test: in a new Pult session ask for a small rule wording change; the session runs edit-rules (read set, duplicates and conflicts list, reviewer).
Verdict: build - one bullet in hub.md "Limits" pointing Pult's rule edits to dev-kit:edit-rules; simple.

## dev-kit: narrow-agents hook blocks other-repo-editor

What: let `plugins/dev-kit/hooks/narrow-agents.py` allow the owner's user-level agents (`~/.claude/agents/*.md`), or ship `other-repo-editor` in a plugin; decide also on a narrow Claude Code docs agent, since `claude-code-guide` is denied with no dev-kit replacement.
Why: Pult, 2026-11-16: `plugins/pult/rules/hub.md` and the owner's global rule "Stay in the session's project" send edits in other repos to `other-repo-editor`, which the hook denies in every dev-kit project; Pult now has a thin project agent `.claude/agents/other-repo-editor.md` that points to the user-level file as a stopgap.
Cheapest test: pipe `{"tool_input":{"subagent_type":"other-repo-editor"}}` into the hook with `CLAUDE_PROJECT_DIR` set to a dev-kit project without that project agent; expect no deny.
Verdict: build differently - ship other-repo-editor as a dev-kit agent (the hook then allows it, the ban on user-level agents stays), update the global rule and hub.md to dev-kit:other-repo-editor; drop the docs-agent part (nothing uses it); complex, one C.
