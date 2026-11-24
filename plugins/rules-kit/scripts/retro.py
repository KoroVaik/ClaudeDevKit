"""Find problems in the sessions' transcripts with no model, sort them into one folder per rule set, and serve the
retro session and the lead of each project. A model reads the findings; this script uses none.

A rule set is a group of rule files with one subscription file (`scripts/subscriptions.py`: the plugins, the owner's
global rules and each project's own rules). Findings and items live per set, in `<retro folder>/sets/<set>/`. A
project's retro handles only the sets its project reviews (`reviewed by` in the subscription; a project's own set, the
default one when it has no file, is reviewed by that project).

    rules-kit scan [--force] [--days N]           the full scan of every transcript (once a day without --force)
    rules-kit scan --transcript PATH              only that transcript and its subagents
    rules-kit items [--project DIR]               the new findings and the items of the sets the project reviews
    rules-kit done [--branch NAME] [--project DIR]
                                                  move the findings the last `items` showed to `seen/`; NAME: the
                                                  branch the retro session left for its lead to merge
    rules-kit add --text LINE [--from NAME] [--project DIR | --set NAME] [--packet PATH]
                                                  add a finding to a set's `new/` (any session, any project); with
                                                  --project, to the sets that project reviews which the text names (a
                                                  file, or a skill or agent `plugin:name`; a line that starts
                                                  `claude app` or `owner check`: FACTS_SET), else to its own set; with
                                                  --packet (the part reader's answer on that packet) also a `sign-gap`
                                                  line when none of the set's own signs fired for the part
    rules-kit parts [--session ID] [--since DATE] [--limit N]
                                                  split the transcripts into parts and write a packet per part with a
                                                  sign for the part reader (see "Parts")
    rules-kit sets                                the sets found, their reviewers, and subscription files that fail
    rules-kit replay --item KEY [--set S] [--file PATH ...]
                                                  write the replay packets of an item: its problem parts and up to 5
                                                  good parts (`scripts/fixes.py`, "Replay"); one line per packet
    rules-kit fixed --item KEY --commit HASH [--set S] [--what TEXT] [--sign]
                                                  record a landed fix: `fix:` line with the set, the hash and the
                                                  commit's files, status `fixed`, a done-list line
    rules-kit check [--project DIR]               the post-change check of the fixed items of the sets the project
                                                  reviews: in main since when, and the sessions started after that
    rules-kit revert --item KEY [--set S]         `git revert --no-edit` of the item's last fix in the current folder
                                                  (the global set: its folder); status `reverted`, `parked` the second time
    rules-kit mark --item KEY --status S [--set S] [--note TEXT]
                                                  set a status by hand (`worked`, `second-try`, `parked`, `rejected`...)
    rules-kit revert-request KEY [--set S] [--from NAME]
                                                  the owner's «поверни»: the next run of the reviewing project reverts it
    rules-kit list [--days N]                     the done list, one plain line per action (Pult's «статус»)
    rules-kit budget --session-id ID              the run's spend against the cap: `under`, `over` or `unknown`
    rules-kit hook-start | hook-end               SessionStart and SessionEnd hooks of the plugin (JSON on stdin)

The fix loop's rules (expiry, the weekly cap, replay, the post-change check, reverts, revert requests, the done list
`done.jsonl`, the spend cap) are in `scripts/fixes.py`. These commands exit 2 for an unknown item or set and 1 when
git fails.

Token spend (units, the weekly limit, `critical`, per-session spend) is not counted here: it belongs to the spend-kit
plugin (`spend-kit session | critical | calibrate`, plugins/spend-kit/scripts/spend.py). The scan runs the command
`spend-kit findings` (a process, no import) and takes its token findings and `## Spend` table; with spend-kit not
installed there are none. The weekly docs session (`Документація:`) is dev-kit's (`plugins/dev-kit/scripts/docs_weekly.py`);
this plugin only writes the run file it waits for (see "Run file").

`--project DIR` is any folder of the project (a worktree too; default the current folder), or a bare repository folder
name of a known retro project (`ClaudeDevKit`, ignoring case; known = it has an item folder whose `state.json` records
its `root`, so another project's retro can write `add --project ClaudeDevKit ...`); a bare name that is no known
project is taken as a folder. A project that is not a retro project gets exit code 2 (the hooks stay silent
instead); when the project's `state.json` stays locked (see Lock), `items` and `done` exit 1 and change
nothing.

Parts (`scripts/parts.py`): each transcript window is split into parts by the skill, agent or hook at work. A
`repeated call`, `failed calls` or `hook refusal` finding is laid to the part at work on its lines (for failed calls,
the part with most of them) and goes to that part's set (`parts.target`: the set whose Files rows name the part's kind,
a hook refusal the set of the hook's plugin; else the session's project set); its line ends `| part: <part> | sets:
<candidate sets>`. The `talk <check>` findings (`scripts/talk.py`) go to the set that owns the talk rule. A finding laid
to a plugin set or the owner's global set is routed from every project (the global rules are checked in the sessions
of every project); one laid to a project's own set only from a retro project, as below. `rules-kit parts` reads whole
transcripts (with --session, the main files whose id starts with ID and their subagents; else those changed since
DATE, default yesterday; the newest first; «Ретро:» and «Документація:» sessions left out), marks the parts with a sign
and writes their packets (`scripts/packets.py`) to `<retro folder>/packets/` (older than SEEN_DAYS days deleted), at
most `--limit` (PACKETS_MAX); it prints one line per packet `<path> | <session> | <part> lines <a>-<b> | signs: ... |
sets: ...` and then the parts counted by kind.

Retro projects: a project counts when its main checkout (the parent of the git common dir) has `.claude/dev-kit.md`
with a line `## project-lead`, or its own `.claude/rules-subscription.md`. A transcript belongs to the project of the
`cwd` of its lines (git, cached per cwd; when git fails, a deleted worktree, the path is cut at `/.claude/worktrees/`
and the part before it is the checkout). Only the findings of retro projects are routed to the project's own set: the
findings of other projects (the home folder, Pult, a project with no lead) that no part lays to a plugin or the global
set stay in `scan-<date>.md` only. A token finding from spend-kit names the `cwd` of
its session and is routed by it the same way. One exception: the `claude app` findings (see Kinds) of every transcript,
a project with no lead, Pult and the home folder included, go to the set FACTS_SET (`dev-kit`, the owner of the Claude
app facts) when it is known, else to the own set of the retro project named `ClaudeDevKit` (found by its repository
folder name among the known retro projects and this scan's projects, never by the place of this script), and not to
the set of their transcript's project; with no such project they stay in the log. The findings of a session whose title starts with `Ретро:` (a retro session)
or `Документація:` (the weekly docs session) and of its subagents are dropped everywhere (log included), so the retro
never feeds on these hook-started sessions; their token spend still counts in spend-kit.

Folders: the retro folder is env RULES_KIT_DIR, else `~/.claude/rules-kit` (local, outside any repository; the retro
used `~/.claude/dev-kit/retro` before, which `scripts/rules_dir.py` copies here once on the first run and leaves as it
is). It holds the global `state.json` (byte offsets, `claude_version`: the
highest Claude Code version seen in the transcripts, a string like `2.1.330`; `facts_recheck`: the day of the
last weekly facts re-check line; the token keys an older version kept there, `daily`, `fit` and the like, are
left alone: spend-kit copied them once), `scan.lock`, the human
log `scan-<date>.md` (all findings of a full scan and the `## Spend` tables) and the owner's `notes.md`. Each rule set
has `<retro folder>/sets/<set name>/` with:
- `new/`: findings no review has seen, one file per writer and run, never shared: `scan-<date>-<HHMMSS>.md` (full
  scan), `<date>-<session id8>-<HHMMSS>.md` (one transcript), `notes-<date>-<HHMMSS>.md` (owner notes), `add-...md`
  (`add`); each finding is a line starting `- `;
- `seen/`: files moved there by `done`, deleted after SEEN_DAYS days;
- `items/<cause-key>.md`: one file per item, written by the retro session and the fix-loop commands; its lines:
  `scripts/fixes.py`.
The retro folder also holds `done.jsonl` (the done list) and `requests/` (revert requests): `scripts/fixes.py`.
Each retro project has `<retro folder>/<repo-folder-name>-<10 hex>/` (`folder_naming.folder_name`, the name of its
state folder) with `state.json`: `root` (the main checkout), `last_review`, `retro_started`, `retro_branch`,
`shown` (the `<set>/<file>` entries of `new/` the last `items` showed). Written
atomically (temp file and replace). The state folders of older versions also hold `new/`, `seen/` and `items/` of the
time before sets: on the first run the retro copies them into the set folders (`migrate_items`: an item goes to the set
of the files its `fix:` lines or text name, else to the project's own set; the old files stay where they are;
`sets/migrated.json` lists the folders done; what moved is printed).
The global subscription `~/.claude/rules-subscription.md` (env RULES_KIT_GLOBAL_DIR) is written from the plugin's
template on the first run when it is missing, and committed in that folder's git repository.
Transcripts: every `*.jsonl` under env DEV_KIT_PROJECTS_DIR, else `~/.claude/projects`, subagent ones in
`<session>/subagents/` included.

Run file: `<retro folder>/runs/<project folder name>.json`, written (atomically, under the project lock) at each
`hook-start` of the project and by `done`: `{"root": <main checkout>, "retro_started": <ISO time or null>,
"last_review": <ISO time or null>, "retro_branch": <branch the retro left for its lead to merge or null>, "retro_due":
<true when findings wait in the `new/` of a set the project reviews and the last review is REVIEW_HOURS old or
missing>}`. dev-kit's weekly docs session
start reads it as a file (never an import) to wait for the retro and for the merge of its branch; whether the branch
is merged it asks git itself. The other way, `hook-start` reads dev-kit's `<state root>/<project folder name>/docs.json`
(`docs_started`, `docs_done`; env DEV_KIT_STATE_DIR, else `~/.claude/dev-kit`) as a file to start no retro session
while a docs session may still run.

Locks (lock files made with O_EXCL; a lock older than its limit is taken over): the global `state.json` is read,
changed and written only while `scan.lock` exists (stale after LOCK_STALE_S). A transcript scan waits up to
LOCK_WAIT_TRANSCRIPT_S for it and then exits 0 with no output (its lines are read by the next full scan); a full scan
waits up to LOCK_WAIT_FULL_S. A project's `state.json` is read, changed and written only
while `state.lock` exists in its item folder (stale after PROJECT_LOCK_STALE_S, wait up to PROJECT_LOCK_WAIT_S): the
stamps of `hook-start`, `items`, `done` and the scan's `root` record. `hook-start` that cannot get it starts
nothing, so two sessions starting at once never both start a retro session.

`scan` reads only what was appended to each transcript since the last scan (`state.json` keeps a byte offset per
file, up to the last complete line, and in `lines` the number of lines before it, so the parts know their line
numbers). On the first full scan (no full scan yet) a file last changed before `--days`
days ago (default 1) that has no offset is skipped and its offset set to its size, so it does not read the whole
history. A full scan writes `scan-<YYYY-MM-DD>.md` (local date; a second scan the same day with `--force` appends to
it), one line per finding, and each line also goes to the `new/` of the own set of its project (token lines from
spend-kit too):

    - <project folder> | <session title (first 8 of its id)> or <session id>[ / subagent <type>] | <kind> | <detail>

A full scan also reads the new lines of `<retro folder>/notes.md` (offset kept in the global state) and then those of
the OLD notes file `~/.claude/dev-kit/retro/notes.md` (`old_notes_offset`; the owner's global docs still name that
path; a line the first copy put into the new file counts once) and puts each into
the `new/` of the own set of the retro project whose repository folder name equals the line's project field, ignoring
case; other lines are dropped. `script candidate` lines go to the own set of the project when all their sessions are of
one project, else to the own set of the project of the repository that holds this plugin (when it is a retro project).
`scan --transcript PATH` is for the SessionEnd hook: only that transcript and its `<id>/subagents/*.jsonl`, the same
per-transcript kinds (and spend-kit's token findings of that transcript), no cross-transcript kinds, no
priority lines, no notes; its findings go to one `new/<date>-<id8>-<HHMMSS>.md` and are appended to `scan-<date>.md`;
nothing found, no file.

`items` first expires the one-off items of the sets the project reviews (`fixes.expire`, one `expired: <set>/<key>`
line each), then prints: the sets folder path; `sets: <the sets the project reviews>`; `last review: <local date and
time of last_review, or never>`; `claude code: <claude_version>` when the global state has it; the new findings of the
`new/` of those sets (token problems first, under "Priority"; each set under a `### <set>` heading; a line that names a
file of a recent fix ends `| possible breakage: <key>`, `fixes.breakage`); the revert requests of those sets
(`## Revert requests`, `<set> | <key>`); for each set under `### <set> (<its items folder>)` one line per `items/*.md`
file `<cause-key> | <status> | <kind> | sightings <N>` (N = the lines starting `- seen:`); and per set `landed fixes in
the last 7 days (<set>): <N> of FIXES_PER_WEEK` (`fixes.landed`). It records the `new/` file names it
showed (`<set>/<file>`); `done` moves exactly those to `seen/` of their set, sets `last_review`, records `retro_branch`
(`--branch`, else none) and deletes what is older than SEEN_DAYS in `seen/`. Findings that came after `items` stay
new. `items`, `add` and `done` print the work of the first run (the migration) on stderr.
`hook-start` (never fails, exit 0): in a retro project, a session titled `Ретро:` or `Документація:` does nothing; a
full scan is spawned
(detached) when none ran today and the scan lock is free; then, under the project lock, when the `new/` of a set the
project reviews has files, `last_review` is older than REVIEW_HOURS (or missing),
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
- `hook refusal`: one hook's reason HOOK_REFUSALS_MIN or more times (an error result `<Event>:<Tool> hook error:
  <reason>`), detail `<event> x<N> (<plugin>): <reason>`;
- `talk <check>` (not for a subagent's file; `scripts/talk.py`): the replies to the owner that break a talk rule, one
  line per check and window, detail `<set>: <file>:<line> (<section>): x<N>; L<reply line>: <excerpt>`;
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
import fixes  # noqa: E402  the fix loop on the item files: expiry, cap, replay, check, revert, done list
import folder_naming  # noqa: E402  the project's folder name and main checkout (a copy of dev-kit's `dev_kit_state`)
import packets  # noqa: E402  the parts with a sign and their packets for the part reader
import parts  # noqa: E402  a transcript split into parts by the skill, agent or hook at work
import rules_dir  # noqa: E402  the data folder and the one-time copy from dev-kit's retro folder
import spend_client  # noqa: E402  runs the `spend-kit` command (token spend), no import of its code
import subscriptions  # noqa: E402  the rule sets, their subscription files and who owns a file
import talk  # noqa: E402  the talk rules checked on every reply to the owner

RETRO_ENV = rules_dir.DIR_ENV
SETS_FOLDER = "sets"  # in the retro folder: one folder per rule set (`new/`, `seen/`, `items/`)
MIGRATED_FILE = "migrated.json"  # in the sets folder: the per-project folders whose items were taken over once
FACTS_SET = "dev-kit"  # the set that owns the Claude app facts: the `claude app` lines go to it (else to ClaudeDevKit's set)
PROJECTS_ENV = "DEV_KIT_PROJECTS_DIR"
NO_START_ENV = "RULES_KIT_NO_START"  # 1: the SessionStart hook does not start the retro session (tests)
STATE_ENV = "DEV_KIT_STATE_DIR"  # dev-kit's state root (the same env as its `dev_kit_state.py`), read for `docs.json`
RUNS_FOLDER = "runs"  # in the retro folder: the run file of each project (see the module doc)
PROFILE_LINE = "## project-lead"  # the line of `.claude/dev-kit.md` that makes a project a retro project
FIXES_PER_WEEK = fixes.FIXES_PER_WEEK  # the cap of landed fixes per set per week, shown by `items`
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
Project = namedtuple("Project", "root name folder")  # main checkout, its folder name, the retro folder name
REPEAT_MIN = 3
ERRORS_MIN = 3
MANY_CALLS = 150
SLOW_CALL_MIN = 10
SLOW_MODEL_MIN = 5
SCRIPT_SESSIONS = 3
HOOK_REFUSALS_MIN = 2  # one refusal is the hook doing its work; a second one of the same reason is a call repeated
PART_FINDINGS = ("repeated call", "failed calls", "hook refusal")  # the technical findings laid to a part's set
PACKETS_FOLDER = "packets"  # in the retro folder: the packets of `rules-kit parts`
PACKETS_MAX = 20  # the packets one `parts` run writes at most (each costs one part reader)
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
    """Whether the checkout `root` has a `## project-lead` line in `.claude/dev-kit.md`, or its own subscription file
    `.claude/rules-subscription.md`."""
    if (Path(root) / ".claude" / subscriptions.FILE_NAME).is_file():
        return True
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


def known_root_paths():
    """The main checkouts recorded in the project folders' `state.json` (any name, a root listed once)."""
    roots = {}
    for state in sorted(retro_dir(create=False).glob("*/state.json")):
        root = load_project(state.parent).get("root")
        if isinstance(root, str) and root:
            roots.setdefault(subscriptions.fold(subscriptions.canon(root)), Path(root))
    return list(roots.values())


