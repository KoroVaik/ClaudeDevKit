"""Find problems in the sessions' transcripts with no model, and keep the findings for a retro session.

    dev-kit-retro check [--days N]     scan if not yet scanned today, then print the count of unreviewed findings
    dev-kit-retro scan [--force] [--days N]
    dev-kit-retro list                 print the unreviewed findings (token problems first, then scan lines, session
                                       notes, then the spend tables)
    dev-kit-retro done                 mark what the last check or list showed as reviewed (after a retro, or a no)
    dev-kit-retro critical [--days N]  scan if not yet scanned today, then print the critical token problems

Findings folder: env DEV_KIT_RETRO_DIR, else `~/.claude/dev-kit/retro` (local, outside any repository, one for all
projects). Transcripts: every `*.jsonl` under env DEV_KIT_PROJECTS_DIR, else `~/.claude/projects`, subagent ones in
`<session>/subagents/` included.

`scan` reads only what was appended to each transcript since the last scan (`state.json` keeps a byte offset per
file, up to the last complete line). On the first scan (no offsets yet) a file last changed before `--days` days ago
(default 1) is skipped and its offset set to its size, so the first scan does not read the whole history. It writes
`scan-<YYYY-MM-DD>.md` (local date; a second scan the same day with `--force` appends to it), one line per finding:

    - <project folder> | <session title (first 8 of its id)> or <session id>[ / subagent <type>] | <kind> | <detail>

Kinds, per transcript and per scan window (the subagents of one type in one session summed; thresholds below):
- `repeated call`: the same tool with the same input, REPEAT_MIN or more times (`run_in_background` calls left out:
  a watcher a lead on dev-kit before 0.1.78 re-arms after each exit is by design);
- `failed calls`: ERRORS_MIN or more tool results marked as an error;
- `many calls`: MANY_CALLS or more tool calls;
- `slow call`: a tool result that came SLOW_CALL_MIN or more minutes after its call (tools that wait on the owner
  by design, WAITING_TOOLS, are left out);
- `long pause`: SLOW_MODEL_MIN or more minutes between a tool result and the next assistant message;
and across transcripts:
- `script candidate`: the same Bash command of SCRIPT_MIN_CHARS or more in SCRIPT_SESSIONS or more sessions (subagents
  count with their session).
The plugin's own commands (containing OWN_COMMAND) count for neither repeats nor script candidates: rules run them.

Token spend, in units (owner, 2026-11-19: a subscription, so no dollars; raw tokens mislead, cache reads are most of
them): 1 unit = one fresh Sonnet input token; per kind WEIGHTS (output 5, cache read 0.1, cache write 1.25 for 5 min
and 2 for 1 h), times MODEL_WEIGHTS by the message's model (Opus 1.5, Haiku 1/3; any other model 1). One message id
repeats on several lines with the same usage: it counts once per scan, and a line dated before the previous scan
started (a resumed session copies old lines) is not counted. Two more kinds:
- `long session`: a main transcript with LONG_TURNS or more main turns so far (an owner or injected message that
  is not a tool result; the total is kept in `state.json`), with this scan's units per turn against the median of
  the sessions under SHORT_TURNS turns (only with USUAL_MIN or more of them);
- `opus coder`: a coder subagent run on Opus, with its units against the usual Sonnet coder run (only with USUAL_MIN
  or more such runs kept).
The scan file also gets a `## Spend` section of `| `-table lines (sessions by title, subagents by type and model;
not findings; `list` prints the unreviewed ones, older ones stay in the scan files). "Usual" is the median units per run of one
subagent type on one model over the last RUNS_KEPT runs (`state.json`), shown only with USUAL_MIN or more runs.

`check` runs `scan` when `state.json` has no scan for today, then prints `new findings: <N>` or `no new findings`.

Token problems (owner, 2026-11-20, plans/pult-idle-cost.md point 9): `state.json` keeps, per local day (by message
time, DAILY_KEPT days) and per session (its subagents summed), the units and the waste in them. Waste is counted once
per message, in this order:
- idle wake: the whole turn that a background task notification started (not a finished subagent) when it had at most
  IDLE_TEXT_CHARS of text, a re-armed background Bash and only IDLE_TOOLS calls (up to IDLE_MAX_CALLS): it did
  nothing but look and wait again;
- cold restart: the cache write of the first message of any other turn not started by the owner (a task notification,
  a peer or coordinator message) that came after the prompt cache lifetime (5 min after a 5-minute write, 60 min after
  a 1-hour write, as the previous message wrote it) since the previous message of that file;
- bloated context: the cache read above BLOAT_CONTEXT tokens of a message, at the cache read weight.
A session's day is a problem when it spent NOTE_SPEND_PCT or wasted NOTE_WASTE_PCT of the weekly limit
(WEEKLY_LIMIT_UNITS, calibrated on WEEKLY_LIMIT_DATE; one place to change), and critical from CRITICAL_SPEND_PCT or
CRITICAL_WASTE_PCT. When a scan runs on a later day, each finished day's problems become scan lines
`- <project folder> | <session> | token spend|token waste | <date>: <detail>[; critical (shown in Pult's status)]`
(once per day); `list` prints them first, under "Priority". `critical` prints, for today and CRITICAL_DAYS days
before, one line per critical problem not shown before, or grown to CRITICAL_GROWTH times the share shown (shown
shares are kept in `state.json`; `list`, `check` and `done` do not touch them), biggest first, nothing when none:

    critical | <project> | <session title (id8)> | <date> | spent 2.4% of the weekly limit (16.6M units)
    critical | <project> | <session title (id8)> | <date> | wasted 0.6% of the weekly limit: idle wakes 0.60% (11),
        cold restarts 0.00%, bloated context 0.00%[ (was 0.5% when last shown)]

(each on one line.)

New findings are the lines of scan files dated after the last `done` plus the lines of `notes.md` past the count
recorded at that `done`. `check` and `list` record what they showed; `done` marks only that, so findings that came
later stay new. Findings files are read as UTF-8 with a BOM allowed and bad bytes replaced. `notes.md` holds what only a session can see; sessions append one line per case (the
owner's global `docs/process-mistakes.md`):

    - <YYYY-MM-DD> | <project> | <session name> | <correction | wrong order> | <what happened, one sentence>

Exit codes: 0 done, 2 bad arguments.
"""
import argparse
import datetime
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

