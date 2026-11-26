---
name: game-clip
description: Use when the owner asks to see how something moves in the game ("покажи, як це рухається", "зроби гіфку", "відео моменту"), a judgement of motion is needed from a picture, or a built screen's state that changes over time needs its clip (`dev-kit:project-lead`, "Build a designed screen"), in a Unity project. Not for a single still (that is `unity-kit:game-view-check`), never inside a speed check, and never for changing a scene or an asset.
---

# Game clip

A short animated GIF of one moment of play, sent to the owner, who judges how it moves. The caption
handed to the owner gives no verdict on the look; the Manager's own check of a built screen against
real-world references (`dev-kit:project-lead`, "Build a designed screen") still uses the clip's frames.
Read the profile section `## game-clip` of `.claude/dev-kit.md` first: it
names the command that records frames for a moment of play (the project's own capture during a run the
agent starts), and where the frames and their time index land, and it overrides the defaults here.
Without that section, tell the owner which facts are missing; never guess a command.

## Record

- The recording is a Play Mode or player run: it follows the `unity-kit:unity-editor` permissions (the
  owner's yes for the task; the owner's «так» to a screen's mockup counts as that yes for its clips) and
  is run by `unity-kit:unity-operator` with the exact command from the profile. The editor is one: the
  manager runs no Unity command while the operator runs.
- The state to record is reached by the project's own scenario or recipe (`unity-kit:user-check`); a
  state no scenario reaches is told to the owner (a Manager tells its Lead), never faked.
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
- The resolution follows what is judged. A whole head's shape or motion may be a small wide clip. A
  graphic detail (a faint redness, wrinkles, a tear) gets a tight crop at the game's real pixel density
  or higher, wide enough to read the detail (about 600-800 px): bring the camera closer or record at a
  higher resolution for the clip, never upscale.

## Make

- The manager makes the GIF from the frames with `unity-kit-gif <frames folder>` (in `plugins/unity-kit/bin`,
  on the Bash tool PATH while unity-kit is enabled; the script is `plugins/unity-kit/scripts/frames_to_gif.py`,
  Python and Pillow only). `--help` lists the options: the index CSV and its file and time columns
  (`--index`, `--file-column`, `--time-column`), the window (`--from`, `--to`, in the time column's
  seconds), the area (`--crop X,Y,W,H`), `--fps`, `--width`, `--speed`, `--max-seconds`, `--max-mb`, `--out`.
- Limits: short (default up to 8 s), small (480 px wide, about 12 fps, under about 5 MB). The script
  retries with fewer fps and then a smaller width when the file is over; if it is still too big, narrow
  the window instead of dropping below about 6 fps and 240 px. A graphic-detail clip (Focus) lifts the
  width and size limits (`--width`, `--max-mb`) as far as the detail needs.

## Hand over

- Send the file to the owner with `SendUserFile` (`display: render`) and a one-line caption: what moment
  and what area it shows, and what the owner is asked to look at. No verdict on the look. A
  graphic-detail clip's caption also says the resolution used and why it is enough to read the detail.
  A built screen's clip is instead saved where its review session can read it, with the same caption
  facts (`dev-kit:project-lead`, "Build a designed screen").
- The GIF is temporary: it stays where the script wrote it unless the owner asks to keep it somewhere;
  old output (frames included) is deleted only at the owner's request.

Why the detail resolution: owner, 2026-11-26 (Prishch, after 300 px GIFs of a faint redness): «треба щоб
гіфки записувались в роздільній здатності достатній для розуміння того на що треб звернуть увагу ... для
графічних деталией потрібно краща картинка».