def set_dir(name):
    """The folder of one rule set: `new/`, `seen/` and `items/` of its findings (see the module doc)."""
    return retro_dir() / SETS_FOLDER / name


def load_registry(mapper=None, roots=()):
    """The rule sets (`subscriptions.discover`): the plugins next to this one, the global folder and every project
    known to the retro (recorded roots, this scan's projects, `roots`) that is a retro project."""
    found = {}
    candidates = known_root_paths() + [owner.root for owner in (mapper.projects.values() if mapper else ()) if owner]
    for root in list(candidates) + [Path(root) for root in roots]:
        found.setdefault(subscriptions.fold(subscriptions.canon(root)), Path(root))
    return subscriptions.discover(project_roots=[root for root in found.values()
                                                 if root.is_dir() and is_retro_project(root)])


def prepare(mapper=None, out=None, roots=()):
    """The registry for a command, after the first-run work: the global subscription is written from its template
    when missing, and the items of the old per-project folders are taken over once (`migrate_items`)."""
    retro_dir()
    subscriptions.ensure_global()
    registry = load_registry(mapper, roots)
    migrate_items(registry, out or sys.stdout)
    return registry


def set_name_of_root(registry, root):
    """The name of a project's own set: the set at its root, else the default one of that folder."""
    found = registry.set_at(root)
    return found.name if found else subscriptions.default_project(root).name


