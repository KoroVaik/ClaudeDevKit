"""Start the weekly «Документація:» session of a project and keep its state (the session itself is the skill
`dev-kit:maintain-project-docs`, "Weekly background run").

    dev-kit-docs done [--project DIR]     stamp the end of the weekly docs run (`docs_done`)
    dev-kit-docs items [--project DIR]    print the project's docs folder and its docs items, see below
    dev-kit-docs hook-start               SessionStart hook of the plugin (JSON on stdin); never fails, exit 0

`--project DIR` is any folder of the project (a worktree too; default the current folder). A project counts when its
main checkout has `.claude/dev-kit.md` with a line `## project-lead`; any other project gets exit code 2 (the hook
stays silent).

Docs folder: `<state root>/<repo-folder-name>-<10 hex>/` of `dev_kit_state.py` (env DEV_KIT_STATE_DIR, else
`~/.claude/dev-kit`; local, outside any repository). It holds `docs.json` with `docs_started` and `docs_done` (ISO
times, written atomically while the lock file `docs.lock` exists: stale after LOCK_STALE_S, wait up to LOCK_WAIT_S; a
hook that cannot get it starts nothing) and `docs-items/<key>.md`, one file per docs item written by the weekly docs
session; its line `- status: owner` marks an item the owner decides. `items` prints the docs folder path, then one line
`<key> | <status>` per item file. These files used to live in the retro folder (`~/.claude/dev-kit/retro/<folder>/`,
env DEV_KIT_OLD_RETRO_DIR); the first run copies the two stamps and the item files from there once (the old ones stay).
With DEV_KIT_STATE_DIR set and DEV_KIT_OLD_RETRO_DIR not, there is no old folder (tests never read the real `~/.claude`).

`hook-start`: in a project with a lead, a session titled `Ретро:` or `Документація:` does nothing; otherwise it starts
the background session `Документація: <repo folder>` running `/dev-kit:maintain-project-docs weekly` (with the
`--settings` file no-remote-control.json, so it stays out of the app; env DEV_KIT_DOCS_NO_START=1 skips the start, not
the stamp) when all hold: `docs_done` is older than DOCS_DAYS (or missing); `docs_started` is older than
DOCS_GUARD_HOURS (or missing), so a run that ended with no `done` is retried once a day, not at every session start;
the retro's run file (below) shows no retro session that may still run (`retro_started` younger than
START_GUARD_HOURS and newer than `last_review`) and no retro due (`retro_due`: the retro session starts first); and
the retro's `retro_branch` is merged into the main checkout's HEAD (or gone) or `last_review` is older than
DOCS_MERGE_WAIT_HOURS. So the docs session runs on the rules the week's retro just fixed, or on its own in a week with
no retro. It stamps `docs_started`.

The retro's run file is read as a file, never through an import of rules-kit: `<rules-kit folder>/runs/<project folder
name>.json` (rules-kit folder: env RULES_KIT_DIR, else `~/.claude/rules-kit`; the writer and the keys: the module doc of
`plugins/rules-kit/scripts/retro.py`, "Run file"). A missing or unreadable file means no retro ran: nothing to wait for.
"""
import argparse
import contextlib
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the launcher runs this file with runpy, which adds nothing
import dev_kit_state  # noqa: E402  the project's folder name, state folder and main checkout

