"""Keep the registry of the background task sessions (C) that a project lead session (P) started, and show how
full their context is.

    dev-kit-sessions add --id <id> --name <name> --worktree <path> --task <file or text> [--parent <id>] [--predecessor <id>] [--owner]
    dev-kit-sessions end --id <id or 8+ char short id> [--status done|replaced|stopped]
    dev-kit-sessions list
    dev-kit-sessions fill [--limit 0.5] [--window N]
    dev-kit-sessions others [--self <id>] [--json]
    dev-kit-sessions state [--id <id> ...]
    dev-kit-sessions watch [--id <id> ...] [--interval 60] [--max-minutes 120]
    dev-kit-sessions limited --id <id> [--id <id> ...]
    dev-kit-sessions restart request --version <V> | ready [--version <V>] | status | clear

The registry is `sessions.json` in the project state folder (see dev_kit_state.py; the same folder for all worktrees
of one repository). Ids (`--id`, `--parent`, `--predecessor`, `--self`) and the registry's ids are trimmed of spaces and
line ends: an id pasted from `claude --bg` output once carried a CR and matched no session. `add --predecessor` marks the replaced session `replaced`. `add --owner` marks a session the
owner started and the lead took over (the record gets `"owner": true`; the UserPromptSubmit hook
hooks/owner-session-note.py reads it). `fill` finds the transcript of every
active record (`<projects>/*/<id>.jsonl`, projects folder = env DEV_KIT_PROJECTS_DIR, else ~/.claude/projects) and
prints its context size: input + cache creation + cache read tokens of the last assistant message that has usage.
The window comes from the transcript's model (see `window_for`) unless `--window` is given. A line ends with OVER when the
percent reaches the limit.

`others` lists the live sessions of this repository (any worktree) other than the caller, for the overlap check
before a task starts. Source: `claude agents --json` (background sessions and running interactive ones, the desktop
Code tab included; env DEV_KIT_AGENTS_JSON names a file to read instead). The claude command is taken from PATH, else
from the usual install places (see `claude_candidates`), since a subagent's shell may lack the npm folder. The caller is `--self`, else env
CLAUDE_CODE_SESSION_ID. Lead sessions (name starts with `P: `) are left out: they do no task work. For each: name,
state, who started it (`lead` when the registry holds its id, else `owner`), branch, cwd, the first task messages
(owner or peer messages of its transcript, cut to TASK_CHARS) and the files it changed (the branch against the base
branch, plus uncommitted ones). Reads no code. Prints `no other sessions` when there are none.

`state` prints one line per active registry record (or per `--id`, full or 8+ char prefix): `name | id | working|
waiting|limited|finished|gone | gist`. The gist is the tail (at most GIST_CHARS) of the last assistant text message of the
transcript, read from the end of the file. Status comes from `claude agents --json --all` (an entry matches a
registry id by `id`, `sessionId` or a sessionId prefix): `finished` when that last reply has a line that, trimmed and
without trailing punctuation, is one of FINISHED_MARKERS and no owner message came after it, and only for a record
added with `--owner` (a C never reports finished); else `gone` when no
matching entry has a `pid` (a session with none is closed, see `watch`); `limited` when its transcript ends with
Claude Code's usage-limit notice (see `usage_limit`; the gist then starts with `resets <YYYY-MM-DD HH:MM>;`, local
time, or `resets unknown;`): such a session keeps its process and is listed as blocked, so the list cannot tell;
`working` when the status is busy; else `waiting`. Exit 3 when the list cannot be read.

`watch` waits in silence while the watched sessions live and exits with one line when one is gone, finished (the
last reply has the finished marker, see `state`) or limited (stopped on the usage limit, see `state`), so a caller that
runs it in the background wakes only then. Watched: the `--id` sessions (full or 8+ char short ids), else the
registry's active records, read again each round (a C added later is watched too; one ended with `end` is not).
Every `--interval` seconds it reads `claude agents --json --all`: a session is live while an entry with its id has a
`pid`; one with no `pid` is not live. A session not in the list is gone at once. An entry in the list with no
`pid`, whatever its state (done, stopped and blocked all occur: Claude Code closes sessions on low memory or after
8 h idle), is reported gone only after it stayed without a `pid` for CLOSED_GRACE seconds (300, counted by the
watcher across rounds; a `pid` again clears it), so the Pult watcher can bring it back with `claude respawn`
first. Lines and exit codes:
`gone: <name> | <id> | <state or 'not in the session list'>` (one per gone session) and
`finished: <name> | <id>` (one per finished session, also one that is gone) and `limited: <name> | <id> | resets
<time or unknown>` (one per live session that stopped on the usage limit, see `state`; each stop is reported once:
LIMITS in the state folder keeps the stop already reported, so the re-armed watcher stays quiet until the session
goes on and stops again) exit 0; `time limit: <N> min,
all alive` exit 4 (re-arm it); `nothing to watch` exit 5 (on the first round, or at the time limit when the registry
has emptied meanwhile: a watcher whose last C ended keeps quiet); `already watching: pid <N>` exit 6 (in registry
mode one watcher per project runs: a lock file in the state folder with a heartbeat; a new watcher waits until the
heartbeat moves, then exits 6, or until it is stale after 3 intervals, then takes the lock of the killed watcher;
a lock whose pid is not a live process is taken at once);
the registry or the session list unreadable WATCH_FAILURES rounds in a row: exit 3; `restart requested: <V>` exit 7
(each round, before the other checks and also on the first round with nothing to watch, only once per request:
`restart.json` holds an open request that is neither ready nor notified yet; the exit sets `"notified"`, so the
re-armed watcher stays quiet, see the next paragraph).

`limited` prints `<id> | <resets> | <key>` for each `--id` (a full session id) whose transcript ends with the
usage-limit notice, nothing for the others; it reads transcripts only, no session list and no project state (the
Pult watcher calls it once per round with the live leads and task sessions). Exit 0.

`restart` is the file handshake for a lead's restart on a new dev-kit version (the Pult watcher does the restart).
`restart.json` in the project state folder holds `{"version": V, "asked": <epoch>, "ready": <epoch>, "notified":
<epoch>}`; the last three keys are optional. The lead itself runs `ready --version V` when it sees a newer version
than its own and is at a safe point; `restart-leads.ps1 -Ask` writes a request for a busy lead with `request
--version V`. `request --version V` writes `{"version", "asked"}` (a request for another version replaces the old
one, the same version keeps it, ready and notified marks included); `ready` marks the open request ready (exit 1
and a message when none is open); `ready --version V` needs no request: it creates one that is ready, or marks
the open one ready when it is for V (one for another version is replaced); `status` prints `none`, `asked <V>
<seconds>` or `ready <V> <seconds>` (the seconds since the request was asked or marked ready); `clear` removes the
file (fine when absent). A ready, notified or absent request does not stop `watch`.

Exit code: 0 done (fill too, whatever the transcripts), 1 unknown or duplicate id (restart: `ready` with no
request), 2 registry unreadable, 3 the session list could not be read.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dev_kit_state  # noqa: E402

REGISTRY = "sessions.json"
RESTART = "restart.json"
PROJECTS_ENV = "DEV_KIT_PROJECTS_DIR"
DEFAULT_WINDOW = 200000
NATIVE_1M_WINDOW = 1000000
USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
CHUNK = 256 * 1024
AGENTS_ENV = "DEV_KIT_AGENTS_JSON"
LEAD_PREFIX = "P: "
TASK_MESSAGES = 2
TASK_CHARS = 700
FILES_SHOWN = 40
WATCH_LOCK = "watch.lock"
WATCH_FAILURES = 5
ID_KEYS = ("id", "parent", "predecessor")
LIMITS = "limits.json"
CLOSED_GRACE = 300  # seconds a session with no pid stays unreported: the Pult watcher may bring it back meanwhile
# A reply line (trimmed, emphasis marks and trailing punctuation removed, case ignored) that says the session is done.
FINISHED_MARKERS = ("Роботу завершено", "Work finished")
GIST_CHARS = 120

class Unreadable(Exception):
    """The registry cannot be read: exit code 2."""


def now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def registry_path(project, create=True):
    return dev_kit_state.project_state_dir(project, create) / REGISTRY


def load(path):
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise Unreadable(f"{path} is unreadable: {exc}")
    if not isinstance(data, list):
        raise Unreadable(f"{path} is not a list of records")
    for record in data:  # an id pasted from `claude --bg` output may carry a CR or spaces: it would match nothing
        if isinstance(record, dict):
            for key in ID_KEYS:
                if isinstance(record.get(key), str):
                    record[key] = record[key].strip()
    return data


def save(path, records):  # records: the registry list, or the restart request dict
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


def resolve(records, session_id):
    """The record whose id is session_id, else the only one whose id starts with it (the 8-hex short id that
    `claude --bg` prints, so at least 8 characters); None if there is none or several."""
    exact = find(records, session_id)
    if exact is not None or len(session_id) < 8:
        return exact
    matches = [record for record in records if str(record.get("id", "")).startswith(session_id)]
    return matches[0] if len(matches) == 1 else None


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
        old = resolve(records, args.predecessor)
        if old is None:
            print(f"dev-kit-sessions: predecessor {args.predecessor} is not registered", file=sys.stderr)
            return 1
        old.update(status="replaced", ended=now())
    records.append({"id": args.id, "name": args.name, "worktree": args.worktree, "task": args.task,
                    "parent": args.parent, "predecessor": old["id"] if args.predecessor else None, "status": "active",
                    "started": now(), "ended": None, **({"owner": True} if args.owner else {})})
    save(path, records)
    print(f"added {args.name} ({args.id})")
    return 0


def cmd_end(args, path, records):
    record = resolve(records, args.id)
    if record is None:
        print(f"dev-kit-sessions: id {args.id} is not registered (or the short id fits several)", file=sys.stderr)
        return 1
    record.update(status=args.status, ended=now())
    save(path, records)
    print(f"{args.status}: {record['name']} ({record['id']})")
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


def claude_candidates():
    """The usual install places of the claude command, for a shell whose PATH lacks it (a subagent's or a hidden
    window's): the native installer, the npm global folders, Homebrew and /usr/local."""
    home = Path.home()
    places = [home / ".local" / "bin", home / ".claude" / "local", home / ".npm-global" / "bin",
              Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    for env in ("APPDATA", "LOCALAPPDATA"):
        if os.environ.get(env):
            places.append(Path(os.environ[env]) / "npm")
    names = ("claude.exe", "claude.cmd", "claude") if os.name == "nt" else ("claude",)
    return [place / name for place in places for name in names]


def find_claude():
    """The claude command: on PATH (on Windows an npm install is claude.CMD, which a bare name misses), else the
    first usual install place that holds it; None when there is none."""
    found = shutil.which("claude")
    if found:
        return found
    return next((str(path) for path in claude_candidates() if path.is_file()), None)


def agents_list(include_ended=False):
    """The parsed `claude agents --json` array (`--all` adds ended sessions); RuntimeError when it cannot be read."""
    source = os.environ.get(AGENTS_ENV)
    try:
        if source:
            text = Path(source).read_text(encoding="utf-8-sig")
        else:
            claude = find_claude()
            if not claude:
                raise RuntimeError("the claude command is not on PATH or in the usual install places")
            command = [claude, "agents", "--json"] + (["--all"] if include_ended else [])
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                    timeout=60)
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"exit code {result.returncode}")
            text = result.stdout
        data = json.loads(text)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise RuntimeError(str(exc))
    if not isinstance(data, list):
        raise RuntimeError("the session list is not an array")
    return [item for item in data if isinstance(item, dict)]