def project_set_name(registry, project):
    return set_name_of_root(registry, project.root)


def reviewed_sets(registry, project):
    """The names of the sets this project's retro handles: the sets whose subscription names it as reviewer, and its
    own set when that set is not known at all (a file that does not parse)."""
    names = [found.name for found in registry.reviewed_by(project.name)]
    if registry.set_at(project.root) is None:
        names.insert(0, project_set_name(registry, project))
    return names


def project_sets(registry, mapper, plugin=None):
    """Retro projects by lower-case repository folder name -> the name of their own set: the known ones, the ones this
    scan's transcripts belong to and `plugin` (the project that holds this plugin, when given)."""
    found = {}
    for root in known_root_paths():
        found.setdefault(root.name.lower(), set_name_of_root(registry, root))
    for owner in mapper.projects.values():
        if owner:
            found.setdefault(owner.name.lower(), set_name_of_root(registry, owner.root))
    if plugin:
        found.setdefault(plugin.name.lower(), set_name_of_root(registry, plugin.root))
    return found


FACT_LINE = re.compile(r"\s*(claude app|owner check)\b", re.IGNORECASE)  # an added line about a Claude app fact
PATH_TOKEN = re.compile(r"[^\s|`\"'()<>,;«»]+")
PART_REF = re.compile(r"(?<![\w:/.-])([a-z][\w-]*):([a-z][\w-]*)(?![\w:/-])")
FILE_ENDINGS = (".md", ".py", ".json", ".ps1", ".psd1", ".mjs", ".cs", ".sh", ".yml", ".css", ".html")


def sets_of_text(text, registry, roots):
    """The sets a text names, the most named first: by the files it names (a path, absolute or relative to one of
    `roots`, which the registry says a set owns), else by the skills and agents it names (`plugin:name`)."""
    counts = {}
    order = []
    for token in PATH_TOKEN.findall(text):
        token = re.sub(r":\d+(-\d+)?$", "", token.rstrip(".:"))
        if not ("/" in token or "\\" in token or token.endswith(FILE_ENDINGS)):
            continue
        token = str(Path(token).expanduser()) if token.startswith("~") else token
        absolute = token.startswith("/") or re.match(r"^[A-Za-z]:", token)
        for path in ([Path(token)] if absolute else [Path(root) / token for root in roots]):
            owner = registry.owner(path)
            if owner:
                counts[owner.set.name] = counts.get(owner.set.name, 0) + 1
                order.append(owner.set.name)
                break
    if not counts:
        for kind_ref in PART_REF.finditer(text):
            reference = kind_ref.group(0)
            for kind in ("skill", "agent"):
                for found in registry.candidates(kind, reference):
                    counts[found.name] = counts.get(found.name, 0) + 1
                    order.append(found.name)
    return sorted(counts, key=lambda name: (-counts[name], order.index(name)))


