---
name: game-view-check
description: Use when the `check-layout` slot comes up in a Unity project, or the owner asks to see how the game looks in the editor right now ("покажи, як виглядає", "зроби знімок гри", "що на екрані"). Not for judging the look, not for other screen sizes, and never for changing the Game view, a scene or an asset.
---

# Game view check

One screenshot of the Game view at its current size, sent to the owner, who judges it. The agent does
not judge the look. Read the profile section `## game-view-check` of `.claude/dev-kit.md` first: it
names the screenshot command and its folder, and overrides the defaults here. Without that section, tell
the owner the command is missing; never guess one.

## Take

- The manager runs the one screenshot command itself, under the `unity-kit:unity-editor` rules: a
  screenshot is a read and needs no yes. Not while `unity-kit:unity-operator` runs: the editor is one.
- The Game view size, the scene and the assets stay as they are. Never change the size, the aspect or the
  zoom for a screenshot; another size is set by the owner, never by the agent.
- What is on screen is what the owner sees now: the agent does not enter Play Mode, move the camera or
  open a scene for it. If the moment to show needs Play Mode or a scenario, that follows the
  `unity-kit:unity-editor` permissions (the owner's yes for the task).
- One screenshot per question. If the command fails or the editor does not answer, stop and tell the
  owner; no workaround.

## Hand over

- Send the file to the owner with `SendUserFile` (`display: render`) and a one-line caption: what moment
  it shows and what the owner is asked to look at. No verdict on the look.
- The screenshot is temporary: it stays where the command wrote it unless the owner asks to keep it
  somewhere; old output is deleted only at the owner's request.