RETRO_ENV = "DEV_KIT_RETRO_DIR"
PROJECTS_ENV = "DEV_KIT_PROJECTS_DIR"
REPEAT_MIN = 3
ERRORS_MIN = 3
MANY_CALLS = 150
SLOW_CALL_MIN = 10
SLOW_MODEL_MIN = 5
SCRIPT_SESSIONS = 3
WAITING_TOOLS = {"AskUserQuestion"}
OWN_COMMAND = "dev-kit-"  # the plugin's own commands, run by its rules at fixed moments (P's checks)
SCRIPT_MIN_CHARS = 30  # shorter Bash commands (git status, ls) are not worth a script
DETAIL_CHARS = 160
WEIGHTS = {"input": 1, "output": 5, "cache_read": 0.1, "cache_5m": 1.25, "cache_1h": 2}
MODEL_WEIGHTS = {"opus": 1.5, "sonnet": 1, "haiku": 1 / 3}  # matched as a part of the model id; Opus set from the
# owner's subscription meter (`/usage`, two 5-hour windows on 2026-11-19/20, fit 1.2-1.8), plans/retro-tokens.md
LONG_TURNS = 100
SHORT_TURNS = 50
USUAL_MIN = 10
RUNS_KEPT = 50
SPEND_ROWS = 15
WEEKLY_LIMIT_UNITS = 690e6  # the owner's weekly limit in units, fit at Opus weight 1.5 from `/usage` on 2026-11-20
WEEKLY_LIMIT_DATE = "2026-11-20"  # (plans/retro-tokens.md, "Opus weight check"; about 30% uncertain): recalibrate here
CRITICAL_SPEND_PCT = 2.0  # a session's day: spent this share of the weekly limit, or ...
CRITICAL_WASTE_PCT = 0.5  # ... wasted this share (idle wakes, cold restarts, bloated context)
NOTE_SPEND_PCT = 0.5  # below the critical shares but from these: a priority item for the retro
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


def retro_dir():
    folder = Path(os.environ[RETRO_ENV]) if os.environ.get(RETRO_ENV) else Path.home() / ".claude" / "dev-kit" / "retro"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def projects_dir():
    return Path(os.environ[PROJECTS_ENV]) if os.environ.get(PROJECTS_ENV) else Path.home() / ".claude" / "projects"