def text_roots(root):
    """The folders a relative path in a finding or an item may be written against: the project, the repository that
    holds this plugin and the owner's global folder."""
    return [Path(root), subscriptions.plugins_dir().parent, subscriptions.global_dir()]


def migrate_items(registry, out):
    """Take over the item and new-finding files of the old per-project folders once, into the set folders: an item goes
    to the set of the files its `fix:` lines name, else of the files its text names, else the project's own set; a
    finding file goes to the project's own set. Copies, never over a file (a file that differs keeps both under
    another name); the old folders stay as they are. A folder with no recorded root waits for a later run. What moved is
    printed, once; `sets/migrated.json` lists the folders done."""
    sets = retro_dir() / SETS_FOLDER
    marker = sets / MIGRATED_FILE
    try:
        done_folders = json.loads(marker.read_text(encoding="utf-8")).get("folders", {})
    except (OSError, ValueError, AttributeError):
        done_folders = {}
    if not isinstance(done_folders, dict):
        done_folders = {}
    changed = False
    for state in sorted(retro_dir().glob("*/state.json")):
        old = state.parent
        root = load_project(old).get("root")
        if old.name == SETS_FOLDER or old.name in done_folders or not isinstance(root, str) or not root:
            continue
        own = set_name_of_root(registry, root)
        moved = []
        for path in sorted((old / "items").glob("*.md")) if (old / "items").is_dir() else []:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            fix_lines = "\n".join(line for line in text.splitlines() if line.startswith("- fix:"))
            named = sets_of_text(fix_lines, registry, text_roots(root)) or sets_of_text(text, registry, text_roots(root))
            target = named[0] if named else own
            moved += copy_file(path, set_dir(target) / "items", f"{path.stem}-{Path(root).name.lower()}{path.suffix}",
                               f"{old.name}/items/{path.name} -> {SETS_FOLDER}/{target}/items/")
        for path in sorted((old / "new").glob("*.md")) if (old / "new").is_dir() else []:
            moved += copy_file(path, set_dir(own) / "new", None, f"{old.name}/new/{path.name} -> {SETS_FOLDER}/{own}/new/")
        done_folders[old.name] = {"set": own, "moved": len(moved)}
        changed = True
        for line in moved:
            print("moved " + line, file=out)
    if changed:
        write_json(marker, {"folders": done_folders})


def copy_file(source, folder, alternative, label):
    """Copy `source` into `folder` under its own name; when that name holds other bytes, under `alternative` (or a
    numbered name when there is none). `[label]` when something was copied, [] for an identical file already there."""
    data = source.read_bytes()
    folder.mkdir(parents=True, exist_ok=True)
    names = [source.name] + ([alternative] if alternative else []) + [f"{source.stem}-{n}{source.suffix}" for n in range(1, 100)]
    for name in names:
        target = folder / name
        if not target.exists():
            target.write_bytes(data)
            return [label]
        try:
            if target.read_bytes() == data:
                return []
        except OSError:
            continue
    return []


def write_new(set_name, name, lines):
    """Write `lines` to a new file of the set's `new/` folder, never over another file; None for no lines."""
    if not lines:
        return None
    new = set_dir(set_name) / "new"
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


def analyse(lines, since=None, first_line=1, at_start=True, hooks=None):
    """Counters of one transcript window: calls, repeats, errors, slow calls, pauses, Bash commands, title,
    app failures (`app`) and the highest Claude Code version of its lines (`version`). Token units are not counted
    here (spend-kit reads the transcripts for them); lines dated before `since` are not counted. Also the window's
    parts (`parts.split`, the lines numbered from `first_line`), the lines of its errors, of each repeated call's first
    use and of its hook refusals, and its talk hits (`talk.check_entries`; `at_start`: the window starts the file)."""
    calls = {}
    repeats = Counter()
    first_input = {}
    first_line_of = {}  # repeat key -> the line of its first call
    errors = 0
    error_tools = Counter()
    error_lines = []
    refusals = []  # (line, event, reason, command)
    slow = []
    pauses = []
    bash = set()
    app = Counter()  # (tool, failure text) -> times
    version = None
    title = ""
    last_result_time = None
    entries = []
    for index, raw in enumerate(lines):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(entry, dict):
            continue
        number = first_line + index
        entries.append((number, entry))
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
                    first_line_of.setdefault(key, number)
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
                    error_lines.append(number)
                    refusal = parts.hook_refusal(result_text(block))
                    if refusal:
                        refusals.append((number,) + refusal)
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
        "first_line_of": first_line_of, "error_lines": error_lines, "refusals": refusals,
        "parts": parts.split(entries, hooks=hooks), "talk": talk.check_entries(entries, at_start),
    }


def merge(a, b):
    """The counters of two windows of one label added together."""
    return {
        "title": b["title"] or a["title"], "calls": a["calls"] + b["calls"], "repeats": a["repeats"] + b["repeats"],
        "first_input": {**b["first_input"], **a["first_input"]}, "errors": a["errors"] + b["errors"],
        "error_tools": a["error_tools"] + b["error_tools"], "slow": a["slow"] + b["slow"],
        "pauses": a["pauses"] + b["pauses"], "bash": a["bash"] | b["bash"],
        "app": a["app"] + b["app"], "version": max(filter(None, (a["version"], b["version"])), default=None),
        "first_line_of": {**b["first_line_of"], **a["first_line_of"]}, "error_lines": a["error_lines"] + b["error_lines"],
        "refusals": a["refusals"] + b["refusals"], "parts": a["parts"] + b["parts"], "talk": a["talk"] + b["talk"],
    }


