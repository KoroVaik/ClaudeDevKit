"""Experiments of spend-kit (docs/features/catch-wasted-work.md, "Experiments"): two variants of one helper or Manager
kind, picked by turns, each run logged with its variant, and the rules that read the runs' numbers. The hook that
picks for helpers is `hooks/experiment.py`; the daily count that joins the log to the transcripts and writes the
findings is `spend.py` (`experiment_entries`); this file holds the state, the pick log and the pure rules.

Types (EXPERIMENTS): `dev-kit:coder`, `dev-kit:reviewer`, `rules-kit:rule-reviewer`: `sonnet-high` (the old one,
model `sonnet`, effort `high`) against `opus-low`; `manager` (a Manager session, picked per task at its start):
`opus-medium` (the old one) against `opus-low`.

State `<data folder>/experiments-state.json`, read and written under `experiments.lock` (a lock like the others):

    {"types": {"dev-kit:coder": {"next": 3, "stopped": {"opus-low": "reason"}, "decided": null, "reason": ""}},
     "marks": {"alarm|dev-kit:coder|opus-low": 4, "result|dev-kit:coder": 1}}

`next` counts the picks (the variants take turns over the ones not stopped); `stopped` maps a stopped variant to the
reason; `decided` is the winner (or null), always given from then on. A stopped variant is skipped; when only the old
one is left the override stops: a helper keeps its agent file's lines, `experiment next` prints the old effort. `marks`
keep what the daily count has reported: the run count at an alarm, a result once.

Pick log `<data folder>/experiments.jsonl` (`signals.EXPERIMENTS_NAME`, which the model-mismatch check also reads),
one JSON per pick, appended: `time`, `session` (env CLAUDE_CODE_SESSION_ID, else the hook payload's `session_id`),
`type`, `variant` (`reset` for a context-heavy helper whose Opus or Fable model was reset), `model`, `effort`, and
`tool_use_id` (a helper) or `task` (a Manager).

The rules (`alarming`, `actions`) work on a tally per variant, `{"runs", "units", "signs"}`: a variant is alarming when
both variants have ALARM_RUNS or more runs and its signs per run are ALARM_SIGNS_RATIO times the other's or more with
ALARM_MIN_SIGNS signs at least, or its units per run are ALARM_UNITS_RATIO times the other's or more; it is reported once
for a run count. With RESULT_RUNS runs of each variant a type gets one result, until it is decided."""
import datetime
import json
from pathlib import Path

import signals
import spend_dir

EXPERIMENTS = {
    "dev-kit:coder": {"old": "sonnet-high", "variants": {"sonnet-high": ("sonnet", "high"), "opus-low": ("opus", "low")}},
    "dev-kit:reviewer": {"old": "sonnet-high",
                         "variants": {"sonnet-high": ("sonnet", "high"), "opus-low": ("opus", "low")}},
    "rules-kit:rule-reviewer": {"old": "sonnet-high",
                                "variants": {"sonnet-high": ("sonnet", "high"), "opus-low": ("opus", "low")}},
    "manager": {"old": "opus-medium", "variants": {"opus-medium": ("opus", "medium"), "opus-low": ("opus", "low")}},
}
CONTEXT_HEAVY = ("dev-kit:mechanical-editor", "dev-kit:overlap-checker", "dev-kit:question-reader",
                 "rules-kit:part-reader", "rules-kit:replayer")  # helpers that fill a big context with easy work
EXPENSIVE = ("opus", "fable")  # a caller's choice of these for a CONTEXT_HEAVY helper is reset to the file's model
STATE_NAME = "experiments-state.json"
LOCK_NAME = "experiments.lock"
LOCK_WAIT_S = 5
LOCK_STALE_S = 60
ALARM_RUNS = 3
ALARM_SIGNS_RATIO = 2
ALARM_MIN_SIGNS = 2
ALARM_UNITS_RATIO = 1.5
RESULT_RUNS = 10  # the spend-kit threshold for a usual run (`spend.USUAL_MIN`)
PACKET_LINES = 40


