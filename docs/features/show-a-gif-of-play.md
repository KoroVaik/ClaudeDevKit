# Show a GIF of play

Epic: [Check and show Unity play](../epics/check-and-show-unity-play.md)

## Purpose
The owner sees a short GIF of a moment of play and judges the motion. A built screen's state that
changes over time comes with its clip next to the mockup.

## Rules
### Who does what
`unity-kit:game-clip` fills no slot. The operator records frames with the project's own capture; the
manager makes the GIF with `unity-kit-gif` (Python and Pillow) and sends it; the owner judges the motion.

### Window and crop
The GIF is cut to a time window and, preferably, cropped around what moves. A small graphic detail
(a faint redness, a tear) gets a tight crop at the game's real pixel density or higher, about 600-800 px
wide, never an upscale; its caption says the resolution and why it is enough.

The project's frame-recording command and where the frames land go in its profile
([sections](../tech/project-profile.md)).

## Acceptance criteria
- The owner asks to see a moment of play: the operator records frames and the owner receives a GIF of that window.
- The GIF is cropped around what moves, when the moving part is small.
- A clip of a graphic detail is sharp enough to read it, with no upscaled pixels.
- A built screen's moving state reaches the owner as a clip next to its mockup, not only as a still.

## Built in
- `plugins/unity-kit/skills/game-clip`
- `plugins/unity-kit/scripts/frames_to_gif.py`
- `plugins/unity-kit/bin/unity-kit-gif`
- `tools/tests/test_frames_to_gif.py`
