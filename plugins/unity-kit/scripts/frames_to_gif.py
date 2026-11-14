"""Make a short animated GIF from a folder of frames, for the owner to see how something moves.

    unity-kit-gif <frames folder> [--index CSV] [--from S --to S] [--fps 12] [--width 480] [--speed 1.0]
                  [--crop X,Y,W,H] [--max-seconds 8] [--max-mb 5] [--out PATH]

The frames are jpg or png files. With an index CSV (default `index.csv` in the folder, if present) each row gives a
frame file (`--file-column`, default `file`) and its time in seconds (`--time-column`, default `sinceStartSeconds`);
without one the frames are taken in name order at `--source-fps` (default 30). The window `--from`..`--to` is in the
time column's seconds. `--crop X,Y,W,H` (source-frame pixels, top-left origin) cuts the same area from every frame
before it is resized; the width never goes above the area's width. Frames are picked at even times for the target fps
from the real times (no duplicates when the source is slower), each frame lasts its real time divided by `--speed`, and
the GIF loops forever. If the file is over `--max-mb`, the script retries with fewer fps and then a smaller width. Prints one line: path, frames, seconds, size,
fps, width; notes about what it did go to stderr. Exit code: 0 done, 2 not done (a clear error). Only the standard
library and Pillow. The `unity-kit:game-clip` skill says when to use it.
"""
import argparse
import bisect
import csv
import os
import sys

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

EXTENSIONS = (".jpg", ".jpeg", ".png")
MIN_FPS = 6.0
MIN_WIDTH = 240
MAX_FPS = 50.0
PALETTE_SAMPLES = 16


class Error(Exception):
    """A reason the clip was not made: exit code 2."""


def note(text):
    print("note: " + text, file=sys.stderr)


def read_index(path, folder, file_column, time_column):
    """Rows of the index as sorted (time, file path) pairs; rows whose file is missing are counted and skipped."""
    try:
        with open(path, newline="", encoding="utf-8-sig") as handle:
            text = handle.read()
    except OSError as error:
        raise Error(f"cannot read the index {path}: {error}")
    lines = text.splitlines()
    if not lines:
        raise Error(f"the index {path} is empty")
    delimiter = max(",;\t", key=lines[0].count)
    reader = csv.DictReader(lines, delimiter=delimiter)
    columns = reader.fieldnames or []
    for column, option in ((file_column, "--file-column"), (time_column, "--time-column")):
        if column not in columns:
            raise Error(f"column '{column}' is not in the index {path} (columns: {', '.join(columns)}); set {option}")
    frames, missing = [], 0
    for number, row in enumerate(reader, start=2):
        name = (row.get(file_column) or "").strip()
        if not name:
            continue
        try:
            seconds = float(row[time_column])
        except (TypeError, ValueError):
            raise Error(f"index row {number}: '{row[time_column]}' in column '{time_column}' is not a number")
        file = next((p for p in (os.path.join(folder, name), os.path.join(folder, os.path.basename(name)))
                     if os.path.isfile(p)), None)
        if file is None:
            missing += 1
        else:
            frames.append((seconds, file))
    if missing:
        note(f"{missing} index rows name files that are not in {folder}; skipped")
    frames.sort(key=lambda frame: frame[0])
    return frames


def read_folder(folder, source_fps):
    names = sorted(n for n in os.listdir(folder) if n.lower().endswith(EXTENSIONS))
    return [(i / source_fps, os.path.join(folder, name)) for i, name in enumerate(names)]


def pick(frames, start, end, fps, speed):
    """Frames at even times: one per 1/fps of playback (speed/fps of source time), the nearest real frame, no repeats."""
    times = [t for t, _ in frames]
    step = speed / fps
    chosen, k = [], 0
    while True:
        target = start + k * step
        if target > end + 1e-9:
            break
        i = bisect.bisect_left(times, target)
        if i > 0 and (i == len(times) or target - times[i - 1] <= times[i] - target):
            i -= 1
        if not chosen or chosen[-1] != i:
            chosen.append(i)
        k += 1
    return [frames[i] for i in chosen]


def durations(picked, speed, fps):
    """GIF frame durations in 10 ms units from the real times, rounded on the running total so the speed stays true."""
    seconds = [(b[0] - a[0]) / speed for a, b in zip(picked, picked[1:])] + [1.0 / fps]
    result, total, given = [], 0.0, 0
    for value in seconds:
        total += value * 100
        units = max(2, round(total) - given)  # browsers play shorter frames at 100 ms
        result.append(units)
        given += units
    return [u * 10 for u in result]


