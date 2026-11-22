"""Find problems in the sessions' transcripts with no model, sort them into one folder per project, and serve the
retro session and the lead of each project. A model reads the findings; this script uses none.

    dev-kit-retro scan [--force] [--days N]       the full scan of every transcript (once a day without --force)
    dev-kit-retro scan --transcript PATH          only that transcript and its subagents
    dev-kit-retro items [--project DIR]           the new findings and the items of the project, see below
    dev-kit-retro done [--branch NAME] [--project DIR]
                                                  move the findings the last `items` showed to `seen/`; NAME: the
                                                  branch the retro session left for its lead to merge
    dev-kit-retro docs-done [--project DIR]       stamp the end of the weekly docs session
    dev-kit-retro add --text LINE [--from NAME] [--project DIR]
                                                  add a finding to the project's `new/` (any session, any project)
    dev-kit-retro due [--session ID] [--project DIR]
                                                  one line when the lead has retro items to act on, else nothing
    dev-kit-retro asked --answer yes|no [--project DIR]
                                                  stamp the weekly question to the owner and the answer
    dev-kit-retro hook-start | hook-end           SessionStart and SessionEnd hooks of the plugin (JSON on stdin)
    dev-kit-retro critical [--days N]             scan if not yet scanned today, then print the critical token problems
    dev-kit-retro session [--id SESSION_ID | --path TRANSCRIPT.jsonl] [--no-subagents]
                                                  the units of one session as a share of the weekly limit (see below)
    dev-kit-retro calibrate                       refit the weekly limit from the status line log and print the result

`--project DIR` is any folder of the project (a worktree too; default the current folder), or a bare repository folder
name of a known retro project (`ClaudeDevKit`, ignoring case; known = it has an item folder whose `state.json` records
its `root`, so another project's retro can write `add --project ClaudeDevKit ...`); a bare name that is no known
project is taken as a folder. A project that is not a retro project gets exit code 2 (`due` and the hooks stay silent
instead); when the project's `state.json` stays locked (see Lock), `items`, `done` and `asked` exit 1 and change
nothing.

Retro projects: a project counts when its main checkout (the parent of the git common dir) has `.claude/dev-kit.md`
with a line `## project-lead`. A transcript belongs to the project of the `cwd` of its lines (git, cached per cwd; when
git fails, a deleted worktree, the path is cut at `/.claude/worktrees/` and the part before it is the checkout).
Only the findings of retro projects are routed: transcripts of other projects (the home folder, Pult, a project with
no lead) are still read for the token statistics, the spend tables and `critical`, which stay global, and their
findings stay in `scan-<date>.md` only. The findings of a session whose title starts with `Ретро:` (a retro session)
or `Документація:` (the weekly docs session) and of its subagents are dropped everywhere (log included), so the retro
never feeds on these hook-started sessions; their token statistics still count.

Folders: the retro folder is env DEV_KIT_RETRO_DIR, else `~/.claude/dev-kit/retro` (local, outside any repository).
It holds the global `state.json` (byte offsets, token statistics, the fitted weekly limit), `scan.lock`, the human
log `scan-<date>.md` (all findings of a full scan and the `## Spend` tables) and the owner's `notes.md`. Each project
has `<retro folder>/<repo-folder-name>-<10 hex>/` (`dev_kit_state.folder_name`, the name of its state folder) with:
- `new/`: findings no review has seen, one file per writer and run, never shared: `scan-<date>-<HHMMSS>.md` (full
  scan), `<date>-<session id8>-<HHMMSS>.md` (one transcript), `notes-<date>-<HHMMSS>.md` (owner notes), `add-...md`
  (`add`); each finding is a line starting `- `;
- `seen/`: files moved there by `done`, deleted after SEEN_DAYS days;
- `items/<cause-key>.md`: one file per item, written by the retro session; lines `- status: <status>`, `- kind:
  <kind>`, one `- seen: ...` line per sighting and `- fix: <YYYY-MM-DD> | <what> | trivial` per trivial fix;
- `docs-items/<key>.md`: one file per docs item, written by the weekly docs session (`dev-kit:maintain-project-docs`,
  "Weekly background run"); its line `- status: owner` marks an item the owner decides;
- `state.json`: `root` (the main checkout), `last_review`, `retro_started`, `retro_branch`, `docs_started`,
  `docs_done`, `lead_session`, `asked_at`, `answer`, `shown` (the `new/` files the last `items` showed). Written
  atomically (temp file and replace).
Transcripts: every `*.jsonl` under env DEV_KIT_PROJECTS_DIR, else `~/.claude/projects`, subagent ones in
`<session>/subagents/` included.

Locks (lock files made with O_EXCL; a lock older than its limit is taken over): the global `state.json` is read,
changed and written only while `scan.lock` exists (stale after LOCK_STALE_S). A transcript scan waits up to
LOCK_WAIT_TRANSCRIPT_S for it and then exits 0 with no output (its lines are read by the next full scan); a full scan,
`critical` and `calibrate` wait up to LOCK_WAIT_FULL_S. A project's `state.json` is read, changed and written only
while `state.lock` exists in its item folder (stale after PROJECT_LOCK_STALE_S, wait up to PROJECT_LOCK_WAIT_S): the
stamps of `hook-start`, `items`, `done`, `docs-done`, `asked` and the scan's `root` record. `hook-start` that cannot get it starts
nothing, so two sessions starting at once never both start a retro session.

`scan` reads only what was appended to each transcript since the last scan (`state.json` keeps a byte offset per
file, up to the last complete line). On the first full scan (no full scan yet) a file last changed before `--days`
days ago (default 1) that has no offset is skipped and its offset set to its size, so it does not read the whole
history. A full scan writes `scan-<YYYY-MM-DD>.md` (local date; a second scan the same day with `--force` appends to
it), one line per finding, and each line also goes to the `new/` of its project (priority token lines too):

    - <project folder> | <session title (first 8 of its id)> or <session id>[ / subagent <type>] | <kind> | <detail>

A full scan also reads the new lines of `<retro folder>/notes.md` (offset kept in the global state) and puts each into
the `new/` of the retro project whose repository folder name equals the line's project field, ignoring case; other
lines are dropped. `script candidate` lines go to the project when all their sessions are of one project, else to the
project of the repository that holds this plugin (when it is a retro project).
`scan --transcript PATH` is for the SessionEnd hook: only that transcript and its `<id>/subagents/*.jsonl`, the same
per-transcript kinds and token statistics (merged into the global state), no cross-transcript kinds, no refit, no
priority lines, no notes; its findings go to one `new/<date>-<id8>-<HHMMSS>.md` and are appended to `scan-<date>.md`;
nothing found, no file.

`items` prints: the folder path; `last review: <local date and time of last_review, or never>`; the new findings of
`new/` (token problems first, under "Priority"); one line per
`items/*.md` file `<cause-key> | <status> | <kind> | sightings <N>` (N = the lines starting `- seen:`); and `trivial
fixes in the last 7 days: <N> of FIXES_PER_WEEK` (the `- fix:` lines marked trivial and dated in the last 7 days, today
included); then one line per `docs-items/*.md` file `<key> | <status>`. It records the `new/` file names it showed;
`done` moves exactly those to `seen/`, sets `last_review`, records `retro_branch` (`--branch`, else none) and deletes
what is older than SEEN_DAYS in `seen/`. Findings that came after `items` stay new. `docs-done` sets `docs_done`.
`due` prints nothing unless the session (when `--session` is given) is the lead recorded by `hook-start`; then
`retro: <N> items due (<U> urgent)` when an item has status `urgent`, or when items with status `disputed` or
`trivial-fixed`, or docs items with status `owner`, exist and the last weekly ask is 7+ days old or missing, or 1+ day
old after the answer `no` (N counts the urgent items, and the others when the weekly ask is due: one weekly question
for the retro and the docs).
`hook-start` (never fails, exit 0): in a retro project, a session titled `Ретро:` or `Документація:` does nothing; a
full scan is spawned
(detached) when none ran today and the scan lock is free; then, under the project lock, a title `P: ` records the
lead's session id, and when `new/` has files, `last_review` is older than REVIEW_HOURS (or missing),
`retro_started` older than START_GUARD_HOURS (or missing) and no docs session may still run (`docs_started` younger
than START_GUARD_HOURS and newer than `docs_done`), it stamps `retro_started` and starts a background
`Ретро: <repo folder>` session running `/dev-kit:retro` (env DEV_KIT_RETRO_NO_START=1 skips that start, not the
stamp). When it starts no retro session, it starts the weekly docs session `Документація: <repo folder>` running
`/dev-kit:maintain-project-docs weekly` (same env switch) when all hold: `docs_done` is older than DOCS_DAYS (or
missing); `docs_started` is older than DOCS_GUARD_HOURS (or missing), so a run that ended with no `docs-done` is
retried once a day, not at every session start; no retro session may still run (`retro_started`
is not newer than `last_review` while younger than START_GUARD_HOURS); and the retro's `retro_branch` is merged into
the main checkout's HEAD (or gone) or `last_review` is older than DOCS_MERGE_WAIT_HOURS. So the docs session runs on
the rules the week's retro just fixed, or on its own in a week with no retro; it stamps `docs_started`.
`hook-end` in a retro project spawns (detached) `scan --transcript` of the ending session when its transcript
exists. Detached start: on Windows CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB (not
DETACHED_PROCESS, which makes the console children, git, open windows); when the session's job forbids the breakaway
(Popen raises OSError) it is started again without it. Elsewhere `start_new_session`.

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
not findings; they stay in the scan files only). "Usual" is the median units per run of one
subagent type on one model over the last RUNS_KEPT runs (`state.json`), shown only with USUAL_MIN or more runs.

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
(`weekly_limit()`: the fit kept in `state.json`, else the seed WEEKLY_LIMIT_UNITS; one place), and critical from
CRITICAL_SPEND_PCT or CRITICAL_WASTE_PCT. When a scan runs on a later day, each finished day's problems become scan lines
`- <project folder> | <session> | token spend|token waste | <date>: <detail>[; critical (shown in Pult's status)]`
(once per day, in the `new/` of the session's project; `items` prints them first, under "Priority"). `critical`
prints, for today and CRITICAL_DAYS days before, one line per critical problem not shown before, or grown to
CRITICAL_GROWTH times the share shown (shown shares are kept in `state.json`; nothing else touches them), biggest
first, nothing when none:

    critical | <project> | <session title (id8)> | <date> | spent 2.4% of the weekly limit (16.6M units)
    critical | <project> | <session title (id8)> | <date> | wasted 0.6% of the weekly limit: idle wakes 0.60% (11),
        cold restarts 0.00%, bloated context 0.00%[ (was 0.5% when last shown)]

(each on one line.)

The weekly limit in units is fitted from the status line log (`usage-log.jsonl`, written by `dev-kit-statusline`, env
DEV_KIT_USAGE_LOG for its folder): its readings are grouped by weekly window (`week_resets`); in each window the
first and last reading give the per cent used between them, and the units are those of all assistant messages of ALL
transcripts (every project, subagents included, a message id once) dated after the first reading up to the last (the
per cent is account-wide). limit = units * 100 / per cent, summed over the windows with a positive delta, used when
the deltas total FIT_MIN_POINTS or more points; else the last fit stays, else the seed. Reset times under an hour
apart are one window; readings without a numeric reset time, windows that began over FIT_DAYS days ago and windows
that began before the oldest transcript file are left out (deleted transcripts would drag the limit down). The units
of a closed window (a later window has readings) are kept in `state.json` (`fit_windows`), so a refit reads only
the transcripts of the current window. The fit is kept in
`state.json`; `scan` refits when the log has readings newer than the last check, `calibrate` always does.

`session` sums the units of one session (default: env CLAUDE_CODE_SESSION_ID; `--path` names a transcript file) over
its transcript and its subagents (`<session>/subagents/*.jsonl`, left out by `--no-subagents`), a message id once,
with the scan's weights, and prints the share of the weekly limit, the one an agent quotes in a report:

    ~2.3% of the weekly limit, estimate
    main 1.1%, subagents 1.2% (4 runs); 15.9M units; limit 690M units (fit 2026-11-20)

It reads no state but the fit and changes nothing. Exit code 2 when the session or its file is not found.

Findings and item files are read as UTF-8 with a BOM allowed and bad bytes replaced. `notes.md` holds what only a
session can see; sessions append one line per case (the owner's global `docs/process-mistakes.md`):

    - <YYYY-MM-DD> | <project> | <session name> | <correction | wrong order> | <what happened, one sentence>

Exit codes: 0 done, 2 bad arguments.
"""
import argparse
import contextlib
import datetime
import json
import os
import re
import secrets
import subprocess
import sys
import time
from collections import Counter, defaultdict, namedtuple
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the launcher runs this file with runpy, which adds nothing
import dev_kit_state  # noqa: E402  the project's folder name and main checkout
import statusline  # noqa: E402  the status line script owns the usage log file