RULES_KIT_ENV = "RULES_KIT_DIR"
OLD_RETRO_ENV = "DEV_KIT_OLD_RETRO_DIR"
NO_START_ENV = "DEV_KIT_DOCS_NO_START"  # 1: the SessionStart hook does not start the docs session (tests)
PROFILE_LINE = "## project-lead"  # the line of `.claude/dev-kit.md` that makes a project a project with a lead
DOCS_TITLE = "Документація:"
RETRO_TITLE = "Ретро:"
DOCS_DAYS = 7  # the weekly docs session runs once in this many days
DOCS_MERGE_WAIT_HOURS = 48  # the docs session waits this long for the retro's branch to be merged
DOCS_GUARD_HOURS = 24  # no new docs session while the last start is younger (one that ended with no `done` too)
START_GUARD_HOURS = 6  # a retro session started less than this long ago may still run (the retro's own guard)
LOCK_NAME = "docs.lock"
LOCK_STALE_S = 60
LOCK_WAIT_S = 2
GIT_TIMEOUT_S = 2  # each git call of the SessionStart hook (its limit is 10 s)
WINDOWS = os.name == "nt"
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000
NO_REMOTE_CONTROL = Path(__file__).resolve().parent.parent / "no-remote-control.json"  # a background session the
# owner need not open starts with no Remote Control (plugins/dev-kit/claude-facts.md, "`remoteControlAtStartup: true`
# gives every new session Remote Control, with or without `--remote-control`")


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def parse_time(value):
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def older(state, key, hours):
    """True when the stamp `key` is missing or at least `hours` old."""
    stamp = parse_time(state.get(key, ""))
    return not stamp or now_utc() - stamp >= datetime.timedelta(hours=hours)


def read_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path, data):
    """Write a JSON file atomically: a temp file of this process, then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def is_lead_project(root):
    """Whether the checkout `root` has a `## project-lead` line in `.claude/dev-kit.md`."""
    try:
        text = (Path(root) / ".claude" / "dev-kit.md").read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return False
    return any(line.strip() == PROFILE_LINE for line in text.splitlines())


def project_of(directory):
    """`(main checkout, folder name)` of the project of a folder (default the current one), or None when it has no lead."""
    start = str(Path(directory or Path.cwd()).resolve())
    root = dev_kit_state.main_checkout(start)
    if root is None or not is_lead_project(root):
        return None
    return root, dev_kit_state.folder_name(root)


def lock_age(path):
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return None


@contextlib.contextmanager
def docs_lock(folder):
    """Hold `docs.lock` of the docs folder (made with O_EXCL; one older than LOCK_STALE_S is taken over); yields False
    after LOCK_WAIT_S seconds."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / LOCK_NAME
    deadline = time.monotonic() + LOCK_WAIT_S
    while True:
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):  # Windows: PermissionError while the other side deletes it
            age = lock_age(path)
            if age is not None and age > LOCK_STALE_S:
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


def old_retro_dir():
    """The folder the retro kept the docs state in before, or None (see the module doc)."""
    if os.environ.get(OLD_RETRO_ENV):
        return Path(os.environ[OLD_RETRO_ENV])
    return None if os.environ.get(dev_kit_state.STATE_ENV) else Path.home() / ".claude" / "dev-kit" / "retro"


def migrate(folder, folder_name):
    """Copy the docs stamps and docs items of the old retro folder once: only what the docs folder lacks."""
    old = old_retro_dir()
    if old is None or not (old / folder_name).is_dir():
        return
    try:
        if not (folder / "docs.json").exists():
            stamps = read_json(old / folder_name / "state.json")
            kept = {key: stamps[key] for key in ("docs_started", "docs_done") if isinstance(stamps.get(key), str)}
            if kept:
                write_json(folder / "docs.json", kept)
        for source in sorted((old / folder_name / "docs-items").glob("*.md")):
            target = folder / "docs-items" / source.name
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(source.read_bytes())
    except OSError:
        pass


def docs_folder(root, folder_name):
    """The project's docs folder; it exists, with the old retro folder's docs state copied in."""
    folder = dev_kit_state.project_state_dir(root, create=True)
    migrate(folder, folder_name)
    return folder


def retro_run(folder_name):
    """The retro's run file of the project as a dict (see the module doc); {} when there is none."""
    base = Path(os.environ[RULES_KIT_ENV]) if os.environ.get(RULES_KIT_ENV) else Path.home() / ".claude" / "rules-kit"
    return read_json(base / "runs" / f"{folder_name}.json")


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


