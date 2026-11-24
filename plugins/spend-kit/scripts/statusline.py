"""The spend-kit status line: shows the weekly subscription use and logs it for `spend-kit` to fit the weekly limit.

    spend-kit-statusline      reads the status line JSON from stdin (Claude Code runs it on each turn)

For subscribers the JSON holds `rate_limits.seven_day.used_percentage` (0-100) and `rate_limits.seven_day.resets_at`
(Unix epoch seconds), and the same two for `five_hour` (plugins/dev-kit/claude-facts.md, "The status line JSON holds
the subscription limits"). The script prints
one line, `тиждень: 23%`, and appends one line to `usage-log.jsonl` only when the weekly per cent rose within the
window of the last log line (reset times under SAME_WINDOW_S apart) or a newer window began. A lower per cent in the
same window, and a window older than the last line's by SAME_WINDOW_S or more (a stale reading from an idle parallel
session), are not logged:

    {"ts": "<UTC ISO>", "week_pct": 23.0, "week_resets": <as given>, "five_hour_pct": 41.0 or null}

Log folder: env DEV_KIT_USAGE_LOG, else the spend-kit data folder `~/.claude/spend-kit` (`spend_dir.py`; a log still in
`~/.claude/dev-kit` is copied there once, when the new one is missing). Parallel sessions may
write at once: the last line is read from the end of the file and a new line is appended in one write. Without
`rate_limits` it prints an empty line and writes nothing. It never raises: any error gives an
empty line and exit 0. It reads no transcript, so it stays fast.
"""
import datetime
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # run as a file: its folder is on the path, this makes it sure
import spend_dir  # noqa: E402

USAGE_ENV = "DEV_KIT_USAGE_LOG"  # an override of the log folder, kept under its old name for the tests and old setups
LOG_NAME = "usage-log.jsonl"
SAME_WINDOW_S = 3600  # reset times under this far apart are one weekly window
TAIL_BYTES = 4096  # a log line is about 100 bytes; this holds the last few


def log_file():
    if os.environ.get(USAGE_ENV):
        return Path(os.environ[USAGE_ENV]) / LOG_NAME
    path = spend_dir.data_dir() / LOG_NAME
    spend_dir.migrate_file(LOG_NAME, path)
    return path


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def last_reading(path):
    """The last complete JSON line of the log, or None."""
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - TAIL_BYTES))
            data = handle.read()
    except OSError:
        return None
    for raw in reversed(data.splitlines()):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue  # a cut first line of the tail, or a damaged line
        if isinstance(entry, dict):
            return entry
    return None


def worth_logging(before, pct, resets):
    """Whether a reading differs from the last log line enough to be logged (see the module doc)."""
    if not before:
        return True
    last_pct, last_resets = number(before.get("week_pct")), number(before.get("week_resets"))
    if number(resets) is None or last_resets is None or last_pct is None:
        return before.get("week_pct") != pct or before.get("week_resets") != resets
    if abs(resets - last_resets) < SAME_WINDOW_S:  # the same window; its reset time jitters
        return pct > last_pct
    return resets > last_resets  # a new window starts; an older one is a stale reading of an idle session


def record(data):
    """Log the weekly reading of one status line JSON when it changed; return the weekly per cent or None."""
    limits = data.get("rate_limits") if isinstance(data, dict) else None
    week = limits.get("seven_day") if isinstance(limits, dict) else None
    pct = number(week.get("used_percentage")) if isinstance(week, dict) else None
    if pct is None:
        return None
    resets = week.get("resets_at")
    five = limits.get("five_hour")
    five_pct = number(five.get("used_percentage")) if isinstance(five, dict) else None
    path = log_file()
    if not worth_logging(last_reading(path), pct, resets):
        return pct
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = json.dumps({"ts": stamp, "week_pct": pct, "week_resets": resets, "five_hour_pct": five_pct}) + "\n"
    with open(path, "ab") as handle:
        handle.write(line.encode("utf-8"))
    return pct


def main(stdin=None, stdout=None):
    stdout = stdout or sys.stdout
    text = ""
    try:
        data = json.loads((stdin or sys.stdin.buffer).read())  # bytes: the console code page may not read the JSON
        pct = record(data)
        if pct is not None:
            text = f"тиждень: {pct:.0f}%"
    except Exception:  # a status line must never fail the session
        text = ""
    if hasattr(stdout, "reconfigure"):
        stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text, file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
