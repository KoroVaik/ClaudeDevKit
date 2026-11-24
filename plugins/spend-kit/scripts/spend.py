"""Claude token spend of the sessions: units, the share of the weekly limit, the weekly limit fit and the critical
problems. It reads the transcripts and uses no model.

    spend-kit session [--id SESSION_ID | --path TRANSCRIPT.jsonl] [--no-subagents]
                                                  the units of one session as a share of the weekly limit (see below)
    spend-kit write-session [--id SESSION_ID | --path TRANSCRIPT.jsonl]
                                                  write the session's spend file `sessions/<session id>.json` (see below)
    spend-kit critical [--days N]                 scan if not yet scanned today, then print the critical token problems
    spend-kit calibrate                           refit the weekly limit from the status line log and print the result
    spend-kit scan [--force] [--days N]           the scan of every transcript (once a day without --force)
    spend-kit scan --transcript PATH              only that transcript and its subagents
    spend-kit findings [--transcript PATH] [--days N]
                                                  scan, then print as JSON the spend findings no reader has taken yet
                                                  and the `## Spend` table lines (see Findings)
    spend-kit units --path FILE --from N --to M   the units of the transcript lines in the byte range [N, M)
    spend-kit hook-end                            SessionEnd hook (JSON on stdin): write the ended session's spend file

The weekly-limit forecast for the phone push is `usage_forecast.py` of this plugin (its own CLI, run by the Pult
watcher); the status line is `spend-kit-statusline`; the API money client is `spend-kit-api`.

Token spend, in units (owner, 2026-11-19: a subscription, so no dollars; raw tokens mislead, cache reads are most of
them): 1 unit = one fresh Sonnet input token; per kind WEIGHTS (output 5, cache read 0.1, cache write 1.25 for 5 min
and 2 for 1 h), times MODEL_WEIGHTS by the message's model (Opus 1.5, Haiku 1/3; any other model 1). One message id
repeats on several lines with the same usage: it counts once per scan, and a line dated before the previous scan
started (a resumed session copies old lines) is not counted.

Folders: the spend-kit data folder (`spend_dir.py`: env SPEND_KIT_DIR, else `~/.claude/spend-kit`; the files it took
over from `~/.claude/dev-kit` are copied once, see there). Transcripts: every `*.jsonl` under env DEV_KIT_PROJECTS_DIR,
else `~/.claude/projects`, subagent ones in `<session>/subagents/` included. `state.json` keeps: `offsets` (a byte
offset per transcript, up to the last complete line), `last_scan`, `scan_started`, `titles` and `cwds` per
`project/session`, `daily` (per local day by message time, DAILY_KEPT days, and per session with its subagents summed: the
units and the waste in them), `turns` (main turns so far per session), `runs` (units of the last RUNS_KEPT runs per
subagent type and model), `last_assistant`, `fit`, `fit_checked`, `fit_windows`, `critical_shown`, `noted_days` and
`pending` (the findings not yet taken by `findings`). It is read, changed and written only while `scan.lock` exists
(stale after LOCK_STALE_S); a transcript scan waits up to LOCK_WAIT_TRANSCRIPT_S and then does nothing, a full scan,
`critical`, `findings` and `calibrate` wait up to LOCK_WAIT_FULL_S. On the first full scan (no full scan yet) a file
last changed before `--days` days ago (default 1) that has no offset is skipped and its offset set to its size.

Waste is counted once per message, in this order:
- idle wake: the whole turn that a background task notification started (not a finished subagent) when it had at most
  IDLE_TEXT_CHARS of text, a re-armed background Bash and only IDLE_TOOLS calls (up to IDLE_MAX_CALLS): it did
  nothing but look and wait again;
- cold restart: the cache write of the first message of any other turn not started by the owner (a task notification,
  a peer or coordinator message) that came after the prompt cache lifetime (5 min after a 5-minute write, 60 min after
  a 1-hour write, as the previous message wrote it) since the previous message of that file;
- bloated context: the cache read above BLOAT_CONTEXT tokens of a message, at the cache read weight.
A session's day is a problem when it spent NOTE_SPEND_PCT or wasted NOTE_WASTE_PCT of the weekly limit
(`weekly_limit()`: the fit kept in `state.json`, else the seed WEEKLY_LIMIT_UNITS; one place), and critical from
CRITICAL_SPEND_PCT or CRITICAL_WASTE_PCT. `critical` prints, for today and CRITICAL_DAYS days before, one line per
critical problem not shown before, or grown to CRITICAL_GROWTH times the share shown (shown shares are kept in
`state.json`; nothing else touches them), biggest first, nothing when none:

    critical | <project> | <session title (id8)> | <date> | spent 2.4% of the weekly limit (16.6M units)
    critical | <project> | <session title (id8)> | <date> | wasted 0.6% of the weekly limit: idle wakes 0.60% (11),
        cold restarts 0.00%, bloated context 0.00%[ (was 0.5% when last shown)]

(each on one line.)

Findings (for a reader such as the rules plugin's retro, which runs `spend-kit findings` as a command and imports
nothing): each scan adds lines to `pending` in the format `- <project folder> | <session title (first 8 of its id)> or
<session id>[ / subagent <type>] | <kind> | <detail>` for these kinds, and `findings` prints them (then clears them) as
`{"findings": [{"session": "<project folder>/<session id>", "title": "...", "cwd": "...", "line": "- ..."}], "table":
["..."]}`:
- `long session`: a main transcript with LONG_TURNS or more main turns so far (an owner or injected message that is
  not a tool result; the total is kept in `state.json`), with this scan's units per turn against the median of the
  sessions under SHORT_TURNS turns (only with USUAL_MIN or more of them);
- `opus coder`: a coder subagent run on Opus, with its units against the usual Sonnet coder run (only with USUAL_MIN
  or more such runs kept);
- `token spend` / `token waste`: when a scan runs on a later day, each finished day's problems, once per day:
  `<date>: <detail>[; critical (shown in Pult's status)]`.
The `table` lines are the `## Spend` section of a full scan (sessions by title, subagents by type and model). "Usual" is
the median units per run of one subagent type on one model over the last RUNS_KEPT runs, shown only with USUAL_MIN or
more runs.

The weekly limit in units is fitted from the status line log (`usage-log.jsonl`, written by `spend-kit-statusline`):
its readings are grouped by weekly window (`week_resets`); in each window the first and last reading give the per cent
used between them, and the units are those of all assistant messages of ALL transcripts (every project, subagents
included, a message id once) dated after the first reading up to the last (the per cent is account-wide). limit = units
* 100 / per cent, summed over the windows with a positive delta, used when the deltas total FIT_MIN_POINTS or more
points; else the last fit stays, else the seed. Reset times under an hour apart are one window; readings without a
numeric reset time, windows that began over FIT_DAYS days ago and windows that began before the oldest transcript file
are left out (deleted transcripts would drag the limit down). The units of a closed window (a later window has
readings) are kept in `state.json` (`fit_windows`), so a refit reads only the transcripts of the current window. `scan`
refits when the log has readings newer than the last check, `calibrate` always does.

`session` sums the units of one session (default: env CLAUDE_CODE_SESSION_ID; `--path` names a transcript file) over
its transcript and its subagents (`<session>/subagents/*.jsonl`, left out by `--no-subagents`), a message id once,
with the scan's weights, and prints the share of the weekly limit, the one an agent quotes in a report:

    ~2.3% of the weekly limit, estimate
    main 1.1%, subagents 1.2% (4 runs); 15.9M units; limit 690M units (fit 2026-11-20)

It reads no state but the fit and changes nothing. Exit code 2 when the session or its file is not found.

The per-session spend file (`sessions-file`): `write-session` (and the SessionEnd hook, which starts it detached and
returns at once) writes `<data folder>/sessions/<session id>.json`, replaced whole each time, files older than
SESSIONS_KEPT_DAYS deleted. Other plugins read it, never import this script:

    {"v": 1, "session": "<id>", "written": "<UTC ISO>", "title": "...", "cwd": "...", "units": 15900000,
     "share_pct": 2.3, "limit_units": 690000000, "limit_date": "2026-11-20",
     "main": {"units": 8000000, "share_pct": 1.1, "turns": 120},
     "subagents": {"units": 7900000, "share_pct": 1.2, "runs": [{"type": "dev-kit:coder", "model": "sonnet", "units": 1000}]},
     "models": {"opus": 1000, "sonnet": 2000},
     "waste": {"units": 100, "share_pct": 0.01, "idle": 60, "cold": 30, "bloat": 10, "wakes": 2}}

Exit codes: 0 done, 1 busy (calibrate), 2 bad arguments or no session.
"""
import argparse
import contextlib
import datetime
import json
import os
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the launcher runs this file with runpy, which adds nothing
import spend_dir  # noqa: E402  the data folder and the one-time move from dev-kit
import statusline  # noqa: E402  the status line script owns the usage log file

