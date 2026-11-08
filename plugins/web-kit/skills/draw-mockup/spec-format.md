# Mockup spec format

Low-fidelity wireframes of user flows: phone screens by default, wide desktop screens with `"frame": "desktop"`
(see "Desktop boards"). Each mockup is a JSON spec in `<mockups folder>/src/`
(the folder defaults to `docs/mockups`); the generator `web-kit-mockups` turns the specs into the HTML
pages next to `src/` and an `index.html`. Pages open in a browser without a server.

```bash
web-kit-mockups                          # write all HTML files
web-kit-mockups --check                  # validate specs and fail if the HTML is stale
web-kit-mockups --dir <mockups folder>   # another folder than docs/mockups
```

Never edit the generated `*.html` files by hand: the next build overwrites them. Every page carries a copy of
`mockups.css` of the mockups folder inside it, so one sent file keeps its look; the project owns that file
(palette, phone frame), so a new look for every mockup is one change there and a rebuild (`--check` reports
the pages stale until then). The project's `mockups.css` wins: when the folder has none, the generator
writes a neutral default (`scripts/default-mockups.css` of the plugin) as `mockups.css` once and never
overwrites an existing file, so a project restyles by editing its own copy. Optional `mockups.config.json` in the mockups folder sets the texts
that differ per project: `title` (index title, default "Mockups"), `pageNote` (the line under every
board's title), `indexNote` (a line under the index title; `` `code` `` spans work), `userLetters`
(`{ "A": "A", "B": "B" }`: the letters shown in the phone tag for users A and B), `stepTitle` (the hover text of
the step dots, default "Step {current} of {total}"), `indexIntro` (the line under the index title, `{count}` is the
number of mockups), `filterPlaceholder` (the index search box) and `screenCount` (the line under each index entry,
`{count}` is its number of screens). Every text a viewer reads can be set here in the project's language.

The generator is run from anywhere inside the project's git repository and resolves `docs/mockups` from the
repository root; with `--dir` the folder is relative to the current directory. The folder (with its `src/`)
must exist: the generator never creates it.

## Spec (`src/<flow-name>.json`)

The file name is lowercase words joined by hyphens and becomes the page name.

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | Page title and index entry. |
| `group` | no | Section in the index (for example `Choice`); default `Other`. |
| `summary` | no | One line in the index. |
| `source` | no | Where the flow is described (for example `docs/features/pick-item.md`). Kept in the JSON, not shown. |
| `notes` | no | At most one short line (160 characters) under the title, for the viewer. |
| `authorNotes` | no | Service text for the next editor: sources, what is approximated or left out, decisions. Never shown. |
| `frame` | no | `phone` (default) or `desktop` ("Desktop boards"). |
| `phones` | yes | Map `id` -> phone (below). A desktop board may call it `screens`. |
| `layout` | yes | Rows of cells that place the phones (below). |

### Phone

`caption` (required, shown above the frame) and `blocks` (the screen content). Optional `user`
(`A` or `B`) colors the frame, and optional `step` (number) goes with it into a tag before the
caption ("A1"). Optional `overlay` dims the screen and
shows a `popup` (`closable: false` hides the ×) or a `sheet` (bottom sheet with an optional
`title`); the overlay has its own `blocks`.

### Blocks

Block names such as `dish` and the day-header `tone` values (`choice`, `chosen`, `cooking`, `done`) are the kit's own vocabulary.

| Type | Fields |
|---|---|
| `topbar` | `title`, `aside`, `progress` (`{ "current": 0, "total": 4 }`: compact step dots in the title row). With `tone` (`choice`, `chosen`, `cooking`, `done`) it becomes a day header instead, a band in a muted color of that step: `back` (where it returns) draws a round «‹» before the title, `titleHint` adds a faint «?» after the title and `titleHintOpen: true` draws that hint, `partner` (`{ user, status, initial, hint }`) shows the partner's letter and status at the right (`…` is drawn as animated dots, `hint` is the bubble after a tap), and `bar` (`{ "current": 1, "total": 4 }`) draws the thin step line in the tone color |
| `dish` | `photo` (placeholder label), `badge`, `name`, `sub`, `tone` (`ok` or `warn`), `big`, `reject` (`{ taste, general }`: two chip lists drawn over the photo on a translucent red layer, split by a thin line), `peek` (the card is cut by the bottom edge to show the list scrolls) |
| `photo` | `label`, `badge`, `big` |
| `name` | `text` (bold line) |
| `text` | `text` (muted line) |
| `field` | `label`, `placeholder` (a text input) |
| `bar` | `width` (1–100, a placeholder text line) |
| `spacer` | pushes the next blocks to the bottom |
| `buttons` | `items`: strings or `{ text, kind, caption }` (`caption` is a small grey line under the button), kind `plain`, `save` or `approve`; 2+ items form one row |
| `chips` | `items`: strings or `{ text, on, size, tone }`; `size` is `s`, `m` or `l` (default is between `s` and `m`); `tone` is `warn` or `danger` |
| `tabs` | `items`, `active` (index) |
| `list` | `rows`: `[left]` or `[left, right]`; `thumbs: true` draws a small photo before each row, `thumbs: "l"` a larger one |
| `tabbar` | `items`, `active` (index); put a `spacer` before it to pin it to the bottom |
| `columns` | desktop areas side by side: `cols`, 2+ entries `{ width, blocks }`; `width` is px (a number) or `"1fr"`, `"2fr"` (default `1fr`) |
| `card` | a titled panel: `title`, `aside` (grey text at the right of the title), `tone` (`ok`, `warn`, `danger`: the border color), `muted: true` (faded back), `blocks` |
| `region` | a labelled area of a page map: `title` (required on the `on` region; on a map leave it out where the name does not fit, but keep a few names so the viewer can tell where the region is), `on: true` (highlights the area a flow is about: solid colored border and a light fill), `blocks` (nested blocks, typically more `region` or `columns` of regions; without them two faint bars under the title mean "this area has content"), `cover: true` (with `blocks`: the blocks keep their size; the `on` region draws them as a text-free skeleton, others hide them behind two bars, "Page map") |
| `toast` | `text`, `action` (for example "Undo"), `oneLine: true` (cut the text with an ellipsis instead of wrapping), `expanded` (`{ title, collapse }`: the opened state with a small photo, the full `title` and a «collapse» line) |
| `part` | `name`: a reusable block list from `parts/<name>.json`, expanded in place ("Parts"); no other fields |

### Layout

`layout` is a list of rows; each row is a list of cells, placed left to right on a grid.

| Cell | Meaning |
|---|---|
| `{ "phone": "<id>" }` | A phone; every phone is placed exactly once. |
| `{ "link": "text", "dir": "right" }` | An arrow between phones labelled with the user action; `dir` is `right` (default, label under the arrow) or `down` (label above the arrow, right under the screen it happens on). |
| `{ "note": "text", "span": 3 }` | A text note over several columns; `**bold**` and `\n` work. |
| `{ "branch": "title", "given": "text" }` | Starts a path of the flow: a full-width divider, a bold title and an optional precondition (`**bold**` works). Alone in its row. |
| `null` | An empty cell. |

Tracks that contain only arrows are narrow automatically. Put the happy path in row 1 and
branches in the rows below.

## Desktop boards

`"frame": "desktop"` draws every screen as one wide admin-style page (width `--screen-w` in `mockups.css`, default
1440 px) instead of a 250 px phone. Put one screen per layout row and join rows with `{ "link": "...", "dir": "down" }`;
branches and notes work as on a phone board. A screen takes `caption`, optional `step`, `blocks`, and:

- `menu` - `{ items, active }`: the left menu rail (250 px). Without it the content uses the full width.
- `overlay` - only `popup` (centered, dims the whole screen).
- `width` - an integer 240-1440 (px) that sets this screen's width instead of `--screen-w`. A screen with `width` has no
  forced minimum height: it is as tall as its content. A phone screen with `width` fails the build.
- `scale` - a number 0.2-1 that draws the whole screen smaller (the page map, "Page map"); names on covered
  regions grow back so they stay readable, and the menu rail loses its text. Desktop boards only.
- `map: true` - the page map screen ("Page map"): a compact chip, left-aligned in the board, with the caption and a tiny
  thumbnail of the page (the highlighted region filled, the other regions outlines, no names). A click opens the readable
  map as a popover under the chip, over the flow's screens, so the board does not move; a click on the map, on the chip,
  outside the map or Escape folds it. Drawn at `scale` (default `0.4`). Desktop boards only.

`columns` and `card` build the page area; all other blocks work as on a phone, restyled for a desktop (`topbar` is the
page heading, `tabs` are page tabs, buttons keep their width). `user` is for phone boards only. One mockups folder
holds one kind of board: a project with both keeps phone boards and desktop boards in separate folders (`--dir`).

### Page map

A flow that concerns only one part of a page shows only that part. It starts with a map screen (`map: true`, folded
until the viewer opens it, so a flow whose place is clear from its title costs no space): the real page, scaled down, each section wrapped in a `region` with `cover: true` and the region the
flow is about marked `on: true`. A covered region keeps its blocks' real size and place, so the map has the page's
proportions; the `on` region draws them as a skeleton (shapes without text), every other region hides them behind two
calm bars, so the map stays quiet. The name sits on the region's border. Build the page from parts
(one part per section) and use the same parts in the full-page mockup and in the map, so the two never drift. Leave
out the names that do not fit; keep a few so the viewer can tell where the region is. The screens that follow draw
that part only, each at its own `width` (for example the width of the part in the real page).

## Parts

A piece that repeats in several mockups (a table, a page header, a menu) is described once as a part:
`<mockups folder>/parts/<name>.json`, next to `src/`. The file name is lowercase words joined by hyphens; the
content is a non-empty JSON array of blocks, the same objects a screen's `blocks` holds. The folder is optional.

```json
{ "type": "part", "name": "dishes-table" }
```

The `part` block works wherever a block list does (screen `blocks`, overlay `blocks`, `columns` and `card`
blocks). At build time it is replaced by the part's blocks, which are validated and drawn like inline ones, so a
rebuild updates every mockup that uses the part, and `--check` fails while a generated page is stale after a
part changed. Parts may use other parts. Parts are not mockups: they are not listed in `index.html` and
produce no page.

A part takes no parameters or overrides. A flow that needs the piece in a changed state writes those blocks
inline instead of using the part.

The build fails, naming the file, on: an unknown part name (the message names the missing `parts/<name>.json`), a
part that is not a JSON array of blocks, a part that includes itself (the message gives the chain, for example
`a -> b -> a`) and extra fields on a `part` block. Every file in `parts/` is checked, also when no spec uses it yet.

## Rules

- A mockup is a draft for discussion, not an accepted UI and never a product decision.
- Organize many mockups with `group`; the index has a filter box.
- A missing block type means the generator needs a new block: add it to
  `scripts/build-mockups.mjs` of the `web-kit` plugin (and the class to the project's `mockups.css`)
  when two or more mockups need it.
