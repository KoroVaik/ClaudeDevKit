# Check and show Unity play

Part of the [ClaudeDevKit product](../product.md).

## What it gives

The `unity-kit` plugin works with the owner's open Unity editor: it checks play, sketches a moment of play
and shows it. It fills `show-idea` with `unity-kit:scene-sketch`, a temporary storyboard of one moment of
play, `check-look` with `unity-kit:game-view-check`, one screenshot of the Game view at its current
size for the owner to judge, and `check-ui` with `unity-kit:user-check`, a recipe of play run in the
editor ([slots](../../plugins/unity-kit/slots.md)).

`unity-kit:unity-editor` holds the permissions and the order of every Unity action in the owner's open
editor (no batchmode, no restart, one operator at a time); it fills no slot, so a project fills `run-app`
and `run-tests` with its own commands or skills. `unity-kit:unity-operator` runs the Unity commands the
manager chose and returns raw results. The project's facts go in its profile
([sections](../tech/project-profile.md)).

## Features

- [Show a GIF of play](../features/show-a-gif-of-play.md)
- [Play a recipe as a user](../features/play-a-recipe-as-a-user.md)

## Not written yet

`scene-sketch`, `game-view-check` and `unity-editor` have no feature files; their rules stay in
`plugins/unity-kit/skills`.