RETRO_ENV = "DEV_KIT_RETRO_DIR"
PROJECTS_ENV = "DEV_KIT_PROJECTS_DIR"
NO_START_ENV = "DEV_KIT_RETRO_NO_START"  # 1: the SessionStart hook does not start the retro session (tests)
PROFILE_LINE = "## project-lead"  # the line of `.claude/dev-kit.md` that makes a project a retro project
FIXES_PER_WEEK = 5  # the cap of trivial fixes per project per week, shown by `items`
REVIEW_HOURS = 20  # no new retro session while the last review is younger
START_GUARD_HOURS = 6  # no new retro session while the last start is younger (a session that is still running)
SEEN_DAYS = 30  # `done` deletes what is older in `seen/`
LOCK_NAME = "scan.lock"
LOCK_STALE_S = 600
LOCK_WAIT_TRANSCRIPT_S = 5
LOCK_WAIT_FULL_S = 60
PROJECT_LOCK_NAME = "state.lock"  # in a project's item folder, for its state.json
PROJECT_LOCK_STALE_S = 60
PROJECT_LOCK_WAIT_S = 2
RETRO_TITLE = "Ретро:"  # the title of a retro session (sessions.RETRO_PREFIX is this plus a space)
DOCS_TITLE = "Документація:"  # the title of the weekly docs session (sessions.DOCS_PREFIX is this plus a space)
DOCS_DAYS = 7  # the weekly docs session runs once in this many days
DOCS_MERGE_WAIT_HOURS = 48  # the docs session waits this long for the retro's branch to be merged
DOCS_GUARD_HOURS = 24  # no new docs session while the last start is younger (one that ended with no `docs-done` too)
GIT_TIMEOUT_S = 2  # each git call of the SessionStart hook (its limit is 10 s)
WINDOWS = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
HEAD_LINES = 200  # the lines of a transcript's start searched for its `cwd`
WORKTREES = re.compile(r"[\\/]\.claude[\\/]worktrees[\\/]", re.IGNORECASE)
URGENT_LINE = re.compile(r" \| token (spend|waste) \| ")
FIX_LINE = re.compile(r"^- fix:\s*(\d{4}-\d\d-\d\d)\s*\|.*\|\s*trivial\s*$")
Project = namedtuple("Project", "root name folder")  # main checkout, its folder name, the retro folder name
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
WEEKLY_LIMIT_UNITS = 690e6  # the seed of the weekly limit in units: a hand fit at Opus weight 1.5 from `/usage` on
WEEKLY_LIMIT_DATE = "2026-11-20"  # 2026-11-20 (plans/retro-tokens.md, "Opus weight check"; about 30% uncertain). The
# fit from the status line log (usage-log.jsonl, see `fit_limit`) replaces it once it has FIT_MIN_POINTS points
FIT_MIN_POINTS = 10  # the weekly per cent points the log must span, summed over windows, before the fit is used
FIT_DAYS = 28  # only windows that began within this many days count: older transcripts are deleted
WINDOW_ROUND_S = statusline.SAME_WINDOW_S  # reset times of one weekly window differing by less are one window
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


