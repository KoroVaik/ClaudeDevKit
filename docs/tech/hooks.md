# Hooks

Code: `plugins/dev-kit/hooks`, `plugins/pult/hooks`.

## Narrow agents (dev-kit, PreToolUse on the `Agent` tool)

`plugins/dev-kit/hooks/narrow-agents.py` runs before each launch of an agent and denies the launch unless
it is allowed. The rule the user sees: [Launch only the project's own agents](../features/launch-only-the-projects-own-agents.md).
A project that had its own copy of this hook removes it.

## Windows traps (dev-kit, PreToolUse on the `Bash` tool)

`plugins/dev-kit/hooks/windows-traps.py` runs before each shell command on Windows and denies one with a known
trap, naming the working form in one line. It reads the shell text with heredoc bodies cut out, so a `python`
written inside a file body is not a launch. A heredoc body or a `python -c` string counts only for the `/tmp`
and size checks. Any error in the hook lets the command run (no `onFailure: block`), so a hook bug never stops
the shell. On other systems it does nothing. The rule the user sees:
[Stop the known Windows shell traps](../features/stop-the-known-windows-shell-traps.md).

## Long commands (dev-kit, PreToolUse on the `Bash` and `PowerShell` tools)

`plugins/dev-kit/hooks/long-commands.py` runs before each shell command and denies a known long one unless the
call sets `run_in_background`. It adds up the waits (`sleep`, `Start-Sleep`, `timeout /t`) in command position and
reads the rows of the profile's `## long commands` section. It cuts heredoc bodies out with the windows-traps
reader, so text in a file body or a commit message is not a command. Any error lets the command run. The rule the
user sees: [Run long commands in the background](../features/run-long-commands-in-the-background.md).

## Owner session note (dev-kit, UserPromptSubmit)

`plugins/dev-kit/hooks/owner-session-note.py` runs at each of the owner's messages and checks whether the
session is registered with `--owner`; only then it adds the note. Any error in the hook is ignored, so a
failing hook never blocks a message. The rule the user sees:
[Take over a session I started](../features/take-over-a-session-i-started.md).

The same hook adds the line of `dev-kit-retro due` to the context of the project's recorded lead session
(P), for example `retro: 3 items due (1 urgent)`: urgent items always count, the others only when the
weekly question to the owner is due. A session that is not the recorded lead gets no line. The line is
built in `retro.due_line` (`plugins/dev-kit/scripts/retro.py`); a broken registry or retro state hides only
its own part, never the other. See [project lead](project-lead.md), section "Retro".

## Retro (dev-kit, SessionStart and SessionEnd)

`plugins/dev-kit/hooks/retro-start.py` and `retro-end.py` call `retro.hook_main("start")` and
`retro.hook_main("end")` in `plugins/dev-kit/scripts/retro.py`. Both act only in a project that has a
lead, print nothing and always exit 0, so a failure never blocks a session. Any other project is left alone.

- SessionEnd (`retro-end.py`): starts a detached scan of the ending session's transcript and returns at once.
- SessionStart (`retro-start.py`): records the lead's session id (a session titled «P: ...»), starts the
  daily scan when it has not run today, and, when new findings wait and the last review is old, starts the
  background «Ретро:» session; once a week it starts the «Документація:» session instead. The «Ретро:» and
  «Документація:» sessions themselves do not trigger it.

What retro finds and does with it: [project lead](project-lead.md), section "Retro".

## Session spend file (spend-kit, SessionEnd)

`plugins/spend-kit/hooks/session-end.py` calls `spend.hook_main()` in `plugins/spend-kit/scripts/spend.py`: it
starts a detached `spend.py write-session --path <transcript>` and returns at once (the hook's limit is 10
seconds), so the ended session's file `sessions/<session id>.json` in the spend-kit data folder appears a moment
later. It runs in every project, prints nothing and always exits 0.

## Hub rules (pult, SessionStart)

`plugins/pult/hooks/hub-rules.py` adds the hub rules to a session whose cwd is exactly the home folder and
prints nothing elsewhere; see [the plugin README](../../plugins/pult/README.md).