def findings_of(result, with_lines=False):
    """`(kind, detail)` of each finding of a window; with `with_lines`, `(kind, detail, lines)`: the lines that lay a
    `repeated call`, `failed calls` or `hook refusal` to a part (empty for the other kinds)."""
    found = []
    for key, count in result["repeats"].most_common():
        if count < REPEAT_MIN:
            break
        name, tool_input = result["first_input"][key]
        found.append(("repeated call", f"{name} x{count}: {short(json.dumps(tool_input, ensure_ascii=False))}",
                      [result["first_line_of"][key]] if key in result.get("first_line_of", {}) else []))
    if result["errors"] >= ERRORS_MIN:
        tools = ", ".join(f"{name} x{count}" for name, count in result["error_tools"].most_common())
        found.append(("failed calls", f"{result['errors']} ({tools})", list(result.get("error_lines", []))))
    by_reason = defaultdict(list)
    for number, event, reason, _ in result.get("refusals", []):
        by_reason[(event, " ".join(reason.split())[:DETAIL_CHARS])].append(number)
    for (event, reason), numbers in by_reason.items():
        if len(numbers) >= HOOK_REFUSALS_MIN:
            found.append(("hook refusal", f"{event} x{len(numbers)}: {short(reason)}", numbers))
    if result["calls"] >= MANY_CALLS:
        found.append(("many calls", f"{result['calls']} tool calls", []))
    for name, minutes in result["slow"]:
        found.append(("slow call", f"{name} took {minutes:.0f} min", []))
    if result["pauses"]:
        longest = max(result["pauses"])
        found.append(("long pause", f"{len(result['pauses'])} pause(s) before the next reply, longest {longest:.0f} min", []))
    for (name, text), count in result["app"].most_common():  # no threshold: one failure of the app is a fact
        found.append((CLAUDE_APP_KIND, f"{name}{f' x{count}' if count > 1 else ''}: {text}", []))
    return found if with_lines else [entry[:2] for entry in found]


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
    line_counts = state.setdefault("lines", {})  # path -> the lines before its offset
    hooks = parts.HookIndex()
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
        base = line_counts.get(key) if offset else 0
        if not isinstance(base, int):
            base = lines_before(path, offset)
        lines, state["offsets"][key] = read_new_lines(path, offset)
        if not lines:
            continue
        line_counts[key] = base + len(lines)
        project, session, sub = session_label(path, root)
        homes[(project, session)] = owner
        result = analyse(lines, since, first_line=base + 1, at_start=offset == 0, hooks=hooks)
        if sub and result["parts"]:  # a subagent's file is a part of that agent
            agent = sub[len("subagent"):].strip() or "subagent"
            result["parts"][0].kind, result["parts"][0].name = "agent", agent
            result["parts"][0].plugin = parts.plugin_of(agent)
        if result["title"] and not sub:
            known[f"{project}/{session}"] = result["title"]
        window = (project, session, sub, path.stem if sub else "")  # the same file in a later scan is the same run
        merged = windows.get(window)
        windows[window] = merge(merged, result) if merged else result
    titles = {(project, session): known[f"{project}/{session}"] for project, session, _, _ in windows
              if known.get(f"{project}/{session}")}
    out_lines = []
    routed = defaultdict(list)  # set name -> its finding lines
    commands = defaultdict(set)
    registry = prepare(mapper, out)

    def own_set(project):
        """The set of a session's own project: a finding that names no other set is the project's own."""
        return project_set_name(registry, project)

    def retro_session(project, session):
        """A retro session's own findings never feed the retro again (its token statistics still count)."""
        return titles.get((project, session), "").strip().startswith((RETRO_TITLE, DOCS_TITLE))

    def route(project, session, line):
        """A finding line to the scan log, and to the project of its session when that is a retro project."""
        out_lines.append(line)
        if homes[(project, session)]:
            routed[own_set(homes[(project, session)])].append(line)

    devkit = project_sets(registry, mapper).get(DEVKIT_NAME)  # None: ClaudeDevKit is not a known project, the log only
    if devkit and FACTS_SET in registry.sets:
        devkit = FACTS_SET  # the facts file is the dev-kit set's: its keeper takes the `claude app` lines

    def route_app(line):
        """A `claude app` line to the scan log and to the set of the Claude app facts, whatever project its
        transcript belongs to."""
        out_lines.append(line)
        if devkit:
            routed[devkit].append(line)

    shared = shared_sets(registry)
    refs = None

    def route_to(project, session, line, target):
        """A finding laid to a set: a plugin or the global set from any project, a project's own set as `route` does."""
        if target in shared:
            out_lines.append(line)
            routed[target].append(line)
        else:
            route(project, session, line)

    for (project, session, sub, _), result in windows.items():
        if retro_session(project, session):
            continue
        label = f"{titles[(project, session)]} ({session[:8]})" if (project, session) in titles else session
        if sub:
            label += " / " + sub
        home = homes[(project, session)]
        own = own_set(home) if home else None
        for kind, detail, anchors in findings_of(result, with_lines=True):
            line = f"- {project} | {label} | {kind} | {detail}"
            part = busiest(result["parts"], anchors) if kind in PART_FINDINGS else None
            if kind == CLAUDE_APP_KIND:
                route_app(line)
            elif part is None:
                route(project, session, line)
            else:
                unknown_hook = kind == "hook refusal" and part.kind == "hook" and not part.plugin
                target = own if unknown_hook else parts.target(part, registry, own)
                line += f" | part: {part.label()} | sets: {', '.join(parts.candidates(part, registry, own))}"
                route_to(project, session, line, target)
        hits = [hit for hit in result["talk"] if not (
            hit["first_prompt"] and titles.get((project, session), "").startswith(talk.STARTED_BY_SESSION))]
        if hits and not sub:
            refs = refs or talk.rule_refs(registry)
            for check in talk.CHECKS:
                found = [hit for hit in hits if hit["check"] == check]
                if found:
                    ref = refs[check]
                    line = (f"- {project} | {label} | talk {check} | {ref.set}: {talk.ref_text(ref)}: x{len(found)}; "
                            f"L{found[0]['line']}: {short(found[0]['excerpt'])}")
                    route_to(project, session, line, ref.set)
        for command in result["bash"]:
            commands[command].add((project, session))
    if not transcript:  # the same command in several sessions needs the sessions of all transcripts
        plugin = plugin_project(mapper)
        for command, sessions in sorted(commands.items()):
            if len(sessions) >= SCRIPT_SESSIONS:
                line = (f"- {len({p for p, _ in sessions})} project(s) | {len(sessions)} sessions | "
                        f"script candidate | {short(command)}")
                out_lines.append(line)
                owners = {own_set(homes[pair]) for pair in sessions if homes[pair]}
                if len(owners) == 1 and all(homes[pair] for pair in sessions):
                    routed[next(iter(owners))].append(line)
                elif plugin and owners:  # spread over several projects, one of them a retro project
                    routed[own_set(plugin)].append(line)
    spend_lines, table = spend_kit_findings(transcript)
    for entry in spend_lines:  # the token findings (long session, opus coder, token spend and waste), see spend-kit
        if str(entry.get("title") or "").strip().startswith((RETRO_TITLE, DOCS_TITLE)):
            continue
        out_lines.append(entry["line"])
        owner = mapper.project_of_cwd(entry.get("cwd"))
        if owner:
            routed[own_set(owner)].append(entry["line"])
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
        sort_notes(state, folder, registry, mapper, plugin, routed)
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


def lines_before(path, offset):
    """The number of lines before a byte offset of a file (a state from before the line counts was kept)."""
    count = 0
    try:
        with open(path, "rb") as handle:
            left = offset
            while left > 0:
                chunk = handle.read(min(left, 1 << 20))
                if not chunk:
                    break
                count += chunk.count(b"\n")
                left -= len(chunk)
    except OSError:
        pass
    return count


def busiest(found, lines):
    """The part at work on most of the lines (the first such on a tie), or None."""
    counts = Counter()
    order = []
    for number in lines:
        part = parts.innermost(found, number)
        if part is not None:
            counts[id(part)] += 1
            if part not in order:
                order.append(part)
    return max(order, key=lambda part: counts[id(part)]) if order else None


