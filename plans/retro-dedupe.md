# Retro: skip duplicated tool_use and tool_result lines

Status: started 2026-11-27 by L: ClaudeDevKit, from the `task:` line of Retro: ClaudeDevKit (2026-11-27).

## Task

The retro's task line: «у retro.py пропускати дубльовані рядки tool_use і tool_result за id
(plugins/rules-kit/scripts/retro.py ~869, ~886)». A transcript can hold the same tool_use / tool_result twice (same id);
the retro counts them twice.

## Success criterion

A test transcript with a duplicated tool_use and tool_result (same ids) gives the same retro result as one without the
duplicates; existing tests pass; rules-kit version bumped with its release mark.
