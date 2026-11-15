# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. An idea leaves the backlog when the owner agrees
it and it is built, or when the owner drops it.

Entry: a `##` title, then `What:`, `Why:` (the concrete case that showed the need: project, date) and
`Cheapest test:`, 2-4 lines in all. A reviewed entry gets a `Verdict:` line (the project lead's
recommendation) and waits for the owner's yes or no.

## Move cross-project things from dev-kit to Pult

What: remove the `list-desktop` command from `plugins/dev-kit/scripts/sessions.py` and its tests in `tools/tests/test_sessions.py`; `plugins/dev-kit/skills/project-lead/SKILL.md` (~line 37) uses it, so that lead step needs a replacement (e.g. `claude agents --json --cwd <repo>`) or removal. Remove or shorten "Working with the project lead (P)" in `README.md` (~lines 153-171), stale since Pult starts P at logon, and point to Pult (`C:/Users/korov/MyRepositories/Pult`) for the phone flow. Boundary: the plugin covers work inside one repository (manager, lead, session registry, fill, PROGRESS.md format); Pult covers anything across projects or the machine (project list, server/P start, watcher, phone flow, all-project session list).
Why: the owner approved this boundary on 2026-11-15 (project: Pult, the phone hub over all projects). Pult now has its own copies: `scripts/list-sessions.py` (port of `dev-kit-sessions list-desktop`) and the phone flow in its `README.md`, so the plugin copies duplicate and drift.
Cheapest test: `claude agents --json --cwd <repo>` lists the repo sessions the lead step needs; after removal the sessions tests pass and `grep -r list-desktop` finds nothing in the plugin repo.