def state_file():
    return spend_dir.data_dir() / STATE_NAME


def log_file():
    return spend_dir.data_dir() / signals.EXPERIMENTS_NAME


def lock():
    return spend_dir.file_lock(spend_dir.data_dir() / LOCK_NAME, LOCK_WAIT_S, LOCK_STALE_S)


def load_state():
    try:
        state = json.loads(state_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    state = state if isinstance(state, dict) else {}
    state.setdefault("types", {})
    state.setdefault("marks", {})
    return state


def save_state(state):
    spend_dir.write_json(state_file(), state)


def type_state(state, kind):
    return state["types"].setdefault(kind, {"next": 0, "stopped": {}, "decided": None, "reason": ""})


def pick_variant(entry, spec):
    """The next variant of a type (`entry` its state, changed: `next` rises), or None when the override stops."""
    if entry["decided"]:
        return entry["decided"]
    active = [variant for variant in spec["variants"] if variant not in entry["stopped"]]
    if not active or active == [spec["old"]]:
        return None
    if len(active) == 1:
        return active[0]
    variant = active[entry["next"] % len(active)]
    entry["next"] += 1
    return variant


def now_text(now=None):
    return (now or datetime.datetime.now(datetime.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_pick(entry):
    log_file().parent.mkdir(parents=True, exist_ok=True)
    with open(log_file(), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_picks():
    """The log's picks (dicts), oldest first; a bad line is skipped."""
    picks = []
    try:
        lines = log_file().read_text(encoding="utf-8").splitlines()
    except OSError:
        return picks
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("type") and entry.get("variant"):
            picks.append(entry)
    return picks


def choose(kind, session="", tool_use_id=None, task=None, now=None):
    """Pick the next variant of `kind` and log it: `(variant, model, effort)` or None when the override stops (or the
    state is busy). A Manager (`task`) gets the old variant's values instead of None, not logged."""
    spec = EXPERIMENTS[kind]
    with lock() as held:
        if not held:
            return None
        state = load_state()
        variant = pick_variant(type_state(state, kind), spec)
        save_state(state)
        if variant is None:
            if task is None:
                return None
            return (spec["old"], *spec["variants"][spec["old"]])
        model, effort = spec["variants"][variant]
        pick = {"time": now_text(now), "session": session, "type": kind, "variant": variant, "model": model,
                "effort": effort}
        pick.update({"task": task} if task is not None else {"tool_use_id": tool_use_id})
        append_pick(pick)
        return variant, model, effort


def log_reset(kind, session, tool_use_id, model, was, now=None):
    """Log a context-heavy helper whose Opus or Fable model was reset to its file's `model`."""
    with lock() as held:
        if held:
            append_pick({"time": now_text(now), "session": session, "type": kind, "variant": "reset", "model": model,
                         "effort": None, "was": was, "tool_use_id": tool_use_id})


def close_variant(kind, variant, reason, decide):
    """`stop` or (`decide`) a variant of a type; ValueError for an unknown type or variant."""
    spec = EXPERIMENTS.get(kind)
    if not spec or variant not in spec["variants"]:
        known = ", ".join(f"{name}: {'/'.join(item['variants'])}" for name, item in EXPERIMENTS.items())
        raise ValueError(f"unknown type or variant {kind!r} {variant!r}; known: {known}")
    with lock() as held:
        if not held:
            raise ValueError("experiments state is busy, try again")
        state = load_state()
        entry = type_state(state, kind)
        if decide:
            entry["decided"], entry["reason"] = variant, reason
        else:
            entry["stopped"][variant] = reason
        save_state(state)


def stop(kind, variant, reason):
    close_variant(kind, variant, reason, decide=False)


def decide(kind, variant, reason):
    close_variant(kind, variant, reason, decide=True)


# ---------------------------------------------------------------- the rules over the runs' numbers

def tally(runs):
    """`{"runs", "units", "signs"}` of a variant's runs (`[{"units": n, "signs": [..]}, ...]`)."""
    return {"runs": len(runs), "units": sum(run["units"] for run in runs), "signs": sum(len(run["signs"]) for run in runs)}


def per_run(value, mine):
    return value / mine["runs"] if mine["runs"] else 0.0


def alarming(mine, other):
    """True when a variant's numbers are alarming against the other's (module doc)."""
    if mine["runs"] < ALARM_RUNS or other["runs"] < ALARM_RUNS:
        return False
    signs = (mine["signs"] >= ALARM_MIN_SIGNS
             and per_run(mine["signs"], mine) >= ALARM_SIGNS_RATIO * per_run(other["signs"], other))
    other_units = per_run(other["units"], other)
    return signs or (other_units > 0 and per_run(mine["units"], mine) >= ALARM_UNITS_RATIO * other_units)


def actions(kind, tallies, marks, entry):
    """`[("alarm", variant), ("result", None)]` still to report for a type: `tallies` maps its two variants to `tally`,
    `marks` is the state's, `entry` the type's state. Nothing once decided."""
    if entry["decided"] or len(tallies) < 2:
        return []
    found = []
    for variant, mine in tallies.items():
        other = next(item for name, item in tallies.items() if name != variant)
        if (variant not in entry["stopped"] and alarming(mine, other)
                and mine["runs"] > marks.get(f"alarm|{kind}|{variant}", 0)):
            found.append(("alarm", variant))
    if all(item["runs"] >= RESULT_RUNS for item in tallies.values()) and not marks.get(f"result|{kind}"):
        found.append(("result", None))
    return found


def numbers(variant, mine, amount):
    """`<signs>/<runs> signs, <units per run> units per run` of a tally (`amount`: the units formatter)."""
    return f"{mine['signs']}/{mine['runs']} signs, {amount(per_run(mine['units'], mine))} units per run"


def packet_text(kind, variant, tallies, runs, amount, date):
    """The packet of an alarming variant (at most PACKET_LINES lines): the numbers, and per run its transcript, its
    helper file and each sign with its line number and excerpt. `runs` are the variant's run records."""
    other = next(name for name in tallies if name != variant)
    lines = [f"# {kind} {variant}, {date}", "",
             f"{variant}: {numbers(variant, tallies[variant], amount)}; {other}: {numbers(other, tallies[other], amount)}", ""]
    for number, run in enumerate(runs, 1):
        lines.append(f"## Run {number}: {amount(run['units'])} units")
        lines.append(f"transcript: {run['transcript']}")
        if run.get("subagent"):
            lines.append(f"helper file: {run['subagent']}")
        lines += [f"- {sign['kind']}, line {sign['line']}: {sign['text']}" for sign in run["signs"]] or ["- no signs"]
    if len(lines) > PACKET_LINES:
        lines = lines[:PACKET_LINES - 1] + [f"... {len(lines) - PACKET_LINES + 1} more lines left out"]
    return "\n".join(lines) + "\n"


def status_text(kind, tallies, entry, amount):
    """The plain-text status of one type: a line per variant (runs, units per run, signs per run), then what is
    stopped or decided with its reason."""
    spec = EXPERIMENTS[kind]
    lines = [f"{kind} (старий {spec['old']})"]
    for variant in spec["variants"]:
        mine = tallies.get(variant) or {"runs": 0, "units": 0, "signs": 0}
        lines.append(f"  {variant}: {mine['runs']} запусків, {amount(per_run(mine['units'], mine))} одиниць на запуск, "
                     f"{per_run(mine['signs'], mine):.1f} ознак на запуск")
    lines += [f"  зупинено {variant}: {reason}" for variant, reason in entry["stopped"].items()]
    if entry["decided"]:
        lines.append(f"  вирішено {entry['decided']}: {entry['reason']}")
    return lines


def packet_path(folder, kind, variant, date):
    return Path(folder) / "experiment-packets" / f"{kind.replace(':', '-')}-{variant}-{date}.md"