def retro_dir(create=True):
    folder = Path(os.environ[RETRO_ENV]) if os.environ.get(RETRO_ENV) else Path.home() / ".claude" / "dev-kit" / "retro"
    if create:
        folder.mkdir(parents=True, exist_ok=True)
    return folder


def projects_dir():
    return Path(os.environ[PROJECTS_ENV]) if os.environ.get(PROJECTS_ENV) else Path.home() / ".claude" / "projects"


def today():
    return datetime.date.today().isoformat()


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def load_state(folder):
    """The global state (offsets, token statistics); read-modify-write it only under `scan_lock`."""
    path = folder / "state.json"
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    state.setdefault("offsets", {})
    state.setdefault("last_scan", "")
    return state


def write_json(path, data):
    """Write a JSON file atomically: a temp file of this process, then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def save_state(folder, state):
    write_json(folder / "state.json", state)


def lock_age(path):
    """Seconds since the lock file was made, or None when there is none."""
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return None


def lock_free(folder):
    """Whether no live scan lock is held (no lock file, or a stale one)."""
    age = lock_age(folder / LOCK_NAME)
    return age is None or age > LOCK_STALE_S


@contextlib.contextmanager
def scan_lock(folder, wait):
    """Hold `scan.lock` of the retro folder for the global state; yields False after `wait` s (see `file_lock`)."""
    with file_lock(folder / LOCK_NAME, wait, LOCK_STALE_S) as held:
        yield held


@contextlib.contextmanager
def project_lock(folder):
    """Hold `state.lock` of a project's item folder for its `state.json`; yields False when it stays taken."""
    folder.mkdir(parents=True, exist_ok=True)
    with file_lock(folder / PROJECT_LOCK_NAME, PROJECT_LOCK_WAIT_S, PROJECT_LOCK_STALE_S) as held:
        yield held


@contextlib.contextmanager
def file_lock(path, wait, stale):
    """Hold a lock file (made with O_EXCL; one older than `stale` s is taken over); yields False after `wait` s."""
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


