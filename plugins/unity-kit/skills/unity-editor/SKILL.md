---
name: unity-editor
description: Use when an agent is about to do anything in Unity in a project that enables unity-kit - a compile, a Play Mode run, a build, a run of the built player, a device, the Profiler, a screenshot or an editor-state question - or to change a scene, an asset or a project setting.
---

# Working with the Unity editor

The owner works in the same open Unity editor that the agents drive. This skill holds the permissions
and the procedure for every Unity action. Read the profile section `## unity-editor` of
`.claude/dev-kit.md` first: it names the project's bridge and wrapper command, where the commands are
documented, the versions, the scene, the build targets, the devices and the Profiler, and it overrides
the defaults here. Without that section, tell the owner which facts are missing; never guess a command.

## The bridge

- Agents reach Unity only through the bridge the profile names. Use the project's wrapper command; call
  the bridge directly only for what the wrapper cannot do, and check its syntax with `--help` first. Do
  not invent commands or flags.
- Never enable a bridge's arbitrary code execution and never change the bridge's version without the
  owner's agreement.
- Who runs what: the manager runs the short commands (compile, editor state) itself; everything longer
  goes to `unity-kit:unity-operator` with the exact commands and the owner's consent in its brief. One
  Unity operator at a time: the editor is one, and the manager runs no Unity command of its own while
  the operator runs.

## Permissions

| Action | Permission |
|---|---|
| Reading: console, hierarchy, scene objects, editor or game state, a screenshot of the editor or the Game view | without asking |
| A compile after the agent's own code change | when the owner agreed to a compile check in the task |
| A Play Mode run, a build, a run of the built player, a device, the Profiler | the owner's yes for the task |
| Changing a scene, an asset or a setting (the Game view size included) | a separate yes, rules under "Scene" |

- A screenshot goes to the owner as a file; the owner judges the look, the agent does not.
- Old run output is deleted only at the owner's request.

## Order of a run

- While a command runs, the editor is busy: warn before a long one (a Play Mode run, a build).
- One command at a time and one blocking wait. No polling, watcher scripts or parallel commands.
- Compile first. Then, for speed, a build if code changed since the last one; then the runs one by one.
  No build or player run while the editor is in Play Mode or compiling.
- During Play Mode the bridge may not answer: do not poll it; wait once for the end signal the profile
  names, at most repeats x timeout plus one minute.
- A built player: one blocking wait for its exit, at most repeats x timeout plus two minutes. If it did
  not exit, stop that process (only the one the agent started) and tell the owner.
- A build that switches the target keeps the editor busy for the whole time (the first switch may take
  tens of minutes): one build at a time.
- The editor does not answer, or a compile, build or launch fails: stop and tell the owner. No workaround.
- Never restart, close or kill Unity. No batchmode or command-line Unity without the owner's separate
  request: the open editor holds the project.
- `Editor.log` (on Windows `%LOCALAPPDATA%/Unity/Editor/Editor.log`) is a read-only error source.

## Devices

Only the device commands the profile names, plus read-only questions. Never change a device's settings,
uninstall or delete anything on it beyond what the profile allows. A device that is not seen, not
allowed or locked: tell the owner, who acts.

## Scene

- By default the agent only reads the scene.
- A change only with a separate permission in chat, only through the open editor after the owner has
  saved their work, and undoable with a single Ctrl+Z.
- Never change a scene file on disk while the editor is open. A compile must not reload a scene changed
  on disk (the profile names the option that refuses instead).
- A command that would save, discard or reload the owner's unsaved scene runs only with the option that
  refuses instead (for example `uloop run-tests --unsaved-changes fail`).
