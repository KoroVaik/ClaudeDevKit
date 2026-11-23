"""Forecast of the weekly subscription limit from the status line's usage log, for one early phone push.

    python usage_forecast.py check --open N --mark FILE [--log FILE] [--now EPOCH]

The Pult watcher (plugins/pult/scripts/watch-servers.ps1) runs it when the usage log got new lines. The log is the one
`statusline.py` writes (`{ts, week_pct, week_resets, five_hour_pct}`, env DEV_KIT_USAGE_LOG or `~/.claude/dev-kit`):
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
in local time: «Тижневий ліміт за темпом скінчиться пт 20:00, скидання пн 10:00.» Exit 0; 2 on bad arguments.
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
        if not isinstance(entry, dict):
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


def push_text(runout, resets):
    return f"Тижневий ліміт за темпом скінчиться {local_text(runout)}, скидання {local_text(resets)}."


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
    return f"push | {int(runout)} | {int(resets)} | {pct:g} | {pace:.2f} | {push_text(runout, resets)}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Weekly limit forecast for one phone push.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--open", type=int, required=True, help="live task sessions the leads manage")
    c.add_argument("--mark", required=True, help="the once-per-window mark file")
    c.add_argument("--log", help="the usage log (default: the status line's)")
    c.add_argument("--now", type=float, help="epoch seconds (tests)")
    args = parser.parse_args(argv)
    line = check(args.log or log_file(), args.mark, args.open, args.now if args.now is not None else time.time())
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