def shared_sets(registry):
    """The names of the sets that are no project's own: the plugin sets and the owner's global set."""
    plugins_root = subscriptions.fold(subscriptions.canon(subscriptions.plugins_dir()))
    global_root = subscriptions.fold(subscriptions.canon(subscriptions.global_dir()))
    return {found.name for found in registry.sets.values()
            if subscriptions.fold(subscriptions.canon(found.root)) == global_root
            or subscriptions.fold(subscriptions.canon(found.root.parent)) == plugins_root}


def write_new_all(routed, make_name):
    """One new file per set in `routed` (set name -> lines)."""
    for set_name, lines in routed.items():
        write_new(set_name, make_name(), lines)


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


def old_note_lines(state, new_path):
    """The unread complete lines of the OLD notes file (`notes.md` in dev-kit's old retro folder): the owner's global
    docs may still tell agents to write there. The offset is kept in the state (`old_notes_offset`). A line the
    one-time copy already put into the new file is skipped."""
    old = rules_dir.old_dir()
    if old is None:
        return []
    path = old / "notes.md"
    try:
        size = path.stat().st_size
    except OSError:
        return []
    offset = state.get("old_notes_offset", 0)
    if offset > size:
        offset = 0
    lines, state["old_notes_offset"] = read_new_lines(path, offset)
    if not lines:
        return []
    try:
        copied = {line.strip() for line in new_path.read_bytes().splitlines()}
    except OSError:
        copied = set()
    return [line for line in lines if line.strip() not in copied]


def sort_notes(state, folder, registry, mapper, plugin, routed):
    """Put the new lines of `notes.md` of the retro folder, then those of the old notes file (`old_note_lines`), into
    the own set of the project named in each line (a retro project; others dropped)."""
    path = folder / "notes.md"
    offset = notes_offset(state, path)
    lines = []
    try:
        size = path.stat().st_size
    except OSError:
        size = None
    if size is not None:
        if offset > size:
            offset = 0
        lines, state["notes_offset"] = read_new_lines(path, offset)
    lines = lines + old_note_lines(state, path)
    if not lines:
        return
    projects = project_sets(registry, mapper, plugin)
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
          f"`{PROFILE_LINE}` line in .claude/dev-kit.md or a .claude/{subscriptions.FILE_NAME}", file=err or sys.stderr)
    return 2


def state_busy():
    print("the project state is locked by another command; run this again", file=sys.stderr)
    return 1


def read_item(path):
    """`(status, kind, sightings)` of one item file."""
    status = kind = "?"
    sightings = 0
    for line in read_lines(path):
        if line.startswith("- status:"):
            status = line[len("- status:"):].strip() or "?"
        elif line.startswith("- kind:"):
            kind = line[len("- kind:"):].strip() or "?"
        elif line.startswith("- seen:"):
            sightings += 1
    return status, kind, sightings


def items(directory=None, out=None):
    """Print the project's new findings and items, and record which `new/` files were shown (see the module doc)."""
    out = out or sys.stdout
    project = project_for(directory)
    if not project:
        return no_project(directory)
    names = reviewed_sets(prepare(roots=[project.root], out=sys.stderr), project)
    for set_name, key in fixes.expire(retro_dir(), retro_dir() / SETS_FOLDER, names):
        print(f"expired: {set_name}/{key}", file=out)
    recent = fixes.recent_fixes(retro_dir() / SETS_FOLDER, names)
    folder = project_folder(project)
    with project_lock(folder) as held:
        if not held:
            return state_busy()
        lines = {}  # set name -> its new findings
        shown = []
        for name in names:
            new = set_dir(name) / "new"
            files = sorted(new.glob("*.md")) if new.is_dir() else []
            lines[name] = [breakage_note(line, recent) for path in files for line in read_lines(path)]
            shown += [f"{name}/{path.name}" for path in files]
        state = load_project(folder)
        state["shown"] = shown
        save_project(folder, state)
    print(retro_dir(create=False) / SETS_FOLDER, file=out)
    print("sets: " + ", ".join(names), file=out)
    reviewed = parse_time(state.get("last_review", ""))
    print("last review: " + (reviewed.astimezone().strftime("%Y-%m-%d %H:%M") if reviewed else "never"), file=out)
    version = load_state(retro_dir(create=False)).get("claude_version")  # the global state, read only
    if version:
        print(f"claude code: {version}", file=out)
    print("\n## Priority: token problems (read first)", file=out)
    print_by_set(lines, out, lambda line: URGENT_LINE.search(line))
    print("\n## New findings", file=out)
    print_by_set(lines, out, lambda line: not URGENT_LINE.search(line))
    print("\n## Revert requests", file=out)
    print("\n".join(f"{set_name} | {key}" for set_name, key in fixes.requests(retro_dir(), names)) or "(none)", file=out)
    print("\n## Items", file=out)
    counts = []
    for name in names:
        rows = []
        folder_items = set_dir(name) / "items"
        for path in sorted(folder_items.glob("*.md")) if folder_items.is_dir() else []:
            status, kind, sightings = read_item(path)
            rows.append(f"{path.stem} | {status} | {kind} | sightings {sightings}")
        print(f"### {name} ({folder_items})", file=out)
        print("\n".join(rows) or "(none)", file=out)
        counts.append(f"landed fixes in the last 7 days ({name}): "
                      f"{fixes.landed(retro_dir() / SETS_FOLDER, name)} of {FIXES_PER_WEEK}")
    print("\n" + "\n".join(counts), file=out)
    return 0


def breakage_note(line, recent):
    """The finding line, with `| possible breakage: <key>` when it names a file of a recent fix (`fixes.breakage`)."""
    key = fixes.breakage(line, recent)
    return f"{line} | possible breakage: {key}" if key else line


def print_by_set(lines, out, keep):
    """The lines of each set that `keep` accepts under a `### <set>` heading; `(none)` when no set has one."""
    shown = False
    for name, found in lines.items():
        chosen = [line for line in found if keep(line)]
        if chosen:
            print(f"### {name}\n" + "\n".join(chosen), file=out)
            shown = True
    if not shown:
        print("(none)", file=out)


def done(directory=None, out=None, branch=None):
    """Move the `new/` files the last `items` showed to `seen/`, stamp `last_review` and `retro_branch`, drop old files
    of `seen/`."""
    out = out or sys.stdout
    project = project_for(directory)
    if not project:
        return no_project(directory)
    names = reviewed_sets(prepare(roots=[project.root], out=sys.stderr), project)
    folder = project_folder(project)
    moved = 0
    with project_lock(folder) as held:
        if not held:
            return state_busy()
        state = load_project(folder)
        for entry in state.pop("shown", None) or []:
            name, _, file_name = str(entry).partition("/")  # `<set>/<file>`; an older entry with no set is dropped
            source = set_dir(name) / "new" / Path(file_name).name
            if name not in names or not file_name or not source.is_file():
                continue
            seen = set_dir(name) / "seen"
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
        write_run_file(project, state, names)
    limit = time.time() - SEEN_DAYS * 86400
    for name in names:
        seen = set_dir(name) / "seen"
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