def load_project(folder):
    """The state of one project's item folder (see the module doc); {} when none."""
    try:
        data = json.loads((folder / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_project(folder, data):
    write_json(folder / "state.json", data)


def remember_root(project):
    """Record the project's main checkout in its item folder state, so the notes can be sorted by repository name."""
    folder = retro_dir() / project.folder
    if load_project(folder).get("root") == str(project.root):
        return
    with project_lock(folder) as held:
        if held:  # else the next scan records it
            data = load_project(folder)
            data["root"] = str(project.root)
            save_project(folder, data)


def is_retro_project(root):
    """Whether the checkout `root` has a `## project-lead` line in `.claude/dev-kit.md`."""
    try:
        text = (Path(root) / ".claude" / "dev-kit.md").read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return False
    return any(line.strip() == PROFILE_LINE for line in text.splitlines())


def head_cwd(path):
    """The `cwd` of the first line of a transcript that has one (within HEAD_LINES lines), or None."""
    try:
        with open(path, "rb") as handle:
            for number, raw in enumerate(handle):
                if number >= HEAD_LINES:
                    break
                if b'"cwd"' not in raw:
                    continue
                try:
                    entry = json.loads(raw)
                except ValueError:
                    continue
                cwd = entry.get("cwd") if isinstance(entry, dict) else None
                if isinstance(cwd, str) and cwd:
                    return cwd
    except OSError:
        pass
    return None


class Mapper:
    """Folders and transcripts to retro projects; the git calls are cached per cwd."""

    def __init__(self):
        self.roots = {}  # cwd -> main checkout
        self.projects = {}  # main checkout -> Project or None
        self.heads = {}  # transcript path -> cwd or None

    def root_of(self, cwd):
        """The main checkout of a folder; for a path git cannot read (a deleted worktree) the part before
        `/.claude/worktrees/`, else the folder itself."""
        if cwd not in self.roots:
            root = dev_kit_state.main_checkout(cwd)
            if root is None:
                base = WORKTREES.split(cwd, maxsplit=1)[0]
                root = dev_kit_state.main_checkout(base) or Path(base)
            self.roots[cwd] = root
        return self.roots[cwd]

    def project_of_cwd(self, cwd):
        """The retro project of a folder, or None."""
        if not isinstance(cwd, str) or not cwd.strip():
            return None
        root = self.root_of(cwd)
        key = str(root)
        if key not in self.projects:
            self.projects[key] = (Project(root, root.name, dev_kit_state.folder_name(root))
                                  if is_retro_project(root) else None)
        return self.projects[key]

    def project_of_transcript(self, path):
        """The retro project of a transcript (the `cwd` of its first lines), None for another or an unknown one."""
        key = str(path)
        if key not in self.heads:
            self.heads[key] = head_cwd(path)
        cwd = self.heads[key]
        if cwd is None:
            del self.heads[key]  # look again at the next call: the lines may come
        return self.project_of_cwd(cwd)


def plugin_project(mapper):
    """The retro project of the repository that holds this plugin, or None."""
    return mapper.project_of_cwd(str(Path(__file__).resolve().parents[3]))


def known_roots():
    """Retro projects with an item folder: lower-case repository folder name -> (item folder name, main checkout)."""
    found = {}
    for state in sorted(retro_dir(create=False).glob("*/state.json")):
        root = load_project(state.parent).get("root")
        if isinstance(root, str) and root:
            found.setdefault(Path(root).name.lower(), (state.parent.name, root))
    return found


def known_projects():
    """Retro projects with an item folder: lower-case repository folder name -> item folder name."""
    return {name: folder for name, (folder, _) in known_roots().items()}


def write_new(folder_name, name, lines):
    """Write `lines` to a new file of the project's `new/` folder, never over another file; None for no lines."""
    if not lines:
        return None
    new = retro_dir() / folder_name / "new"
    new.mkdir(parents=True, exist_ok=True)
    stem = name[:-len(".md")]
    for number in range(1000):
        path = new / (name if number == 0 else f"{stem}-{number}.md")
        try:
            handle = open(path, "x", encoding="utf-8")
        except FileExistsError:
            continue
        with handle:
            handle.write("".join(line + "\n" for line in lines))
        return path
    return None


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


def scan(days=1, force=False, out=None, transcript=None):
    """The full scan, or with `transcript` only that transcript and its subagents (see the module doc)."""
    out = out or sys.stdout
    folder = retro_dir()
    with scan_lock(folder, LOCK_WAIT_TRANSCRIPT_S if transcript else LOCK_WAIT_FULL_S) as held:
        if not held:
            if not transcript:
                print("scan busy: another scan holds scan.lock", file=out)
            return 0
        return scan_locked(folder, days, force, out, transcript)


def scan_locked(folder, days, force, out, transcript):
    state = load_state(folder)
    day = today()
    if not transcript and state["last_scan"] == day and not force:
        print("already scanned today", file=out)
        return 0
    root = projects_dir()
    started = now_utc()
    since = parse_time(state.get("scan_started", ""))
    seen = set()  # message ids counted in this scan
    first = not state["last_scan"] and not transcript
    cutoff = time.time() - days * 86400
    known = state.setdefault("titles", {})  # a title is written once, often in an earlier scan's lines
    windows = {}  # (project, session, subagent type) -> counters; subagents of one type in one session are summed
    homes = {}  # (project, session) -> the retro project of the transcripts read
    mapper = Mapper()
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
        owner = mapper.project_of_transcript(path)  # None: not a retro project; read for the token statistics only
        lines, state["offsets"][key] = read_new_lines(path, offset)
        if not lines:
            continue
        project, session, sub = session_label(path, root)
        homes[(project, session)] = owner
        if owner:
            state.setdefault("home", {})[f"{project}/{session}"] = owner.folder
        else:
            state.get("home", {}).pop(f"{project}/{session}", None)
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
    routed = defaultdict(list)  # item folder name -> its finding lines
    commands = defaultdict(set)

    def retro_session(project, session):
        """A retro session's own findings never feed the retro again (its token statistics still count)."""
        return titles.get((project, session), "").strip().startswith((RETRO_TITLE, DOCS_TITLE))

    def route(project, session, line):
        """A finding line to the scan log, and to the project of its session when that is a retro project."""
        out_lines.append(line)
        if homes[(project, session)]:
            routed[homes[(project, session)].folder].append(line)

    for (project, session, sub), result in windows.items():
        if retro_session(project, session):
            continue
        label = f"{titles[(project, session)]} ({session[:8]})" if (project, session) in titles else session
        if sub:
            label += " / " + sub
        for kind, detail in findings_of(result):
            route(project, session, f"- {project} | {label} | {kind} | {detail}")
        for command in result["bash"]:
            commands[command].add((project, session))
    if not transcript:  # the same command in several sessions needs the sessions of all transcripts
        plugin = plugin_project(mapper)
        for command, sessions in sorted(commands.items()):
            if len(sessions) >= SCRIPT_SESSIONS:
                line = (f"- {len({p for p, _ in sessions})} project(s) | {len(sessions)} sessions | "
                        f"script candidate | {short(command)}")
                out_lines.append(line)
                owners = {homes[pair].folder for pair in sessions if homes[pair]}
                if len(owners) == 1 and all(homes[pair] for pair in sessions):
                    routed[next(iter(owners))].append(line)
                elif plugin and owners:  # spread over several projects, one of them a retro project
                    routed[plugin.folder].append(line)
    spend_findings, table = spend(windows, titles, state)
    for project, session, line in spend_findings:
        if not retro_session(project, session):
            route(project, session, line)
    if not transcript:
        refit_if_new(state)
        for key, line in priority_lines(state, day):
            if state.get("titles", {}).get(key, "").strip().startswith((RETRO_TITLE, DOCS_TITLE)):
                continue
            out_lines.append(line)
            if state.get("home", {}).get(key):
                routed[state["home"][key]].append(line)
        sort_notes(state, folder, mapper, plugin, routed)
    else:
        table = []
    for owner in {owner.folder: owner for owner in mapper.projects.values() if owner}.values():
        remember_root(owner)  # also without findings: the notes are sorted by the repository name of these roots
    clock = datetime.datetime.now().strftime("%H%M%S")
    if transcript:
        write_new_all(routed, lambda: f"{day}-{Path(transcript).stem[:8]}-{clock}.md")
    else:
        write_new_all(routed, lambda: f"scan-{day}-{clock}.md")
    if out_lines or table:
        report = folder / f"scan-{day}.md"
        header = "" if report.exists() else f"# Scan {day}\n\n"
        with open(report, "a", encoding="utf-8") as handle:
            handle.write(header + "".join(line + "\n" for line in out_lines))
            if table:
                handle.write(f"\n## Spend {started.astimezone().strftime('%H:%M')}\n\n" + "\n".join(table) + "\n\n")
    if not transcript:
        state["scan_started"] = started.isoformat()
        state["last_scan"] = day
    save_state(folder, state)
    print(f"scanned {len(windows)} transcript(s), {len(out_lines)} finding(s)", file=out)
    return 0


def write_new_all(routed, make_name):
    """One new file per project in `routed` (item folder name -> lines)."""
    for folder_name, lines in routed.items():
        write_new(folder_name, make_name(), lines)


def notes_offset(state, path):
    """The byte offset in `notes.md` where the unread lines begin: kept in the state; with none (an older state), after
    the lines an earlier version had marked reviewed (`reviewed.notes_lines`)."""
    if "notes_offset" in state:
        return state["notes_offset"]
    reviewed = state.get("reviewed")
    skip = reviewed.get("notes_lines", 0) if isinstance(reviewed, dict) else 0
    if not skip:
        return 0
    try:
        data = path.read_bytes()
    except OSError:
        return 0
    offset = 0
    for line in data.splitlines(keepends=True):
        if skip <= 0:
            break
        offset += len(line)
        skip -= line.decode("utf-8-sig", errors="replace").startswith("- ")  # an earlier version counted these
    return offset


def sort_notes(state, folder, mapper, plugin, routed):
    """Put the new lines of `notes.md` into the project named in each line (a retro project; others dropped)."""
    path = folder / "notes.md"
    offset = notes_offset(state, path)
    try:
        size = path.stat().st_size
    except OSError:
        return
    if offset > size:
        offset = 0
    lines, state["notes_offset"] = read_new_lines(path, offset)
    if not lines:
        return
    projects = known_projects()
    for owner in mapper.projects.values():
        if owner:
            projects.setdefault(owner.name.lower(), owner.folder)
    if plugin:
        projects.setdefault(plugin.name.lower(), plugin.folder)
    for raw in lines:
        line = raw.decode("utf-8-sig", errors="replace").strip()
        fields = [field.strip() for field in line.split("|")]
        if line.startswith("- ") and len(fields) >= 5 and fields[1].lower() in projects:
            routed[projects[fields[1].lower()]].append(line)


def weekly_limit(state=None):
    """`(units, date)` of the weekly limit: the fit kept in the state, else the seed constants."""
    if state is None:
        state = load_state(retro_dir())
    fit = state.get("fit")
    if isinstance(fit, dict) and number(fit.get("units")) > 0:
        return fit["units"], str(fit.get("date") or "")
    return WEEKLY_LIMIT_UNITS, WEEKLY_LIMIT_DATE


def percent(units, limit=None):
    """Units as a share of the weekly limit (`limit` in units, default the current one), in per cent."""
    return units * 100 / (limit or weekly_limit()[0])


def pct_text(value):
    return f"{value:.1f}%" if value >= 1 else f"{value:.2f}%"


def problems(row, limit=None):
    """The token problems of one session's day, from the note shares up: `(kind, share, detail, critical)`.

    kind is `spend` (units spent) or `waste` (idle wakes, cold restarts, bloated context)."""
    limit = limit or weekly_limit()[0]
    found = []
    spend = percent(row["units"], limit)
    if spend >= NOTE_SPEND_PCT:
        found.append(("spend", spend, f"spent {pct_text(spend)} of the weekly limit ({amount(row['units'])} units)",
                      spend >= CRITICAL_SPEND_PCT))
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
    """`(session key, scan line)` for the token problems of every finished day not written yet; the retro lists them first.

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
    homes = state.setdefault("home", {})
    for old in [key for key in homes if key not in alive]:
        del homes[old]  # the project of a session is kept as long as its days are
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


def read_lines(path):
    """The `- ` lines of a findings file; agents may write it with a BOM or a non-UTF-8 code page."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    return [line for line in text.splitlines() if line.startswith("- ")]


def quiet_scan(days):
    """The full scan of today when none ran, with no output."""
    if load_state(retro_dir())["last_scan"] != today():
        with open(os.devnull, "w", encoding="utf-8") as quiet:
            scan(days=days, out=quiet)


def critical(days=1, out=None):
    """Print the critical token problems of today and the days before it not shown yet, or grown since shown."""
    out = out or sys.stdout
    folder = retro_dir()
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


def project_for(directory):
    """The retro project of a folder (default the current one), or None.

    A bare name with no path part (`ClaudeDevKit`) is first looked up among the known retro projects by the repository
    folder name of their recorded main checkout, ignoring case; no such project, it is a folder name as any other."""
    mapper = Mapper()
    name = str(directory or "")
    if name and name not in (".", "..") and not any(char in name for char in "/\\:"):
        known = known_roots().get(name.lower())
        if known:
            return mapper.project_of_cwd(known[1])
    return mapper.project_of_cwd(str(Path(directory or Path.cwd()).resolve()))


def project_folder(project):
    return retro_dir() / project.folder


def no_project(directory, err=None):
    print(f"no retro project at {Path(directory or Path.cwd()).resolve()}: its main checkout needs a "
          f"`{PROFILE_LINE}` line in .claude/dev-kit.md", file=err or sys.stderr)
    return 2


def state_busy():
    print("the project state is locked by another command; run this again", file=sys.stderr)
    return 1


def read_item(path):
    """`(status, kind, sightings, fix lines)` of one item file."""
    status = kind = "?"
    sightings = 0
    fixes = []
    for line in read_lines(path):
        if line.startswith("- status:"):
            status = line[len("- status:"):].strip() or "?"
        elif line.startswith("- kind:"):
            kind = line[len("- kind:"):].strip() or "?"
        elif line.startswith("- seen:"):
            sightings += 1
        elif FIX_LINE.match(line):
            fixes.append(line)
    return status, kind, sightings, fixes


def trivial_fixes(fixes, now=None):
    """How many `- fix: <date> | ... | trivial` lines are dated in the last 7 days, today included."""
    today_date = (now or datetime.datetime.now()).date()
    count = 0
    for line in fixes:
        try:
            stamp = datetime.date.fromisoformat(FIX_LINE.match(line).group(1))
        except ValueError:  # a date like 2026-13-45
            continue
        count += (today_date - stamp).days < 7
    return count


def items(directory=None, out=None):
    """Print the project's new findings and items, and record which `new/` files were shown (see the module doc)."""
    out = out or sys.stdout
    project = project_for(directory)
    if not project:
        return no_project(directory)
    folder = project_folder(project)
    with project_lock(folder) as held:
        if not held:
            return state_busy()
        files = sorted((folder / "new").glob("*.md")) if (folder / "new").is_dir() else []
        lines = [line for path in files for line in read_lines(path)]
        state = load_project(folder)
        state["shown"] = [path.name for path in files]
        save_project(folder, state)
    urgent = [line for line in lines if URGENT_LINE.search(line)]
    print(folder, file=out)
    reviewed = parse_time(state.get("last_review", ""))
    print("last review: " + (reviewed.astimezone().strftime("%Y-%m-%d %H:%M") if reviewed else "never"), file=out)
    print("\n## Priority: token problems (read first; the retro asks them before the rest)", file=out)
    print("\n".join(urgent) or "(none)", file=out)
    print("\n## New findings", file=out)
    print("\n".join(line for line in lines if line not in urgent) or "(none)", file=out)
    print("\n## Items", file=out)
    fixes = []
    rows = []
    for path in sorted((folder / "items").glob("*.md")) if (folder / "items").is_dir() else []:
        status, kind, sightings, found = read_item(path)
        fixes += found
        rows.append(f"{path.stem} | {status} | {kind} | sightings {sightings}")
    print("\n".join(rows) or "(none)", file=out)
    print(f"\ntrivial fixes in the last 7 days: {trivial_fixes(fixes)} of {FIXES_PER_WEEK}", file=out)
    print("\n## Docs items", file=out)
    print("\n".join(f"{path.stem} | {read_item(path)[0]}" for path in docs_items(folder)) or "(none)", file=out)
    return 0


def docs_items(folder):
    docs = folder / "docs-items"
    return sorted(docs.glob("*.md")) if docs.is_dir() else []


def done(directory=None, out=None, branch=None):
    """Move the `new/` files the last `items` showed to `seen/`, stamp `last_review` and `retro_branch`, drop old files
    of `seen/`."""
    out = out or sys.stdout
    project = project_for(directory)
    if not project:
        return no_project(directory)
    folder = project_folder(project)
    seen = folder / "seen"
    moved = 0
    with project_lock(folder) as held:
        if not held:
            return state_busy()
        state = load_project(folder)
        for name in state.pop("shown", None) or []:
            source = folder / "new" / Path(str(name)).name
            if not source.is_file():
                continue
            seen.mkdir(parents=True, exist_ok=True)
            target = seen / source.name
            while target.exists():
                target = seen / f"{source.stem}-{secrets.token_hex(3)}{source.suffix}"
            os.replace(source, target)
            os.utime(target)  # the age counts from the review, not from the finding
            moved += 1
        state["last_review"] = now_utc().isoformat()
        if branch:
            state["retro_branch"] = branch
        else:
            state.pop("retro_branch", None)
        save_project(folder, state)
    limit = time.time() - SEEN_DAYS * 86400
    for old in seen.iterdir() if seen.is_dir() else []:
        with contextlib.suppress(OSError):
            if old.is_file() and old.stat().st_mtime < limit:
                old.unlink()
    print(f"marked reviewed: {moved} file(s) moved to seen", file=out)
    return 0


def docs_done(directory=None, out=None):
    """Stamp the end of the weekly docs session (`docs_done`)."""
    out = out or sys.stdout
    project = project_for(directory)
    if not project:
        return no_project(directory)
    folder = project_folder(project)
    with project_lock(folder) as held:
        if not held:
            return state_busy()
        state = load_project(folder)
        state["docs_done"] = now_utc().isoformat()
        save_project(folder, state)
    print("docs run stamped", file=out)
    return 0


def add(text, sender=None, directory=None, out=None):
    """Add one finding line to the project's `new/` as a file of its own."""
    out = out or sys.stdout
    project = project_for(directory)
    if not project:
        return no_project(directory)
    if not sender:
        origin = Mapper().root_of(str(Path.cwd().resolve()))
        sender = origin.name
    stamp = datetime.datetime.now()
    line = f"- {stamp.date().isoformat()} | from {sender} | {' '.join(str(text).split())}"
    name = f"add-{stamp.date().isoformat()}-{stamp.strftime('%H%M%S')}-{secrets.token_hex(3)}.md"
    path = write_new(project.folder, name, [line])
    print(f"added to {path}", file=out)
    return 0


def due_line(directory=None, session_id=None):
    """The `retro: ...` line the lead sees, or "" (see the module doc)."""
    project = project_for(directory)
    if not project:
        return ""
    folder = retro_dir(create=False) / project.folder
    state = load_project(folder)
    if session_id is not None and (not session_id or state.get("lead_session") != session_id):
        return ""
    urgent = other = 0
    for path in sorted((folder / "items").glob("*.md")) if (folder / "items").is_dir() else []:
        status = read_item(path)[0].lower()
        urgent += status == "urgent"
        other += status in ("disputed", "trivial-fixed")
    other += sum(read_item(path)[0].lower() == "owner" for path in docs_items(folder))
    last_ask = parse_time(state.get("asked_at", ""))
    waited = (now_utc() - last_ask) if last_ask else None
    weekly = bool(other) and (waited is None or waited >= datetime.timedelta(days=7)
                              or (state.get("answer") == "no" and waited >= datetime.timedelta(days=1)))
    if not urgent and not weekly:
        return ""
    return f"retro: {urgent + (other if weekly else 0)} items due ({urgent} urgent)"


def due(session_id=None, directory=None, out=None):
    line = due_line(directory, session_id)
    if line:
        print(line, file=out or sys.stdout)
    return 0


def asked(answer, directory=None, out=None):
    """Stamp the weekly question to the owner and his answer in the project state."""
    out = out or sys.stdout
    project = project_for(directory)
    if not project:
        return no_project(directory)
    folder = project_folder(project)
    with project_lock(folder) as held:
        if not held:
            return state_busy()
        state = load_project(folder)
        state["asked_at"] = now_utc().isoformat()
        state["answer"] = answer
        save_project(folder, state)
    print(f"asked stamped: {answer}", file=out)
    return 0


def spawn(argv, cwd=None):
    """Start a command detached from this process (no window, no console, outlives the caller)."""
    options = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL,
               "close_fds": True, "cwd": cwd}
    if not WINDOWS:
        subprocess.Popen(argv, start_new_session=True, **options)
        return
    # Not DETACHED_PROCESS: with it CREATE_NO_WINDOW is ignored and every console child (git) opens a window. The
    # breakaway lets the child outlive the session's job object; a job that forbids it makes Popen raise: retry without.
    flags = CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen(argv, creationflags=flags | CREATE_BREAKAWAY_FROM_JOB, **options)
    except OSError:
        subprocess.Popen(argv, creationflags=flags, **options)


def script_command(*args):
    return [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), *args]


