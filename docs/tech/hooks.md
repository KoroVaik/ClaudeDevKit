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

## Owner session note (dev-kit, UserPromptSubmit)

`plugins/dev-kit/hooks/owner-session-note.py` runs at each of the owner's messages and checks whether the
session is registered with `--owner`; only then it adds the note. Any error in the hook is ignored, so a
failing hook never blocks a message. The rule the user sees:
[Take over a session I started](../features/take-over-a-session-i-started.md).

## Hub rules (pult, SessionStart)

`plugins/pult/hooks/hub-rules.py` adds the hub rules to a session whose cwd is exactly the home folder and
prints nothing elsewhere; see [the plugin README](../../plugins/pult/README.md).