def run_git(cwd, *args):
    """stdout of a git command, or None when it fails."""
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def norm(path):
    return os.path.normcase(os.path.realpath(str(path)))


def worktree_roots(project):
    """Normalized roots of all worktrees of the project's repository."""
    out = run_git(project, "worktree", "list", "--porcelain") or ""
    roots = [norm(line[len("worktree "):]) for line in out.splitlines() if line.startswith("worktree ")]
    return roots or [norm(project)]


def inside(path, roots):
    path = norm(path)
    return any(path == root or path.startswith(root.rstrip(os.sep) + os.sep) for root in roots)


def message_text(entry):
    """The task text of a transcript entry written by the owner or sent by a peer session, else None."""
    if entry.get("type") != "user":
        return None
    origin = entry.get("origin") or {}
    if origin.get("kind") == "peer":
        return str(origin.get("body") or "").strip() or None
    if entry.get("isMeta") or origin.get("kind") not in (None, "human"):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content
                            if isinstance(part, dict) and part.get("type") == "text")
    if not isinstance(content, str):
        return None
    content = content.strip()
    if content.startswith("<"):  # a slash command keeps its arguments; caveats and reminders carry no task
        args = re.search(r"<command-args>(.*?)</command-args>", content, re.S)
        content = args.group(1).strip() if args else ""
    return content or None


