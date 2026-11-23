# Run long commands in the background

Epic: [Run a task through the process](../epics/run-a-task.md)

## Purpose
A long command run in the foreground holds the session: the owner cannot talk to it until the command ends. The
owner's global rule already says a wait over about a minute runs in the background, but a text rule did not stop
it (Zhratva, 2026-11-05: a store repair ran in the foreground). Now a known long command run in the foreground is
refused before it runs, with the fix named, so the agent runs it again in the background.

## Rules
### Known long commands
- A wait of 60 seconds or more: `sleep`, `Start-Sleep`, `timeout /t`. The waits of one command are added up, so
  `sleep 30; sleep 30` counts as 60.
- A command the project lists in its profile `.claude/dev-kit.md`, section `## long commands`, as a row
  `` | `<Python regex>` | <why> | ``. The why is shown in the refusal. A row with a broken regex is skipped.
  Example: `` | `court\.py\s+(repair|check)-all` | the whole-store court runs for minutes | ``.

### What passes
- The same command with `run_in_background: true`.
- A wait under 60 seconds, a wait written inside text (a quoted string, a heredoc body such as a commit message)
  and GNU `timeout N <command>`, which is a time limit, not a wait.

### Both shells
The hook is on the Bash and the PowerShell tools, on every system.
Claude Code itself already blocks a lone long `sleep` or `Start-Sleep` ([Claude facts](../../plugins/dev-kit/claude-facts.md),
"Claude Code blocks a lone long `sleep`"); the hook adds a wait inside a longer
command (`echo start; sleep 70; echo end`) and the project's own list.

How the hook works: [hooks](../tech/hooks.md).

## Acceptance criteria
- `sleep 120` in a foreground Bash call: refused; the reason says to run it with `run_in_background`.
- `sleep 120` with `run_in_background: true`: runs.
- `Start-Sleep -Seconds 120` in a foreground PowerShell call: refused.
- A command matching a row of the project's `## long commands`: refused, the reason is the row's why.
- `sleep 5`, `echo "sleep 120"` and a commit message with `sleep 120` in a heredoc: run.

## Built in
- `plugins/dev-kit/hooks/long-commands.py`
- `plugins/dev-kit/hooks/hooks.json`
- `tools/tests/test_long_commands.py`

## Open
- [ ] Zhratva lists its whole-store court commands in its profile's `## long commands`; needs the owner's yes to a migration entry or a Zhratva task
- [ ] Record commands that took over 60 seconds, to suggest new `## long commands` rows; idea from the backlog entry, not agreed