PROJECTS_ENV = "DEV_KIT_PROJECTS_DIR"
LOCK_NAME = "scan.lock"
LOCK_STALE_S = 600
LOCK_WAIT_TRANSCRIPT_S = 5
LOCK_WAIT_FULL_S = 60
WINDOWS = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
DETAIL_CHARS = 160
WEIGHTS = {"input": 1, "output": 5, "cache_read": 0.1, "cache_5m": 1.25, "cache_1h": 2}
MODEL_WEIGHTS = {"opus": 1.5, "sonnet": 1, "haiku": 1 / 3}  # matched as a part of the model id; Opus set from the
# owner's subscription meter (`/usage`, two 5-hour windows on 2026-11-19/20, fit 1.2-1.8), docs/findings/token-weights-and-weekly-limit.md
LONG_TURNS = 100
SHORT_TURNS = 50
USUAL_MIN = 10
RUNS_KEPT = 50
SPEND_ROWS = 15
WEEKLY_LIMIT_UNITS = 690e6  # the seed of the weekly limit in units: a hand fit at Opus weight 1.5 from `/usage` on
WEEKLY_LIMIT_DATE = "2026-11-20"  # 2026-11-20 (docs/findings/token-weights-and-weekly-limit.md; about 30% uncertain). The
# fit from the status line log (usage-log.jsonl, see `fit_limit`) replaces it once it has FIT_MIN_POINTS points
FIT_MIN_POINTS = 10  # the weekly per cent points the log must span, summed over windows, before the fit is used
FIT_DAYS = 28  # only windows that began within this many days count: older transcripts are deleted
WINDOW_ROUND_S = statusline.SAME_WINDOW_S  # reset times of one weekly window differing by less are one window
CRITICAL_SPEND_PCT = 2.0  # a session's day: spent this share of the weekly limit, or ...
CRITICAL_WASTE_PCT = 0.5  # ... wasted this share (idle wakes, cold restarts, bloated context)
NOTE_SPEND_PCT = 0.5  # below the critical shares but from these: a priority item for a reader of the findings
NOTE_WASTE_PCT = 0.1
CRITICAL_DAYS = 2  # `critical` looks at today and the days before it up to this many
CRITICAL_GROWTH = 1.25  # a shown critical problem is shown again when it grew to this many times what was shown
IDLE_TEXT_CHARS = 500  # a wake turn (task notification) with at most this much text, a re-arm and only look-up tools
IDLE_MAX_CALLS = 8  # (IDLE_TOOLS) calls is idle: it re-armed a watcher and acted on nothing
IDLE_TOOLS = {"Bash", "PowerShell", "ListAgents", "Read", "Grep", "Glob", "CronList"}
WAKE_ORIGINS = {"task-notification", "agent-notification", "peer", "coordinator"}  # turn starts not by the owner
BLOAT_CONTEXT = 300_000  # the cache read above this many tokens in one message counts as bloated context
COLD_TTL_MIN = {"5m": 5, "1h": 60}  # the prompt cache lifetime by write kind
DAILY_KEPT = 14  # days of per-session units kept in `state.json`
PENDING_KEPT = 300  # findings kept for a reader that does not come
PENDING_DAYS = 14
SESSIONS_KEPT_DAYS = 60  # per-session spend files older than this are deleted
STATE_KEYS_FROM_RETRO = ("offsets", "last_assistant", "titles", "last_scan", "scan_started", "daily", "turns", "runs",
                         "fit", "fit_checked", "fit_windows", "critical_shown", "noted_days")  # the token part of the
# retro's old `state.json` (`~/.claude/dev-kit/retro/state.json`), copied once into the new state


def projects_dir():
    return Path(os.environ[PROJECTS_ENV]) if os.environ.get(PROJECTS_ENV) else Path.home() / ".claude" / "projects"


def today():
    return datetime.date.today().isoformat()


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_time(value):
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def number(value):
    return value if isinstance(value, (int, float)) else 0


def short(text):
    text = " ".join(str(text).split())
    return text if len(text) <= DETAIL_CHARS else text[:DETAIL_CHARS - 3] + "..."


# ---------------------------------------------------------------- state and locks