def retro_due(names, state):
    """Whether findings wait in `new/` of one of the sets (`names`) the project reviews and the last review is at least
    REVIEW_HOURS old (or none): a retro session is due."""
    waiting = any((set_dir(name) / "new").is_dir() and any((set_dir(name) / "new").iterdir()) for name in names)
    return waiting and older(state, "last_review", REVIEW_HOURS)


def write_run_file(project, state, names):
    """Write the project's run file from its state (see "Run file" in the module doc); `names`: the sets the project
    reviews. The caller holds the project lock. A write failure is ignored: the next start or review writes it again."""
    data = {"root": state.get("root"), "retro_started": state.get("retro_started"),
            "last_review": state.get("last_review"), "retro_branch": state.get("retro_branch"),
            "retro_due": retro_due(names, state)}
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


def add(text, sender=None, directory=None, out=None, set_name=None, packet=None):
    """Add one finding line to the `new/` of a set, as a file of its own. `set_name` names the set; otherwise the
    project (`--project`, see `project_for`) is the alias for the sets it reviews that the text names (a file or a
    skill or agent of that set), else for its own set. `packet`: the part reader's packet the finding came from; a set
    none of whose own signs fired for that part also gets a `sign-gap` line in the same file (`packets.gap_line`)."""
    out = out or sys.stdout
    registry = None
    data = None
    if packet:
        data = packets.load(packet)
        if data is None:
            print(f"no packet at {packet} (its .json beside it is missing or broken)", file=sys.stderr)
            return 2
    if set_name:
        registry = prepare(out=sys.stderr)
        if set_name not in registry.sets:
            print(f"no rule set named {set_name} (known: {', '.join(registry.sets) or 'none'})", file=sys.stderr)
            return 2
        names = [set_name]
    else:
        project = project_for(directory)
        if not project:
            return no_project(directory)
        registry = prepare(roots=[project.root], out=sys.stderr)
        reviewed = reviewed_sets(registry, project)
        named = [name for name in sets_of_text(str(text), registry, text_roots(project.root)) if name in reviewed]
        if FACT_LINE.match(str(text)) and FACTS_SET in reviewed:  # the scan routes its `claude app` lines the same way
            named = [FACTS_SET]
        names = named or [project_set_name(registry, project)]
    if not sender:
        origin = Mapper().root_of(str(Path.cwd().resolve()))
        sender = origin.name
    stamp = datetime.datetime.now()
    line = f"- {stamp.date().isoformat()} | from {sender} | {' '.join(str(text).split())}"
    for name in names:
        file_name = f"add-{stamp.date().isoformat()}-{stamp.strftime('%H%M%S')}-{secrets.token_hex(3)}.md"
        gap = packets.gap_line(data, name, stamp.date().isoformat()) if data else None
        print(f"added to {write_new(name, file_name, [line] + ([gap] if gap else []))}", file=out)
        if gap:
            print(f"sign gap recorded for {name}", file=out)
    return 0


def parts_command(session=None, since=None, limit=PACKETS_MAX, out=None):
    """Split the chosen transcripts into parts, write a packet per part with a sign and list them (module doc,
    "Parts")."""
    out = out or sys.stdout
    root = projects_dir()
    if not session and not since:
        since = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    try:
        start = datetime.datetime.combine(datetime.date.fromisoformat(since), datetime.time()).timestamp() if since else None
    except ValueError:
        print(f"--since needs a date YYYY-MM-DD, not {since}", file=sys.stderr)
        return 2
    mains = []
    for path in root.glob("*/*.jsonl") if root.is_dir() else []:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if session and not path.stem.lower().startswith(session.lower()):
            continue
        if start is not None and mtime < start:
            continue
        mains.append((mtime, path))
    mapper = Mapper()
    registry = prepare(mapper, out=sys.stderr)
    folder = retro_dir() / PACKETS_FOLDER
    prune(folder, SEEN_DAYS)
    hooks = parts.HookIndex()
    kinds = Counter()
    written = skipped = 0
    for _, main in sorted(mains, reverse=True):
        entries = parts.read_file(main)
        title = parts.title_of(entries).strip()
        if title.startswith((RETRO_TITLE, DOCS_TITLE)):
            continue
        project = mapper.project_of_transcript(main)
        own = project_set_name(registry, project) if project else None
        label = f"{title} ({main.stem[:8]})" if title else main.stem
        files = [(main, entries, "session", title, label)]
        for sub in sorted((main.with_suffix("") / "subagents").glob("*.jsonl")):
            agent = parts.agent_type(sub)
            files.append((sub, None, "agent", agent, f"{label} / subagent {agent}"))
        for path, found_entries, kind, name, part_label in files:
            found_entries = found_entries if found_entries is not None else parts.read_file(path)
            found = parts.split(found_entries, kind, name if kind == "agent" else "", hooks)
            kinds.update(part.kind for part in found)
            skip_first = kind == "session" and title.startswith(talk.STARTED_BY_SESSION)
            for marks in packets.mark(found_entries, found, registry, own, skip_first):
                if written >= limit:
                    skipped += 1
                    continue
                packet, data = packets.write(folder, path, part_label, found_entries, marks, registry, own)
                written += 1
                signs = [item["sign"] for item in data["general"]] + [
                    f"{set_name}: {sign}" for set_name, names in data["own_signs"].items() for sign in names]
                print(f"{packet} | {part_label} | {marks.part.label()} lines {marks.part.start}-{marks.part.end} | "
                      f"signs: {', '.join(signs)} | sets: {', '.join(data['candidates'])}", file=out)
    print("parts: " + (", ".join(f"{kind} {count}" for kind, count in sorted(kinds.items())) or "none")
          + f"; packets: {written}" + (f" ({skipped} more over the limit of {limit})" if skipped else ""), file=out)
    return 0


def prune(folder, days):
    """Delete the files of a folder older than `days` days."""
    limit = time.time() - days * 86400
    for old in folder.iterdir() if folder.is_dir() else []:
        with contextlib.suppress(OSError):
            if old.is_file() and old.stat().st_mtime < limit:
                old.unlink()


def item_or_error(key, set_name):
    """`(Item, registry)`, or `(None, None)` after printing why on stderr (no such item, or in several sets)."""
    registry = prepare(out=sys.stderr)
    item, error = fixes.find_item(retro_dir() / SETS_FOLDER, key, set_name)
    if error:
        print(error, file=sys.stderr)
        return None, None
    return item, registry


def own_set_of(registry, mapper):
    """A function: a transcript's project set name, or None (for the replay packets' candidate sets)."""
    def find(path):
        project = mapper.project_of_transcript(path)
        return project_set_name(registry, project) if project else None
    return find


def replay_command(key, set_name=None, files=(), out=None):
    out = out or sys.stdout
    item, registry = item_or_error(key, set_name)
    if not item:
        return 2
    written = fixes.replay(item, registry, projects_dir(), retro_dir(), own_set_of(registry, Mapper()),
                           [str(Path(name).resolve()) for name in files])
    for role, path, label in written:
        print(f"{role} | {path} | {label}", file=out)
    problem = sum(role == "problem" for role, _, _ in written)
    print(f"replay {item.set}/{item.key}: problem parts {problem}, good parts {len(written) - problem}", file=out)
    return 0