def hook_end(payload):
    """SessionEnd: scan the ending session's transcript when its project is a retro project."""
    transcript = payload.get("transcript_path")
    if not isinstance(transcript, str) or not transcript or not Path(transcript).is_file():
        return
    if Mapper().project_of_cwd(payload.get("cwd")):
        spawn(script_command("scan", "--transcript", transcript))


def hook_start(payload):
    """SessionStart in a retro project: record the lead, start the daily scan and the retro session (module doc)."""
    project = Mapper().project_of_cwd(payload.get("cwd"))
    title = str(payload.get("session_title") or "").strip()
    if not project or title.startswith((RETRO_TITLE, DOCS_TITLE)):
        return
    folder = project_folder(project)
    retro = retro_dir()
    if load_state(retro)["last_scan"] != today() and lock_free(retro):
        spawn(script_command("scan"))
    command = None
    with project_lock(folder) as held:  # two sessions starting at once must not both start a retro session
        if not held:
            return
        state = load_project(folder)
        state["root"] = str(project.root)
        session_id = payload.get("session_id")
        if title.startswith("P: ") and isinstance(session_id, str) and session_id:
            state["lead_session"] = session_id
        save_project(folder, state)
        command = retro_start_command(project, folder, state) or docs_start_command(project, folder, state)
    if command:
        spawn(command, cwd=str(project.root))


