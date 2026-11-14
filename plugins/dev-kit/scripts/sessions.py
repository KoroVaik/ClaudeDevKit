"""Keep the registry of the background task sessions (C) that a project lead session (P) started, and show how
full their context is.

    dev-kit-sessions add --id <id> --name <name> --worktree <path> --task <file or text> [--parent <id>] [--predecessor <id>]
    dev-kit-sessions end --id <id> [--status done|replaced|stopped]
    dev-kit-sessions list
    dev-kit-sessions fill [--limit 0.5] [--window N]

The registry is `sessions.json` in the project state folder (see dev_kit_state.py; the same folder for all worktrees
of one repository). `add --predecessor` marks the replaced session `replaced`. `fill` finds the transcript of every
active record (`<projects>/*/<id>.jsonl`, projects folder = env DEV_KIT_PROJECTS_DIR, else ~/.claude/projects) and
prints its context size: input + cache creation + cache read tokens of the last assistant message that has usage.
The window comes from the transcript's model (see `window_for`) unless `--window` is given. A line ends with OVER when the
percent reaches the limit. Exit code: 0 done (fill too, whatever the transcripts), 1 unknown or duplicate id,
2 registry unreadable.
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dev_kit_state  # noqa: E402

REGISTRY = "sessions.json"
PROJECTS_ENV = "DEV_KIT_PROJECTS_DIR"
DEFAULT_WINDOW = 200000
NATIVE_1M_WINDOW = 1000000
USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
CHUNK = 256 * 1024


class Unreadable(Exception):
    """The registry cannot be read: exit code 2."""


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def registry_path(project):
    return dev_kit_state.project_state_dir(project) / REGISTRY


def load(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise Unreadable(f"{path} is unreadable: {exc}")
    if not isinstance(data, list):
        raise Unreadable(f"{path} is not a list of records")
    return data


def save(path, records):
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for attempt in range(6):  # on Windows a reader that has the file open makes the replace fail for a moment
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(0.05 * (attempt + 1))


def find(records, session_id):
    return next((record for record in records if record.get("id") == session_id), None)


def projects_dir():
    return Path(os.environ[PROJECTS_ENV]) if os.environ.get(PROJECTS_ENV) else Path.home() / ".claude" / "projects"


def find_transcript(session_id):
    found = sorted(projects_dir().glob(f"*/{session_id}.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0] if found else None


def last_usage(path):
    """(tokens, model) of the last assistant message with non-zero usage, reading the file from the end; None if
    none. Messages whose usage sums to 0 (synthetic or interrupted) are skipped."""
    size = path.stat().st_size
    window = CHUNK
    with open(path, "rb") as handle:
        while True:
            start = max(0, size - window)
            handle.seek(start)
            lines = handle.read(size - start).split(b"\n")
            if start > 0:
                lines = lines[1:]  # the first line may be cut; the next, larger read covers it whole
            for line in reversed(lines):
                if b'"usage"' not in line:
                    continue
                try:
                    message = json.loads(line.decode("utf-8")).get("message") or {}
                except ValueError:  # includes UnicodeDecodeError
                    continue
                usage = message.get("usage")
                if message.get("role", "assistant") == "assistant" and isinstance(usage, dict):
                    tokens = sum(int(usage.get(field) or 0) for field in USAGE_FIELDS)
                    if tokens > 0:
                        return tokens, message.get("model") or ""
            if start == 0:
                return None
            window *= 4


def cmd_add(args, path, records):
    if find(records, args.id):
        print(f"dev-kit-sessions: id {args.id} is already registered", file=sys.stderr)
        return 1
    if args.predecessor:
        old = find(records, args.predecessor)
        if old is None:
            print(f"dev-kit-sessions: predecessor {args.predecessor} is not registered", file=sys.stderr)
            return 1
        old.update(status="replaced", ended=now())
    records.append({"id": args.id, "name": args.name, "worktree": args.worktree, "task": args.task,
                    "parent": args.parent, "predecessor": args.predecessor, "status": "active",
                    "started": now(), "ended": None})
    save(path, records)
    print(f"added {args.name} ({args.id})")
    return 0


def cmd_end(args, path, records):
    record = find(records, args.id)
    if record is None:
        print(f"dev-kit-sessions: id {args.id} is not registered", file=sys.stderr)
        return 1
    record.update(status=args.status, ended=now())
    save(path, records)
    print(f"{args.status}: {record['name']} ({args.id})")
    return 0


def active(records):
    return [record for record in records if record.get("status") == "active"]


def cmd_list(args, path, records):
    rows = active(records)
    for record in rows:
        print(f"{record['name']} | {record['id']} | {record['worktree']} | {record['task']} | {record['started']}")
    if not rows:
        print("no active sessions")
    return 0


def window_for(model):
    """Context window of a model id as Claude Code runs it by default.

    Claude Code docs (model-config, "Extended context"): Fable models, Sonnet 5 and later, Haiku 5.5 and
    Opus 4.7 and later run with the 1M window by default, with no `[1m]` suffix; env
    CLAUDE_CODE_DISABLE_1M_CONTEXT=1 makes them 200K. Older models get 200K unless the id carries `[1m]`.
    """
    name = (model or "").lower()
    if "[1m]" in name:
        return NATIVE_1M_WINDOW
    if os.environ.get("CLAUDE_CODE_DISABLE_1M_CONTEXT") == "1":
        return DEFAULT_WINDOW
    if "fable" in name or name in ("opus", "sonnet", "haiku"):
        return NATIVE_1M_WINDOW
    match = re.search(r"(opus|sonnet|haiku)-(\d+)-(\d+)", name)
    if match:
        family, version = match.group(1), (int(match.group(2)), int(match.group(3)))
        if (family == "sonnet" and version >= (5, 0)) or (family == "haiku" and version >= (5, 5)) \
                or (family == "opus" and version >= (4, 7)):
            return NATIVE_1M_WINDOW
    return DEFAULT_WINDOW


def cmd_fill(args, path, records):
    rows = active(records)
    for record in rows:
        transcript = find_transcript(record["id"])
        usage = last_usage(transcript) if transcript else None
        if usage is None:
            print(f"{record['name']} | {record['id']} | no transcript")
            continue
        tokens, model = usage
        window = args.window or window_for(model)
        percent = tokens / window
        flag = " OVER" if percent >= args.limit else ""
        print(f"{record['name']} | {record['id']} | {tokens} tokens | window {window} | {percent:.0%}{flag}")
    if not rows:
        print("no active sessions")
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="dev-kit-sessions", description=__doc__.splitlines()[0])
    parser.add_argument("--project", default=".", help="the project folder or a folder inside it (default: current)")
    sub = parser.add_subparsers(dest="action", required=True)
    add = sub.add_parser("add")
    for flag in ("--id", "--name", "--worktree", "--task"):
        add.add_argument(flag, required=True)
    add.add_argument("--parent")
    add.add_argument("--predecessor")
    end = sub.add_parser("end")
    end.add_argument("--id", required=True)
    end.add_argument("--status", choices=["done", "replaced", "stopped"], default="done")
    sub.add_parser("list")
    fill = sub.add_parser("fill")
    fill.add_argument("--limit", type=float, default=0.5)
    fill.add_argument("--window", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        path = registry_path(args.project)
        records = load(path)
        return {"add": cmd_add, "end": cmd_end, "list": cmd_list, "fill": cmd_fill}[args.action](args, path, records)
    except Unreadable as exc:
        print(f"dev-kit-sessions: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