def first_tasks(session_id):
    """Up to TASK_MESSAGES first owner or peer messages of the session, joined and cut to TASK_CHARS."""
    transcript = find_transcript(session_id) if session_id else None
    if transcript is None:
        return ""
    found = []
    try:
        with open(transcript, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if '"user"' not in line:
                    continue
                try:
                    text = message_text(json.loads(line))
                except ValueError:
                    continue
                if text:
                    found.append(" ".join(text.split()))
                    if len(found) >= TASK_MESSAGES:
                        break
    except OSError:
        return ""
    joined = " // ".join(found)
    return joined if len(joined) <= TASK_CHARS else joined[:TASK_CHARS] + "..."


def base_branch(cwd):
    for name in ("main", "master"):
        if run_git(cwd, "rev-parse", "--verify", "--quiet", name) is not None:
            return name
    return None


def changed_files(cwd):
    """(branch, files): the current branch and the files it changed against the base branch, plus uncommitted ones."""
    branch = (run_git(cwd, "branch", "--show-current") or "").strip()
    files = []
    base = base_branch(cwd)
    if base and branch and branch != base:
        files += (run_git(cwd, "diff", "--name-only", f"{base}...HEAD") or "").splitlines()
    for line in (run_git(cwd, "status", "--porcelain", "--untracked-files=all") or "").splitlines():
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        if path and not (Path(cwd) / path / ".git").exists():  # a nested worktree is not a change of this one
            files.append(path)
    return branch, sorted(set(files))


def cmd_others(args, path, records):
    try:
        agents = agents_list()
    except RuntimeError as exc:
        print(f"dev-kit-sessions: the session list could not be read: {exc}", file=sys.stderr)
        return 3
    me = args.self or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    roots = worktree_roots(args.project)
    registered = {str(record.get("id")) for record in records}
    rows = []
    for agent in agents:
        session_id = str(agent.get("sessionId") or "")
        name = str(agent.get("name") or "")
        cwd = agent.get("cwd")
        if not cwd or not inside(cwd, roots) or (me and session_id == me) or name.startswith(LEAD_PREFIX):
            continue
        branch, files = changed_files(cwd) if Path(cwd).is_dir() else ("", [])
        rows.append({"name": name, "sessionId": session_id, "kind": agent.get("kind"),
                     "status": agent.get("state") or agent.get("status"),
                     "startedBy": "lead" if session_id in registered else "owner", "cwd": cwd, "branch": branch,
                     "task": first_tasks(session_id), "files": files})
    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return 0
    for row in rows:
        files = row["files"]
        more = f" (+{len(files) - FILES_SHOWN} more)" if len(files) > FILES_SHOWN else ""
        print(f"{row['name'] or '(no name)'} | {row['kind']} {row['status']} | started by {row['startedBy']} | "
              f"branch {row['branch'] or '?'} | {row['cwd']}")
        print(f"  task: {row['task'] or '(no transcript)'}")
        print(f"  files: {', '.join(files[:FILES_SHOWN]) + more if files else 'none'}")
    if not rows:
        print("no other sessions")
    return 0


def matches(agent_id, wanted):
    """Whether a session id from the list is the wanted full id or starts with a short id of 8+ characters."""
    return agent_id == wanted or (len(wanted) >= 8 and agent_id.startswith(wanted))


def agent_entries(agents, wanted):
    """The entries of the session list for a registry id: its `id` or `sessionId` is the wanted id or starts with it."""
    return [agent for agent in agents
            if matches(str(agent.get("sessionId") or ""), wanted) or matches(str(agent.get("id") or ""), wanted)]


def assistant_text(entry):
    """The text parts of an assistant transcript entry joined, else ''."""
    message = entry.get("message") or {}
    if entry.get("isSidechain") or message.get("model") == "<synthetic>":
        return ""
    content = message.get("content")
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content
                            if isinstance(part, dict) and part.get("type") == "text")
    return content.strip() if isinstance(content, str) else ""


