# Backlog

Ideas for the plugins (`dev-kit`, `web-kit`, `unity-kit`) that the owner has not agreed yet. Agents in
other projects add their wanted plugin changes here instead of editing the plugins; the plugin's own
agent decides and builds them after the owner's yes. An idea leaves the backlog when the owner agrees
it and it is built, or when the owner drops it.

Entry: a `##` title, then `What:`, `Why:` (the concrete case that showed the need: project, date) and
`Cheapest test:`, 2-4 lines in all. A reviewed entry gets a `Verdict:` line (the project lead's
recommendation) and waits for the owner's yes or no.

## Long-term quality over speed, in every project

What: move the principle "Long-term quality over speed" from Zhratva's `CLAUDE.md` into dev-kit so it holds in every project: the owner cares about the durable result, so when a step needs tooling, build the proper reusable piece, not a one-off hack. Added clarification: the principle chooses the design of what a plan lists; it does not add fixes, steps or review rounds beyond the plan and its two-round cap.
Why: on 2026-11-14 a Zhratva feature task ran very long because "quality" was read as licence to fix every reviewer doubt in extra rounds run one after another.
Cheapest test: after the move, run one small plan with a reviewer doubt below the report threshold and check that it is recorded, not fixed in an extra round.
