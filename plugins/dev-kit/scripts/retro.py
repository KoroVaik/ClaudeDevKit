"""Find problems in the sessions' transcripts with no model, and keep the findings for a retro session.

    dev-kit-retro check [--days N]     scan if not yet scanned today, then print the count of unreviewed findings
    dev-kit-retro scan [--force] [--days N]
    dev-kit-retro list                 print the unreviewed findings (scan lines, then session notes)
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


def analyse(lines):
    """Counters of one transcript window: calls, repeats, errors, slow calls, pauses, Bash commands, title."""
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
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            content = []
        if kind == "assistant":
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
        "error_tools": error_tools, "slow": slow, "pauses": pauses, "bash": bash,
    }


def merge(a, b):
    """The counters of two windows of one label added together."""
    return {
        "title": b["title"] or a["title"], "calls": a["calls"] + b["calls"], "repeats": a["repeats"] + b["repeats"],
        "first_input": {**b["first_input"], **a["first_input"]}, "errors": a["errors"] + b["errors"],
        "error_tools": a["error_tools"] + b["error_tools"], "slow": a["slow"] + b["slow"],
        "pauses": a["pauses"] + b["pauses"], "bash": a["bash"] | b["bash"],
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
    first = not state["offsets"]
    cutoff = time.time() - days * 86400
    titles = {}
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
        result = analyse(lines)
        if result["title"] and not sub:
            titles[(project, session)] = result["title"]
        merged = windows.get((project, session, sub))
        windows[(project, session, sub)] = merge(merged, result) if merged else result
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
    if out_lines:
        report = folder / f"scan-{day}.md"
        header = "" if report.exists() else f"# Scan {day}\n\n"
        with open(report, "a", encoding="utf-8") as handle:
            handle.write(header + "\n".join(out_lines) + "\n")
    state["last_scan"] = day
    save_state(folder, state)
    print(f"scanned {len(windows)} transcript(s), {len(out_lines)} finding(s)", file=out)
    return 0


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