def last_reply(path):
    """(text, pending): the last assistant text message of a transcript, read from the end of the file, and whether
    an owner or peer message came after it (the session was asked again and has not answered yet). ('', pending)
    when the transcript has no assistant text."""
    size = path.stat().st_size
    window = CHUNK
    with open(path, "rb") as handle:
        while True:
            start = max(0, size - window)
            handle.seek(start)
            lines = handle.read(size - start).split(b"\n")
            if start > 0:
                lines = lines[1:]  # the first line may be cut; the next, larger read covers it whole
            pending = False
            for line in reversed(lines):
                if b'"assistant"' not in line and b'"user"' not in line:
                    continue
                try:
                    entry = json.loads(line.decode("utf-8"))
                except ValueError:  # includes UnicodeDecodeError
                    continue
                if not isinstance(entry, dict):
                    continue
                if entry.get("type") == "assistant":
                    text = assistant_text(entry)
                    if text:
                        return text, pending
                elif entry.get("type") == "user" and message_text(entry):
                    pending = True
            if start == 0:
                return "", pending
            window *= 4


def tail_entries(path):
    """The parsed assistant and user entries of a transcript, last first, read from the end of the file in growing
    windows (a window's first line may be cut; the next, larger read covers it whole)."""
    size = path.stat().st_size
    window, seen = CHUNK, 0
    with open(path, "rb") as handle:
        while True:
            start = max(0, size - window)
            handle.seek(start)
            lines = handle.read(size - start).split(b"\n")
            if start > 0:
                lines = lines[1:]
            entries = []
            for line in reversed(lines):
                if b'"assistant"' not in line and b'"user"' not in line:
                    continue
                try:
                    entry = json.loads(line.decode("utf-8"))
                except ValueError:  # includes UnicodeDecodeError
                    continue
                if isinstance(entry, dict) and entry.get("type") in ("assistant", "user"):
                    entries.append(entry)
            yield from entries[seen:]
            seen = len(entries)
            if start == 0:
                return
            window *= 4