def retro_start_command(project, folder, state):
    """The command that starts the retro session when findings wait, the review is old and no start is recent; it
    stamps `retro_started` (the caller holds the project lock). None otherwise, and with env DEV_KIT_RETRO_NO_START=1."""
    new = folder / "new"
    if not (new.is_dir() and any(new.iterdir())):
        return None
    docs_started, docs_done = parse_time(state.get("docs_started", "")), parse_time(state.get("docs_done", ""))
    if docs_started and not older(state, "docs_started", START_GUARD_HOURS) and (not docs_done or
                                                                                 docs_started > docs_done):
        return None  # the docs session may still run: never both at once
    for key, hours in {"last_review": REVIEW_HOURS, "retro_started": START_GUARD_HOURS}.items():
        stamp = parse_time(state.get(key, ""))
        if stamp and now_utc() - stamp < datetime.timedelta(hours=hours):
            return None
    import sessions  # late: only this hook needs it
    claude = sessions.find_claude()
    if not claude:
        return None
    state["retro_started"] = now_utc().isoformat()
    save_project(folder, state)
    if os.environ.get(NO_START_ENV) == "1":
        return None
    return [claude, "--bg", "--name", f"{RETRO_TITLE} {project.name}", "--model", "opus", "--effort", "medium",
            "--permission-mode", "bypassPermissions", "--", "/dev-kit:retro"]


