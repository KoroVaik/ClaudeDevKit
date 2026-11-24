"""Forecast of the weekly subscription limit from the status line's usage log, for one early phone push; and the
limit notices to the project leads.

    python usage_forecast.py check --open N --mark FILE [--log FILE] [--now EPOCH]
    python usage_forecast.py notices --mark FILE [--log FILE] [--now EPOCH]

The Pult watcher (plugins/pult/scripts/watch-servers.ps1) runs it when the usage log got new lines. The log is the one
`statusline.py` writes (`{ts, week_pct, week_resets, five_hour_pct}`, env DEV_KIT_USAGE_LOG or `~/.claude/spend-kit`):
the real account per cent, so no retro estimate is used here (plans/limit-tracking.md, "Owner's approval").

Forecast: the readings of the current weekly window (the last line's `week_resets`, reset times under SAME_WINDOW_S
apart count as one window) taken in the last SPAN_H hours before now. At least two readings at least MIN_GAP_S apart,
else no forecast. Pace = the per cent rise / the hours between the first and the last of them. Run-out time = the
last reading's time + (100 - its per cent) / pace (the time of the reading, not now: the log gets a line only when the
per cent rose, so a quiet spell does not move the forecast). A push is due only when the window resets more than
MARGIN_H hours after the run-out time. A 5-hour window wait is at most 5 hours, so there is no 5-hour logic.

`--open N`: the number of live task sessions the leads manage (not the leads); 0 means no push. `--mark FILE`: a JSON
file `{"week_resets": <epoch>}`; a push is due at most once per weekly window, so a due push writes the mark and a
window already marked gives none, even if the forecast got worse.

Prints one line: `none <reason>` (no-log, few-readings, short-span, no-rise, window-over, limit-reached, enough, no-open-tasks,
marked) or `push | <run-out epoch> | <reset epoch> | <per cent> | <pace %/h> | <push text>`. The text is Ukrainian,
in local time: «Тижневий ліміт: витрачено 49%, за темпом скінчиться пт 20:00, оновиться пн 10:00» (the per cent is the last
reading's, rounded). Exit 0; 2 on bad arguments. `five_only` lines (a 5-hour reading logged alone) are not readings
of the forecast: their weekly per cent did not rise.

`notices` (docs/features/wind-down-at-weekly-limit.md, plans/limit-wind-down.md): the Pult watcher runs it when the
usage log changed or every few minutes and sends each printed text to the project leads. Thresholds: WEEK_AT for the
weekly limit (90, 95), FIVE_AT for the 5-hour one (90). The last log line with a reset time in the future gives the
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

SPAN_H = 6  # readings of the last this many hours give the pace
MIN_GAP_S = 3600  # the first and the last reading of the span must be at least this far apart
MARGIN_H = 6  # a push only when the limit runs out more than this many hours before the reset
DAYS = ("пн", "вт", "ср", "чт", "пт", "сб", "нд")
WEEK_AT = (90, 95)  # weekly notice thresholds, per cent
FIVE_AT = (90,)  # 5-hour notice thresholds, per cent
LIMIT_NAMES = {"week": "тижневий", "five": "5-годинний"}


def parse_ts(text):
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
    except (TypeError, ValueError):
        return None


def read_log(path):
    """The readings of the log as (epoch, per cent, reset epoch), in file order; bad lines are skipped."""
    out = []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return None
    for raw in lines:
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("five_only"):
            continue
        ts, pct, resets = parse_ts(entry.get("ts")), number(entry.get("week_pct")), number(entry.get("week_resets"))
        if ts is None or pct is None or resets is None:
            continue
        out.append((ts, float(pct), float(resets)))
    return out


def forecast(readings, now):
    """('none', reason) or ('push', run-out epoch, reset epoch, last per cent, pace per hour); no mark or open check."""
    if not readings:
        return ("none", "few-readings")
    resets = readings[-1][2]
    if resets <= now:
        return ("none", "window-over")
    span = [r for r in readings if abs(r[2] - resets) < SAME_WINDOW_S and now - SPAN_H * 3600 <= r[0] <= now]
    span.sort(key=lambda r: r[0])
    if len(span) < 2:
        return ("none", "few-readings")
    first, last = span[0], span[-1]
    if last[0] - first[0] < MIN_GAP_S:
        return ("none", "short-span")
    pace = (last[1] - first[1]) / ((last[0] - first[0]) / 3600)
    if pace <= 0:
        return ("none", "no-rise")
    if last[1] >= 100:
        return ("none", "limit-reached")  # already stopped: a forecast says nothing new
    runout = last[0] + max(0.0, 100 - last[1]) / pace * 3600
    if resets - runout <= MARGIN_H * 3600:
        return ("none", "enough")
    return ("push", runout, resets, last[1], pace)


def local_text(epoch):
    t = datetime.datetime.fromtimestamp(epoch)
    return f"{DAYS[t.weekday()]} {t:%H:%M}"


def push_text(pct, runout, resets):
    return f"Тижневий ліміт: витрачено {round(pct):d}%, за темпом скінчиться {local_text(runout)}, оновиться {local_text(resets)}"


def marked(path, resets):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    old = number(data.get("week_resets")) if isinstance(data, dict) else None
    return old is not None and abs(old - resets) < SAME_WINDOW_S


def check(log, mark, open_tasks, now):
    """The output line of `check` (see the module doc); writes the mark when a push is due."""
    readings = read_log(log)
    if readings is None:
        return "none no-log"
    result = forecast(readings, now)
    if result[0] == "none":
        return f"none {result[1]}"
    _, runout, resets, pct, pace = result
    if open_tasks < 1:
        return "none no-open-tasks"
    if marked(mark, resets):
        return "none marked"
    Path(mark).parent.mkdir(parents=True, exist_ok=True)
    Path(mark).write_text(json.dumps({"week_resets": resets, "pushed": int(now)}), encoding="utf-8")
    return f"push | {int(runout)} | {int(resets)} | {pct:g} | {pace:.2f} | {push_text(pct, runout, resets)}"


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
    parser = argparse.ArgumentParser(description="Weekly limit forecast for one phone push.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--open", type=int, required=True, help="live task sessions the leads manage")
    c.add_argument("--mark", required=True, help="the once-per-window mark file")
    c.add_argument("--log", help="the usage log (default: the status line's)")
    c.add_argument("--now", type=float, help="epoch seconds (tests)")
    n = sub.add_parser("notices")
    n.add_argument("--mark", required=True, help="the once-per-window notice mark file")
    n.add_argument("--log", help="the usage log (default: the status line's)")
    n.add_argument("--now", type=float, help="epoch seconds (tests)")
    args = parser.parse_args(argv)
    now = args.now if args.now is not None else time.time()
    if args.cmd == "notices":
        out = notices(args.log or log_file(), args.mark, now)
    else:
        out = [check(args.log or log_file(), args.mark, args.open, now)]
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for line in out:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
