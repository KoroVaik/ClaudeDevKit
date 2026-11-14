"""Start the project's application with its run-app commands, or tear it down with its stop-app commands.

    dev-kit-app start|stop|list [--project <folder>]

The commands are the `run-app` and `stop-app` rows of the `## Slots` table in the project's `.claude/dev-kit.md`,
one row per command, both lists written in start order. `start` runs the run-app rows in order and stops at the first
failure; `stop` runs the stop-app rows in reverse and goes on after a failure, so as much as possible is torn down;
`list` prints both lists. A row runs only when its whole value is one command in backticks; a skill or prose is
followed by hand, and the runner then refuses before running anything. Each command runs in the project root through
the system shell. What a command may stop (the owner's processes) is decided by the project's own helpers; this only
sequences them. Exit code: 0 done, 1 a command failed, 2 not run (no profile, a row that is not a command),
3 queue timeout (another worktree holds the app).

Queue: several sessions work on one project, each in its own git worktree, but only one runs the app. A project whose
profile has run-app rows keeps a lock file `app.lock` (worktree, start time, pid) in the project state folder. `start`
takes the lock, or waits while another worktree holds it (poll every few seconds, up to env DEV_KIT_QUEUE_WAIT seconds,
default 900, then exit 3 naming the holder); a lock older than env DEV_KIT_LOCK_TTL seconds (default 7200) is taken
over; the same worktree starts again at once. A failed `start` releases the lock. `stop` releases it; a worktree that
does not hold the lock stops nothing. Run `start` in the background: it may wait.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dev_kit_state  # noqa: E402

PROFILE = os.path.join(".claude", "dev-kit.md")
START, STOP = "run-app", "stop-app"
COMMAND = re.compile(r"^`([^`]+)`$")
MUTEX_STALE = 60  # seconds after which a takeover mutex left by a dead process is removed


class NotRun(Exception):
    """The run cannot start: exit code 2."""


class Queued(Exception):
    """Another worktree holds the app and the wait limit passed: exit code 3."""


def find_root(start):
    # The search stops at the checkout's own top (the folder holding `.git`, a folder in the main
    # checkout and a file in a linked worktree). A worktree nested inside the main checkout
    # (.claude/worktrees/...) must never fall through to the main checkout's profile: its commands
    # would then run the owner's app on the owner's data.
    folder = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(folder, PROFILE)):
            return folder
        if os.path.exists(os.path.join(folder, ".git")):
            raise NotRun(f"no {PROFILE} in this checkout ({folder}); nothing was run. In a worktree, "
                         "update it from main or commit the profile; never run from the main checkout")
        parent = os.path.dirname(folder)
        if parent == folder:
            raise NotRun(f"no {PROFILE} in {os.path.abspath(start)} or above")
        folder = parent


def _cells(line):
    # A command may hold a pipe written as \| inside the table cell.
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [cell.strip().replace("\\|", "|") for cell in cells]


def slot_rows(text):
    """Return (slot, raw value) for every row of the `## Slots` table, in file order."""
    rows, inside, fenced, table = [], False, False, []
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = re.match(r"^##\s+(.*?)\s*$", line)
        if heading:
            if inside:
                break
            inside = heading.group(1) == "Slots"
            continue
        if not inside:
            continue
        if line.lstrip().startswith("|"):
            table.append(line)
        elif table:
            break
    for line in table[2:]:
        cells = _cells(line)
        rows.append((cells[0], cells[1] if len(cells) > 1 else ""))
    return rows


def command_of(value):
    """The command of a row whose whole value is one command in backticks, else None."""
    match = COMMAND.match(value.strip())
    return match.group(1).strip() if match else None


def commands(text, slot):
    """The commands of a slot, in file order; NotRun if a row is not a plain command."""
    found = []
    for name, value in slot_rows(text):
        if name != slot:
            continue
        command = command_of(value)
        if command is None:
            raise NotRun(f"{slot} row '{value}' is not one command in backticks; follow it by hand")
        found.append(command)
    return found


def run(command, root):
    print(f"> {command}", flush=True)
    return subprocess.run(command, shell=True, cwd=root).returncode


def _seconds(name, default):
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def lock_path(root):
    return dev_kit_state.project_state_dir(root) / "app.lock"


def norm(root):
    """The worktree path as written in the lock: real path, case folded on Windows."""
    return os.path.normcase(os.path.realpath(root))


def retry(action, tries=6, delay=0.05):
    """Run action; on Windows a file another process has open raises PermissionError, so try again a few times."""
    for attempt in range(tries):
        try:
            return action()
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(delay * (attempt + 1))


def lock_info(path):
    """None when there is no lock; else its content as a dict. A lock that exists but cannot be read or parsed
    (just created and not written yet, or busy) is {}: it counts as held."""
    try:
        data = json.loads(retry(lambda: path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return None
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _age(held, path):
    """Seconds since the lock was taken; for a lock without a readable time, since the file was last changed."""
    try:
        started = datetime.fromisoformat(held["started"])
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - started).total_seconds()
    except (KeyError, TypeError, ValueError):
        pass
    try:
        return max(time.time() - path.stat().st_mtime, 0.0)
    except OSError:
        return 0.0


def _content(root):
    return json.dumps({"worktree": norm(root),
                       "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pid": os.getpid()})


def _unlink(path):
    try:
        retry(path.unlink)
    except FileNotFoundError:
        pass


def _take_over(path, root, expected):
    """Replace the lock `expected` with ours. Takeovers are serialised by a short-lived mutex file, and inside it the
    lock is checked to be still the same one; False when someone else got there first (the caller looks again)."""
    mutex = path.with_name(path.name + ".takeover")
    try:
        os.close(os.open(mutex, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except (FileExistsError, PermissionError):
        try:
            if time.time() - mutex.stat().st_mtime > MUTEX_STALE:
                _unlink(mutex)
        except OSError:
            pass
        return False
    try:
        if lock_info(path) != expected:
            return False
        temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        temp.write_text(_content(root), encoding="utf-8")
        retry(lambda: os.replace(temp, path))
        return True
    except PermissionError:
        return False
    finally:
        try:
            _unlink(mutex)
        except OSError:
            pass


def acquire(root):
    """Take the app lock for this worktree, waiting in the queue; Queued when the wait limit passes."""
    path, me = lock_path(root), norm(root)
    ttl, limit = _seconds("DEV_KIT_LOCK_TTL", 7200), _seconds("DEV_KIT_QUEUE_WAIT", 900)
    poll = _seconds("DEV_KIT_LOCK_POLL", 3)
    deadline, announced = time.monotonic() + limit, False
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except (FileExistsError, PermissionError):
            pass
        else:
            with os.fdopen(fd, "w", encoding="utf-8") as lock:
                lock.write(_content(root))
            return
        held = lock_info(path)
        if held is None:
            time.sleep(0.05)
            continue  # released between our attempt and our read
        holder, since = held.get("worktree", "an unknown worktree"), held.get("started", "an unknown time")
        if holder == me or _age(held, path) > ttl:
            if _take_over(path, root, held):
                if holder != me:
                    print(f"{START}: the lock held by {holder} since {since} expired; taking it over.", flush=True)
                return
            time.sleep(0.05)
            continue
        if time.monotonic() >= deadline:
            raise Queued(f"{START}: still waiting after {limit:g} s; the app is held by {holder} since {since}.")
        if not announced:
            print(f"waiting for the app, held by {holder} since {since}", flush=True)
            announced = True
        time.sleep(min(poll, max(deadline - time.monotonic(), 0.01)))


def release(root):
    """Remove the lock if this worktree holds it."""
    path = lock_path(root)
    held = lock_info(path)
    if held is not None and held.get("worktree") == norm(root):
        try:
            _unlink(path)
        except OSError:
            pass


def start(text, root):
    steps = commands(text, START)
    if not steps:
        raise NotRun(f"the profile fills no {START}")
    acquire(root)
    for command in steps:
        code = run(command, root)
        if code != 0:
            release(root)
            print(f"{START}: '{command}' failed with exit code {code}; the later commands did not run. "
                  f"The app is not up, so the queue lock is released. Run 'dev-kit-app stop' when the work is done.",
                  flush=True)
            return 1
    print(f"{START}: {len(steps)} command(s) done.", flush=True)
    return 0


def stop(text, root):
    steps = commands(text, STOP)
    queued = any(name == START for name, _ in slot_rows(text))
    if queued:
        held = lock_info(lock_path(root))
        if held is not None and held.get("worktree") != norm(root):
            print(f"the app is held by {held.get('worktree', 'an unknown worktree')}, not stopped", flush=True)
            return 0
    if not steps:
        print(f"{STOP}: the profile fills no {STOP}; nothing was stopped.", flush=True)
        if queued:
            release(root)
        return 0
    failed = [command for command in reversed(steps) if run(command, root) != 0]
    if queued:
        release(root)
    for command in failed:
        print(f"{STOP}: '{command}' failed.", flush=True)
    if not failed:
        print(f"{STOP}: {len(steps)} command(s) done, in reverse order.", flush=True)
    return 1 if failed else 0


def show(text):
    for slot, order in ((START, "in this order"), (STOP, "in reverse of this order")):
        rows = [value for name, value in slot_rows(text) if name == slot]
        print(f"{slot} ({order}):" if rows else f"{slot}: not filled")
        for value in rows:
            command = command_of(value)
            print(f"  {command}" if command else f"  not a command, followed by hand: {value}")
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="dev-kit-app", description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["start", "stop", "list"])
    parser.add_argument("--project", default=".", help="the project folder or a folder inside it")
    args = parser.parse_args(argv)
    try:
        root = find_root(args.project)
        with open(os.path.join(root, PROFILE), encoding="utf-8-sig") as profile:
            text = profile.read()
        if args.action == "list":
            return show(text)
        return start(text, root) if args.action == "start" else stop(text, root)
    except NotRun as exc:
        print(f"dev-kit-app: not run: {exc}", file=sys.stderr)
        return 2
    except Queued as exc:
        print(f"dev-kit-app: {exc}", file=sys.stderr, flush=True)
        return 3


if __name__ == "__main__":
    sys.exit(main())
