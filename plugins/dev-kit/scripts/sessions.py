"""Keep the registry of the background task sessions (C) that a project lead session (P) started, and show how
full their context is.

    dev-kit-sessions add --id <id> --name <name> --worktree <path> --task <file or text> [--parent <id>] [--predecessor <id>] [--owner]
    dev-kit-sessions end --id <id or 8+ char short id> [--status done|replaced|stopped]
    dev-kit-sessions list
    dev-kit-sessions fill [--limit 0.33] [--window N] [--over-only]
    dev-kit-sessions others [--self <id>] [--json]
    dev-kit-sessions state [--id <id> ...]
    dev-kit-sessions answers [--id <id> ...]
    dev-kit-sessions watch [--id <id> ...] [--interval 60] [--max-minutes 120] [--stale-minutes 20]
    dev-kit-sessions check [--id <id> ...] [--stale-minutes 20] [--fill-limit 0.33]
    dev-kit-sessions mark --kind gone|finished|limited|stale|fill|restart|handoff [--id <id>] --key <key>
    dev-kit-sessions size --id <id> [--id <id> ...] [--wakes <state file>]
    dev-kit-sessions limited --id <id> [--id <id> ...]
    dev-kit-sessions restart request --version <V> | ready [--version <V>] | status | clear
    dev-kit-sessions handoff save --file <name.md> [--go] | go | request | status | clear
    dev-kit-sessions fill --self [<id>] [--limit 0.33] [--window N] [--over-only]
    dev-kit-sessions release --from <V|older> --to <V> [--started <ISO time>] [--file <releases.json>]
    dev-kit-sessions quiet --id <session id> [--minutes 5]

The registry is `sessions.json` in the project state folder (see dev_kit_state.py; the same folder for all worktrees
of one repository). Ids (`--id`, `--parent`, `--predecessor`, `--self`) and the registry's ids are trimmed of spaces and
line ends (plugins/dev-kit/claude-facts.md, "`claude --bg` prints only a short id"). `add --predecessor` marks the replaced session `replaced`. `add --owner` marks a session the
owner started and the lead took over (the record gets `"owner": true`; the UserPromptSubmit hook
hooks/owner-session-note.py reads it). A session's transcript, wherever one is read by id: the `linkScanPath`
file of its background job (`<jobs>/*/state.json` whose `sessionId` or `resumeSessionId` is the id; jobs folder = env
DEV_KIT_JOBS_DIR, else ~/.claude/jobs; the newest such file when several jobs match) when that file exists, since a
`/clear` keeps the job and its `sessionId` but writes a new transcript file (plugins/dev-kit/claude-facts.md, "A resume
with `/clear` as its prompt clears the context and keeps the job and the Remote Control link"); else the newest
`<projects>/*/<id>.jsonl` (projects folder = env DEV_KIT_PROJECTS_DIR, else ~/.claude/projects). So the job's first
id and the new transcript's own id (the one `claude agents` shows as the sessionId after a /clear) both lead to the
live file. `fill` finds the transcript of every active record and
prints its context size: input + cache creation + cache read tokens of the last assistant message that has usage.
The window comes from the transcript's model (see `window_for`) unless `--window` is given. A line ends with OVER when the
percent reaches the limit. `--over-only` prints only the OVER rows (nothing else, not even "no active sessions"). Lines
of a side chain (`"isSidechain": true`, a subagent's) are not counted as the session's context.

`others` lists the live sessions of this repository (any worktree) other than the caller, for the overlap check
before a task starts. Source: `claude agents --json` (background sessions and running interactive ones, the desktop
Code tab included; env DEV_KIT_AGENTS_JSON names a file to read instead). The claude command is taken from PATH, else
from the usual install places (see `claude_candidates`), since a subagent's shell may lack the npm folder. The caller is `--self`, else env
CLAUDE_CODE_SESSION_ID. Lead sessions (name starts with `P: `) and the hook-started retro and docs sessions
(`Ретро: `, `Документація: `) are left out: no owner started them and P merges their work. For each: name,
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
time, or `resets unknown;`): the session list cannot tell it (plugins/dev-kit/claude-facts.md, "Other sessions
listed as `blocked` or `done` in `claude agents --json`");
`working` when the status is busy; else `waiting`. Exit 3 when the list cannot be read.

`answers` shows, per active registry record (or per `--id`, as in `state`), what the owner wrote in that session
since its last question or report to a peer: the owner's own messages (peer messages left out) after the session's
last SendMessage call, oldest first, each cut to ANSWER_CHARS, then the gist of the session's last text after them.
Head line: `name | id | after report <YYYY-MM-DD HH:MM> | N owner messages` (local time); a session that never
called SendMessage (an owner session taken over) shows its last ANSWER_FALLBACK owner messages instead. The lead
reads it before it asks the owner about a session or writes its status, so it never asks what the owner already
answered there. Exit 3 when the list cannot be read.

`watch` waits in silence while the watched sessions live and exits with one line when one is gone, finished (the
last reply has the finished marker, see `state`), limited (stopped on the usage limit, see `state`) or stale (waiting
`--stale-minutes` since its last reply), so a caller that
runs it in the background wakes only then. Watched: the `--id` sessions (full or 8+ char short ids), else the
registry's active records, read again each round (a C added later is watched too; one ended with `end` is not).
Every `--interval` seconds it reads `claude agents --json --all`: a session is live while an entry with its id has a
`pid`; one with no `pid` is not live. A session not in the list is gone at once. An entry in the list with no
`pid`, whatever its state (done, stopped and blocked all occur: plugins/dev-kit/claude-facts.md, "Claude closes an
idle background session after 8 h of waiting, 1 h without Remote Control" and "A low-memory spell closes idle background sessions"), is reported gone only after it stayed without a `pid` for CLOSED_GRACE seconds (300, counted by the
watcher across rounds; a `pid` again clears it), so the Pult watcher can bring it back with `claude respawn`
first. Lines and exit codes:
`gone: <name> | <id> | <state or 'not in the session list'>` (one per gone session) and
`finished: <name> | <id>` (one per finished session, also one that is gone) and `limited: <name> | <id> | resets
<time or unknown>` (one per live session that stopped on the usage limit, see `state`; each stop is reported once:
LIMITS in the state folder keeps the stop already reported, so the re-armed watcher stays quiet until the session
goes on and stops again) and `stale: <name> | <id> | waiting <N> min` (one per live session in `waiting` whose last
assistant entry, see `wait_started`, is at least `--stale-minutes` old, default 20; each wait is reported once:
STALE in the state folder keeps the wait start already reported, so the re-armed watcher stays quiet until the
session answers again and a new wait passes the threshold; the lead decides whether the wait is on the owner and
pushes a reminder, since the cache of a waiting session runs out: plugins/dev-kit/claude-facts.md, "A main session's prompt cache lives about one hour") exit 0; `time limit: <N> min,
all alive` exit 4 (re-arm it); `nothing to watch` exit 5 (on the first round, or at the time limit when the registry
has emptied meanwhile: a watcher whose last C ended keeps quiet); `already watching: pid <N>` exit 6 (in registry
mode one watcher per project runs: a lock file in the state folder with a heartbeat; a new watcher waits until the
heartbeat moves, then exits 6, or until it is stale after 3 intervals, then takes the lock of the killed watcher;
a lock whose pid is not a live process is taken at once);
the registry or the session list unreadable WATCH_FAILURES rounds in a row: exit 3; `restart requested: <V>` exit 7
(each round, before the other checks and also on the first round with nothing to watch, only once per request:
`restart.json` holds an open request that is neither ready nor notified yet; the exit sets `"notified"`, so the
re-armed watcher stays quiet, see the next paragraph).

`check` is one round of `watch` for the Pult watcher (no lead keeps a watcher any more): it reads the session list
once and prints one line per event not delivered yet, `<kind> | <name> | <id> | <detail> | <key>`, nothing when there is
none; exit 0, exit 3 when the session list cannot be read, no lock. Watched: the `--id` sessions, else the registry's
active records. Kinds (detection is the same code as `watch`): `gone` (detail = state; key = the timestamp of the
last transcript entry, or `none`, so a session that came back and went again reports again; the CLOSED_GRACE of a
closed session works across calls: `check-closed.json` next to the registry keeps the epoch each closed session was
first seen, the one file `check` writes; a call with `--id` keeps the clocks of the other ids); `finished` (owner
sessions; key = timestamp of the last assistant reply); `limited` (detail `resets <time or unknown>`; key = the limit
key; delivered when LIMITS holds it); `stale` (detail `waiting <N> min`; key = wait start; delivered when STALE holds
it); `fill` (an active registry record that is not an owner session and whose context reaches `--fill-limit` of its
window; detail like `65% of 1000000`; key `fill`, so once per id); `restart` (an open, not ready, not notified
request of `restart.json`: `restart | - | - | <version> | <version>`); `handoff` (a saved handoff that was asked for
with `handoff request`, is not `go` and not notified: `handoff | - | - | <file> | <file>`). `check` never writes LIMITS,
STALE, the delivered marks, the restart file or the handoff file. `mark --kind K [--id X] --key KEY` records the
delivery after the caller got the message: limited writes LIMITS and stale writes STALE (the same files `watch` keeps),
restart sets `notified` on the open request when its version is KEY (else prints `not marked restart - ...`, exit 0),
handoff sets `notified` on the saved handoff when its file is KEY (else `not marked handoff - ...`, exit 0), gone,
finished and fill write `delivered.json` next to the registry (`{id: {kind: key}}`; ids of ended records are dropped);
it prints `marked <kind> <id>` (`marked restart -`, `marked handoff -`). `check` leaves out what is marked.

`size --id <full session id> ...` prints `<id> | <tokens> | <window> | <model>` for each id that has a transcript (the
tokens as `fill`; 0 and the default window when it has no usage), no registry and no session list. With `--wakes
<state file>` (json id -> byte offset in the transcript) it reads each transcript from the stored offset and appends
` | owner=N peer=N notify=N | units=U`: the turn starts since (owner: a user entry with text and no `origin`, or a
human one; peer: `origin.kind` peer; notify: any other user entry with text, a task notification or a meta note) and the
units (`retro.units_of`, each message id once) of the new assistant entries; the offsets are saved to the file, and the
first call for an id stores the end and counts nothing.

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

`fill --self [<id>]` reports the caller's own context instead of the registry rows (the id defaults to env
CLAUDE_CODE_SESSION_ID; none: stderr, exit 1; the registry is not read): `self | <id> | N tokens | window W | P%` (with
OVER at the limit) or `self | <id> | no transcript`; `--over-only` prints only the OVER line.

`handoff` is the file handshake for a full lead (the Pult watcher moves it to a fresh context that loads the
handoff file; works with an unreadable registry). `handoff.json` next to the registry holds `{"file": NAME, "saved":
<epoch>, "go": bool, "go_at": <epoch>, "asked": <epoch>, "notified": <epoch>}`; the last three keys are optional.
`save --file NAME [--go]` writes it (NAME is a bare file name ending in .md of letters, digits, dot, underscore,
hyphen, starting with a letter or digit, else exit 1; `--go` sets `go_at` to now; a re-save keeps `go`, `go_at`,
`asked` and `notified`: the request is about the move, not the file); `go` sets `go` and `go_at` to now (the lead
wrote its 30-second warning just before; exit 1 when nothing is saved); `request` (the watcher, for a lead that is not
quiet) sets `asked` and prints `handoff asked: NAME`, or `handoff already asked: NAME` when it was set before (exit 1
when nothing is saved); `status` prints `none`, `saved NAME <seconds>` (since the save) or `go NAME <seconds>` (since
`go_at`, else since the save); `clear` removes the file (fine when absent).

`release` tells the Pult watcher whether a lead that runs an older dev-kit must restart the same day. The release
marks are `releases.json` in the dev-kit plugin folder (`--file` for another): a JSON object, version -> `{"kind":
"critical"|"routine", "date": "YYYY-MM-DD" (local date of the release), "reason": one line}`; the agent that bumps the
version adds its entry in the same commit. It prints `critical <version>: <reason>` for the newest critical entry
with `--from` < version <= `--to` (versions compared as dotted numbers), else `routine`. `--from older` (or any
`--from` that is not a version: the watcher does not know the version the process started on) counts a critical
entry with version <= `--to` whose date is on or after the local date of `--started` (the process start, ISO time);
with no `--started` as well nothing is known about the start, so it prints `routine`. A missing file counts as routine;
a file or an entry that is not as above counts as routine with a one-line warning on stderr (an entry: that entry
only). Exit 0 always.

`quiet --id <session id>` tells whether a lead's chat is quiet enough for a silent restart (transcript only, no
registry, no session list). It prints `active no transcript` when the session has none; `active owner <N>s ago` when
the owner's own last message (a user entry with text, no `origin` or a human one, not a meta note, side chain, tool
result or peer message) is less than `--minutes` old (default QUIET_MINUTES); `active open question` when the
session's last main-chain assistant text came after the owner's last message and asks a question: its last non-empty
line, with trailing emphasis marks and spaces removed, ends with `?` or with `?` and one bracketed part (the
example of the owner's question form); trailing recommendation lines (RECOMMENDATION_LINE: `Рекомендую:`,
`Recommend:`, `немає рекомендації`, `no recommendation`, list marks allowed) are skipped first, since a question
always ends with one; else `quiet`. At most ANSWER_ENTRIES entries are read back from the end. Exit 0.

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
HANDOFF = "handoff.json"
HANDOFF_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\.md")  # a bare file name: the watcher puts it on a command line
PROJECTS_ENV = "DEV_KIT_PROJECTS_DIR"
JOBS_ENV = "DEV_KIT_JOBS_DIR"
DEFAULT_WINDOW = 200000
NATIVE_1M_WINDOW = 1000000
USAGE_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
CHUNK = 256 * 1024
AGENTS_ENV = "DEV_KIT_AGENTS_JSON"
LEAD_PREFIX = "P: "
RETRO_PREFIX = "Ретро: "  # a background retro session the dev-kit SessionStart hook starts (dev-kit:retro)
DOCS_PREFIX = "Документація: "  # the weekly docs session the same hook starts (dev-kit:maintain-project-docs)
TASK_MESSAGES = 2
TASK_CHARS = 700
FILES_SHOWN = 40
WATCH_LOCK = "watch.lock"
WATCH_FAILURES = 5
ID_KEYS = ("id", "parent", "predecessor")
LIMITS = "limits.json"
STALE = "stale.json"
STALE_KEEP_DAYS = 7
CLOSED = "check-closed.json"  # id -> epoch when `check` first saw the session closed (the grace spans calls)
DELIVERED = "delivered.json"  # id -> {kind: key} of the gone, finished and fill events already delivered
FILL_LIMIT = 0.33  # a third of the window: past it a long session costs more than a fresh one (owner, 2026-11-23)
MARK_KINDS = ("gone", "finished", "limited", "stale", "fill", "restart", "handoff")
CLOSED_GRACE = 300  # seconds a session with no pid stays unreported: the Pult watcher may bring it back meanwhile
# A reply line (trimmed, emphasis marks and trailing punctuation removed, case ignored) that says the session is done.
FINISHED_MARKERS = ("Роботу завершено", "Work finished")
GIST_CHARS = 120
ANSWER_CHARS = 400  # an owner message in `answers` is cut to this
ANSWER_FALLBACK = 3  # owner messages `answers` shows for a session that never sent a SendMessage
ANSWER_SCAN = 50  # owner messages read back while looking for that SendMessage
ANSWER_ENTRIES = 2000  # transcript entries read back at most (a long C transcript is not read whole)
SUBAGENT_ID = re.compile(r"^a?[0-9a-f]{16,}$")  # a SendMessage `to` that names a subagent, not a session
RELEASES = Path(__file__).resolve().parents[1] / "releases.json"  # the dev-kit release marks (see `release`)
RELEASE_KINDS = ("critical", "routine")
QUIET_MINUTES = 5  # the owner wrote to the lead less than this ago: not quiet (owner's rule, 2026-11-23)
# A line that follows the owner's question in the reply format (the question's recommendation), list marks allowed.
RECOMMENDATION_LINE = re.compile(r"^[-*>\s]*[*_]*(Рекомендую|Recommend|немає рекомендації|no recommendation)\b",
                                 re.I)
QUESTION_END = re.compile(r"\?\s*(\([^()]*\))?$")  # `?`, or `?` and the bracketed example of the question form

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
    for record in data:  # trim ids (plugins/dev-kit/claude-facts.md, "`claude --bg` prints only a short id")
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


def jobs_dir():
    return Path(os.environ[JOBS_ENV]) if os.environ.get(JOBS_ENV) else Path.home() / ".claude" / "jobs"


def job_transcript(session_id):
    """The live transcript (`linkScanPath`) of the background job whose sessionId or resumeSessionId is session_id,
    the newest when several match; None when no such job has an existing file."""
    best = None
    for state in jobs_dir().glob("*/state.json"):
        try:
            text = state.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        if session_id not in text:  # most jobs are someone else's: skip the parse
            continue
        try:
            data = json.loads(text)
        except ValueError:
            continue
        if not isinstance(data, dict) or session_id not in (data.get("sessionId"), data.get("resumeSessionId")):
            continue
        link = data.get("linkScanPath")
        if not isinstance(link, str) or not link:
            continue
        try:
            mtime = Path(link).stat().st_mtime
        except OSError:
            continue
        if best is None or mtime > best[0]:
            best = (mtime, Path(link))
    return best[1] if best else None


def find_transcript(session_id):
    """The live transcript of a session id (see the module doc): its job's linkScanPath, else <projects>/*/<id>.jsonl."""
    if not session_id:
        return None
    live = job_transcript(session_id)
    if live is not None:
        return live
    found = sorted(projects_dir().glob(f"*/{session_id}.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return found[0] if found else None


def last_usage(path):
    """(tokens, model) of the last assistant message with non-zero usage, reading the file from the end; None if
    none. Messages whose usage sums to 0 (synthetic or interrupted) and side-chain messages (a subagent's, with its
    own small context) are skipped."""
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
                    entry = json.loads(line.decode("utf-8"))
                except ValueError:  # includes UnicodeDecodeError
                    continue
                if not isinstance(entry, dict) or entry.get("isSidechain"):
                    continue
                message = entry.get("message") or {}
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

    The windows by model: plugins/dev-kit/claude-facts.md, "Context window by model".
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


def cmd_fill_self(args):
    own = args.self or os.environ.get("CLAUDE_CODE_SESSION_ID") or ""
    if not own:
        print("dev-kit-sessions: no session id: pass --self <id> or set CLAUDE_CODE_SESSION_ID", file=sys.stderr)
        return 1
    transcript = find_transcript(own)
    usage = last_usage(transcript) if transcript else None
    if usage is None:
        if not args.over_only:
            print(f"self | {own} | no transcript")
        return 0
    tokens, model = usage
    window = args.window or window_for(model)
    percent = tokens / window
    flag = " OVER" if percent >= args.limit else ""
    if flag or not args.over_only:
        print(f"self | {own} | {tokens} tokens | window {window} | {percent:.0%}{flag}")
    return 0


def cmd_fill(args, path, records):
    if args.self is not None:
        return cmd_fill_self(args)
    rows = active(records)
    for record in rows:
        transcript = find_transcript(record["id"])
        usage = last_usage(transcript) if transcript else None
        if usage is None:
            if not args.over_only:
                print(f"{record['name']} | {record['id']} | no transcript")
            continue
        tokens, model = usage
        window = args.window or window_for(model)
        percent = tokens / window
        flag = " OVER" if percent >= args.limit else ""
        if args.over_only and not flag:
            continue
        print(f"{record['name']} | {record['id']} | {tokens} tokens | window {window} | {percent:.0%}{flag}")
    if not rows and not args.over_only:
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
        skipped = name.startswith((LEAD_PREFIX, RETRO_PREFIX, DOCS_PREFIX))
        if not cwd or not inside(cwd, roots) or (me and session_id == me) or skipped:
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
    None. The session list cannot tell it (plugins/dev-kit/claude-facts.md, "Other sessions listed as `blocked` or
    `done` in `claude agents --json`")."""
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


def sent_report(entry):
    """Whether an assistant transcript entry calls the SendMessage tool to a peer session (the session's question or
    report). A message to its own subagent (`to` is an agent id such as `a` + 16 hex digits) does not count."""
    content = (entry.get("message") or {}).get("content")
    return (entry.get("type") == "assistant" and not entry.get("isSidechain") and isinstance(content, list)
            and any(isinstance(part, dict) and part.get("type") == "tool_use" and part.get("name") == "SendMessage"
                    and not SUBAGENT_ID.match(str((part.get("input") or {}).get("to") or "").strip())
                    for part in content))


def clock(value):
    """Local `YYYY-MM-DD HH:MM` of a transcript timestamp, else '?'."""
    epoch = parse_time(value)
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d %H:%M") if epoch is not None else "?"


def owner_after_report(path):
    """(report_time, owner, reply) of a transcript: report_time is the timestamp of the session's last SendMessage
    call (None when it sent none); owner lists (timestamp, text) of the owner's own messages after it, oldest first
    (peer messages, the lead's own included, are left out; with no SendMessage, the last ANSWER_FALLBACK; at most
    ANSWER_ENTRIES entries are read back); reply is
    the session's last assistant text after the owner's last message, '' when none."""
    owner, reply, report_time = [], "", None
    for scanned, entry in enumerate(tail_entries(path)):
        if scanned >= ANSWER_ENTRIES:
            break
        if entry.get("isSidechain"):
            continue
        if sent_report(entry):
            report_time = entry.get("timestamp")
            break
        if entry.get("type") == "assistant":
            if not owner and not reply:
                reply = assistant_text(entry)
        elif (entry.get("origin") or {}).get("kind") != "peer":
            text = message_text(entry)
            if text:
                owner.append((entry.get("timestamp"), text))
                if report_time is None and len(owner) >= ANSWER_SCAN:
                    break
    if report_time is None:
        owner = owner[:ANSWER_FALLBACK]
    return report_time, owner[::-1], reply


def cmd_answers(args, path, records):
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
        transcript = transcript_of(agents, session_id)
        try:
            report_time, owner, reply = owner_after_report(transcript) if transcript else (None, [], "")
        except OSError:
            report_time, owner, reply = None, [], ""
        since = f"after report {clock(report_time)}" if report_time else f"last {ANSWER_FALLBACK}, no report sent"
        count = f"{len(owner)} owner message{'s' if len(owner) != 1 else ''}" if owner else "no owner message"
        print(f"{name or '(no name)'} | {session_id} | {since} | {count}")
        for stamp, text in owner:
            flat = " ".join(text.split())
            print(f"  {clock(stamp)} owner: {flat if len(flat) <= ANSWER_CHARS else flat[:ANSWER_CHARS] + '...'}")
        if owner and reply:
            print(f"  session after it: {gist_of(reply)}")
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


def read_map(target):
    """The JSON object in a state file (LIMITS, STALE, ...), {} when the file is absent or not an object."""
    try:
        known = json.loads(target.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return known if isinstance(known, dict) else {}


def write_map(target, data):
    target.parent.mkdir(parents=True, exist_ok=True)
    save(target, data)


def new_limits(limited, path, watched_ids):
    """The limited items not reported yet, and remember them: LIMITS in the registry folder maps a session id to the
    key of the limit stop last reported, so a re-armed watcher does not report the same stop again. Watched ids no
    longer limited are dropped from it; entries of other ids (another watcher's `--id` sessions) are kept."""
    target = path.with_name(LIMITS)
    known = read_map(target)
    report = [item for item in limited if known.get(item[1]) != item[2]]
    current = {key: value for key, value in known.items() if key not in watched_ids}
    current.update({item[1]: item[2] for item in limited})
    if current != known:
        target.parent.mkdir(parents=True, exist_ok=True)
        save(target, current)
    return report


def parse_time(value):
    """Epoch seconds of a transcript `timestamp` (ISO 8601, `Z` allowed), else None."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def wait_started(path):
    """(key, epoch) of the start of a session's current wait: the timestamp of the last assistant entry of its
    transcript (side chains, meta notes and limit notices skipped). None when an owner or peer message came after it
    (the session was asked again), when there is no such entry or its time is unreadable."""
    try:
        for entry in tail_entries(path):
            if entry.get("isSidechain") or entry.get("isMeta"):
                continue
            if entry.get("type") == "user":
                if message_text(entry):
                    return None
                continue  # a tool result: the turn goes on
            if is_limit_notice(entry):
                continue
            at = parse_time(entry.get("timestamp"))
            return (entry["timestamp"], at) if at is not None else None
    except OSError:
        return None
    return None


def stale_sessions(watched, agents, minutes, at):
    """(name, id, key, waited minutes) of each watched (name, id) that is live, not busy, not stopped on the usage
    limit and whose wait (see wait_started) began at least `minutes` before `at` (epoch seconds)."""
    found = []
    for name, wanted in watched:
        entries = agent_entries(agents, wanted)
        if not any(agent.get("pid") for agent in entries):
            continue
        if any("busy" in (agent.get("status"), agent.get("state")) or agent.get("state") == "working"
               for agent in entries):
            continue
        session_id = next((str(agent["sessionId"]) for agent in entries if agent.get("sessionId")), wanted)
        transcript = find_transcript(session_id)
        if not transcript or usage_limit(transcript):
            continue
        start = wait_started(transcript)
        if start and at - start[1] >= minutes * 60:
            found.append((name or str(entries[0].get("name") or ""), wanted, start[0], int((at - start[1]) // 60)))
    return found


def prune_stale(known):
    """The STALE map without the entries whose wait started over STALE_KEEP_DAYS ago."""
    cutoff = time.time() - STALE_KEEP_DAYS * 86400
    return {key: value for key, value in known.items() if (parse_time(value) or 0) >= cutoff}


def new_stale(stale, path):
    """The stale items not reported yet, and remember them: STALE in the registry folder maps a session id to the
    start of the wait last reported, so a re-armed or restarted watcher does not report the same wait again. An entry
    stays while its session is not stale (a round with no pid or a busy flicker must not let the same wait fire
    twice; a new wait has a new key anyway) and is dropped once its wait started over STALE_KEEP_DAYS ago."""
    target = path.with_name(STALE)
    known = read_map(target)
    report = [item for item in stale if known.get(item[1]) != item[2]]
    current = prune_stale(known)
    current.update({item[1]: item[2] for item in stale})
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


def read_handoff(path):
    """The saved handoff (dict with a valid `file`) of the project, else None; an unreadable file counts as none."""
    try:
        data = json.loads(path.with_name(HANDOFF).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    if isinstance(data, dict) and isinstance(data.get("file"), str) and HANDOFF_NAME.fullmatch(data["file"]):
        return data
    return None


def cmd_handoff(args, path, records):
    target = path.with_name(HANDOFF)
    saved = read_handoff(path)
    if args.handoff_action == "save":
        if not HANDOFF_NAME.fullmatch(args.file):
            print(f"dev-kit-sessions: {args.file!r} is not a bare file name like handoff-1.md", file=sys.stderr)
            return 1
        data = {"file": args.file, "saved": time.time(), "go": bool(args.go or (saved and saved.get("go")))}
        for key in ("go_at", "asked", "notified"):  # the move's marks outlive a new file name
            if saved and saved.get(key) is not None:
                data[key] = saved[key]
        if args.go and not (saved and saved.get("go")):
            data["go_at"] = data["saved"]
        save(target, data)
        print(f"handoff saved: {args.file}")
    elif args.handoff_action in ("go", "request"):
        if saved is None:
            print("dev-kit-sessions: no handoff is saved", file=sys.stderr)
            return 1
        if args.handoff_action == "go":
            saved["go"] = True
            saved["go_at"] = time.time()
            save(target, saved)
            print(f"handoff go: {saved['file']}")
        elif saved.get("asked"):
            print(f"handoff already asked: {saved['file']}")
        else:
            saved["asked"] = time.time()
            save(target, saved)
            print(f"handoff asked: {saved['file']}")
    elif args.handoff_action == "status":
        if saved is None:
            print("none")
        else:
            go = bool(saved.get("go"))
            since = saved.get("go_at") if go and isinstance(saved.get("go_at"), (int, float)) else saved.get("saved")
            age = int(max(0, time.time() - float(since))) if isinstance(since, (int, float)) else 0
            print(f"{'go' if go else 'saved'} {saved['file']} {age}")
    else:
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        print("handoff cleared")
    return 0


def transcript_of(agents, wanted):
    """The transcript path of a registry id: by the sessionId of its list entry, else by the id itself."""
    entries = agent_entries(agents, wanted)
    return find_transcript(next((str(agent["sessionId"]) for agent in entries if agent.get("sessionId")), wanted))


def last_timestamp(path):
    """The `timestamp` of the last transcript entry that has one (any entry type), read from the end of the file;
    None when there is none or the file cannot be read."""
    try:
        size = path.stat().st_size
        window = CHUNK
        with open(path, "rb") as handle:
            while True:
                start = max(0, size - window)
                handle.seek(start)
                lines = handle.read(size - start).split(b"\n")
                if start > 0:
                    lines = lines[1:]
                for line in reversed(lines):
                    if b'"timestamp"' not in line:
                        continue
                    try:
                        entry = json.loads(line.decode("utf-8"))
                    except ValueError:
                        continue
                    if isinstance(entry, dict) and isinstance(entry.get("timestamp"), str):
                        return entry["timestamp"]
                if start == 0:
                    return None
                window *= 4
    except OSError:
        return None


def last_reply_timestamp(path):
    """The `timestamp` of the last assistant text message of a transcript (see last_reply), else None."""
    try:
        for entry in tail_entries(path):
            if entry.get("type") == "assistant" and assistant_text(entry):
                stamp = entry.get("timestamp")
                return stamp if isinstance(stamp, str) else None
    except OSError:
        return None
    return None


def event_line(kind, name, wanted, detail, key):
    return f"{kind} | {name or '(no name)'} | {wanted} | {detail} | {key}"


def cmd_check(args, path, records):
    """One round of `watch` with no side effects but the closed-session clock: one line per event not delivered yet
    (see `mark`): `<kind> | <name> | <id> | <detail> | <key>`."""
    at = time.time()
    if args.id:
        found = [(resolve(records, given), given) for given in args.id]
        watched = [(record.get("name"), str(record["id"])) if record else (None, given) for record, given in found]
    else:
        watched = [(record.get("name"), str(record.get("id"))) for record in active(records)]
    watched_ids = {wanted for _, wanted in watched}
    agents = []
    if watched:
        try:
            agents = agents_list(include_ended=True)
        except RuntimeError as exc:
            print(f"dev-kit-sessions: the session list could not be read: {exc}", file=sys.stderr)
            return 3
    delivered = read_map(path.with_name(DELIVERED))
    limits, waits = read_map(path.with_name(LIMITS)), read_map(path.with_name(STALE))

    def fresh(kind, wanted, key):
        marks = delivered.get(wanted)
        return not (isinstance(marks, dict) and marks.get(kind) == key)

    lines = []
    request = read_restart(path)
    if request is not None and not request.get("ready") and not request.get("notified"):
        lines.append(f"restart | - | - | {request['version']} | {request['version']}")
    handoff = read_handoff(path)
    if handoff is not None and handoff.get("asked") and not handoff.get("go") and not handoff.get("notified"):
        lines.append(f"handoff | - | - | {handoff['file']} | {handoff['file']}")
    finished = finished_sessions(watched, agents, records)
    done = {wanted for _, wanted in finished}
    gone = [item for item in gone_sessions(watched, agents) if item[1] not in done]
    closed = read_map(path.with_name(CLOSED))
    mine = {wanted: since for wanted, since in closed.items() if wanted in watched_ids}
    gone = after_grace(gone, agents, mine, at)  # forgets the ids that are not closed any more
    others = {wanted: since for wanted, since in closed.items() if wanted not in watched_ids} if args.id else {}
    remembered = {**others, **mine}  # a call for some --id sessions keeps the clocks of the others
    if remembered != closed:
        write_map(path.with_name(CLOSED), remembered)
    for name, wanted, state in gone:
        transcript = transcript_of(agents, wanted)
        key = (last_timestamp(transcript) if transcript else None) or "none"
        if fresh("gone", wanted, key):
            lines.append(event_line("gone", name, wanted, state, key))
    for name, wanted in finished:
        transcript = transcript_of(agents, wanted)
        key = (last_reply_timestamp(transcript) if transcript else None) or "none"
        if fresh("finished", wanted, key):
            lines.append(event_line("finished", name, wanted, "finished", key))
    ended = done | {item[1] for item in gone}
    limited = [item for item in limited_sessions(watched, agents) if item[1] not in ended]
    for name, wanted, key, resets in limited:
        if limits.get(wanted) != key:
            lines.append(event_line("limited", name, wanted, f"resets {reset_text(resets)}", key))
    ended |= {item[1] for item in limited}
    for name, wanted, key, waited in stale_sessions(watched, agents, args.stale_minutes, at):
        if wanted not in ended and waits.get(wanted) != key:
            lines.append(event_line("stale", name, wanted, f"waiting {waited} min", key))
    for record in active(records):
        wanted = str(record.get("id"))
        if (args.id and wanted not in watched_ids) or record.get("owner") is True:
            continue
        transcript = find_transcript(wanted)
        usage = last_usage(transcript) if transcript else None
        if usage is None:
            continue
        window = window_for(usage[1])
        if usage[0] / window >= args.fill_limit and fresh("fill", wanted, "fill"):
            lines.append(event_line("fill", record.get("name"), wanted, f"{usage[0] / window:.0%} of {window}", "fill"))
    for line in lines:
        print(line)
    return 0


def cmd_mark(args, path, records):
    """Record that an event line of `check` reached the lead, so `check` stops printing it."""
    if args.kind == "restart":
        request = read_restart(path)
        if request is None or str(request["version"]) != args.key:
            print(f"not marked restart - (no open request for {args.key})")
            return 0
        request["notified"] = time.time()
        save(path.with_name(RESTART), request)
        print("marked restart -")
        return 0
    if args.kind == "handoff":
        saved = read_handoff(path)
        if saved is None or saved["file"] != args.key:
            print(f"not marked handoff - (no open request for {args.key})")
            return 0
        saved["notified"] = time.time()
        save(path.with_name(HANDOFF), saved)
        print("marked handoff -")
        return 0
    if not args.id:
        print("dev-kit-sessions: mark needs --id for this kind", file=sys.stderr)
        return 1
    wanted = args.id
    if args.kind in ("limited", "stale"):
        target = path.with_name(LIMITS if args.kind == "limited" else STALE)
        known = read_map(target)
        if args.kind == "stale":
            known = prune_stale(known)
        known[wanted] = args.key
    else:
        target = path.with_name(DELIVERED)
        known = read_map(target)
        ended = {str(record.get("id")) for record in records if record.get("status") != "active"}
        known = {key: value for key, value in known.items() if key not in ended}
        marks = known.get(wanted)
        known[wanted] = {**(marks if isinstance(marks, dict) else {}), args.kind: args.key}
    write_map(target, known)
    print(f"marked {args.kind} {wanted}")
    return 0


def complete_end(path):
    """The byte offset after the last complete line of a file (the whole size when its tail has no line end)."""
    size = path.stat().st_size
    start = max(0, size - CHUNK)
    with open(path, "rb") as handle:
        handle.seek(start)
        found = handle.read(size - start).rfind(b"\n")
    return start + found + 1 if found >= 0 else (0 if start == 0 else size)


def turn_kind(entry):
    """How a transcript entry starts a turn: owner (a user entry with text, no `origin` or a human one), peer
    (`origin.kind` peer), notify (any other user entry with text: a task notification, a meta note); else None (an
    assistant entry, a tool result, a side chain)."""
    if entry.get("type") != "user" or entry.get("isSidechain"):
        return None
    origin = entry.get("origin") if isinstance(entry.get("origin"), dict) else {}
    if origin.get("kind") == "peer":
        return "peer"
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list):
        content = "\n".join(part.get("text", "") for part in content
                            if isinstance(part, dict) and part.get("type") == "text")
    text = content.strip() if isinstance(content, str) else ""
    if not text:
        return None
    if entry.get("isMeta") or origin.get("kind") not in (None, "human") or text.startswith("<task-notification"):
        return "notify"
    return "owner"


def count_wakes(path, offset):
    """(counts, units, new offset) of the transcript lines after `offset`: turn starts by kind (see turn_kind) and the
    units (retro.units_of) of the assistant messages, each message id once."""
    import retro
    lines, end = retro.read_new_lines(path, offset)
    counts, units, seen = {"owner": 0, "peer": 0, "notify": 0}, 0.0, set()
    for raw in lines:
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        kind = turn_kind(entry)
        if kind:
            counts[kind] += 1
        message = entry.get("message") or {}
        usage, model, mid = message.get("usage"), message.get("model"), message.get("id")
        if (entry.get("type") == "assistant" and not entry.get("isSidechain") and isinstance(usage, dict)
                and model != "<synthetic>" and mid not in seen):
            if mid:
                seen.add(mid)
            units += retro.units_of(usage, model)
    return counts, units, end


def cmd_size(args, path, records):
    """`<id> | <tokens> | <window> | <model>` per --id session that has a transcript; with --wakes also the turn
    starts and units since the last call (the offsets live in that file; the first call counts nothing)."""
    offsets = read_map(Path(args.wakes)) if args.wakes else {}
    saved = dict(offsets)
    for wanted in args.id:
        transcript = find_transcript(wanted)
        if transcript is None:
            continue
        usage = last_usage(transcript)
        tokens, model = usage if usage else (0, "")
        line = f"{wanted} | {tokens} | {window_for(model)} | {model}"
        if args.wakes:
            offset = offsets.get(wanted)
            if not isinstance(offset, int) or isinstance(offset, bool) or not 0 <= offset <= transcript.stat().st_size:
                counts, units, end = {"owner": 0, "peer": 0, "notify": 0}, 0.0, complete_end(transcript)
            else:
                counts, units, end = count_wakes(transcript, offset)
            saved[wanted] = end
            line += (f" | owner={counts['owner']} peer={counts['peer']} notify={counts['notify']}"
                     f" | units={round(units)}")
        print(line)
    if args.wakes and saved != offsets:
        write_map(Path(args.wakes), saved)
    return 0


def version_key(text):
    """A dotted version (`0.1.103`) as a tuple of ints, else None."""
    text = str(text or "").strip()
    return tuple(int(part) for part in text.split(".")) if re.fullmatch(r"\d+(\.\d+)*", text) else None


def read_releases(path):
    """(entries, warnings) of the release marks file: entries are (version key, version, kind, date, reason) of the
    valid entries; a missing file gives none and no warning, a file or entry that is not valid a warning (it counts
    as routine)."""
    if not path.exists():
        return [], []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return [], [f"{path} is unreadable, counted as routine: {exc}"]
    if not isinstance(data, dict):
        return [], [f"{path} is not an object of versions, counted as routine"]
    entries, warnings = [], []
    for version, entry in data.items():
        key = version_key(version)
        mark = entry if isinstance(entry, dict) else {}
        try:
            day = datetime.strptime(str(mark.get("date")), "%Y-%m-%d").date()
        except ValueError:
            day = None
        if key is None or mark.get("kind") not in RELEASE_KINDS or day is None:
            warnings.append(f"{path}: the entry {version!r} is not valid, counted as routine")
            continue
        entries.append((key, version, mark["kind"], day, " ".join(str(mark.get("reason") or "").split())))
    return entries, warnings


def local_day(value):
    """The local date of an ISO time (`Z` allowed; a fraction of more than 6 digits is cut), else None."""
    text = str(value or "").strip().replace("Z", "+00:00")
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return None
    return (moment.astimezone() if moment.tzinfo else moment).date()


def cmd_release(args, path, records):
    entries, warnings = read_releases(Path(args.file) if args.file else RELEASES)
    to = version_key(args.to)
    if to is None:
        warnings.append(f"--to {args.to!r} is not a version, counted as routine")
        entries = []
    start = version_key(args.from_version)
    if start is not None:
        hits = [entry for entry in entries if entry[2] == "critical" and start < entry[0] <= to]
    else:  # the start version is unknown: a critical release dated on or after the start day may be missing
        day = local_day(args.started)
        hits = [entry for entry in entries if entry[2] == "critical" and entry[0] <= to and entry[3] >= day] if day else []
    for warning in warnings:
        print(f"dev-kit-sessions: {warning}", file=sys.stderr)
    if hits:
        newest = max(hits)
        print(f"critical {newest[1]}: {newest[4]}")
    else:
        print("routine")
    return 0


def asks_question(text):
    """Whether a reply ends with a question: its last non-empty line that is not a recommendation line, without
    trailing emphasis marks and spaces, ends with `?` (a bracketed example after it allowed)."""
    lines = [line for line in text.splitlines() if line.strip()]
    while lines and RECOMMENDATION_LINE.match(lines[-1]):
        lines.pop()
    return bool(lines) and bool(QUESTION_END.search(lines[-1].rstrip(" \t*_`")))


def chat_activity(path, minutes, at):
    """`quiet`, `active owner <N>s ago` or `active open question` for a transcript (see `quiet` in the module
    docstring), reading back at most ANSWER_ENTRIES entries."""
    question = None  # whether the last assistant text (with no owner message after it) asks a question
    for scanned, entry in enumerate(tail_entries(path)):
        if scanned >= ANSWER_ENTRIES:
            break
        if entry.get("isSidechain"):
            continue
        if entry.get("type") == "assistant":
            text = assistant_text(entry) if question is None else ""
            if text:
                question = asks_question(text)
            continue
        if (entry.get("origin") or {}).get("kind") == "peer" or not message_text(entry):
            continue
        sent = parse_time(entry.get("timestamp"))
        if sent is not None and at - sent < minutes * 60:
            return f"active owner {max(0, int(at - sent))}s ago"
        break
    return "active open question" if question else "quiet"


def cmd_quiet(args, path, records):
    transcript = find_transcript(args.id)
    if transcript is None:
        print("active no transcript")
        return 0
    try:
        print(chat_activity(transcript, args.minutes, time.time()))
    except OSError as exc:
        print(f"dev-kit-sessions: {transcript} is unreadable: {exc}", file=sys.stderr)
        print("active no transcript")
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
            limited, stale = [], []
            if agents is not None:
                gone = after_grace(gone, agents, closed_since, time.monotonic())
                ended = done | {item[1] for item in gone}
                limited = new_limits([item for item in limited_sessions(watched, agents) if item[1] not in ended],
                                     path, {wanted for _, wanted in watched})
                ended |= {item[1] for item in limited}
                stale = new_stale([item for item in stale_sessions(watched, agents, args.stale_minutes, time.time())
                                   if item[1] not in ended], path)
            if gone or finished or limited or stale:
                for name, wanted, state in gone:
                    print(f"gone: {name or '(no name)'} | {wanted} | {state}")
                for name, wanted in finished:
                    print(f"finished: {name or '(no name)'} | {wanted}")
                for name, wanted, _key, resets in limited:
                    print(f"limited: {name or '(no name)'} | {wanted} | resets {reset_text(resets)}")
                for name, wanted, _key, waited in stale:
                    print(f"stale: {name or '(no name)'} | {wanted} | waiting {waited} min")
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
    fill.add_argument("--limit", type=float, default=FILL_LIMIT)
    fill.add_argument("--window", type=int, default=0)
    fill.add_argument("--over-only", action="store_true", help="print only the OVER rows, nothing else")
    fill.add_argument("--self", nargs="?", const="", default=None,
                      help="the caller's own context instead of the registry rows (id default: env CLAUDE_CODE_SESSION_ID)")
    others = sub.add_parser("others")
    others.add_argument("--self", default="", help="the caller's session id (default: env CLAUDE_CODE_SESSION_ID)")
    others.add_argument("--json", action="store_true")
    state = sub.add_parser("state")
    state.add_argument("--id", action="append", default=[], help="a session to show (repeatable; default: the registry)")
    answers = sub.add_parser("answers", help="what the owner wrote in a session after its last SendMessage")
    answers.add_argument("--id", action="append", default=[], help="a session to show (repeatable; default: the registry)")
    watch = sub.add_parser("watch")
    watch.add_argument("--id", action="append", default=[], help="a session to watch (repeatable; default: the registry)")
    watch.add_argument("--interval", type=float, default=60, help="seconds between reads of the session list")
    watch.add_argument("--max-minutes", type=float, default=120, help="exit with the time-limit line after this")
    watch.add_argument("--stale-minutes", type=float, default=20,
                       help="report a session waiting this long since its last assistant entry")
    check = sub.add_parser("check", help="one round of watch: the events not delivered yet, one line each; marks nothing")
    check.add_argument("--id", action="append", default=[], help="a session to check (repeatable; default: the registry)")
    check.add_argument("--stale-minutes", type=float, default=20,
                       help="report a session waiting this long since its last assistant entry")
    check.add_argument("--fill-limit", type=float, default=FILL_LIMIT,
                       help="report an active C whose context reaches this share of its window")
    mark = sub.add_parser("mark", help="record that an event line of check was delivered")
    mark.add_argument("--kind", required=True, choices=MARK_KINDS)
    mark.add_argument("--id", default="", help="the session id (not for restart or handoff)")
    mark.add_argument("--key", required=True, help="the last field of the event line")
    size = sub.add_parser("size", help="context size, and with --wakes the turn starts and units since the last call")
    size.add_argument("--id", action="append", default=[], help="a full session id (repeatable)")
    size.add_argument("--wakes", help="a state file (json id -> transcript offset) that the call reads and updates")
    limited = sub.add_parser("limited", help="which sessions stopped on the usage limit (transcripts only)")
    limited.add_argument("--id", action="append", default=[], help="a full session id (repeatable)")
    restart = sub.add_parser("restart", help="the restart request the Pult watcher leaves for a lead")
    restart_sub = restart.add_subparsers(dest="restart_action", required=True)
    restart_sub.add_parser("request").add_argument("--version", required=True)
    restart_sub.add_parser("ready").add_argument("--version", help="mark ready even with no open request")
    for action in ("status", "clear"):
        restart_sub.add_parser(action)
    handoff = sub.add_parser("handoff", help="the handoff a full lead leaves for the Pult watcher, which moves it to a fresh context")
    handoff_sub = handoff.add_subparsers(dest="handoff_action", required=True)
    handoff_save = handoff_sub.add_parser("save")
    handoff_save.add_argument("--file", required=True, help="the handoff file name (bare, ends in .md)")
    handoff_save.add_argument("--go", action="store_true", help="move now: skip the quiet wait")
    for action in ("go", "request", "status", "clear"):
        handoff_sub.add_parser(action)
    release = sub.add_parser("release", help="whether the dev-kit releases a lead lacks hold a critical one")
    release.add_argument("--from", dest="from_version", required=True,
                         help="the dev-kit version the lead process started on, or older when unknown")
    release.add_argument("--to", required=True, help="the installed dev-kit version")
    release.add_argument("--started", default="", help="the start time of the lead process (ISO), for --from older")
    release.add_argument("--file", default="", help="the release marks file (default: releases.json of dev-kit)")
    quiet = sub.add_parser("quiet", help="whether a lead's chat is quiet: no recent owner message, no open question")
    quiet.add_argument("--id", required=True, help="the full session id")
    quiet.add_argument("--minutes", type=float, default=QUIET_MINUTES,
                       help="an owner message younger than this makes the chat active")
    args = parser.parse_args(argv)
    for key in ("id", "parent", "predecessor", "self", "name", "worktree", "task"):  # ids pasted with a CR or spaces
        value = getattr(args, key, None)
        if isinstance(value, str):
            setattr(args, key, value.strip())
        elif isinstance(value, list):
            setattr(args, key, [item.strip() for item in value])
    try:
        stateless = args.action in ("limited", "size", "release", "quiet")  # no project state: transcripts or a file
        path = registry_path(args.project, create=not stateless)
        no_rows = args.action in ("restart", "handoff") or (args.action == "fill" and args.self is not None)
        records = [] if no_rows or stateless else load(path)  # the handshakes and `fill --self` work with a broken registry too
        return {"add": cmd_add, "end": cmd_end, "list": cmd_list, "fill": cmd_fill, "restart": cmd_restart, "handoff": cmd_handoff,
                "others": cmd_others, "state": cmd_state, "answers": cmd_answers, "watch": cmd_watch, "check": cmd_check, "mark": cmd_mark,
                "size": cmd_size, "limited": cmd_limited, "release": cmd_release,
                "quiet": cmd_quiet}[args.action](args, path, records)
    except Unreadable as exc:
        print(f"dev-kit-sessions: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