def today():
    return datetime.date.today().isoformat()


def load_state(folder):
    path = folder / "state.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    state.setdefault("offsets", {})
    state.setdefault("last_scan", "")
    state.setdefault("reviewed", {"scans_until": "", "notes_lines": 0})
    return state


def save_state(folder, state):
    path = folder / "state.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def parse_time(value):
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def short(text):
    text = " ".join(str(text).split())
    return text if len(text) <= DETAIL_CHARS else text[:DETAIL_CHARS - 3] + "..."


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


def model_family(model):
    model = str(model or "").lower()
    return next((family for family in MODEL_WEIGHTS if family in model), "other")


def number(value):
    return value if isinstance(value, (int, float)) else 0


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
    day = (stamp or datetime.datetime.now(datetime.timezone.utc)).astimezone().date().isoformat()
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
    """Counters of one transcript window: calls, repeats, errors, slow calls, pauses, Bash commands, title, spend.

    `seen` is the set of message ids already counted in this scan; lines dated before `since` are not counted.
    `last` is `(time, cache lifetime in minutes)` of the previous assistant message of this file, from an earlier scan;
    the result's `last` is the same for the next scan, and `days` the per-day units and waste (see the module doc)."""
    seen = set() if seen is None else seen
    days = {}
    turn = new_turn(None)
    prev_assistant, ttl = last if last else (None, COLD_TTL_MIN["1h"])
    units = Counter()  # model family -> units
    turns = 0
    calls = {}
    repeats = Counter()
    first_input = {}
    errors = 0
    error_tools = Counter()
    slow = []
    pauses = []
    bash = set()
    title = ""
    last_result_time = None
    for raw in lines:
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
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
        if kind == "assistant":
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
            if last_result_time and stamp:
                gap = (stamp - last_result_time).total_seconds() / 60
                if gap >= SLOW_MODEL_MIN:
                    pauses.append(gap)
            last_result_time = None
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                name = block.get("name") or "?"
                tool_input = block.get("input") or {}
                key = name + " " + json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
                own = name == "Bash" and isinstance(tool_input, dict) and OWN_COMMAND in str(tool_input.get("command"))
                if not (isinstance(tool_input, dict) and tool_input.get("run_in_background")) and not own:
                    repeats[key] += 1  # an older lead's re-armed background watcher and the plugin's own checks are by design
                first_input.setdefault(key, (name, tool_input))
                calls[block.get("id")] = (name, stamp)
                if name == "Bash" and isinstance(tool_input, dict) and tool_input.get("command") and not own:
                    command = " ".join(str(tool_input["command"]).split())
                    if len(command) >= SCRIPT_MIN_CHARS:
                        bash.add(command)
        else:
            got_result = False
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                got_result = True
                name, called = calls.get(block.get("tool_use_id"), ("?", None))
                if block.get("is_error"):
                    errors += 1
                    error_tools[name] += 1
                if called and stamp and name not in WAITING_TOOLS:
                    minutes = (stamp - called).total_seconds() / 60
                    if minutes >= SLOW_CALL_MIN:
                        slow.append((name, minutes))
            last_result_time = stamp if got_result else None
    close_turn(turn, days)
    return {
        "days": days, "last": (prev_assistant, ttl) if prev_assistant else None,
        "title": title, "calls": len(calls), "repeats": repeats, "first_input": first_input, "errors": errors,
        "error_tools": error_tools, "slow": slow, "pauses": pauses, "bash": bash, "units": units, "turns": turns,
        "runs": 1 if units else 0, "run_units": [(units.most_common(1)[0][0], sum(units.values()))] if units else [],
    }


def merge(a, b):
    """The counters of two windows of one label added together."""
    days = {day: {key: a["days"].get(day, {}).get(key, 0) + b["days"].get(day, {}).get(key, 0)
                  for key in ("units", "idle", "cold", "bloat", "wakes")} for day in {*a["days"], *b["days"]}}
    return {
        "days": days, "last": b["last"] or a["last"],
        "title": b["title"] or a["title"], "calls": a["calls"] + b["calls"], "repeats": a["repeats"] + b["repeats"],
        "first_input": {**b["first_input"], **a["first_input"]}, "errors": a["errors"] + b["errors"],
        "error_tools": a["error_tools"] + b["error_tools"], "slow": a["slow"] + b["slow"],
        "pauses": a["pauses"] + b["pauses"], "bash": a["bash"] | b["bash"], "units": a["units"] + b["units"],
        "turns": a["turns"] + b["turns"], "runs": a["runs"] + b["runs"], "run_units": a["run_units"] + b["run_units"],
    }


