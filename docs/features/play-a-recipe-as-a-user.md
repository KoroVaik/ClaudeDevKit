# Play a recipe as a user

Epic: [Check and show Unity play](../epics/check-and-show-unity-play.md)

## Purpose
A scripted "user check" plays the game the way a user does and reports what happened, so a change to play
is checked without the owner pressing keys.

## Rules
### Who does what
`unity-kit:user-check` fills the `check-ui` slot. Any agent writes a recipe of play (keys, mouse, the
project's own bridge commands, expectations on the console, state and files); the operator runs it with
`unity-kit-user-check <name>` and returns the report; the manager concludes.

### The plugin ships no Unity code
The project copies the sample state and IMGUI mouse commands from
`plugins/unity-kit/skills/user-check/samples/`.

The project's bridge, recipe and report folders, scene, state command and click command go in its profile
([sections](../tech/project-profile.md)).

## Acceptance criteria
- An agent writes a recipe: the operator plays it in the open editor and a report comes back.
- An expectation on the console, the state or a file fails: the report says so and the manager concludes.

## Built in
- `plugins/unity-kit/skills/user-check`
- `plugins/unity-kit/scripts/user_check.py`
- `plugins/unity-kit/bin/unity-kit-user-check`
- `plugins/unity-kit/agents/unity-operator.md`
- `tools/tests/test_user_check.py`