def is_limit_notice(entry):
    """Whether a transcript entry is Claude Code's notice that the account hit its usage limit (5-hour or weekly):
    a synthetic assistant message with `apiError` usage_limit_reached (older: `error` rate_limit)."""
    return entry.get("type") == "assistant" and (entry.get("apiError") == "usage_limit_reached"
                                                 or (entry.get("isApiErrorMessage") and entry.get("error") == "rate_limit"))


def usage_limit(path):
    """(key, resets_at) when the session stopped on the usage limit: the last entry of its transcript that is not a
    side chain or a meta note is the limit notice (any later reply, tool result, owner or peer message means it went
    on). key tells one stop from the next (the notice's uuid or time); resets_at is epoch seconds or None. Else
    None. Claude Code keeps such a session's process and lists it as blocked, so the session list cannot tell."""
    try:
        for entry in tail_entries(path):
            if entry.get("isSidechain") or entry.get("isMeta"):
                continue
            if not is_limit_notice(entry):
                return None
            info = ((entry.get("apiErrorParams") or {}).get("rate_limit_info") or entry.get("quotaLimits") or {})
            resets = info.get("resetsAt") if isinstance(info, dict) else None
            key = str(entry.get("uuid") or entry.get("timestamp") or "")
            return key, resets if isinstance(resets, (int, float)) and not isinstance(resets, bool) else None
    except OSError:
        return None
    return None


def reset_text(resets_at):
    if not resets_at:
        return "unknown"
    if resets_at > 1e11:  # milliseconds
        resets_at /= 1000
    try:
        return datetime.fromtimestamp(resets_at).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return "unknown"


def is_marker_line(line):
    line = line.strip().strip("*_`#> «»\"'").rstrip(".,;:!?…»\"'*_` ")
    return line.casefold() in {marker.casefold() for marker in FINISHED_MARKERS}


def gist_of(text):
    """The reply as one line without marker lines, cut from the front to GIST_CHARS."""
    flat = " ".join(" ".join(line for line in text.splitlines() if not is_marker_line(line)).split())
    if not flat:
        return " ".join(text.split()) or "(no reply text)"
    return flat if len(flat) <= GIST_CHARS else "..." + flat[-(GIST_CHARS - 3):]


def is_owner(records, wanted):
    """Whether the registry record of this id (full or 8+ char prefix) is an owner session."""
    record = resolve(records, wanted)
    return record is not None and record.get("owner") is True