def findings_of(result):
    found = []
    for key, count in result["repeats"].most_common():
        if count < REPEAT_MIN:
            break
        name, tool_input = result["first_input"][key]
        found.append(("repeated call", f"{name} x{count}: {short(json.dumps(tool_input, ensure_ascii=False))}"))
    if result["errors"] >= ERRORS_MIN:
        tools = ", ".join(f"{name} x{count}" for name, count in result["error_tools"].most_common())
        found.append(("failed calls", f"{result['errors']} ({tools})"))
    if result["calls"] >= MANY_CALLS:
        found.append(("many calls", f"{result['calls']} tool calls"))
    for name, minutes in result["slow"]:
        found.append(("slow call", f"{name} took {minutes:.0f} min"))
    if result["pauses"]:
        longest = max(result["pauses"])
        found.append(("long pause", f"{len(result['pauses'])} pause(s) before the next reply, longest {longest:.0f} min"))
    return found


def scan(days=1, force=False, out=None):
    out = out or sys.stdout
    folder = retro_dir()
    state = load_state(folder)
    day = today()
    if state["last_scan"] == day and not force:
        print("already scanned today", file=out)
        return 0
    root = projects_dir()
    started = datetime.datetime.now(datetime.timezone.utc)
    since = parse_time(state.get("scan_started", ""))
    seen = set()  # message ids counted in this scan
    first = not state["offsets"]
    cutoff = time.time() - days * 86400
    known = state.setdefault("titles", {})  # a title is written once, often in an earlier scan's lines
    windows = {}  # (project, session, subagent type) -> counters; subagents of one type in one session are summed
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else []:
        key = str(path)
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
        result = analyse(lines, seen, since, (parse_time(before[0]), before[1]) if before else None)
        if result["last"]:
            state["last_assistant"][key] = [result["last"][0].isoformat(), result["last"][1]]
        for date, row in result["days"].items():
            total = state.setdefault("daily", {}).setdefault(date, {}).setdefault(
                f"{project}/{session}", {"units": 0, "idle": 0, "cold": 0, "bloat": 0, "wakes": 0})
            for field, value in row.items():
                total[field] = round(total[field] + value)
        if result["title"] and not sub:
            known[f"{project}/{session}"] = result["title"]
        merged = windows.get((project, session, sub))
        windows[(project, session, sub)] = merge(merged, result) if merged else result
    titles = {(project, session): known[f"{project}/{session}"] for project, session, _ in windows
              if known.get(f"{project}/{session}")}
    out_lines = []
    commands = defaultdict(set)
    for (project, session, sub), result in windows.items():
        label = f"{titles[(project, session)]} ({session[:8]})" if (project, session) in titles else session
        if sub:
            label += " / " + sub
        for kind, detail in findings_of(result):
            out_lines.append(f"- {project} | {label} | {kind} | {detail}")
        for command in result["bash"]:
            commands[command].add((project, session))
    for command, sessions in sorted(commands.items()):
        if len(sessions) >= SCRIPT_SESSIONS:
            out_lines.append(f"- {len({p for p, _ in sessions})} project(s) | {len(sessions)} sessions | "
                             f"script candidate | {short(command)}")
    spend_findings, table = spend(windows, titles, state)
    out_lines += spend_findings
    out_lines += priority_lines(state, day)
    if out_lines or table:
        report = folder / f"scan-{day}.md"
        header = "" if report.exists() else f"# Scan {day}\n\n"
        with open(report, "a", encoding="utf-8") as handle:
            handle.write(header + "".join(line + "\n" for line in out_lines))
            if table:
                handle.write(f"\n## Spend {started.astimezone().strftime('%H:%M')}\n\n" + "\n".join(table) + "\n\n")
    state["scan_started"] = started.isoformat()
    state["last_scan"] = day
    save_state(folder, state)
    print(f"scanned {len(windows)} transcript(s), {len(out_lines)} finding(s)", file=out)
    return 0