def parse_crop(text):
    try:
        x, y, w, h = (int(part) for part in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError("expected X,Y,W,H as four whole numbers, e.g. 400,156,560,300")
    if w <= 0 or h <= 0 or x < 0 or y < 0:
        raise argparse.ArgumentTypeError("X and Y must not be negative, W and H must be above 0")
    return x, y, w, h


def clip_crop(crop, size):
    """The crop box inside a frame of this size (a note if it stuck out); an error if nothing of it is inside."""
    x, y, w, h = crop
    right, bottom = min(x + w, size[0]), min(y + h, size[1])
    if x >= right or y >= bottom:
        raise Error(f"--crop {x},{y},{w},{h} is outside the {size[0]}x{size[1]} frame")
    if (right - x, bottom - y) != (w, h):
        note(f"--crop {x},{y},{w},{h} sticks out of the {size[0]}x{size[1]} frame; clipped to {x},{y},{right - x},{bottom - y}")
    return x, y, right - x, bottom - y


def load(path, width, crop=None):
    image = Image.open(path).convert("RGB")
    if crop:
        image = image.crop((crop[0], crop[1], crop[0] + crop[2], crop[1] + crop[3]))
    if image.width > width:
        image = image.resize((width, max(1, round(image.height * width / image.width))), Image.LANCZOS)
    return image


def write_gif(picked, speed, fps, width, out, crop=None):
    images = [load(path, width, crop) for _, path in picked]
    # One shared palette from a sample of the frames, so colours do not flicker between frames.
    sample = images[:: max(1, len(images) // PALETTE_SAMPLES)]
    strip = Image.new("RGB", (images[0].width, images[0].height * len(sample)))
    for n, image in enumerate(sample):
        strip.paste(image, (0, n * images[0].height))
    palette = strip.quantize(colors=256, method=Image.MEDIANCUT)
    frames = [image.quantize(palette=palette) for image in images]
    length = durations(picked, speed, fps)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=length, loop=0, optimize=True)
    return len(frames), sum(length) / 1000.0, images[0].width


def make(frames, start, end, fps, width, speed, max_mb, out, crop=None):
    while True:
        picked = pick(frames, start, end, fps, speed)
        count, seconds, real_width = write_gif(picked, speed, fps, width, out, crop)
        size = os.path.getsize(out) / (1024 * 1024)
        if size <= max_mb:
            return count, seconds, size, fps, real_width
        if fps * 0.75 >= MIN_FPS:
            fps, how = round(fps * 0.75, 2), "fewer fps"
        elif width * 0.75 >= MIN_WIDTH:
            width, how = int(width * 0.75), "a smaller width"
        else:
            note(f"{size:.2f} MB is over {max_mb} MB and fps {fps:g} and width {width} are at their floor; kept")
            return count, seconds, size, fps, real_width
        note(f"{size:.2f} MB is over {max_mb} MB: retry with {how} (fps {fps:g}, width {width})")


def run(args):
    if Image is None:
        raise Error("Pillow is not installed (pip install pillow)")
    folder = args.folder
    if not os.path.isdir(folder):
        raise Error(f"the frames folder {folder} does not exist")
    if not 0 < args.fps <= MAX_FPS:
        raise Error(f"--fps must be above 0 and at most {MAX_FPS:g}")
    if args.speed <= 0 or args.width < 16 or args.max_seconds <= 0 or args.max_mb <= 0 or args.source_fps <= 0:
        raise Error("--speed, --max-seconds, --max-mb and --source-fps must be above 0 and --width at least 16")
    index = args.index or os.path.join(folder, "index.csv")
    if args.index or os.path.isfile(index):
        frames = read_index(index, folder, args.file_column, args.time_column)
    else:
        frames = read_folder(folder, args.source_fps)
        note(f"no index: {len(frames)} frames in name order at {args.source_fps:g} fps")
    if not frames:
        raise Error(f"no frames (jpg, png) found in {folder}")
    start = frames[0][0] if args.start is None else args.start
    end = frames[-1][0] if args.end is None else args.end
    if end < start:
        raise Error(f"--to {end:g} is before --from {start:g}")
    longest = args.max_seconds * args.speed
    if end - start > longest + 1e-9:
        end = start + longest
        note(f"the window is longer than --max-seconds {args.max_seconds:g} at speed {args.speed:g}; cut to {start:g}-{end:g}")
    inside = [f for f in frames if start - 1e-9 <= f[0] <= end + 1e-9]
    if not inside:
        raise Error(f"no frames between {start:g} and {end:g} s (the frames cover {frames[0][0]:g}-{frames[-1][0]:g} s)")
    start = inside[0][0]
    with Image.open(inside[0][1]) as first:
        crop = clip_crop(args.crop, first.size) if args.crop else None
        source_width = crop[2] if crop else first.width
    out = args.out or os.path.join(folder, f"clip_{start:g}-{end:g}.gif")
    count, seconds, size, fps, width = make(inside, start, end, args.fps, min(args.width, source_width), args.speed,
                                            args.max_mb, out, crop)
    where = " crop=" + ",".join(str(v) for v in crop) if crop else ""
    print(f"{out} frames={count} seconds={seconds:.2f} size_mb={size:.2f} fps={fps:g} width={width}{where}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Make a short animated GIF from a folder of frames.")
    parser.add_argument("folder", help="folder of jpg/png frames")
    parser.add_argument("--index", help="CSV with the frame file and time columns (default index.csv in the folder)")
    parser.add_argument("--file-column", default="file")
    parser.add_argument("--time-column", default="sinceStartSeconds")
    parser.add_argument("--source-fps", type=float, default=30.0, help="frame rate when there is no index")
    parser.add_argument("--from", dest="start", type=float, help="window start, seconds in the time column")
    parser.add_argument("--to", dest="end", type=float, help="window end, seconds in the time column")
    parser.add_argument("--crop", type=parse_crop, metavar="X,Y,W,H", help="area of the source frame, pixels, top-left origin")
    parser.add_argument("--fps", type=float, default=12.0)
    parser.add_argument("--width", type=int, default=480)
    parser.add_argument("--max-seconds", type=float, default=8.0, help="longest playing time of the clip")
    parser.add_argument("--max-mb", type=float, default=5.0)
    parser.add_argument("--speed", type=float, default=1.0, help="playback speed, 0.5 is slow motion")
    parser.add_argument("--out", help="output file (default clip_<from>-<to>.gif next to the frames)")
    try:
        run(parser.parse_args(argv))
    except Error as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