def session_state(agents, wanted, owner):
    """(state, gist) of a registry id: finished, gone, limited, working or waiting (see the module docstring). Only an owner
    session can be finished: a C reports through its own channel, so its reply lines never count."""
    entries = agent_entries(agents, wanted)
    session_id = next((str(agent["sessionId"]) for agent in entries if agent.get("sessionId")), wanted)
    transcript = find_transcript(session_id)
    try:
        text, pending = last_reply(transcript) if transcript else ("", False)
    except OSError:
        text, pending = "", False
    gist = gist_of(text) if text else "(no reply text)"
    if owner and text and not pending and any(is_marker_line(line) for line in text.splitlines()):
        return "finished", gist
    if not any(agent.get("pid") for agent in entries):
        return "gone", gist
    limit = usage_limit(transcript) if transcript else None
    if limit:
        return "limited", f"resets {reset_text(limit[1])}; {gist}"
    busy = any("busy" in (agent.get("status"), agent.get("state")) or agent.get("state") == "working"
               for agent in entries)
    return ("working" if busy else "waiting"), gist


def finished_sessions(watched, agents, records):
    """(name, id) of each watched (name, id) that is an owner session in the registry whose last reply says the work
    is finished."""
    return [(name or next((str(agent.get("name") or "") for agent in agent_entries(agents, wanted)), ""), wanted)
            for name, wanted in watched
            if is_owner(records, wanted) and session_state(agents, wanted, True)[0] == "finished"]


def cmd_state(args, path, records):
    try:
        agents = agents_list(include_ended=True)
    except RuntimeError as exc:
        print(f"dev-kit-sessions: the session list could not be read: {exc}", file=sys.stderr)
        return 3
    if args.id:
        wanted = [(record.get("name") if record else None, str(record["id"]) if record else given)
                  for given in args.id for record in [resolve(records, given)]]
    else:
        wanted = [(record.get("name"), str(record.get("id"))) for record in active(records)]
    for name, session_id in wanted:
        name = name or next((str(agent.get("name") or "") for agent in agent_entries(agents, session_id)), "")
        state, gist = session_state(agents, session_id, is_owner(records, session_id))
        print(f"{name or '(no name)'} | {session_id} | {state} | {gist}")
    if not wanted:
        print("no active sessions")
    return 0


def limited_sessions(watched, agents):
    """(name, id, key, resets_at) of each watched (name, id) that is live in the session list (has a pid) but whose
    transcript ends with the usage-limit notice (see usage_limit)."""
    found = []
    for name, wanted in watched:
        entries = agent_entries(agents, wanted)
        if not any(agent.get("pid") for agent in entries):
            continue
        session_id = next((str(agent["sessionId"]) for agent in entries if agent.get("sessionId")), wanted)
        transcript = find_transcript(session_id)
        limit = usage_limit(transcript) if transcript else None
        if limit:
            found.append((name or str(entries[0].get("name") or ""), wanted, *limit))
    return found


def new_limits(limited, path, watched_ids):
    """The limited items not reported yet, and remember them: LIMITS in the registry folder maps a session id to the
    key of the limit stop last reported, so a re-armed watcher does not report the same stop again. Watched ids no
    longer limited are dropped from it; entries of other ids (another watcher's `--id` sessions) are kept."""
    target = path.with_name(LIMITS)
    try:
        known = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        known = {}
    if not isinstance(known, dict):
        known = {}
    report = [item for item in limited if known.get(item[1]) != item[2]]
    current = {key: value for key, value in known.items() if key not in watched_ids}
    current.update({item[1]: item[2] for item in limited})
    if current != known:
        target.parent.mkdir(parents=True, exist_ok=True)
        save(target, current)
    return report


def cmd_limited(args, path, records):
    """One line per --id session whose transcript ends with the usage-limit notice: `<id> | <resets> | <key>`.
    Reads transcripts only, not the session list (the Pult watcher already has it)."""
    for wanted in args.id:
        transcript = find_transcript(wanted)
        limit = usage_limit(transcript) if transcript else None
        if limit:
            print(f"{wanted} | {reset_text(limit[1])} | {limit[0]}")
    return 0


def gone_sessions(watched, agents):
    """(name, id, state) of each watched (name, id) with no live entry in the session list."""
    gone = []
    for name, wanted in watched:
        entries = agent_entries(agents, wanted)
        if any(agent.get("pid") for agent in entries):
            continue
        state = next((agent.get("state") or agent.get("status") for agent in entries), None)
        gone.append((name or str(entries[0].get("name") or "") if entries else name, wanted,
                     state or "not in the session list"))
    return gone


