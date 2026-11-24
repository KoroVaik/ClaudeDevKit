"""Find problems in the sessions' transcripts with no model, sort them into one folder per project, and serve the
retro session and the lead of each project. A model reads the findings; this script uses none.

    rules-kit scan [--force] [--days N]           the full scan of every transcript (once a day without --force)
    rules-kit scan --transcript PATH              only that transcript and its subagents
    rules-kit items [--project DIR]               the new findings and the items of the project, see below
    rules-kit done [--branch NAME] [--project DIR]
                                                  move the findings the last `items` showed to `seen/`; NAME: the
                                                  branch the retro session left for its lead to merge
    rules-kit add --text LINE [--from NAME] [--project DIR]
                                                  add a finding to the project's `new/` (any session, any project)
    rules-kit due [--session ID] [--project DIR]  one line when the lead has retro items to act on, else nothing
    rules-kit asked --answer yes|no [--project DIR]
                                                  stamp the weekly question to the owner and the answer
    rules-kit hook-start | hook-end               SessionStart and SessionEnd hooks of the plugin (JSON on stdin)

Token spend (units, the weekly limit, `critical`, per-session spend) is not counted here: it belongs to the spend-kit
plugin (`spend-kit session | critical | calibrate`, plugins/spend-kit/scripts/spend.py). The scan runs the command
`spend-kit findings` (a process, no import) and takes its token findings and `## Spend` table; with spend-kit not
installed there are none. The weekly docs session (`Документація:`) is dev-kit's (`plugins/dev-kit/scripts/docs_weekly.py`);
this plugin only writes the run file it waits for (see "Run file").

`--project DIR` is any folder of the project (a worktree too; default the current folder), or a bare repository folder
name of a known retro project (`ClaudeDevKit`, ignoring case; known = it has an item folder whose `state.json` records
its `root`, so another project's retro can write `add --project ClaudeDevKit ...`); a bare name that is no known
project is taken as a folder. A project that is not a retro project gets exit code 2 (`due` and the hooks stay silent
instead); when the project's `state.json` stays locked (see Lock), `items`, `done` and `asked` exit 1 and change
nothing.

Retro projects: a project counts when its main checkout (the parent of the git common dir) has `.claude/dev-kit.md`
with a line `## project-lead`. A transcript belongs to the project of the `cwd` of its lines (git, cached per cwd; when
git fails, a deleted worktree, the path is cut at `/.claude/worktrees/` and the part before it is the checkout).
Only the findings of retro projects are routed: the findings of other projects (the home folder, Pult, a project with
no lead) stay in `scan-<date>.md` only. A token finding from spend-kit names the `cwd` of its session and is routed
by it the same way. One exception: the `claude app` findings (see Kinds) of every transcript, a
project with no lead, Pult and the home folder included, go to the retro project named `ClaudeDevKit` (found by its
repository folder name among the known retro projects and this scan's projects, never by the place of this script) and
not to the project of their transcript; with no such project they stay in the log. The findings of a session whose title starts with `Ретро:` (a retro session)
or `Документація:` (the weekly docs session) and of its subagents are dropped everywhere (log included), so the retro
never feeds on these hook-started sessions; their token spend still counts in spend-kit.

Folders: the retro folder is env RULES_KIT_DIR, else `~/.claude/rules-kit` (local, outside any repository; the retro
used `~/.claude/dev-kit/retro` before, which `scripts/rules_dir.py` copies here once on the first run and leaves as it
is). It holds the global `state.json` (byte offsets, `claude_version`: the
highest Claude Code version seen in the transcripts, a string like `2.1.330`; `facts_recheck`: the day of the
last weekly facts re-check line; the token keys an older version kept there, `daily`, `fit` and the like, are
left alone: spend-kit copied them once), `scan.lock`, the human
log `scan-<date>.md` (all findings of a full scan and the `## Spend` tables) and the owner's `notes.md`. Each project
has `<retro folder>/<repo-folder-name>-<10 hex>/` (`folder_naming.folder_name`, the name of its state folder) with:
- `new/`: findings no review has seen, one file per writer and run, never shared: `scan-<date>-<HHMMSS>.md` (full
  scan), `<date>-<session id8>-<HHMMSS>.md` (one transcript), `notes-<date>-<HHMMSS>.md` (owner notes), `add-...md`
  (`add`); each finding is a line starting `- `;
- `seen/`: files moved there by `done`, deleted after SEEN_DAYS days;
- `items/<cause-key>.md`: one file per item, written by the retro session; lines `- status: <status>`, `- kind:
  <kind>`, one `- seen: ...` line per sighting and `- fix: <YYYY-MM-DD> | <what> | trivial` per trivial fix;
- `state.json`: `root` (the main checkout), `last_review`, `retro_started`, `retro_branch`, `lead_session`,
  `asked_at`, `answer`, `shown` (the `new/` files the last `items` showed). Written atomically (temp file and replace).
Transcripts: every `*.jsonl` under env DEV_KIT_PROJECTS_DIR, else `~/.claude/projects`, subagent ones in
`<session>/subagents/` included.

Run file: `<retro folder>/runs/<project folder name>.json`, written (atomically, under the project lock) at each
`hook-start` of the project and by `done`: `{"root": <main checkout>, "retro_started": <ISO time or null>,
"last_review": <ISO time or null>, "retro_branch": <branch the retro left for its lead to merge or null>, "retro_due":
<true when findings wait in `new/` and the last review is REVIEW_HOURS old or missing>}`. dev-kit's weekly docs session
start reads it as a file (never an import) to wait for the retro and for the merge of its branch; whether the branch
is merged it asks git itself. The other way, `hook-start` reads dev-kit's `<state root>/<project folder name>/docs.json`
(`docs_started`, `docs_done`; env DEV_KIT_STATE_DIR, else `~/.claude/dev-kit`) as a file to start no retro session
while a docs session may still run.

Locks (lock files made with O_EXCL; a lock older than its limit is taken over): the global `state.json` is read,
changed and written only while `scan.lock` exists (stale after LOCK_STALE_S). A transcript scan waits up to
LOCK_WAIT_TRANSCRIPT_S for it and then exits 0 with no output (its lines are read by the next full scan); a full scan
waits up to LOCK_WAIT_FULL_S. A project's `state.json` is read, changed and written only
while `state.lock` exists in its item folder (stale after PROJECT_LOCK_STALE_S, wait up to PROJECT_LOCK_WAIT_S): the
stamps of `hook-start`, `items`, `done`, `asked` and the scan's `root` record. `hook-start` that cannot get it starts
nothing, so two sessions starting at once never both start a retro session.

`scan` reads only what was appended to each transcript since the last scan (`state.json` keeps a byte offset per
file, up to the last complete line). On the first full scan (no full scan yet) a file last changed before `--days`
days ago (default 1) that has no offset is skipped and its offset set to its size, so it does not read the whole
history. A full scan writes `scan-<YYYY-MM-DD>.md` (local date; a second scan the same day with `--force` appends to
it), one line per finding, and each line also goes to the `new/` of its project (token lines from spend-kit too):

    - <project folder> | <session title (first 8 of its id)> or <session id>[ / subagent <type>] | <kind> | <detail>

A full scan also reads the new lines of `<retro folder>/notes.md` (offset kept in the global state) and puts each into
the `new/` of the retro project whose repository folder name equals the line's project field, ignoring case; other
lines are dropped. `script candidate` lines go to the project when all their sessions are of one project, else to the
project of the repository that holds this plugin (when it is a retro project).
`scan --transcript PATH` is for the SessionEnd hook: only that transcript and its `<id>/subagents/*.jsonl`, the same
per-transcript kinds (and spend-kit's token findings of that transcript), no cross-transcript kinds, no
priority lines, no notes; its findings go to one `new/<date>-<id8>-<HHMMSS>.md` and are appended to `scan-<date>.md`;
nothing found, no file.

`items` prints: the folder path; `last review: <local date and time of last_review, or never>`; `claude code:
<claude_version>` when the global state has it; the new findings of
`new/` (token problems first, under "Priority"); one line per
`items/*.md` file `<cause-key> | <status> | <kind> | sightings <N>` (N = the lines starting `- seen:`); and `trivial
fixes in the last 7 days: <N> of FIXES_PER_WEEK` (the `- fix:` lines marked trivial and dated in the last 7 days, today
included). It records the `new/` file names it showed;
`done` moves exactly those to `seen/`, sets `last_review`, records `retro_branch` (`--branch`, else none) and deletes
what is older than SEEN_DAYS in `seen/`. Findings that came after `items` stay new.
`due` prints nothing unless the session (when `--session` is given) is the lead recorded by `hook-start`; then
`retro: <N> items due (<U> urgent)` when an item has status `urgent`, or when items with status `disputed` or
`trivial-fixed` exist and the last weekly ask is 7+ days old or missing, or 1+ day old after the answer `no` (N counts
the urgent items, and the others when the weekly ask is due).
`hook-start` (never fails, exit 0): in a retro project, a session titled `Ретро:` or `Документація:` does nothing; a
full scan is spawned
(detached) when none ran today and the scan lock is free; then, under the project lock, a title `P: ` records the
lead's session id, and when `new/` has files, `last_review` is older than REVIEW_HOURS (or missing),
`retro_started` older than START_GUARD_HOURS (or missing) and no docs session may still run (see "Run file"), it
stamps `retro_started` and starts a background `Ретро: <repo folder>` session running `/rules-kit:retro` (env RULES_KIT_NO_START=1 skips that
start, not the stamp). The session starts with the `--settings` file NO_REMOTE_CONTROL (no Remote Control, so it stays
out of the app). The weekly docs session is not started here any more: dev-kit's own SessionStart hook starts it.
`hook-end` in a retro project spawns (detached) `scan --transcript` of the ending session when its transcript
exists. Detached start: on Windows CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB (not
DETACHED_PROCESS, which makes the console children, git, open windows); when the session's job forbids the breakaway
(Popen raises OSError) it is started again without it. Elsewhere `start_new_session`.

Kinds, per transcript and per scan window (each subagent run, its own file, counts alone, never summed with another run
of its type; thresholds below):
- `repeated call`: the same tool with the same input, REPEAT_MIN or more times (`run_in_background` calls left out:
  a watcher a lead on dev-kit before 0.1.78 re-arms after each exit is by design);
- `failed calls`: ERRORS_MIN or more tool results marked as an error;
- `many calls`: MANY_CALLS or more tool calls;
- `slow call`: a tool result that came SLOW_CALL_MIN or more minutes after its call (tools that wait on the owner
  by design, WAITING_TOOLS, are left out);
- `long pause`: SLOW_MODEL_MIN or more minutes between a tool result and the next assistant message;
- `claude app`: the Claude app itself failed a call, found by the tool's name, never by text (the same words stand in
  docs and plans): a `SendMessage` result whose JSON text has `"success": false` (not marked as an error: no such
  agent, a session not active, not delivered) or an error result of `Agent` or a session start tool
  (APP_START_TOOLS: a subagent limit, an unknown agent type, a refused folder). No threshold; ids are replaced
  (`cse_<id>`) and one line per distinct tool and text with `x<count>` when repeated, detail `<tool>[ x<N>]: <text>`.
  Results with APP_SKIP (`Re-send with the ref`, a one-time confirm, a hook error: normal flow or the project's own
  hook) are left out; lines older than the previous scan (a resumed session copies them) are not counted. Routed to
  ClaudeDevKit (see above). The full scan also reads `version` of every line (the highest of the scan, before
  anything else is read) and, when it is higher than `claude_version` of the global state, stores it and adds
  `- ClaudeDevKit | - | claude app | updated <old> -> <new>` (the first run stores it with no line);
  once in 7 days (global state `facts_recheck`, the day of the last one) it also adds
  `- ClaudeDevKit | - | claude app | weekly re-check due`, so the ClaudeDevKit retro starts and re-checks the facts;
and across transcripts:
- `script candidate`: the same Bash command of SCRIPT_MIN_CHARS or more in SCRIPT_SESSIONS or more sessions (subagents
  count with their session).
The plugin's own commands (containing OWN_COMMAND) count for neither repeats nor script candidates: rules run them.

Token findings (owner, 2026-11-20, docs/features/fix-agent-problems-in-the-retro.md): `long session`, `opus coder`,
`token spend` and `token waste` come from spend-kit (`spend-kit findings`, its module doc, "Findings", holds the
units, the waste kinds, the thresholds and the line formats). Each line is routed like the other findings (a
`Ретро:` or `Документація:` session's lines are dropped); `token ...` lines are the "Priority" part of `items`. The
scan file also gets spend-kit's `## Spend` section of `| `-table lines (not findings; they stay in the scan files
only).

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
import claude_path  # noqa: E402  the `claude` command (a copy of dev-kit's, no plugin imports another's code)
import folder_naming  # noqa: E402  the project's folder name and main checkout (a copy of dev-kit's `dev_kit_state`)
import rules_dir  # noqa: E402  the data folder and the one-time copy from dev-kit's retro folder
import spend_client  # noqa: E402  runs the `spend-kit` command (token spend), no import of its code

RETRO_ENV = rules_dir.DIR_ENV
PROJECTS_ENV = "DEV_KIT_PROJECTS_DIR"
NO_START_ENV = "RULES_KIT_NO_START"  # 1: the SessionStart hook does not start the retro session (tests)
STATE_ENV = "DEV_KIT_STATE_DIR"  # dev-kit's state root (the same env as its `dev_kit_state.py`), read for `docs.json`
RUNS_FOLDER = "runs"  # in the retro folder: the run file of each project (see the module doc)
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
RETRO_TITLE = "Ретро:"  # the title of a retro session (dev-kit's sessions.RETRO_PREFIX is this plus a space)
DOCS_TITLE = "Документація:"  # the title of the weekly docs session of dev-kit (its findings are dropped too)
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
OWN_COMMAND = ("dev-kit-", "rules-kit", "spend-kit")  # the plugins' own commands, run by rules at fixed moments (P's checks)
SCRIPT_MIN_CHARS = 30  # shorter Bash commands (git status, ls) are not worth a script
DETAIL_CHARS = 160
CLAUDE_APP_KIND = "claude app"  # a finding about the Claude app itself, not about the session: routed to DEVKIT_NAME
DEVKIT_NAME = "claudedevkit"  # the retro project (lower-case repository folder name) that gets every `claude app` line
APP_SEND_TOOLS = {"SendMessage"}  # a failure is a JSON result with "success": false, not marked as an error
APP_START_TOOLS = {"Agent", "mcp__ccd_session__start_session", "mcp__ccd_session__hand_off_to_session",
                   "mcp__ccd_session__spawn_task", "mcp__ccd_session__move_to_cloud"}  # a refusal is an error result
APP_SKIP = re.compile(r"Re-send with the ref|needs a one-time confirm|hook error")  # normal flow, the project's own hook
APP_IDS = ((re.compile(r"\b(cse|local)_[\w-]+"), r"\1_<id>"), (re.compile(r"cc-msg-\w+"), "cc-msg-<id>"),
           (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE), "<id>"))
# ids and hashes of a failure text, replaced so that the same failure of two sessions or two calls is one line
SPEND_TIMEOUT_FULL_S = 300  # the `spend-kit findings` call of a full scan (it may read a week of transcripts)
SPEND_TIMEOUT_TRANSCRIPT_S = 60  # the same for the one-transcript scan of the SessionEnd hook


def retro_dir(create=True):
    """The retro folder (module doc); with `create` it exists and holds the copy of dev-kit's old retro folder."""
    folder = rules_dir.data_dir()
    if create:
        folder.mkdir(parents=True, exist_ok=True)
        rules_dir.migrate(folder)
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
            root = folder_naming.main_checkout(cwd)
            if root is None:
                base = WORKTREES.split(cwd, maxsplit=1)[0]
                root = folder_naming.main_checkout(base) or Path(base)
            self.roots[cwd] = root
        return self.roots[cwd]

    def project_of_cwd(self, cwd):
        """The retro project of a folder, or None."""
        if not isinstance(cwd, str) or not cwd.strip():
            return None
        root = self.root_of(cwd)
        key = str(root)
        if key not in self.projects:
            self.projects[key] = (Project(root, root.name, folder_naming.folder_name(root))
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


def result_text(block):
    """The text of a tool result block (a string, or a list of text blocks)."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(part.get("text") or "") for part in content
                         if isinstance(part, dict) and part.get("type") == "text")
    return ""


def app_error(name, block):
    """The text of a failure of the Claude app in a tool result (see `claude app` in the module doc), with its ids
    replaced and cut to DETAIL_CHARS; None for any other result. Matched by the tool's name, never by the text: the same
    words stand in docs, plans and the output of other tools."""
    if name in APP_SEND_TOOLS:
        try:
            data = json.loads(result_text(block))
        except ValueError:
            return None
        if not isinstance(data, dict) or data.get("success") is not False:
            return None
        text = data.get("message") or data.get("display")
    elif name in APP_START_TOOLS and block.get("is_error"):
        text = result_text(block)
    else:
        return None
    text = " ".join(re.sub(r"</?tool_use_error>", "", str(text or "")).split())
    if APP_SKIP.search(text):
        return None
    for pattern, replacement in APP_IDS:
        text = pattern.sub(replacement, text)
    return short(text or "(no text)")


def version_of(value):
    """A Claude Code version string like `2.1.330` as a tuple of numbers, or None."""
    try:
        return tuple(int(part) for part in value.split("."))
    except (AttributeError, ValueError):
        return None


def analyse(lines, since=None):
    """Counters of one transcript window: calls, repeats, errors, slow calls, pauses, Bash commands, title,
    app failures (`app`) and the highest Claude Code version of its lines (`version`). Token units are not counted
    here (spend-kit reads the transcripts for them); lines dated before `since` are not counted."""
    calls = {}
    repeats = Counter()
    first_input = {}
    errors = 0
    error_tools = Counter()
    slow = []
    pauses = []
    bash = set()
    app = Counter()  # (tool, failure text) -> times
    version = None
    title = ""
    last_result_time = None
    for raw in lines:
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        found_version = version_of(entry.get("version"))
        if found_version and (version is None or found_version > version):
            version = found_version  # the highest, never the last: a resumed session copies lines of older versions
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
                own = name == "Bash" and isinstance(tool_input, dict) and any(
                    own_command in str(tool_input.get("command")) for own_command in OWN_COMMAND)
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
                text = app_error(name, block) if fresh else None  # a resumed session copies old lines: not again
                if text:
                    app[(name, text)] += 1
                if called and stamp and name not in WAITING_TOOLS:
                    minutes = (stamp - called).total_seconds() / 60
                    if minutes >= SLOW_CALL_MIN:
                        slow.append((name, minutes))
            last_result_time = stamp if got_result else None
    return {
        "title": title, "calls": len(calls), "repeats": repeats, "first_input": first_input, "errors": errors,
        "error_tools": error_tools, "slow": slow, "pauses": pauses, "bash": bash, "app": app, "version": version,
    }


def merge(a, b):
    """The counters of two windows of one label added together."""
    return {
        "title": b["title"] or a["title"], "calls": a["calls"] + b["calls"], "repeats": a["repeats"] + b["repeats"],
        "first_input": {**b["first_input"], **a["first_input"]}, "errors": a["errors"] + b["errors"],
        "error_tools": a["error_tools"] + b["error_tools"], "slow": a["slow"] + b["slow"],
        "pauses": a["pauses"] + b["pauses"], "bash": a["bash"] | b["bash"],
        "app": a["app"] + b["app"], "version": max(filter(None, (a["version"], b["version"])), default=None),
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
    for (name, text), count in result["app"].most_common():  # no threshold: one failure of the app is a fact
        found.append((CLAUDE_APP_KIND, f"{name}{f' x{count}' if count > 1 else ''}: {text}"))
    return found


def spend_kit_findings(transcript=None):
    """`(findings, table lines)` from the command `spend-kit findings` (a process, never an import): the token findings
    no scan has taken yet, each `{"session", "title", "cwd", "line"}`, and the `## Spend` table of a full scan. Both
    empty when spend-kit is not installed or its command fails (the retro then has no token findings)."""
    args = ["findings"] + (["--transcript", transcript] if transcript else [])
    done = spend_client.run(args, SPEND_TIMEOUT_TRANSCRIPT_S if transcript else SPEND_TIMEOUT_FULL_S)
    if not done or done.returncode != 0:
        return [], []
    try:
        data = json.loads(done.stdout)
    except ValueError:
        return [], []
    found = data.get("findings") if isinstance(data, dict) else None
    table = data.get("table") if isinstance(data, dict) else None
    return ([entry for entry in found if isinstance(entry, dict) and isinstance(entry.get("line"), str)]
            if isinstance(found, list) else []), ([line for line in table if isinstance(line, str)]
                                                   if isinstance(table, list) else [])


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
    first = not state["last_scan"] and not transcript
    cutoff = time.time() - days * 86400
    known = state.setdefault("titles", {})  # a title is written once, often in an earlier scan's lines
    windows = {}  # (project, session, subagent type, run) -> counters; a subagent run (its file) counts alone, never summed
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
        owner = mapper.project_of_transcript(path)  # None: not a retro project; its findings stay in the log only
        lines, state["offsets"][key] = read_new_lines(path, offset)
        if not lines:
            continue
        project, session, sub = session_label(path, root)
        homes[(project, session)] = owner
        result = analyse(lines, since)
        if result["title"] and not sub:
            known[f"{project}/{session}"] = result["title"]
        window = (project, session, sub, path.stem if sub else "")  # the same file in a later scan is the same run
        merged = windows.get(window)
        windows[window] = merge(merged, result) if merged else result
    titles = {(project, session): known[f"{project}/{session}"] for project, session, _, _ in windows
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

    devkit = project_folders(mapper).get(DEVKIT_NAME)  # None: ClaudeDevKit is not a known project, the log only

    def route_app(line):
        """A `claude app` line to the scan log and to ClaudeDevKit, whatever project its transcript belongs to."""
        out_lines.append(line)
        if devkit:
            routed[devkit].append(line)

    for (project, session, sub, _), result in windows.items():
        if retro_session(project, session):
            continue
        label = f"{titles[(project, session)]} ({session[:8]})" if (project, session) in titles else session
        if sub:
            label += " / " + sub
        for kind, detail in findings_of(result):
            line = f"- {project} | {label} | {kind} | {detail}"
            if kind == CLAUDE_APP_KIND:
                route_app(line)
            else:
                route(project, session, line)
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
    spend_lines, table = spend_kit_findings(transcript)
    for entry in spend_lines:  # the token findings (long session, opus coder, token spend and waste), see spend-kit
        if str(entry.get("title") or "").strip().startswith((RETRO_TITLE, DOCS_TITLE)):
            continue
        out_lines.append(entry["line"])
        owner = mapper.project_of_cwd(entry.get("cwd"))
        if owner:
            routed[owner.folder].append(entry["line"])
    if not transcript:
        newest = max(filter(None, (result["version"] for result in windows.values())), default=None)
        if newest:
            old = state.get("claude_version")
            if version_of(old) is None or newest > version_of(old):
                state["claude_version"] = ".".join(map(str, newest))
                if version_of(old):  # the first run stores the version silently
                    route_app(f"- ClaudeDevKit | - | {CLAUDE_APP_KIND} | updated {old} -> {state['claude_version']}")
        last = state.get("facts_recheck")  # the day the last weekly re-check line was routed
        if devkit and (not last or (datetime.date.fromisoformat(day) - datetime.date.fromisoformat(last)).days >= 7):
            state["facts_recheck"] = day
            route_app(f"- ClaudeDevKit | - | {CLAUDE_APP_KIND} | weekly re-check due")
        sort_notes(state, folder, mapper, plugin, routed)
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


def project_folders(mapper, plugin=None):
    """Retro projects by lower-case repository folder name -> item folder name: the known ones, the ones this scan's
    transcripts belong to and `plugin` (the project that holds this plugin, when given)."""
    projects = known_projects()
    for owner in mapper.projects.values():
        if owner:
            projects.setdefault(owner.name.lower(), owner.folder)
    if plugin:
        projects.setdefault(plugin.name.lower(), plugin.folder)
    return projects


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
    projects = project_folders(mapper, plugin)
    for raw in lines:
        line = raw.decode("utf-8-sig", errors="replace").strip()
        fields = [field.strip() for field in line.split("|")]
        if line.startswith("- ") and len(fields) >= 5 and fields[1].lower() in projects:
            routed[projects[fields[1].lower()]].append(line)


def read_lines(path):
    """The `- ` lines of a findings file; agents may write it with a BOM or a non-UTF-8 code page."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return []
    return [line for line in text.splitlines() if line.startswith("- ")]


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
    version = load_state(retro_dir(create=False)).get("claude_version")  # the global state, read only
    if version:
        print(f"claude code: {version}", file=out)
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
    return 0


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
        write_run_file(project, state)
    limit = time.time() - SEEN_DAYS * 86400
    for old in seen.iterdir() if seen.is_dir() else []:
        with contextlib.suppress(OSError):
            if old.is_file() and old.stat().st_mtime < limit:
                old.unlink()
    print(f"marked reviewed: {moved} file(s) moved to seen", file=out)
    return 0


def older(state, key, hours):
    """True when the stamp `key` is missing or at least `hours` old."""
    stamp = parse_time(state.get(key, ""))
    return not stamp or now_utc() - stamp >= datetime.timedelta(hours=hours)


def retro_due(folder, state):
    """Whether findings wait in `new/` and the last review is at least REVIEW_HOURS old (or none): a retro session is due."""
    new = folder / "new"
    return new.is_dir() and any(new.iterdir()) and older(state, "last_review", REVIEW_HOURS)


def write_run_file(project, state):
    """Write the project's run file from its state (see "Run file" in the module doc); the caller holds the project
    lock. A write failure is ignored: the next start or review writes it again."""
    data = {"root": state.get("root"), "retro_started": state.get("retro_started"),
            "last_review": state.get("last_review"), "retro_branch": state.get("retro_branch"),
            "retro_due": retro_due(project_folder(project), state)}
    with contextlib.suppress(OSError):
        write_json(retro_dir() / RUNS_FOLDER / f"{project.folder}.json", data)


def docs_may_run(project):
    """Whether dev-kit's weekly docs session may still run: its `docs.json` (read as a file, never through an import;
    dev-kit's state folder of the project, env DEV_KIT_STATE_DIR else `~/.claude/dev-kit`) has `docs_started` younger
    than START_GUARD_HOURS and newer than `docs_done`. The retro session never starts beside it."""
    root = Path(os.environ[STATE_ENV]) if os.environ.get(STATE_ENV) else Path.home() / ".claude" / "dev-kit"
    try:
        docs = json.loads((root / project.folder / "docs.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    if not isinstance(docs, dict):
        return False
    started, finished = parse_time(docs.get("docs_started", "")), parse_time(docs.get("docs_done", ""))
    return bool(started and not older(docs, "docs_started", START_GUARD_HOURS) and (not finished or started > finished))


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
        command = retro_start_command(project, folder, state)
        write_run_file(project, state)  # after the stamp: dev-kit's docs session start reads it
    if command:
        spawn(command, cwd=str(project.root))


def retro_start_command(project, folder, state):
    """The command that starts the retro session when findings wait, the review is old and no start is recent; it
    stamps `retro_started` (the caller holds the project lock). None otherwise, and with env RULES_KIT_NO_START=1."""
    if not retro_due(folder, state) or not older(state, "retro_started", START_GUARD_HOURS):
        return None
    if docs_may_run(project):
        return None  # dev-kit's docs session may still run: never both at once
    claude = claude_path.find_claude()
    if not claude:
        return None
    state["retro_started"] = now_utc().isoformat()
    save_project(folder, state)
    if os.environ.get(NO_START_ENV) == "1":
        return None
    return [claude, "--bg", "--name", f"{RETRO_TITLE} {project.name}", "--settings", str(NO_REMOTE_CONTROL),
            "--model", "opus", "--effort", "medium", "--permission-mode", "bypassPermissions", "--", "/rules-kit:retro"]


# A background session the owner need not open starts with no Remote Control, so it stays out of the app: the
# owner's `remoteControlAtStartup` would give it one (plugins/dev-kit/claude-facts.md, "`remoteControlAtStartup: true`
# gives every new session Remote Control, with or without `--remote-control`"). A C, unlike these, keeps the link.
NO_REMOTE_CONTROL = Path(__file__).resolve().parent.parent / "no-remote-control.json"


def hook_main(kind):
    """Run a hook from the JSON on stdin; never fails and prints nothing."""
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if isinstance(payload, dict):
            (hook_start if kind == "start" else hook_end)(payload)
    except Exception:  # a hook must never block a session
        pass
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):  # transcripts hold any language; a Windows console code page cannot
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="rules-kit")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("scan")
    command.add_argument("--days", type=float, default=1)
    command.add_argument("--force", action="store_true")
    command.add_argument("--transcript")
    for name in ("items", "done", "due", "asked", "add"):
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
    args = parser.parse_args(argv)
    if args.command in ("hook-start", "hook-end"):
        return hook_main(args.command[len("hook-"):])
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
    return done(args.project, branch=args.branch)


if __name__ == "__main__":
    sys.exit(main())
