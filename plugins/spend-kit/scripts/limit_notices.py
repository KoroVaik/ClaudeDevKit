"""The limit notices to the project leads, from the status line's usage log.

    python limit_notices.py notices --mark FILE [--log FILE] [--now EPOCH]

The Pult watcher (plugins/pult/scripts/watch-servers.ps1) runs it. The log is the one `statusline.py` writes
(`{ts, week_pct, week_resets, five_hour_pct}`, env DEV_KIT_USAGE_LOG or `~/.claude/spend-kit`): the real account per
cent, so no retro estimate is used here. The weekly limit forecast push it once also made was removed by the owner on
2026-11-25 (plans/drop-forecast-push.md).

`notices` (docs/features/wind-down-at-weekly-limit.md, plans/limit-wind-down.md): the Pult watcher runs it when the
usage log changed or every few minutes and sends each printed text to the project leads. Thresholds: WEEK_AT for the
weekly limit (90, 95, 98), FIVE_AT for the 5-hour one (90). The last log line with a reset time in the future gives the
per cent of each limit (a weekly reading from any line, a 5-hour one from a line with `five_hour_resets`). A notice is
due for the highest threshold the per cent reached that this window has no notice for yet; every threshold up to it
is then marked done, so a jump from 80 to 96 gives one notice, for 95. Once the reset time of a window that got a
notice has passed, one `back` line is due and the mark keeps only that reset time (`over`), so a late reading of the
window that has reset gives no new notice. `--mark FILE` holds `{"week": {"resets": <epoch>, "done": [90]},
"five": {"over": <epoch>}}`; reset times under SAME_WINDOW_S apart are one window.
Prints zero or more lines, `back` ones first:

    notice | week|five | <threshold> | <per cent> | <reset epoch> | ЛІМІТ: тижневий 95%, оновиться пн 10:00
    back | week|five | <reset epoch> | ЛІМІТ: тижневий ліміт оновився, можна будити призупинені сесії
"""
import argparse
import datetime
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from statusline import SAME_WINDOW_S, log_file, number  # noqa: E402

DAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "нд")
WEEK_AT = (90, 95, 98)  # weekly notice thresholds, per cent; 98 is the reserve stop (plans/limit-reserve-98.md)
FIVE_AT = (90,)  # 5-hour notice thresholds, per cent
LIMIT_NAMES = {"week": "тижневий", "five": "5-годинний"}


def local_text(epoch):
    t = datetime.datetime.fromtimestamp(epoch)
    return f"{DAYS[t.weekday()]} {t:%H:%M}"


def last_limits(path, now):
    """{'week' | 'five': (per cent, reset epoch)} from the last log line of each that has a reset time after now."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return {}
    out = {}
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        for limit, pct_key, resets_key in (("week", "week_pct", "week_resets"), ("five", "five_hour_pct", "five_hour_resets")):
            pct, resets = number(entry.get(pct_key)), number(entry.get(resets_key))
            if limit not in out and pct is not None and resets is not None and resets > now:
                out[limit] = (float(pct), float(resets))
        if len(out) == 2:
            break
    return out


def read_mark(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def notice_text(limit, threshold, resets):
    return f"ЛІМІТ: {LIMIT_NAMES[limit]} {threshold}%, оновиться {local_text(resets)}"


def back_text(limit):
    return f"ЛІМІТ: {LIMIT_NAMES[limit]} ліміт оновився, можна будити призупинені сесії"


def notices(log, mark, now):
    """The output lines of `notices` (see the module doc); writes the mark when a line is due."""
    state = read_mark(mark)
    current = last_limits(log, now)
    lines, changed = [], False
    for limit, thresholds in (("week", WEEK_AT), ("five", FIVE_AT)):
        seen = state.get(limit) if isinstance(state.get(limit), dict) else None
        seen_resets = number(seen.get("resets")) if seen else None
        over = number(seen.get("over")) if seen else None  # the reset time of the last window that has reset
        if seen is not None and seen_resets is not None and seen_resets <= now and "done" in seen:
            if seen.get("done"):
                lines.append(f"back | {limit} | {int(seen_resets)} | {back_text(limit)}")
            state[limit] = {"over": seen_resets}
            seen, over, changed = None, seen_resets, True
        elif seen is not None and "done" not in seen:
            seen = None  # only the reset mark of an older window
        if limit not in current:
            continue
        pct, resets = current[limit]
        if over is not None and abs(resets - over) < SAME_WINDOW_S:
            continue  # a reading of the window that has reset (its reset time jitters a little later)
        if seen is None or seen_resets is None or abs(seen_resets - resets) >= SAME_WINDOW_S:
            seen = {"resets": resets, "done": []}  # a new window (an older one not yet reset is replaced)
        done = [t for t in seen.get("done", []) if isinstance(t, (int, float))]
        reached = [t for t in thresholds if pct >= t]
        if reached and max(reached) not in done:
            top, resets = max(reached), seen["resets"]  # one reset time per window: the watcher keys its leads by it
            lines.append(f"notice | {limit} | {top} | {pct:g} | {int(resets)} | {notice_text(limit, top, resets)}")
            state[limit] = {"resets": resets, "done": sorted(set(done) | set(reached))}
            changed = True
    lines.sort(key=lambda line: not line.startswith("back"))
    if changed:
        Path(mark).parent.mkdir(parents=True, exist_ok=True)
        Path(mark).write_text(json.dumps(state), encoding="utf-8")
    return lines


def main(argv=None):
    parser = argparse.ArgumentParser(description="Limit notices to the project leads.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("notices")
    n.add_argument("--mark", required=True, help="the once-per-window notice mark file")
    n.add_argument("--log", help="the usage log (default: the status line's)")
    n.add_argument("--now", type=float, help="epoch seconds (tests)")
    args = parser.parse_args(argv)
    now = args.now if args.now is not None else time.time()
    out = notices(args.log or log_file(), args.mark, now)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for line in out:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