def is_closed(agents, wanted):
    """Whether a watched session is in the list with no `pid`, whatever its state: Claude Code may have closed it
    (low memory, idle retire) and the state does not tell (done, stopped and blocked all occur)."""
    entries = agent_entries(agents, wanted)
    return bool(entries) and not any(agent.get("pid") for agent in entries)


def after_grace(gone, agents, closed_since, at):
    """The gone items to report now. A closed session (see is_closed) is held back until it has stayed without a
    pid for CLOSED_GRACE seconds: `closed_since` (wanted id -> when first seen closed, same clock as `at`) keeps
    that across rounds and forgets a session that is no longer closed."""
    report, closed = [], set()
    for item in gone:
        if is_closed(agents, item[1]):
            closed.add(item[1])
            if at - closed_since.setdefault(item[1], at) < CLOSED_GRACE:
                continue
        report.append(item)
    for wanted in set(closed_since) - closed:
        del closed_since[wanted]
    return report


def pid_alive(pid):
    """Whether a process with this pid exists. No psutil: ctypes on Windows (os.kill would end the process there),
    signal 0 elsewhere."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return kernel32.GetLastError() == 5  # access denied: it exists
        try:
            code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def read_lock(lock):
    """(pid, beat) of the watcher that holds the lock; None when there is no readable lock."""
    try:
        held = json.loads(lock.read_text(encoding="utf-8"))
        return held.get("pid"), float(held.get("beat", 0))
    except (OSError, ValueError, AttributeError, TypeError):
        return None


def take_lock(lock, interval):
    """Write this watcher's heartbeat. If another watcher holds the lock, wait: its pid as soon as its heartbeat
    moves (it lives), or take the lock once the heartbeat is stale (that watcher was killed). A holder whose pid
    is not a live process (killed, e.g. on low memory) loses the lock at once."""
    stale = max(3 * interval, 10)
    held = read_lock(lock)
    if held is not None and held[0] != os.getpid() and not pid_alive(held[0]):
        held = None
    if held is not None and held[0] != os.getpid():
        first_beat = held[1]
        while held is not None and time.time() - held[1] < stale:
            time.sleep(min(max(interval, 1), stale))
            held = read_lock(lock)
            if held is not None and held[1] != first_beat:
                return held[0]
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"pid": os.getpid(), "beat": time.time()}), encoding="utf-8")
    return None


def read_restart(path):
    """The open restart request (dict with a `version`) of the project, else None; an unreadable file counts as none."""
    try:
        data = json.loads(path.with_name(RESTART).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("version") else None


def cmd_restart(args, path, records):
    target = path.with_name(RESTART)
    request = read_restart(path)
    if args.restart_action == "request":
        if request is None or str(request["version"]) != args.version:
            save(target, {"version": args.version, "asked": time.time()})
        print(f"asked {args.version}")
    elif args.restart_action == "ready":
        if args.version and (request is None or str(request["version"]) != args.version):
            request = {"version": args.version}  # no request for this version: the lead noticed the bump itself
        elif request is None:
            print("dev-kit-sessions: no restart request is open", file=sys.stderr)
            return 1
        request["ready"] = time.time()
        save(target, request)
        print(f"restart ready: {request['version']}")
    elif args.restart_action == "status":
        if request is None:
            print("none")
        else:
            ready = request.get("ready")
            since = ready if ready else request.get("asked")
            age = int(max(0, time.time() - float(since))) if isinstance(since, (int, float)) else 0
            print(f"{'ready' if ready else 'asked'} {request['version']} {age}")
    else:
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        print("restart cleared")
    return 0


def cmd_watch(args, path, records):
    lock = None if args.id else path.with_name(WATCH_LOCK)
    deadline = time.monotonic() + args.max_minutes * 60
    failures = 0
    first = True
    closed_since = {}  # wanted id -> time.monotonic() when first seen closed
    watched = [(None, wanted) for wanted in args.id]
    try:
        while True:
            problem = None
            if lock is not None:
                holder = take_lock(lock, args.interval)
                if holder is not None:
                    lock = None  # not ours: leave it
                    print(f"already watching: pid {holder}")
                    return 6
                try:
                    records = load(path)
                    watched = [(record.get("name"), str(record.get("id"))) for record in active(records)]
                except Unreadable as exc:  # e.g. caught mid-replace on Windows; counted like a list failure
                    problem = exc
            request = read_restart(path)
            if request is not None and not request.get("ready") and not request.get("notified"):
                request["notified"] = time.time()  # once per request: the lead's re-armed watcher stays quiet
                save(path.with_name(RESTART), request)
                print(f"restart requested: {request['version']}")
                return 7
            if problem is None and not watched and first:
                print("nothing to watch")
                return 5
            first = False
            agents = None
            if problem is None and watched:
                try:
                    agents = agents_list(include_ended=True)
                except RuntimeError as exc:
                    problem = exc
            if problem is not None:
                failures += 1
                if failures >= WATCH_FAILURES:
                    print(f"dev-kit-sessions: the session list could not be read: {problem}", file=sys.stderr)
                    return 3
            else:
                failures = 0
            finished = finished_sessions(watched, agents, records) if agents is not None else []
            done = {wanted for _, wanted in finished}
            gone = [item for item in gone_sessions(watched, agents) if item[1] not in done] if agents is not None else []
            limited = []
            if agents is not None:
                gone = after_grace(gone, agents, closed_since, time.monotonic())
                ended = done | {item[1] for item in gone}
                limited = new_limits([item for item in limited_sessions(watched, agents) if item[1] not in ended],
                                     path, {wanted for _, wanted in watched})
            if gone or finished or limited:
                for name, wanted, state in gone:
                    print(f"gone: {name or '(no name)'} | {wanted} | {state}")
                for name, wanted in finished:
                    print(f"finished: {name or '(no name)'} | {wanted}")
                for name, wanted, _key, resets in limited:
                    print(f"limited: {name or '(no name)'} | {wanted} | resets {reset_text(resets)}")
                return 0
            if time.monotonic() + args.interval > deadline:
                if not watched:
                    print("nothing to watch")
                    return 5
                print(f"time limit: {args.max_minutes:g} min, all alive")
                return 4
            time.sleep(args.interval)
    finally:
        if lock is not None:
            try:
                lock.unlink()
            except OSError:
                pass


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
    add.add_argument("--owner", action="store_true", help="a session the owner started and the lead took over")
    end = sub.add_parser("end")
    end.add_argument("--id", required=True)
    end.add_argument("--status", choices=["done", "replaced", "stopped"], default="done")
    sub.add_parser("list")
    fill = sub.add_parser("fill")
    fill.add_argument("--limit", type=float, default=0.5)
    fill.add_argument("--window", type=int, default=0)
    others = sub.add_parser("others")
    others.add_argument("--self", default="", help="the caller's session id (default: env CLAUDE_CODE_SESSION_ID)")
    others.add_argument("--json", action="store_true")
    state = sub.add_parser("state")
    state.add_argument("--id", action="append", default=[], help="a session to show (repeatable; default: the registry)")
    watch = sub.add_parser("watch")
    watch.add_argument("--id", action="append", default=[], help="a session to watch (repeatable; default: the registry)")
    watch.add_argument("--interval", type=float, default=60, help="seconds between reads of the session list")
    watch.add_argument("--max-minutes", type=float, default=120, help="exit with the time-limit line after this")
    limited = sub.add_parser("limited", help="which sessions stopped on the usage limit (transcripts only)")
    limited.add_argument("--id", action="append", default=[], help="a full session id (repeatable)")
    restart = sub.add_parser("restart", help="the restart request the Pult watcher leaves for a lead")
    restart_sub = restart.add_subparsers(dest="restart_action", required=True)
    restart_sub.add_parser("request").add_argument("--version", required=True)
    restart_sub.add_parser("ready").add_argument("--version", help="mark ready even with no open request")
    for action in ("status", "clear"):
        restart_sub.add_parser(action)
    args = parser.parse_args(argv)
    for key in ("id", "parent", "predecessor", "self", "name", "worktree", "task"):  # ids pasted with a CR or spaces
        value = getattr(args, key, None)
        if isinstance(value, str):
            setattr(args, key, value.strip())
        elif isinstance(value, list):
            setattr(args, key, [item.strip() for item in value])
    try:
        path = registry_path(args.project, create=args.action != "limited")  # limited reads no project state
        records = [] if args.action in ("restart", "limited") else load(path)  # the handshake works with a broken registry too
        return {"add": cmd_add, "end": cmd_end, "list": cmd_list, "fill": cmd_fill, "restart": cmd_restart,
                "others": cmd_others, "state": cmd_state, "watch": cmd_watch,
                "limited": cmd_limited}[args.action](args, path, records)
    except Unreadable as exc:
        print(f"dev-kit-sessions: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