def write_json(path, data):
    """Write a JSON file atomically: a temp file of this process, then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def migrate_state(folder):
    """Once, when the new `state.json` is missing: the token part of the retro's old state (see spend_dir)."""
    old = spend_dir.old_dir()
    if old is None or (folder / "state.json").exists():
        return
    try:
        data = json.loads((old / "retro" / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if isinstance(data, dict):
        kept = {key: data[key] for key in STATE_KEYS_FROM_RETRO if key in data}
        if kept:
            write_json(folder / "state.json", kept)


def load_state(folder):
    """The state (offsets, per-day units, the fit); read-modify-write it only under `scan_lock`."""
    try:
        state = json.loads((folder / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    state.setdefault("offsets", {})
    state.setdefault("last_scan", "")
    return state


def save_state(folder, state):
    write_json(folder / "state.json", state)


def lock_age(path):
    """Seconds since the lock file was made, or None when there is none."""
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return None


@contextlib.contextmanager
def file_lock(path, wait, stale):
    """Hold a lock file (made with O_EXCL; one older than `stale` s is taken over); yields False after `wait` s."""
    path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + wait
    while True:
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):  # Windows: PermissionError while the other side deletes it
            age = lock_age(path)
            if age is not None and age > stale:
                with contextlib.suppress(OSError):
                    path.unlink()
                continue
            if time.monotonic() >= deadline:
                yield False
                return
            time.sleep(0.1)
            continue
        os.write(handle, str(os.getpid()).encode("ascii"))
        os.close(handle)
        break
    try:
        yield True
    finally:
        with contextlib.suppress(OSError):
            path.unlink()


def scan_lock(folder, wait):
    return file_lock(folder / LOCK_NAME, wait, LOCK_STALE_S)


def read_new_lines(path, offset):
    """The complete lines appended after `offset`, and the offset after the last complete line."""
    try:
        with open(path, "rb") as handle:
            handle.seek(offset)
            data = handle.read()
    except OSError:
        return [], offset
    end = data.rfind(b"\n")
    if end < 0:
        return [], offset
    return data[:end + 1].splitlines(), offset + end + 1


def session_label(path, root):
    """(project folder, session key, label) of a transcript path; a subagent's key is its parent session."""
    rel = path.relative_to(root).parts
    project = rel[0] if len(rel) > 1 else ""
    if "subagents" in rel:
        session = rel[rel.index("subagents") - 1]
        kind = "subagent"
        meta = path.with_suffix(".meta.json")
        try:
            kind = "subagent " + str(json.loads(meta.read_text(encoding="utf-8")).get("agentType") or "").strip()
        except (OSError, ValueError):
            pass
        return project, session, kind.strip()
    return project, path.stem, ""


# ---------------------------------------------------------------- units and waste

def model_family(model):
    model = str(model or "").lower()
    return next((family for family in MODEL_WEIGHTS if family in model), "other")


def cache_writes(usage):
    """(5-minute, 1-hour) cache write tokens of one message's usage."""
    cache = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else None
    if cache:
        return number(cache.get("ephemeral_5m_input_tokens")), number(cache.get("ephemeral_1h_input_tokens"))
    return number(usage.get("cache_creation_input_tokens")), 0


def units_of(usage, model):
    """The units of one message's usage."""
    five, hour = cache_writes(usage)
    raw = (number(usage.get("input_tokens")) * WEIGHTS["input"] + number(usage.get("output_tokens")) * WEIGHTS["output"]
           + number(usage.get("cache_read_input_tokens")) * WEIGHTS["cache_read"]
           + five * WEIGHTS["cache_5m"] + hour * WEIGHTS["cache_1h"])
    return raw * MODEL_WEIGHTS.get(model_family(model), 1)


def waste_of(usage, model):
    """(cache write units, units of the cache read above BLOAT_CONTEXT) of one message."""
    five, hour = cache_writes(usage)
    weight = MODEL_WEIGHTS.get(model_family(model), 1)
    over = max(0, number(usage.get("cache_read_input_tokens")) - BLOAT_CONTEXT)
    return (five * WEIGHTS["cache_5m"] + hour * WEIGHTS["cache_1h"]) * weight, over * WEIGHTS["cache_read"] * weight


def new_turn(origin):
    return {"origin": origin, "msgs": [], "text": 0, "calls": 0, "rearms": 0, "acts": 0, "assistant": False}


def day_row(days, stamp):
    """The row of the local date of `stamp` in a per-day table of units."""
    day = (stamp or now_utc()).astimezone().date().isoformat()
    return days.setdefault(day, {"units": 0.0, "idle": 0.0, "cold": 0.0, "bloat": 0.0, "wakes": 0})


def close_turn(turn, days):
    """Add a finished turn's units to the per-day table, and the waste in them (see the module doc)."""
    idle = (turn["origin"] == "task-notification" and turn["text"] <= IDLE_TEXT_CHARS
            and turn["calls"] <= IDLE_MAX_CALLS and not turn["acts"] and (turn["rearms"] or not turn["calls"]))
    for msg in turn["msgs"]:
        row = day_row(days, msg["stamp"])
        row["units"] += msg["units"]
        if idle:
            row["idle"] += msg["units"]
            continue
        row["bloat"] += msg["over"]
        if msg["cold"] and turn["origin"] in WAKE_ORIGINS:
            row["cold"] += msg["write"]
    if idle and turn["msgs"]:
        day_row(days, turn["msgs"][0]["stamp"])["wakes"] += 1


def analyse(lines, seen=None, since=None, last=None):
    """Counters of one transcript window: units by model family, main turns, the per-day units and waste (`days`),
    the title, the `cwd` and the units of the run.

    `seen` is the set of message ids already counted in this scan; lines dated before `since` are not counted.
    `last` is `(time, cache lifetime in minutes)` of the previous assistant message of this file, from an earlier scan;
    the result's `last` is the same for the next scan."""
    seen = set() if seen is None else seen
    days = {}
    turn = new_turn(None)
    prev_assistant, ttl = last if last else (None, COLD_TTL_MIN["1h"])
    units = Counter()  # model family -> units
    turns = 0
    title = ""
    cwd = None
    for raw in lines:
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        if cwd is None and isinstance(entry.get("cwd"), str) and entry["cwd"]:
            cwd = entry["cwd"]
        kind = entry.get("type")
        if kind == "custom-title":
            title = entry.get("customTitle") or title
            continue
        if kind not in ("assistant", "user"):
            continue
        stamp = parse_time(entry.get("timestamp"))
        message = entry.get("message") or {}
        content = message.get("content")
        fresh = not (since and stamp and stamp < since)
        if kind == "user" and not entry.get("isMeta") and not (
                isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result"
                                                  for b in content)):
            close_turn(turn, days)
            origin = entry.get("origin")
            turn = new_turn(origin.get("kind") if isinstance(origin, dict) else None)
            if isinstance(content, str) and "<summary>Agent " in content:
                turn["origin"] = "agent-notification"  # a finished subagent: real work follows, not an idle wake
            if fresh:
                turns += 1
        if not isinstance(content, list):
            content = []
        if kind != "assistant":
            continue
        usage, model, mid = message.get("usage"), message.get("model"), message.get("id")
        cold = not turn["assistant"] and bool(stamp and prev_assistant
                                              and (stamp - prev_assistant).total_seconds() / 60 >= ttl)
        turn["assistant"] = True
        if stamp:
            prev_assistant = stamp
        if isinstance(usage, dict) and model != "<synthetic>":
            five, hour = cache_writes(usage)
            ttl = COLD_TTL_MIN["1h"] if hour else COLD_TTL_MIN["5m"] if five else ttl
        if isinstance(usage, dict) and model != "<synthetic>" and fresh and mid not in seen:
            if mid:
                seen.add(mid)
            units[model_family(model)] += units_of(usage, model)
            write, over = waste_of(usage, model)
            turn["msgs"].append({"stamp": stamp, "units": units_of(usage, model), "write": write, "over": over,
                                 "cold": cold})
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                turn["text"] += len(str(block.get("text") or "").strip())
            elif isinstance(block, dict) and block.get("type") == "tool_use":
                turn["calls"] += 1
                given = block.get("input")
                if block.get("name") == "Bash" and isinstance(given, dict) and given.get("run_in_background"):
                    turn["rearms"] += 1
                if block.get("name") not in IDLE_TOOLS:
                    turn["acts"] += 1
    close_turn(turn, days)
    return {
        "days": days, "last": (prev_assistant, ttl) if prev_assistant else None, "title": title, "cwd": cwd,
        "units": units, "turns": turns, "runs": 1 if units else 0,
        "run_units": [(units.most_common(1)[0][0], sum(units.values()))] if units else [],
    }


def merge(a, b):
    """The counters of two windows of one label added together."""
    days = {day: {key: a["days"].get(day, {}).get(key, 0) + b["days"].get(day, {}).get(key, 0)
                  for key in ("units", "idle", "cold", "bloat", "wakes")} for day in {*a["days"], *b["days"]}}
    return {
        "days": days, "last": b["last"] or a["last"], "title": b["title"] or a["title"], "cwd": a["cwd"] or b["cwd"],
        "units": a["units"] + b["units"], "turns": a["turns"] + b["turns"], "runs": a["runs"] + b["runs"],
        "run_units": a["run_units"] + b["run_units"],
    }


# ---------------------------------------------------------------- the weekly limit and the problems

def weekly_limit(state=None):
    """`(units, date)` of the weekly limit: the fit kept in the state, else the seed constants."""
    if state is None:
        state = load_state(spend_dir.data_dir())
    fit = state.get("fit")
    if isinstance(fit, dict) and number(fit.get("units")) > 0:
        return fit["units"], str(fit.get("date") or "")
    return WEEKLY_LIMIT_UNITS, WEEKLY_LIMIT_DATE


def percent(units, limit=None):
    """Units as a share of the weekly limit (`limit` in units, default the current one), in per cent."""
    return units * 100 / (limit or weekly_limit()[0])


def pct_text(value):
    return f"{value:.1f}%" if value >= 1 else f"{value:.2f}%"


def amount(units):
    """Units in a short form: 950, 7.5k, 12k, 3.4M."""
    if units >= 1e6:
        return f"{units / 1e6:.1f}M"
    if units >= 1e4:
        return f"{units / 1e3:.0f}k"
    return f"{units / 1e3:.1f}k" if units >= 1e3 else f"{units:.0f}"


def median(values):
    values = sorted(values)
    if not values:
        return 0
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def mix(units):
    """Model families by share: `opus 90%, sonnet 10%`."""
    total = sum(units.values()) or 1
    return ", ".join(f"{family} {value * 100 / total:.0f}%" for family, value in units.most_common() if value)


def project_name(folder):
    """A project folder in the table: `Zhratva/next-categories` for a worktree of `...-MyRepositories-Zhratva`."""
    repo, _, worktree = folder.partition("--claude-worktrees-")
    repo = repo.rsplit("-MyRepositories-", 1)[-1]
    return f"{repo}/{worktree}" if worktree else repo


def problems(row, limit=None):
    """The token problems of one session's day, from the note shares up: `(kind, share, detail, critical)`.

    kind is `spend` (units spent) or `waste` (idle wakes, cold restarts, bloated context)."""
    limit = limit or weekly_limit()[0]
    found = []
    spend_share = percent(row["units"], limit)
    if spend_share >= NOTE_SPEND_PCT:
        found.append(("spend", spend_share,
                      f"spent {pct_text(spend_share)} of the weekly limit ({amount(row['units'])} units)",
                      spend_share >= CRITICAL_SPEND_PCT))
    waste = percent(row["idle"] + row["cold"] + row["bloat"], limit)
    if waste >= NOTE_WASTE_PCT:
        found.append(("waste", waste, f"wasted {pct_text(waste)} of the weekly limit: idle wakes "
                      f"{pct_text(percent(row['idle'], limit))} ({row['wakes']}), cold restarts "
                      f"{pct_text(percent(row['cold'], limit))}, bloated context {pct_text(percent(row['bloat'], limit))}",
                      waste >= CRITICAL_WASTE_PCT))
    return found


def session_label_of(state, key):
    """(project folder, `title (id8)` or the session id) of a `project/session` key of `state['daily']`."""
    project, _, session = key.rpartition("/")
    title = state.get("titles", {}).get(key)
    return project, f"{title} ({session[:8]})" if title else session


def priority_lines(state, day):
    """`(session key, scan line)` for the token problems of every finished day not written yet.

    A day is finished once a scan runs on a later day. The days older than DAILY_KEPT are dropped from the state."""
    keep = (datetime.date.fromisoformat(day) - datetime.timedelta(days=DAILY_KEPT)).isoformat()
    daily = state.setdefault("daily", {})
    for old in [date for date in daily if date < keep]:
        del daily[old]
    stale = (now_utc() - datetime.timedelta(days=3)).isoformat()
    last = state.setdefault("last_assistant", {})
    for old in [path for path, (stamp, _) in last.items() if parse_time(stamp) < parse_time(stale)]:
        del last[old]
    written = state.setdefault("noted_days", [])
    limit = weekly_limit(state)[0]
    lines = []
    for date in sorted(date for date in daily if date < day and date not in written):
        written.append(date)
        found = []
        for key, row in daily[date].items():
            project, label = session_label_of(state, key)
            found += [(share, key, f"- {project} | {label.replace('|', '/')} | token {kind} | {date}: {detail}"
                       + ("; critical (shown in Pult's status)" if critical else ""))
                      for kind, share, detail, critical in problems(row, limit)]
        lines += [(key, line) for _, key, line in sorted(found, key=lambda item: -item[0])]
    state["noted_days"] = written[-DAILY_KEPT:]
    alive = {key for sessions in daily.values() for key in sessions}
    cwds = state.setdefault("cwds", {})
    for old in [key for key in cwds if key not in alive]:
        del cwds[old]  # the folder of a session is kept as long as its days are
    return lines


def spend_findings(windows, titles, state):
    """The spend findings (long sessions, Opus coders) as `(project, session, line)` and the `## Spend` table lines."""
    def label(project, session):
        name = titles[(project, session)].replace("|", "/") if (project, session) in titles else ""
        return f"{name} ({session[:8]})" if name else session

    total = Counter()
    sessions = defaultdict(lambda: {"main": Counter(), "subs": 0.0, "turns": 0})
    subagents = defaultdict(list)  # (type, model family) -> units per run
    for (project, session, sub), result in windows.items():
        total += result["units"]
        row = sessions[(project, session)]
        if sub:
            row["subs"] += sum(result["units"].values())
            for family, units in result["run_units"]:
                subagents[(sub[len("subagent "):] or "?", family)].append(units)
        else:
            row["main"] += result["units"]
            row["turns"] += result["turns"]
    grand = sum(total.values())
    if not grand:
        return [], []
    history = state.setdefault("runs", {})
    for (kind, family), runs in subagents.items():
        key = f"{kind} {family}"
        history[key] = (history.get(key, []) + [round(units) for units in runs])[-RUNS_KEPT:]
    found = []
    turns_total = state.setdefault("turns", {})
    per_turn = {}
    for (project, session), row in sessions.items():
        if row["turns"]:
            key = f"{project}/{session}"
            turns_total[key] = turns_total.get(key, 0) + row["turns"]
            per_turn[(project, session)] = sum(row["main"].values()) / row["turns"]
    shorts = [cost for (project, session), cost in per_turn.items() if turns_total[f"{project}/{session}"] < SHORT_TURNS]
    short_usual = median(shorts) if len(shorts) >= USUAL_MIN else 0
    for (project, session), cost in per_turn.items():
        so_far = turns_total[f"{project}/{session}"]
        if so_far < LONG_TURNS:
            continue
        ratio = f", x{cost / short_usual:.1f} of a session under {SHORT_TURNS} turns" if short_usual else ""
        found.append((project, session, f"- {project} | {label(project, session)} | long session | {so_far} main turns "
                      f"so far; this scan {sessions[(project, session)]['turns']} turns at {amount(cost)} units per "
                      f"turn{ratio}"))
    sonnet_runs = [units for key, runs in history.items() if key.endswith("coder sonnet") for units in runs]
    sonnet_coder = median(sonnet_runs) if len(sonnet_runs) >= USUAL_MIN else 0
    for (project, session, sub), result in windows.items():
        for family, units in result["run_units"]:
            if family == "opus" and sub.endswith("coder"):
                ratio = f", x{units / sonnet_coder:.0f} of a usual Sonnet coder run" if sonnet_coder else ""
                found.append((project, session, f"- {project} | {label(project, session)} / {sub} | opus coder | "
                              f"{amount(units)} units{ratio}"))
    subs_share = sum(sum(runs) for runs in subagents.values()) * 100 / grand
    table = [f"Total {amount(grand)} units ({mix(total)}); subagents {subs_share:.0f}%.", "",
             "| project | session | main models | main turns | main units | subagent units | share |",
             "|---|---|---|---|---|---|---|"]
    ranked = sorted(sessions.items(), key=lambda item: -(sum(item[1]["main"].values()) + item[1]["subs"]))
    for (project, session), row in ranked[:SPEND_ROWS]:
        both = sum(row["main"].values()) + row["subs"]
        table.append(f"| {project_name(project)} | {label(project, session)} | {mix(row['main']) or '-'} | {row['turns']} | "
                     f"{amount(sum(row['main'].values()))} | {amount(row['subs'])} | {both * 100 / grand:.0f}% |")
    if subagents:
        table += ["", "| subagent | model | runs | units | median per run | usual per run | share |",
                  "|---|---|---|---|---|---|---|"]
        for (kind, family), runs in sorted(subagents.items(), key=lambda item: -sum(item[1]))[:SPEND_ROWS]:
            usual = history.get(f"{kind} {family}", [])
            shown = amount(median(usual)) if len(usual) >= USUAL_MIN else "-"
            table.append(f"| {kind} | {family} | {len(runs)} | {amount(sum(runs))} | {amount(median(runs))} | "
                         f"{shown} | {sum(runs) * 100 / grand:.0f}% |")
    return found, table


# ---------------------------------------------------------------- the scan

def scan(days=1, force=False, out=None, transcript=None, drain=False):
    """The full scan, or with `transcript` only that transcript and its subagents (see the module doc).

    Returns `{"code": 0|1, "findings": [...], "table": [...]}`; `findings` only with `drain` (the pending ones, taken)."""
    out = out or sys.stdout
    folder = spend_dir.data_dir()
    migrate_state(folder)
    result = {"code": 0, "findings": [], "table": []}
    with scan_lock(folder, LOCK_WAIT_TRANSCRIPT_S if transcript else LOCK_WAIT_FULL_S) as held:
        if not held:
            if not transcript:
                print("scan busy: another scan holds scan.lock", file=out)
            return result
        scan_locked(folder, days, force, out, transcript, drain, result)
    return result


def scan_locked(folder, days, force, out, transcript, drain, result):
    state = load_state(folder)
    day = today()
    if not transcript and state["last_scan"] == day and not force:
        print("already scanned today", file=out)
        if drain:
            result["findings"] = take_pending(state)
            save_state(folder, state)
        return
    root = projects_dir()
    started = now_utc()
    since = parse_time(state.get("scan_started", ""))
    seen = set()  # message ids counted in this scan
    first = not state["last_scan"] and not transcript
    cutoff = time.time() - days * 86400
    known = state.setdefault("titles", {})  # a title is written once, often in an earlier scan's lines
    cwds = state.setdefault("cwds", {})
    windows = {}  # (project, session, subagent type) -> counters; subagents of one type in one session are summed
    if transcript:
        main_file = Path(transcript)
        root = main_file.parent.parent  # the project folder is its parent: the same labels as in the full scan
        paths = [main_file] + sorted((main_file.with_suffix("") / "subagents").rglob("*.jsonl"))
    else:
        paths = sorted(root.rglob("*.jsonl")) if root.is_dir() else []
    index = {os.path.normcase(known_key): known_key for known_key in state["offsets"]}  # a hook's path may differ in case
    for path in paths:
        key = index.get(os.path.normcase(str(path)), str(path))
        try:
            size = path.stat().st_size
            mtime = path.stat().st_mtime
        except OSError:
            continue
        offset = state["offsets"].get(key, 0)
        if key not in state["offsets"] and first and mtime < cutoff:
            state["offsets"][key] = size
            continue
        if offset > size:  # the file was rewritten; read it again
            offset = 0
        if offset == size:
            continue
        lines, state["offsets"][key] = read_new_lines(path, offset)
        if not lines:
            continue
        project, session, sub = session_label(path, root)
        before = state.setdefault("last_assistant", {}).get(key)
        found = analyse(lines, seen, since, (parse_time(before[0]), before[1]) if before else None)
        if found["last"]:
            state["last_assistant"][key] = [found["last"][0].isoformat(), found["last"][1]]
        for date, row in found["days"].items():
            total = state.setdefault("daily", {}).setdefault(
                date, {}).setdefault(f"{project}/{session}", {"units": 0, "idle": 0, "cold": 0, "bloat": 0, "wakes": 0})
            for field, value in row.items():
                total[field] = round(total[field] + value)
        if found["title"] and not sub:
            known[f"{project}/{session}"] = found["title"]
        if found["cwd"]:
            cwds[f"{project}/{session}"] = found["cwd"]
        merged = windows.get((project, session, sub))
        windows[(project, session, sub)] = merge(merged, found) if merged else found
    titles = {(project, session): known[f"{project}/{session}"] for project, session, _ in windows
              if known.get(f"{project}/{session}")}
    new = []  # (project, session, line)
    findings, table = spend_findings(windows, titles, state)
    new += findings
    entries = []
    for project, session, line in new:
        key = f"{project}/{session}"
        entries.append({"session": key, "title": titles.get((project, session), ""),
                        "cwd": cwds.get(key) or next((r["cwd"] for (p, s, _), r in windows.items()
                                                      if (p, s) == (project, session) and r["cwd"]), None) or "",
                        "line": line, "day": day})
    if not transcript:
        refit_if_new(state)
        for key, line in priority_lines(state, day):
            entries.append({"session": key, "title": state.get("titles", {}).get(key, ""),
                            "cwd": cwds.get(key, ""), "line": line, "day": day})
    else:
        table = []
    pending = state.setdefault("pending", [])
    pending.extend(entries)
    keep = (datetime.date.fromisoformat(day) - datetime.timedelta(days=PENDING_DAYS)).isoformat()
    state["pending"] = [entry for entry in pending if entry.get("day", day) >= keep][-PENDING_KEPT:]
    result["table"] = table
    if drain:
        result["findings"] = take_pending(state)
    if not transcript:
        state["scan_started"] = started.isoformat()
        state["last_scan"] = day
    save_state(folder, state)
    print(f"scanned {len(windows)} transcript(s)", file=out)


def take_pending(state):
    """The pending findings, cleared from the state (the caller saves it)."""
    taken = [{key: value for key, value in entry.items() if key != "day"} for entry in state.get("pending", [])]
    state["pending"] = []
    return taken


def quiet_scan(days):
    """The full scan of today when none ran, with no output."""
    if load_state(spend_dir.data_dir())["last_scan"] != today():
        with open(os.devnull, "w", encoding="utf-8") as quiet:
            scan(days=days, out=quiet)


def critical(days=1, out=None):
    """Print the critical token problems of today and the days before it not shown yet, or grown since shown."""
    out = out or sys.stdout
    folder = spend_dir.data_dir()
    migrate_state(folder)
    quiet_scan(days)
    lines = []
    with scan_lock(folder, LOCK_WAIT_FULL_S) as held:
        if not held:
            return 0
        state = load_state(folder)
        first = (datetime.date.fromisoformat(today()) - datetime.timedelta(days=CRITICAL_DAYS)).isoformat()
        shown = {key: value for key, value in state.setdefault("critical_shown", {}).items()
                 if key.split("|")[0] >= first}
        limit = weekly_limit(state)[0]
        for date, sessions in state.get("daily", {}).items():
            if date < first:
                continue
            for key, row in sessions.items():
                project, label = session_label_of(state, key)
                for kind, share, detail, is_critical in problems(row, limit):
                    before = shown.get(f"{date}|{key}|{kind}")
                    if not is_critical or (before is not None and share < before * CRITICAL_GROWTH):
                        continue
                    shown[f"{date}|{key}|{kind}"] = share
                    grown = f" (was {pct_text(before)} when last shown)" if before is not None else ""
                    lines.append((share, f"critical | {project_name(project)} | {label.replace('|', '/')} | {date} | "
                                         f"{detail}{grown}"))
        state["critical_shown"] = shown
        save_state(folder, state)
    for _, line in sorted(lines, key=lambda item: -item[0]):
        print(line, file=out)
    return 0


def findings(days=1, transcript=None, out=None):
    """Scan and print the pending spend findings as JSON (see the module doc, Findings)."""
    out = out or sys.stdout
    with open(os.devnull, "w", encoding="utf-8") as quiet:
        result = scan(days=days, force=not transcript, out=quiet, transcript=transcript, drain=True)
    print(json.dumps({"findings": result["findings"], "table": result["table"]}, ensure_ascii=False), file=out)
    return 0


# ---------------------------------------------------------------- the weekly limit fit

def usage_messages(path):
    """`(time, message id, units)` of every assistant message with usage in a transcript, in file order.

    Lines without usage are skipped before parsing, so a week of transcripts reads fast."""
    try:
        with open(path, "rb") as handle:
            for raw in handle:
                parsed = usage_message(raw)
                if parsed:
                    yield parsed
    except OSError:
        return


def usage_message(raw, main_only=False):
    """`(time, message id, units)` of one transcript line, or None when it is no assistant message with usage
    (`main_only`: or when it is a side chain line, a message of a subagent kept in the main file)."""
    if b'"usage"' not in raw or b'"assistant"' not in raw:
        return None
    try:
        entry = json.loads(raw)
    except ValueError:
        return None
    message = entry.get("message") if isinstance(entry, dict) else None
    if entry.get("type") != "assistant" or not isinstance(message, dict) or (main_only and entry.get("isSidechain")):
        return None
    usage, model = message.get("usage"), message.get("model")
    if isinstance(usage, dict) and model != "<synthetic>":
        return parse_time(entry.get("timestamp")), message.get("id"), units_of(usage, model)
    return None


def read_log():
    """The readings of the status line log with a valid time and weekly per cent, oldest first."""
    readings = []
    try:
        with open(statusline.log_file(), "rb") as handle:
            lines = handle.read().splitlines()
    except OSError:
        return readings
    for raw in lines:
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        stamp = parse_time(entry.get("ts")) if isinstance(entry, dict) else None
        pct = statusline.number(entry.get("week_pct")) if stamp else None
        if pct is not None:
            readings.append({"ts": stamp, "pct": pct, "resets": entry.get("week_resets")})
    return sorted(readings, key=lambda reading: reading["ts"])


def window_spans(readings, now=None):
    """`(first time, last time, per cent between, closed)` of each weekly window of the log with a positive delta.

    Readings without a numeric reset time are left out. Readings whose reset times differ by under WINDOW_ROUND_S
    (one window, the time jitters) are one window; a window whose first reading is older than FIT_DAYS is left out.
    A window is closed once a later window has readings: no reading will be added to it."""
    since = (now or now_utc()) - datetime.timedelta(days=FIT_DAYS)
    numbered = sorted((reading for reading in readings if statusline.number(reading["resets"]) is not None),
                      key=lambda reading: reading["resets"])
    windows = []
    for reading in numbered:
        if windows and reading["resets"] - windows[-1][-1]["resets"] < WINDOW_ROUND_S:
            windows[-1].append(reading)
        else:
            windows.append([reading])
    spans = []
    for index, rows in enumerate(windows):
        rows.sort(key=lambda reading: reading["ts"])
        delta = rows[-1]["pct"] - rows[0]["pct"]
        if delta > 0 and rows[0]["ts"] >= since:
            spans.append((rows[0]["ts"], rows[-1]["ts"], delta, index < len(windows) - 1))
    return sorted(spans)


def transcripts(root):
    """`(path, mtime)` of every transcript under `root`."""
    found = []
    for path in root.rglob("*.jsonl") if root.is_dir() else []:
        try:
            found.append((path, path.stat().st_mtime))
        except OSError:
            continue
    return found


def units_in_spans(spans, files):
    """The units of the transcripts `files` (a message id once) per span, for messages in (first, last]."""
    totals = [0.0] * len(spans)
    if not spans:
        return totals
    earliest = min(span[0] for span in spans).timestamp()
    seen = set()
    for path, mtime in files:
        if mtime < earliest:
            continue  # last written before the first window began
        for stamp, mid, units in usage_messages(path):
            if stamp is None or (mid and mid in seen):
                continue
            for index, (first, last, *_) in enumerate(spans):
                if first < stamp <= last:
                    totals[index] += units
                    if mid:
                        seen.add(mid)
                    break
    return totals


def fit_limit(readings, root, now=None, cache=None):
    """`(fit, why)`: the fitted weekly limit as `{"units", "date", "points", "windows"}` or None, and a sentence.

    A window that began before the oldest transcript is left out: its units are partly deleted, which would drag the
    limit down. `cache` (the state's `fit_windows`) keeps the units of each closed window, by the time of its first
    reading: a cached window is not read again (and stays usable after its transcripts are deleted); the cache is
    updated here and loses the windows older than FIT_DAYS."""
    cache = {} if cache is None else cache
    files = transcripts(root)
    oldest = min((mtime for _, mtime in files), default=None)
    usable = []  # (span, cached units or None)
    for span in window_spans(readings, now):
        first, last, delta, closed = span
        kept = cache.get(first.isoformat())
        if closed and kept and kept.get("last") == last.isoformat() and kept.get("points") == delta:
            usable.append((span, kept["units"]))
        elif oldest is not None and first.timestamp() >= oldest:
            usable.append((span, None))
    points = sum(span[2] for span, _ in usable)
    if points < FIT_MIN_POINTS:
        return None, (f"the log spans {points:.1f} per cent points in {len(usable)} usable window(s) "
                      f"(the last {FIT_DAYS} days, inside the kept transcripts); "
                      f"need {FIT_MIN_POINTS} before the limit is refitted")
    fresh = [span for span, kept in usable if kept is None]
    counted = iter(units_in_spans(fresh, files))
    total = 0.0
    for span, kept in usable:
        units = kept if kept is not None else next(counted)
        total += units
        if kept is None and span[3] and units > 0:
            cache[span[0].isoformat()] = {"last": span[1].isoformat(), "points": span[2], "units": units}
    since = ((now or now_utc()) - datetime.timedelta(days=FIT_DAYS)).isoformat()
    for old in [key for key in cache if key < since]:
        del cache[old]
    spans = [span for span, _ in usable]
    units = total
    if units <= 0:
        return None, "no transcript messages between the log readings"
    fit = {"units": round(units * 100 / points), "date": today(), "points": round(float(points), 1), "windows": len(spans)}
    return fit, f"{amount(fit['units'])} units from {fit['points']} points in {len(spans)} window(s)"


def refit(state):
    """Refit the weekly limit from the log into `state`; a sentence on the result."""
    readings = read_log()
    state["fit_checked"] = readings[-1]["ts"].isoformat() if readings else ""
    if not readings:
        return f"kept {amount(weekly_limit(state)[0])} units: the usage log has no readings yet"
    fit, why = fit_limit(readings, projects_dir(), cache=state.setdefault("fit_windows", {}))
    if not fit:
        return f"kept {amount(weekly_limit(state)[0])} units ({weekly_limit(state)[1]}): {why}"
    state["fit"] = fit
    return f"weekly limit fitted: {why}"


def refit_if_new(state):
    """`scan` refits only when the log has readings newer than the last check."""
    readings = read_log()
    checked = parse_time(state.get("fit_checked", ""))
    if readings and (checked is None or readings[-1]["ts"] > checked):
        refit(state)


def calibrate(out=None):
    out = out or sys.stdout
    folder = spend_dir.data_dir()
    migrate_state(folder)
    state = load_state(folder)
    print(refit(state), file=out)
    with scan_lock(folder, LOCK_WAIT_FULL_S) as held:
        if not held:
            print("scan busy: the fit was not saved, run calibrate again", file=sys.stderr)
            return 1
        fresh = load_state(folder)  # a scan may have finished meanwhile: keep its offsets, set only the fit keys
        for key in ("fit", "fit_checked", "fit_windows"):
            if key in state:
                fresh[key] = state[key]
        save_state(folder, fresh)
    return 0


# ---------------------------------------------------------------- one session

def share_text(pct, tilde=True):
    if pct < 0.1:
        return "<0.1%"
    return f"{'~' if tilde else ''}{pct:.1f}%"


def session_files(session_id, path):
    """The main transcripts of a session (a resumed copy is another file) from an id or a path; [] when none."""
    if path:
        return [Path(path)] if Path(path).is_file() else []
    root = projects_dir()
    return sorted(root.glob(f"*/{session_id}.jsonl")) if root.is_dir() else []


def subagent_files(mains):
    return sorted({file for main in mains for file in (main.with_suffix("") / "subagents").rglob("*.jsonl")})


def sum_units(files, seen):
    """`(units, files with units)` of transcript files, a message id once over `seen`."""
    units, used = 0.0, 0
    for file in files:
        before = units
        for _, mid, value in usage_messages(file):
            if mid and mid in seen:
                continue
            if mid:
                seen.add(mid)
            units += value
        used += units > before
    return units, used


def session(session_id=None, path=None, subagents=True, out=None, err=None):
    """Print a session's units as a share of the weekly limit (see the module doc); exit code 2 when not found."""
    out, err = out or sys.stdout, err or sys.stderr
    session_id = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not session_id and not path:
        print("no session: give --id or --path, or run inside a Claude Code session (CLAUDE_CODE_SESSION_ID)", file=err)
        return 2
    mains = session_files(session_id, path)
    if not mains:
        print(f"no transcript found for {path or session_id} under {projects_dir()}", file=err)
        return 2
    migrate_state(spend_dir.data_dir())  # the fit of the old retro state, on the first run
    seen = set()
    main_units, _ = sum_units(mains, seen)
    sub_units, runs = 0.0, 0
    if subagents:
        sub_units, runs = sum_units(subagent_files(mains), seen)
    limit, date = weekly_limit()
    both = main_units + sub_units
    print(f"{share_text(percent(both, limit))} of the weekly limit, estimate", file=out)
    parts = [f"main {share_text(percent(main_units, limit), False)}"]
    if subagents:
        parts.append(f"subagents {share_text(percent(sub_units, limit), False)} ({runs} run{'' if runs == 1 else 's'})")
    print(f"{', '.join(parts)}; {amount(both)} units; limit {limit / 1e6:.0f}M units (fit {date})", file=out)
    return 0


def analyse_files(files, seen):
    """The merged `analyse` result of whole files (a message id once over `seen`), or None for no files."""
    merged = None
    for file in files:
        lines, _ = read_new_lines(file, 0)
        found = analyse(lines, seen)
        merged = merge(merged, found) if merged else found
    return merged


def subagent_runs(files, seen):
    """`[{"type", "model", "units"}]` of the subagent files that spent units, a message id once over `seen`."""
    runs = []
    for file in files:
        lines, _ = read_new_lines(file, 0)
        found = analyse(lines, seen)
        if found["units"]:
            kind = session_label(file, file.parents[2])[2][len("subagent "):] or "?"
            runs.append({"type": kind, "model": found["run_units"][0][0], "units": round(sum(found["units"].values()))})
    return runs


def session_record(session_id, mains):
    """The per-session spend file's content (see the module doc) of a session's main files and its subagents."""
    seen = set()
    main = analyse_files(mains, seen)
    subs = subagent_files(mains)
    runs = subagent_runs(subs, seen)
    limit, date = weekly_limit()
    main_units = sum(main["units"].values()) if main else 0
    sub_units = sum(run["units"] for run in runs)
    models = Counter(main["units"] if main else {})
    waste = {"idle": 0.0, "cold": 0.0, "bloat": 0.0, "wakes": 0}
    for row in (main["days"].values() if main else []):
        for key in waste:
            waste[key] += row[key]
    wasted = waste["idle"] + waste["cold"] + waste["bloat"]
    for run in runs:
        models[run["model"]] += run["units"]
    return {
        "v": 1, "session": session_id, "written": now_utc().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "title": main["title"] if main else "", "cwd": (main["cwd"] if main else None) or "",
        "units": round(main_units + sub_units), "share_pct": round(percent(main_units + sub_units, limit), 3),
        "limit_units": round(limit), "limit_date": date,
        "main": {"units": round(main_units), "share_pct": round(percent(main_units, limit), 3),
                 "turns": main["turns"] if main else 0},
        "subagents": {"units": round(sub_units), "share_pct": round(percent(sub_units, limit), 3), "runs": runs[:RUNS_KEPT]},
        "models": {family: round(units) for family, units in models.items()},
        "waste": {"units": round(wasted), "share_pct": round(percent(wasted, limit), 3), "idle": round(waste["idle"]),
                  "cold": round(waste["cold"]), "bloat": round(waste["bloat"]), "wakes": waste["wakes"]},
    }


def sessions_dir():
    return spend_dir.data_dir() / "sessions"


def write_session(session_id=None, path=None, out=None, err=None):
    """Write the session's spend file; exit code 2 when the session or its file is not found."""
    out, err = out or sys.stdout, err or sys.stderr
    session_id = session_id or os.environ.get("CLAUDE_CODE_SESSION_ID")
    if path:
        session_id = Path(path).stem
    if not session_id:
        print("no session: give --id or --path, or run inside a Claude Code session (CLAUDE_CODE_SESSION_ID)", file=err)
        return 2
    mains = session_files(session_id, path)
    if not mains:
        print(f"no transcript found for {path or session_id} under {projects_dir()}", file=err)
        return 2
    folder = spend_dir.data_dir()
    migrate_state(folder)
    target = sessions_dir() / f"{Path(session_id).name}.json"
    write_json(target, session_record(session_id, mains))
    limit = time.time() - SESSIONS_KEPT_DAYS * 86400
    for old in sessions_dir().glob("*.json"):
        with contextlib.suppress(OSError):
            if old != target and old.stat().st_mtime < limit:
                old.unlink()
    print(f"wrote {target}", file=out)
    return 0


def range_units(path, start, end):
    """The units of the main-chain assistant messages on the complete lines of `path` in the byte range [start, end), an
    id once (the wake counter of `dev-kit-sessions size --wakes` runs this)."""
    try:
        with open(path, "rb") as handle:
            handle.seek(start)
            data = handle.read(max(0, end - start))
    except OSError:
        return 0.0
    units, seen = 0.0, set()
    for raw in data.splitlines():
        parsed = usage_message(raw, main_only=True)
        if parsed and not (parsed[1] and parsed[1] in seen):
            if parsed[1]:
                seen.add(parsed[1])
            units += parsed[2]
    return units


# ---------------------------------------------------------------- the SessionEnd hook

def spawn(argv):
    """Start a command detached from this process (no window, no console, outlives the caller)."""
    options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
               "close_fds": True}
    if not WINDOWS:
        subprocess.Popen(argv, start_new_session=True, **options)
        return
    # Not DETACHED_PROCESS: with it CREATE_NO_WINDOW is ignored and every console child opens a window. The breakaway
    # lets the child outlive the session's job object; a job that forbids it makes Popen raise: retry without.
    flags = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen(argv, creationflags=flags | CREATE_BREAKAWAY_FROM_JOB, **options)
    except OSError:
        subprocess.Popen(argv, creationflags=flags, **options)


def hook_end(payload):
    """SessionEnd: start the writing of the ending session's spend file, detached, and return at once."""
    transcript = payload.get("transcript_path")
    if isinstance(transcript, str) and transcript and Path(transcript).is_file():
        spawn([sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "write-session", "--path", transcript])


def hook_main():
    """Run the hook from the JSON on stdin; never fails and prints nothing."""
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if isinstance(payload, dict):
            hook_end(payload)
    except Exception:  # a hook must never block a session
        pass
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # transcripts hold any language; a Windows console code page cannot
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="spend-kit")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "critical", "findings"):
        command = sub.add_parser(name)
        command.add_argument("--days", type=float, default=1)
        if name == "scan":
            command.add_argument("--force", action="store_true")
        if name in ("scan", "findings"):
            command.add_argument("--transcript")
    sub.add_parser("calibrate")
    sub.add_parser("hook-end")
    for name in ("session", "write-session"):
        one = sub.add_parser(name)
        which = one.add_mutually_exclusive_group()
        which.add_argument("--id")
        which.add_argument("--path")
        if name == "session":
            one.add_argument("--no-subagents", action="store_true")
    units = sub.add_parser("units")
    units.add_argument("--path", required=True)
    units.add_argument("--from", dest="start", type=int, required=True)
    units.add_argument("--to", dest="end", type=int, required=True)
    args = parser.parse_args(argv)
    if args.command == "hook-end":
        return hook_main()
    if args.command == "calibrate":
        return calibrate()
    if args.command == "session":
        return session(args.id, args.path, not args.no_subagents)
    if args.command == "write-session":
        return write_session(args.id, args.path)
    if args.command == "critical":
        return critical(days=args.days)
    if args.command == "findings":
        return findings(days=args.days, transcript=args.transcript)
    if args.command == "units":
        print(f"{range_units(args.path, args.start, args.end):.3f}")
        return 0
    return scan(days=args.days, force=args.force, transcript=args.transcript)["code"]


if __name__ == "__main__":
    sys.exit(main())