def older(state, key, hours):
    """True when the stamp `key` is missing or at least `hours` old."""
    stamp = parse_time(state.get(key, ""))
    return not stamp or now_utc() - stamp >= datetime.timedelta(hours=hours)


def git_ok(root, *args):
    """True when the git command exits 0; False on any other exit or failure."""
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, timeout=GIT_TIMEOUT_S,
                              creationflags=CREATE_NO_WINDOW if WINDOWS else 0).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def merged(root, branch):
    """True when `branch` is merged into the main checkout's HEAD or no longer exists (deleted after its merge). A
    git failure reads as gone; the docs session then starts at once, as it would after DOCS_MERGE_WAIT_HOURS."""
    ref = f"refs/heads/{branch}"
    return not git_ok(root, "rev-parse", "--verify", "--quiet", ref) or git_ok(root, "merge-base", "--is-ancestor",
                                                                                ref, "HEAD")


def docs_start_command(project, folder, state):
    """The command that starts the weekly docs session when it is due (module doc, `hook-start`); it stamps
    `docs_started` (the caller holds the project lock). None otherwise, and with env DEV_KIT_RETRO_NO_START=1."""
    if not older(state, "docs_done", DOCS_DAYS * 24) or not older(state, "docs_started", DOCS_GUARD_HOURS):
        return None
    started, reviewed = parse_time(state.get("retro_started", "")), parse_time(state.get("last_review", ""))
    if started and not older(state, "retro_started", START_GUARD_HOURS) and (not reviewed or started > reviewed):
        return None  # the retro session may still run: its fixes come first
    branch = state.get("retro_branch")
    if branch and not older(state, "last_review", DOCS_MERGE_WAIT_HOURS) and not merged(project.root, branch):
        return None  # the retro's fixes are not on main yet
    import sessions  # late: only this hook needs it
    claude = sessions.find_claude()
    if not claude:
        return None
    state["docs_started"] = now_utc().isoformat()
    save_project(folder, state)
    if os.environ.get(NO_START_ENV) == "1":
        return None
    return [claude, "--bg", "--name", f"{DOCS_TITLE} {project.name}", "--model", "opus", "--effort", "medium",
            "--permission-mode", "bypassPermissions", "--", "/dev-kit:maintain-project-docs weekly"]


