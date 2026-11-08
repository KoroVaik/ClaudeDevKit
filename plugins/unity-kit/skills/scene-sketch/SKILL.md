---
name: scene-sketch
description: Use when a game idea must be shown as a picture - the `show-idea` slot while brainstorming in a Unity project, or the owner asks to sketch a moment, a scene or a sequence of play ("намалюй ідею", "покажи, як це буде"). Not for judging how the game looks, and never for changing a scene or an asset.
---

# Scene sketch

A storyboard of one moment of play: 2-6 frames with a one-line caption each, drawn as one self-contained
SVG or HTML page. It is a draft for discussion, not accepted art and not a scene. Read the profile
section `## scene-sketch` of `.claude/dev-kit.md` if it exists: it gives the usual subject, the names to
use and the caption language, and overrides the defaults here.

## Draw

- One idea per sketch. Frames go left to right in the order the player lives them; each shows only what
  the idea changes, plus enough context to recognise the place.
- Simple shapes, outlines and arrows; labels use the glossary names. No textures, no lighting, no detail
  the idea does not need: a sketch that looks finished gets judged as art.
- A frame may use a real screenshot of the Game view as its background, with the idea drawn over it.
  The screenshot is a read under the `unity-kit:unity-editor` permissions (no yes needed); never change
  the Game view, the scene or an asset for it.
- One light palette, fixed in the page; no theme switching. Text stays readable at half size.
- Captions: what the player does and sees, in the profile's caption language. Mark guesses as guesses.

## Hand over

- Write the page to the session scratchpad, never to the repo. Render it to a PNG beside it (a headless
  browser screenshot with a temporary profile, not the owner's browser), look at the PNG yourself and fix
  cut or overlapping text. Send the PNG, not the page (a client may not show HTML), with `SendUserFile`
  (`display: render`) and a one-line caption naming the idea; the page only when the owner asks.
- A sketch (the page and its PNG) is temporary: delete it once the surviving ideas are in `BACKLOG.md` (the
  `dev-kit:brainstorm` rules). A sketch the owner wants kept goes where the owner says.
- No 3D, no generated art and no new tool in the project for a sketch.
