# Plan: the narrow-agents hook lets the built-in web-fetch helper pass

Status: done (2026-11-26).

Source: «Retro: ClaudeDevKit» 2026-11-26, task line: «in hooks/narrow-agents.py let the built-in web-fetch agent pass (blocked in every dev-kit project, session 569da651 L91)». Started by the Lead with no owner ask (dev-kit:project-lead, "Retro of session problems").

Success criterion: an Agent call with subagent_type `web-fetch` passes `plugins/dev-kit/hooks/narrow-agents.py` in a dev-kit project; the cases the hook blocks today stay blocked; a test covers both; dev-kit version bumped with a routine release mark.

Result: `narrow-agents.py` lets the built-in `web-fetch` pass (constant BUILT_IN_AGENTS, also listed in the deny reason);
other built-in types and lookalikes (`web-fetch-extra`, `dev-kit:web-fetch`) stay denied. Three new tests in
`tools/tests/test_narrow_agents.py`, all 41 pass. Feature doc updated; dev-kit 0.1.136, routine mark.

Spend: ~0.1% of the weekly limit, estimate; API: 0 USD
