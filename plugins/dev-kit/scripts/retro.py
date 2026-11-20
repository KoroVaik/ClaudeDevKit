"""Find problems in the sessions' transcripts with no model, and keep the findings for a retro session.

    dev-kit-retro check [--days N]     scan if not yet scanned today, then print the count of unreviewed findings
    dev-kit-retro scan [--force] [--days N]
    dev-kit-retro list                 print the unreviewed findings (scan lines, session notes, then the spend tables)
    dev-kit-retro done                 mark what the last check or list showed as reviewed (after a retro, or a no)

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
  a watcher re-armed after each exit is by design);
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


def units_of(usage, model):
    """The units of one message's usage."""
    def number(value):
        return value if isinstance(value, (int, float)) else 0
    cache = usage.get("cache_creation") if isinstance(usage.get("cache_creation"), dict) else None
    if cache:
        five, hour = number(cache.get("ephemeral_5m_input_tokens")), number(cache.get("ephemeral_1h_input_tokens"))
    else:
        five, hour = number(usage.get("cache_creation_input_tokens")), 0
    raw = (number(usage.get("input_tokens")) * WEIGHTS["input"] + number(usage.get("output_tokens")) * WEIGHTS["output"]
           + number(usage.get("cache_read_input_tokens")) * WEIGHTS["cache_read"]
           + five * WEIGHTS["cache_5m"] + hour * WEIGHTS["cache_1h"])
    return raw * MODEL_WEIGHTS.get(model_family(model), 1)


def analyse(lines, seen=None, since=None):
    """Counters of one transcript window: calls, repeats, errors, slow calls, pauses, Bash commands, title, spend.

    `seen` is the set of message ids already counted in this scan; lines dated before `since` are not counted."""
    seen = set() if seen is None else seen
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
        if kind == "user" and fresh and not entry.get("isMeta") and not (
                isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result"
                                                  for b in content)):
            turns += 1
        if not isinstance(content, list):
            content = []
        if kind == "assistant":
            usage, model, mid = message.get("usage"), message.get("model"), message.get("id")
            if isinstance(usage, dict) and model != "<synthetic>" and fresh and mid not in seen:
                if mid:
                    seen.add(mid)
                units[model_family(model)] += units_of(usage, model)
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
                    repeats[key] += 1  # a re-armed background watcher and the plugin's own checks are by design
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
    return {
        "title": title, "calls": len(calls), "repeats": repeats, "first_input": first_input, "errors": errors,
        "error_tools": error_tools, "slow": slow, "pauses": pauses, "bash": bash, "units": units, "turns": turns,
        "runs": 1 if units else 0, "run_units": [(units.most_common(1)[0][0], sum(units.values()))] if units else [],
    }


def merge(a, b):
    """The counters of two windows of one label added together."""
    return {
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
        result = analyse(lines, seen, since)
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
    print("## Scan findings", file=out)
    print("\n".join(scan_lines) or "(none)", file=out)
    print("\n## Session notes", file=out)
    print("\n".join(note_lines) or "(none)", file=out)
    tables = spend_tables(folder, state["reviewed"].get("scans_until", ""))
    if tables:
        print("\n## Spend (units; evidence for the findings above, not findings)", file=out)
        print("\n".join(tables).rstrip(), file=out)
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
    for name in ("check", "scan"):
        command = sub.add_parser(name)
        command.add_argument("--days", type=float, default=1)
        if name == "scan":
            command.add_argument("--force", action="store_true")
    sub.add_parser("list")
    sub.add_parser("done")
    args = parser.parse_args(argv)
    if args.command == "check":
        return check(days=args.days)
    if args.command == "scan":
        return scan(days=args.days, force=args.force)
    if args.command == "list":
        return list_findings()
    return done()


if __name__ == "__main__":
    sys.exit(main())
