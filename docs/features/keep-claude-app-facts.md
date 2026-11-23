# Keep Claude app facts

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
The official docs say almost nothing about how the Claude apps behave in practice (the desktop and phone apps,
Remote Control, background sessions, hooks). Agents learn it the hard way. One file keeps what was learned, so
every session finds it before it relies on an app, and the facts stay true as Claude changes.

## Rules
### One file, by app, one home per fact
All facts sit in `plugins/dev-kit/claude-facts.md`, grouped by app or area. A fact, its date and its check live
only there; a skill or rule keeps what to do and links to the fact. Not a separate plugin: dev-kit is enabled in
every project of the owner. Not the owner's local docs: they are on one machine and keep no history.
Why: owner, 2026-11-23 (`plans/claude-quirks-docs.md`): such facts were scattered over skills, scripts and notes,
and one of them had two contradicting wordings.

### Every fact has a date, a version, a check and a status
Each entry says what happens, the workaround, the app and Claude Code version, the date, how it was checked and
how to re-check it, and a status: `checked`, `doubtful` or `outdated`. Agents trust `checked` and treat
`doubtful` as a hypothesis.

### Only the facts agent writes it, no owner yes per fact
The `dev-kit:facts-keeper` agent matches each new fact against the file for duplicates and contradictions and
writes it in the one format. It never writes a rule.
Why: owner, 2026-11-23: «обовязково апдейт клод фактів через спец агента, щоб все було стандартищовано».

### Collected in the background, with no questions
The daily scan of session transcripts finds Claude app errors (a failed send to a session, a refused launch) in
every project, Pult and the home folder included, and routes them to the ClaudeDevKit retro. An agent that met a
quiet quirk and worked around it adds one line with `dev-kit-retro add`. Sessions are not made to report facts.
Why: owner, 2026-11-23: collecting facts must not add questions for the owner.

### Re-checked weekly and after a Claude update
The daily scan raises a line when Claude Code's version changes and once a week, so the ClaudeDevKit retro starts
and has the facts agent re-check the file. It runs only safe checks; a failed one marks the fact `doubtful`. Facts only the owner can
see (a phone push, what the phone app shows) reach the owner as one item in P's weekly retro question, at most 5
at a time; a fresh observation from another session settles one before that.
Why: owner, 2026-11-23: «або ж інша сесія внесе факт по цьом питанню, а так ок».

### Every session learns of the file
One line in the owner's global rules, loaded in every session and subagent on the machine, says to read the
matching section before relying on how a Claude app behaves.

## Acceptance criteria
- A session in any project gets a failed send to another session: the next ClaudeDevKit retro hands it to the facts agent.
- The scan sees a newer Claude Code version: the next ClaudeDevKit retro re-checks the facts.
- A doubtful fact only the owner can check reaches him once in the weekly retro question.
- A fact appears once in the plugins; the rules that rely on it link to it.

## Built in
- `plugins/dev-kit/claude-facts.md`
- `plugins/dev-kit/agents/facts-keeper.md`
- `plugins/dev-kit/scripts/retro.py`
- `plugins/dev-kit/skills/retro/SKILL.md`
