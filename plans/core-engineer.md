# dev-kit: shared core engineer agent with helpers

Status: done, waiting for P's merge (C: Спільний інженер ядра).

Spend: ~0.3% of the weekly limit, estimate; API: 0 USD

Source: BACKLOG.md entry «dev-kit: shared core engineer agent with helpers» (commit 5e08ab2). Owner's yes to take it now: «хвісно!» (= «звісно!») in Zhratva «Обговорення: Інженер ядра аналізу», 2026-11-23. Zhratva's agreed points: Zhratva `plans/core-engineer.md` «Owner's approval» on branch `c/core-engineer` of C:/Users/korov/MyRepositories/Zhratva (read only; never edit that repo). The model for it: Prishch `.claude/agents/core-engineer.md` (read only).

Scope: the entry's What; Prishch's move onto the plugin agent goes as a note to Prishch (BACKLOG-style FYI), not an edit of Prishch. Remove the BACKLOG entry in the same branch.

Fable: every launch of this agent, a test launch included, needs the owner's yes. Ask P before any launch; P asks the owner.

Success criterion: the entry's cheapest test, run after the owner's yes for the one test launch.

## Built

- `plugins/dev-kit/agents/core-engineer.md`: generic engineer (fable, high, `cacheTtl: 1h`); reads the profile's `## core-engineer` section and stops without it; describes a new approach without code first; asks side research as "Helper questions"; writes a handoff note `.claude/helper-notes/<task>-engineer.md` per phase.
- `plugins/dev-kit/agents/investigator.md`: gets Write for helper mode only (a note under `.claude/helper-notes/`, a `.gitignore` of `*` there, conclusions up to about 2k tokens, returns only the path).
- `plugins/dev-kit/skills/manager/SKILL.md`: table row and section "A core engineer and its helpers" (when, yes per launch, continuation vs fresh run, go-ahead for an approach, helper route, no stand-in when the type is missing).
- Docs: `docs/features/solve-a-hard-core-problem.md`, `docs/tech/project-profile.md`, epic link. BACKLOG entry removed. dev-kit 0.1.114, routine.
- Review (dev-kit:reviewer, sonnet): fixed the uncapped helper note, the missing handoff note, the Fable stand-in fallback, the `.gitignore` vs "no other file" clash; added the agent's own stop without a profile section. Accepted: investigator is read-only by prompt, not by tools (the entry asked for its Write).

## Checks

- 1-hour cache: owner said no Fable test launch («це ж вже тестували колись»). Checked from the 20 Prishch `core-engineer` transcripts: runs before `cacheTtl: 1h` (to 2026-11-11) wrote only 5-minute cache, all 7 after it only 1-hour cache. Fact set to checked in `claude-facts.md` by `dev-kit:facts-keeper`.
- Helper route: one round on sonnet (engineer) and haiku (helper) through headless `claude -p` in this worktree, with the agent files copied to `.claude/agents/` for the run (the `narrow-agents` hook reads the plugin agents from the main checkout's marketplace folder, so a `--plugin-dir` copy of a new agent is denied; first run blocked this way). Passed: the engineer stopped with one helper question; the helper wrote `.gitignore` and a 3 KB note and returned only its path; the engineer read the note (transcript Read of the file), answered and wrote its handoff note. Temp copies and notes removed.
- Known gap, not fixed here: `narrow-agents` denies a new plugin agent loaded only by `claude -p --plugin-dir` (it lists agents from the enabled marketplace folder).
- Side hypothesis from the test answer, unchecked: `window_for` (`plugins/dev-kit/scripts/sessions.py:428`) treats a Mythos model id as 200K; no source says what its window is.

## Note for Prishch (FYI, P relays)

dev-kit 0.1.114 has `dev-kit:core-engineer`. Prishch may move onto it: add a `## core-engineer` section to `.claude/dev-kit.md` (core areas Scripts/Solvers and the rendering core, read `docs/standards/engineering.md`, `PROGRESS.md`, `docs/findings/`; never run Unity, the bridge, builds or tests), route the manager to `dev-kit:core-engineer`, then delete `.claude/agents/core-engineer.md`.