def fixed_command(key, commit, set_name=None, what="", sign=False, out=None):
    out = out or sys.stdout
    item, registry = item_or_error(key, set_name)
    if not item:
        return 2
    subscription = registry.sets.get(item.set)
    repo = fixes.set_repo(subscription, subscriptions.global_dir())
    files = fixes.changed_files(repo, commit, subscription)
    if files is None:
        print(f"no commit {commit} in {repo}", file=sys.stderr)
        return 1
    fixes.fixed(item, retro_dir(), item.set, commit, files, what, sign)
    print(f"fixed {item.set}/{item.key}: {commit[:8]} ({', '.join(files)}); landed in the last 7 days: "
          f"{fixes.landed(retro_dir() / SETS_FOLDER, item.set)} of {FIXES_PER_WEEK}", file=out)
    return 0


def check_command(directory=None, out=None):
    out = out or sys.stdout
    project = project_for(directory)
    if not project:
        return no_project(directory)
    registry = prepare(roots=[project.root], out=sys.stderr)
    names = reviewed_sets(registry, project)
    shown = 0
    for item in fixes.items_of(retro_dir() / SETS_FOLDER, names):
        if item.status.lower() != "fixed":
            continue
        text, sessions = fixes.check(item, registry.sets.get(item.set), projects_dir())
        print(f"{item.set} | {item.key} | {text} | sessions after: {len(sessions)}", file=out)
        for line in sessions:
            print(f"  {line}", file=out)
        shown += 1
    if not shown:
        print("no fixed items to check", file=out)
    return 0


def revert_command(key, set_name=None, out=None):
    out = out or sys.stdout
    item, registry = item_or_error(key, set_name)
    if not item:
        return 2
    repo = fixes.set_repo(registry.sets.get(item.set), subscriptions.global_dir())
    ok, text = fixes.revert(item, retro_dir(), repo)
    print(text, file=out if ok else sys.stderr)
    return 0 if ok else 1


def mark_command(key, status, set_name=None, note="", out=None):
    item, _ = item_or_error(key, set_name)
    if not item:
        return 2
    fixes.mark(item, retro_dir(), status, note)
    print(f"{item.set}/{item.key}: status {status}", file=out or sys.stdout)
    return 0


def request_command(key, set_name=None, sender="", out=None):
    item, _ = item_or_error(key, set_name)
    if not item:
        return 2
    path = fixes.request(item, retro_dir(), sender)
    print(f"revert requested: {item.set}/{item.key} ({path}); the next retro of the set's reviewer carries it out",
          file=out or sys.stdout)
    return 0


def list_command(days=None, out=None):
    out = out or sys.stdout
    lines = fixes.list_lines(retro_dir(create=False), days)
    print("\n".join(lines) if lines else "(nothing)", file=out)
    return 0


def budget_command(session_id, out=None):
    word, _, text = fixes.budget(session_id)
    print(f"{word}: {text}", file=out or sys.stdout)
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
        save_project(folder, state)
        names = reviewed_sets(load_registry(roots=[project.root]), project)
        command = retro_start_command(project, folder, state, names)
        write_run_file(project, state, names)  # after the stamp: dev-kit's docs session start reads it
    if command:
        spawn(command, cwd=str(project.root))


def retro_start_command(project, folder, state, names):
    """The command that starts the retro session when findings wait in the sets `names`, the review is old and no
    start is recent; it stamps `retro_started` (the caller holds the project lock). None otherwise, and with env
    RULES_KIT_NO_START=1."""
    if not retro_due(names, state) or not older(state, "retro_started", START_GUARD_HOURS):
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
    for name in ("items", "done", "add", "check"):
        command = sub.add_parser(name)
        command.add_argument("--project", help="any folder of the project (default: the current folder)")
        if name == "done":
            command.add_argument("--branch")
        if name == "add":
            command.add_argument("--text", required=True)
            command.add_argument("--from", dest="sender")
            command.add_argument("--set", dest="set_name", help="the rule set that gets the finding (instead of --project)")
            command.add_argument("--packet", help="the part packet the finding came from (adds a sign-gap line)")
    command = sub.add_parser("parts")
    command.add_argument("--session", help="the start of a session id")
    command.add_argument("--since", help="a date YYYY-MM-DD (default: yesterday)")
    command.add_argument("--limit", type=int, default=PACKETS_MAX)
    sub.add_parser("sets")
    for name in ("replay", "fixed", "revert", "mark"):
        command = sub.add_parser(name)
        command.add_argument("--item", required=True, help="the item's cause key")
        command.add_argument("--set", dest="set_name", help="the set of the item (when the key is in several)")
        if name == "replay":
            command.add_argument("--file", action="append", default=[], help="a file the fix edits")
        if name == "fixed":
            command.add_argument("--commit", required=True)
            command.add_argument("--what", default="", help="what the fix removed or merged")
            command.add_argument("--sign", action="store_true", help="the fix adds a sign to the subscription")
        if name == "mark":
            command.add_argument("--status", required=True)
            command.add_argument("--note", default="")
    command = sub.add_parser("revert-request")
    command.add_argument("key")
    command.add_argument("--set", dest="set_name")
    command.add_argument("--from", dest="sender", default="")
    command = sub.add_parser("list")
    command.add_argument("--days", type=int)
    command = sub.add_parser("budget")
    command.add_argument("--session-id", required=True)
    sub.add_parser("hook-start")
    sub.add_parser("hook-end")
    args = parser.parse_args(argv)
    if args.command in ("hook-start", "hook-end"):
        return hook_main(args.command[len("hook-"):])
    if args.command == "scan":
        return scan(days=args.days, force=args.force, transcript=args.transcript)
    if args.command == "items":
        return items(args.project)
    if args.command == "check":
        return check_command(args.project)
    if args.command == "replay":
        return replay_command(args.item, args.set_name, args.file)
    if args.command == "fixed":
        return fixed_command(args.item, args.commit, args.set_name, args.what, args.sign)
    if args.command == "revert":
        return revert_command(args.item, args.set_name)
    if args.command == "mark":
        return mark_command(args.item, args.status, args.set_name, args.note)
    if args.command == "revert-request":
        return request_command(args.key, args.set_name, args.sender)
    if args.command == "list":
        return list_command(args.days)
    if args.command == "budget":
        return budget_command(args.session_id)
    if args.command == "add":
        return add(args.text, args.sender, args.project, set_name=args.set_name, packet=args.packet)
    if args.command == "parts":
        return parts_command(args.session, args.since, args.limit)
    if args.command == "sets":
        return list_sets()
    return done(args.project, branch=args.branch)


def list_sets(out=None):
    """Print every rule set found: name, reviewer, root, and the subscription files that did not parse."""
    out = out or sys.stdout
    registry = prepare(out=sys.stderr)
    for found in registry.sets.values():
        print(f"{found.name} | reviewed by {found.reviewer} | {found.root} | {len(found.files)} file rows", file=out)
    for message in registry.errors:
        print(f"error: {message}", file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
