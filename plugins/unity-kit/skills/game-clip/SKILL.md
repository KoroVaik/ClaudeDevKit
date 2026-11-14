---
name: game-clip
description: Use when the owner asks to see how something moves in the game ("покажи, як це рухається", "зроби гіфку", "відео моменту") or a judgement of motion is needed from a picture, in a Unity project. Not for a single still (that is `unity-kit:game-view-check`), not for judging the motion, never inside a speed check, and never for changing a scene or an asset.
---

# Game clip

A short animated GIF of one moment of play, sent to the owner, who judges how it moves. The agent does
not judge the look. Read the profile section `## game-clip` of `.claude/dev-kit.md` first: it names the
command that records frames for a moment of play (the project's own capture during a run the agent
starts), and where the frames and their time index land, and it overrides the defaults here. Without
that section, tell the owner which facts are missing; never guess a command.

## Record

- The recording is a Play Mode or player run: it follows the `unity-kit:unity-editor` permissions (the
  owner's yes for the task) and is run by `unity-kit:unity-operator` with the exact command from the
  profile. The editor is one: the manager runs no Unity command while the operator runs.
- If the command fails or the editor does not answer, stop and tell the owner; no workaround.
- Never in a speed check: a clip costs run time and disturbs the numbers. A clip is its own run.

## Focus

- The moment: the manager chooses the time window from the run's step times (the index, the run log),
  not the whole run. Slow motion (`--speed` below 1) only when the owner asks or the moment is too fast
  to see.
- The area: crop (`--crop X,Y,W,H`, source-frame pixels, top-left origin) to what the owner must look
  at, for example the area around the objects the scenario moves; a cropped clip is the preferred kind.
  Take the positions from the project's own frame marks if the profile names them. Pad the box so the
  object stays inside while it moves. No crop when the whole picture is the point. A box that sticks out
  of the frame is clipped with a note.

## Make

- The manager makes the GIF from the frames with `unity-kit-gif <frames folder>` (in `plugins/unity-kit/bin`,
  on the Bash tool PATH while unity-kit is enabled; the script is `plugins/unity-kit/scripts/frames_to_gif.py`,
  Python and Pillow only). `--help` lists the options: the index CSV and its file and time columns
  (`--index`, `--file-column`, `--time-column`), the window (`--from`, `--to`, in the time column's
  seconds), the area (`--crop X,Y,W,H`), `--fps`, `--width`, `--speed`, `--max-seconds`, `--max-mb`, `--out`.
- Limits: short (default up to 8 s), small (480 px wide, about 12 fps, under about 5 MB). The script
  retries with fewer fps and then a smaller width when the file is over; if it is still too big, narrow
  the window instead of dropping below about 6 fps and 240 px.

## Hand over

- Send the file to the owner with `SendUserFile` (`display: render`) and a one-line caption: what moment
  and what area it shows, and what the owner is asked to look at. No verdict on the look.
- The GIF is temporary: it stays where the script wrote it unless the owner asks to keep it somewhere;
  old output (frames included) is deleted only at the owner's request.