def hook_main(kind):
    """Run a hook from the JSON on stdin; never fails and prints nothing."""
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if isinstance(payload, dict):
            (hook_start if kind == "start" else hook_end)(payload)
    except Exception:  # a hook must never block a session
        pass
    return 0


def usage_messages(path):
    """`(time, message id, units)` of every assistant message with usage in a transcript, in file order.

    Lines without usage are skipped before parsing, so a week of transcripts reads fast."""
    try:
        with open(path, "rb") as handle:
            for raw in handle:
                if b'"usage"' not in raw or b'"assistant"' not in raw:
                    continue
                try:
                    entry = json.loads(raw)
                except ValueError:
                    continue
                message = entry.get("message") if isinstance(entry, dict) else None
                if entry.get("type") != "assistant" or not isinstance(message, dict):
                    continue
                usage, model = message.get("usage"), message.get("model")
                if isinstance(usage, dict) and model != "<synthetic>":
                    yield parse_time(entry.get("timestamp")), message.get("id"), units_of(usage, model)
    except OSError:
        return


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
    folder = retro_dir()
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
    seen = set()

    def total(files):
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

    main_units, _ = total(mains)
    sub_units, runs = 0.0, 0
    if subagents:
        subs = sorted({file for main in mains for file in (main.with_suffix("") / "subagents").rglob("*.jsonl")})
        sub_units, runs = total(subs)
    limit, date = weekly_limit()
    both = main_units + sub_units
    print(f"{share_text(percent(both, limit))} of the weekly limit, estimate", file=out)
    parts = [f"main {share_text(percent(main_units, limit), False)}"]
    if subagents:
        parts.append(f"subagents {share_text(percent(sub_units, limit), False)} ({runs} run{'' if runs == 1 else 's'})")
    print(f"{', '.join(parts)}; {amount(both)} units; limit {limit / 1e6:.0f}M units (fit {date})", file=out)
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # transcripts hold any language; a Windows console code page cannot
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="dev-kit-retro")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("scan", "critical"):
        command = sub.add_parser(name)
        command.add_argument("--days", type=float, default=1)
        if name == "scan":
            command.add_argument("--force", action="store_true")
            command.add_argument("--transcript")
    for name in ("items", "done", "docs-done", "due", "asked", "add"):
        command = sub.add_parser(name)
        command.add_argument("--project", help="any folder of the project (default: the current folder)")
        if name == "due":
            command.add_argument("--session")
        if name == "done":
            command.add_argument("--branch")
        if name == "asked":
            command.add_argument("--answer", choices=("yes", "no"), required=True)
        if name == "add":
            command.add_argument("--text", required=True)
            command.add_argument("--from", dest="sender")
    sub.add_parser("hook-start")
    sub.add_parser("hook-end")
    sub.add_parser("calibrate")
    one = sub.add_parser("session")
    which = one.add_mutually_exclusive_group()
    which.add_argument("--id")
    which.add_argument("--path")
    one.add_argument("--no-subagents", action="store_true")
    args = parser.parse_args(argv)
    if args.command in ("hook-start", "hook-end"):
        return hook_main(args.command[len("hook-"):])
    if args.command == "calibrate":
        return calibrate()
    if args.command == "session":
        return session(args.id, args.path, not args.no_subagents)
    if args.command == "critical":
        return critical(days=args.days)
    if args.command == "scan":
        return scan(days=args.days, force=args.force, transcript=args.transcript)
    if args.command == "items":
        return items(args.project)
    if args.command == "due":
        return due(args.session, args.project)
    if args.command == "asked":
        return asked(args.answer, args.project)
    if args.command == "add":
        return add(args.text, args.sender, args.project)
    if args.command == "docs-done":
        return docs_done(args.project)
    return done(args.project, branch=args.branch)


if __name__ == "__main__":
    sys.exit(main())