def docs_start_command(root, folder, state, run):
    """The command that starts the weekly docs session when it is due (module doc, `hook-start`); it stamps
    `docs_started` (the caller holds the lock). None otherwise, and with env DEV_KIT_DOCS_NO_START=1."""
    if not older(state, "docs_done", DOCS_DAYS * 24) or not older(state, "docs_started", DOCS_GUARD_HOURS):
        return None
    started, reviewed = parse_time(run.get("retro_started", "")), parse_time(run.get("last_review", ""))
    if started and not older(run, "retro_started", START_GUARD_HOURS) and (not reviewed or started > reviewed):
        return None  # the retro session may still run: its fixes come first
    if run.get("retro_due") is True:
        return None  # the retro session starts first (the same session start, or the next one)
    branch = run.get("retro_branch")
    if isinstance(branch, str) and branch and not older(run, "last_review", DOCS_MERGE_WAIT_HOURS) \
            and not merged(root, branch):
        return None  # the retro's fixes are not on main yet
    import sessions  # late: only a start needs it
    claude = sessions.find_claude()
    if not claude:
        return None
    state["docs_started"] = now_utc().isoformat()
    write_json(folder / "docs.json", state)
    if os.environ.get(NO_START_ENV) == "1":
        return None
    return [claude, "--bg", "--name", f"{DOCS_TITLE} {root.name}", "--settings", str(NO_REMOTE_CONTROL),
            "--model", "opus", "--effort", "medium", "--permission-mode", "bypassPermissions", "--",
            "/dev-kit:maintain-project-docs weekly"]


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


def hook_start(payload):
    """SessionStart in a project with a lead: start the weekly docs session when it is due (module doc)."""
    title = str(payload.get("session_title") or "").strip()
    if title.startswith((RETRO_TITLE, DOCS_TITLE)):
        return
    cwd = payload.get("cwd")
    project = project_of(cwd) if isinstance(cwd, str) and cwd.strip() else None
    if not project:
        return
    root, folder_name = project
    folder = docs_folder(root, folder_name)
    command = None
    with docs_lock(folder) as held:  # two sessions starting at once must not both start a docs session
        if not held:
            return
        command = docs_start_command(root, folder, read_json(folder / "docs.json"), retro_run(folder_name))
    if command:
        spawn(command, cwd=str(root))


def hook_main():
    """Run the hook from the JSON on stdin; never fails and prints nothing."""
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if isinstance(payload, dict):
            hook_start(payload)
    except Exception:  # a hook must never block a session
        pass
    return 0


def no_project(directory, err=None):
    print(f"no project with a lead at {Path(directory or Path.cwd()).resolve()}: its main checkout needs a "
          f"`{PROFILE_LINE}` line in .claude/dev-kit.md", file=err or sys.stderr)
    return 2


def done(directory=None, out=None):
    """Stamp the end of the weekly docs session (`docs_done`)."""
    out = out or sys.stdout
    project = project_of(directory)
    if not project:
        return no_project(directory)
    folder = docs_folder(*project)
    with docs_lock(folder) as held:
        if not held:
            print("the docs state is locked by another command; run this again", file=sys.stderr)
            return 1
        state = read_json(folder / "docs.json")
        state["docs_done"] = now_utc().isoformat()
        write_json(folder / "docs.json", state)
    print("docs run stamped", file=out)
    return 0


def read_status(path):
    """The value of the `- status:` line of an item file, `?` when it has none."""
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return "?"
    for line in text.splitlines():
        if line.startswith("- status:"):
            return line[len("- status:"):].strip() or "?"
    return "?"


def items(directory=None, out=None):
    """Print the docs folder and one `<key> | <status>` line per docs item."""
    out = out or sys.stdout
    project = project_of(directory)
    if not project:
        return no_project(directory)
    folder = docs_folder(*project)
    print(folder, file=out)
    print("\n## Docs items", file=out)
    found = sorted((folder / "docs-items").glob("*.md")) if (folder / "docs-items").is_dir() else []
    print("\n".join(f"{path.stem} | {read_status(path)}" for path in found) or "(none)", file=out)
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(prog="dev-kit-docs")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("done", "items"):
        command = sub.add_parser(name)
        command.add_argument("--project", help="any folder of the project (default: the current folder)")
    sub.add_parser("hook-start")
    args = parser.parse_args(argv)
    if args.command == "hook-start":
        return hook_main()
    if args.command == "items":
        return items(args.project)
    return done(args.project)


if __name__ == "__main__":
    sys.exit(main())
