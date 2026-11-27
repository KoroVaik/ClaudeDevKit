# Retro: skip duplicated tool_use and tool_result lines

Status: started 2026-11-27 by L: ClaudeDevKit, from the `task:` line of Retro: ClaudeDevKit (2026-11-27).

## Task

The retro's task line: «у retro.py пропускати дубльовані рядки tool_use і tool_result за id
(plugins/rules-kit/scripts/retro.py ~869, ~886)». A transcript can hold the same tool_use / tool_result twice (same id);
the retro counts them twice.

## Success criterion

A test transcript with a duplicated tool_use and tool_result (same ids) gives the same retro result as one without the
duplicates; existing tests pass; rules-kit version bumped with its release mark.

## Result

Done 2026-11-27. `analyse` in `plugins/rules-kit/scripts/retro.py` skips a tool_use whose id it already counted and a
tool_result whose tool_use_id it already counted. New test `test_a_tool_use_and_tool_result_written_twice_count_once`;
four fixtures in `tools/tests/test_retro.py` reused one id to fake repeats and now use distinct ids. rules-kit 0.1.3
(routine). Retro, parts, fixes, subscriptions and docs_weekly tests and lint pass; the full suite did not finish in
8 minutes (stuck in a test outside retro, not checked which).

Spend: <0.1% of the weekly limit, estimate; API: 0 USD