def percent(units):
    """Units as a share of the weekly limit, in per cent."""
    return units * 100 / WEEKLY_LIMIT_UNITS


def pct_text(value):
    return f"{value:.1f}%" if value >= 1 else f"{value:.2f}%"


def problems(row):
    """The token problems of one session's day, from the note shares up: `(kind, share, detail, critical)`.

    kind is `spend` (units spent) or `waste` (idle wakes, cold restarts, bloated context)."""
    found = []
    spend = percent(row["units"])
    if spend >= NOTE_SPEND_PCT:
        found.append(("spend", spend, f"spent {pct_text(spend)} of the weekly limit ({amount(row['units'])} units)",
                      spend >= CRITICAL_SPEND_PCT))
    waste = percent(row["idle"] + row["cold"] + row["bloat"])
    if waste >= NOTE_WASTE_PCT:
        found.append(("waste", waste, f"wasted {pct_text(waste)} of the weekly limit: idle wakes "
                      f"{pct_text(percent(row['idle']))} ({row['wakes']}), cold restarts "
                      f"{pct_text(percent(row['cold']))}, bloated context {pct_text(percent(row['bloat']))}",
                      waste >= CRITICAL_WASTE_PCT))
    return found


def session_label_of(state, key):
    """(project folder, `title (id8)` or the session id) of a `project/session` key of `state['daily']`."""
    project, _, session = key.rpartition("/")
    title = state.get("titles", {}).get(key)
    return project, f"{title} ({session[:8]})" if title else session


def priority_lines(state, day):
    """Scan lines for the token problems of every finished day not written yet; the retro lists them first.

    A day is finished once a scan runs on a later day. The days older than DAILY_KEPT are dropped from the state."""
    keep = (datetime.date.fromisoformat(day) - datetime.timedelta(days=DAILY_KEPT)).isoformat()
    daily = state.setdefault("daily", {})
    for old in [date for date in daily if date < keep]:
        del daily[old]
    stale = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)).isoformat()
    last = state.setdefault("last_assistant", {})
    for old in [path for path, (stamp, _) in last.items() if parse_time(stamp) < parse_time(stale)]:
        del last[old]
    written = state.setdefault("noted_days", [])
    lines = []
    for date in sorted(date for date in daily if date < day and date not in written):
        written.append(date)
        found = []
        for key, row in daily[date].items():
            project, label = session_label_of(state, key)
            found += [(share, f"- {project} | {label.replace('|', '/')} | token {kind} | {date}: {detail}"
                       + ("; critical (shown in Pult's status)" if critical else ""))
                      for kind, share, detail, critical in problems(row)]
        lines += [line for _, line in sorted(found, key=lambda item: -item[0])]
    state["noted_days"] = written[-DAILY_KEPT:]
    return lines


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


def spend(windows, titles, state):
    """The spend findings (long sessions, Opus coders) and the `## Spend` table lines of one scan."""
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
        found.append(f"- {project} | {label(project, session)} | long session | {so_far} main turns so far; this scan "
                     f"{sessions[(project, session)]['turns']} turns at {amount(cost)} units per turn{ratio}")
    sonnet_runs = [units for key, runs in history.items() if key.endswith("coder sonnet") for units in runs]
    sonnet_coder = median(sonnet_runs) if len(sonnet_runs) >= USUAL_MIN else 0
    for (project, session, sub), result in windows.items():
        for family, units in result["run_units"]:
            if family == "opus" and sub.endswith("coder"):
                ratio = f", x{units / sonnet_coder:.0f} of a usual Sonnet coder run" if sonnet_coder else ""
                found.append(f"- {project} | {label(project, session)} / {sub} | opus coder | "
                             f"{amount(units)} units{ratio}")
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


def spend_tables(folder, until):
    """The `## Spend` sections of the scan files dated after `until`."""
    shown = []
    for report in sorted(folder.glob("scan-*.md")):
        if report.stem[len("scan-"):] <= until:
            continue
        inside = False
        for line in report.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            if line.startswith("## Spend"):
                inside = True
                shown.append(f"### {report.stem[len('scan-'):]} {line[len('## Spend '):]}")
            elif inside and not line.startswith("- "):
                shown.append(line)
            else:
                inside = False
    return shown


def read_lines(path):
    """The `- ` lines of a findings file; agents may write it with a BOM or a non-UTF-8 code page."""
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            if line.startswith("- ")]


def snapshot(folder):
    """The newest scan date and the notes line count now."""
    scans = sorted(report.stem[len("scan-"):] for report in folder.glob("scan-*.md"))
    return {"scans_until": scans[-1] if scans else "", "notes_lines": len(read_lines(folder / "notes.md"))}


def unreviewed(folder, state):
    """The unreviewed scan lines and note lines."""
    until = state["reviewed"].get("scans_until", "")
    scan_lines = []
    for report in sorted(folder.glob("scan-*.md")):
        if report.stem[len("scan-"):] > until:
            scan_lines += read_lines(report)
    note_lines = read_lines(folder / "notes.md")
    return scan_lines, note_lines[state["reviewed"].get("notes_lines", 0):]


def check(days=1, out=None):
    out = out or sys.stdout
    folder = retro_dir()
    if load_state(folder)["last_scan"] != today():
        with open(os.devnull, "w", encoding="utf-8") as quiet:
            scan(days=days, out=quiet)
    state = load_state(folder)
    scan_lines, note_lines = unreviewed(folder, state)
    count = len(scan_lines) + len(note_lines)
    state["shown"] = snapshot(folder)
    save_state(folder, state)
    print(f"new findings: {count}" if count else "no new findings", file=out)
    return 0


def list_findings(out=None):
    out = out or sys.stdout
    folder = retro_dir()
    state = load_state(folder)
    scan_lines, note_lines = unreviewed(folder, state)
    state["shown"] = snapshot(folder)
    save_state(folder, state)
    urgent = [line for line in scan_lines if " | token spend | " in line or " | token waste | " in line]
    print("## Priority: token problems (read first; the retro asks them before the rest)", file=out)
    print("\n".join(urgent) or "(none)", file=out)
    print("\n## Scan findings", file=out)
    print("\n".join(line for line in scan_lines if line not in urgent) or "(none)", file=out)
    print("\n## Session notes", file=out)
    print("\n".join(note_lines) or "(none)", file=out)
    tables = spend_tables(folder, state["reviewed"].get("scans_until", ""))
    if tables:
        print("\n## Spend (units; evidence for the findings above, not findings)", file=out)
        print("\n".join(tables).rstrip(), file=out)
    return 0


def critical(days=1, out=None):
    """Print the critical token problems of today and the days before it not shown yet, or grown since shown."""
    out = out or sys.stdout
    folder = retro_dir()
    if load_state(folder)["last_scan"] != today():
        with open(os.devnull, "w", encoding="utf-8") as quiet:
            scan(days=days, out=quiet)
    state = load_state(folder)
    first = (datetime.date.fromisoformat(today()) - datetime.timedelta(days=CRITICAL_DAYS)).isoformat()
    shown = {key: value for key, value in state.setdefault("critical_shown", {}).items() if key.split("|")[0] >= first}
    lines = []
    for date, sessions in state.get("daily", {}).items():
        if date < first:
            continue
        for key, row in sessions.items():
            project, label = session_label_of(state, key)
            for kind, share, detail, is_critical in problems(row):
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


def done(out=None):
    """Mark reviewed what the last `check` or `list` showed (not findings added after it)."""
    out = out or sys.stdout
    folder = retro_dir()
    state = load_state(folder)
    shown = state.pop("shown", None) or snapshot(folder)
    reviewed = state["reviewed"]
    state["reviewed"] = {"scans_until": max(shown["scans_until"], reviewed.get("scans_until", "")),
                         "notes_lines": max(shown["notes_lines"], reviewed.get("notes_lines", 0))}
    save_state(folder, state)
    print("marked reviewed", file=out)
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # transcripts hold any language; a Windows console code page cannot
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="dev-kit-retro")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "scan", "critical"):
        command = sub.add_parser(name)
        command.add_argument("--days", type=float, default=1)
        if name == "scan":
            command.add_argument("--force", action="store_true")
    sub.add_parser("list")
    sub.add_parser("done")
    args = parser.parse_args(argv)
    if args.command == "check":
        return check(days=args.days)
    if args.command == "critical":
        return critical(days=args.days)
    if args.command == "scan":
        return scan(days=args.days, force=args.force)
    if args.command == "list":
        return list_findings()
    return done()


if __name__ == "__main__":
    sys.exit(main())
