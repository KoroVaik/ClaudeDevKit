"""Wakes the Pult session when the server watcher gives up on something.

Pult runs it in the Bash tool with run_in_background (see rules/hub.md, "Phone push"). It follows
~/.claude/pult/logs/servers.log (written by watch-servers.ps1) and exits with the first new problem line,
so the Pult session wakes and pushes it to the owner's phone. It reads from where its last run stopped
(a position file), so a line written between two runs is not lost. On its first run, or when the position
is older than FRESH seconds (Pult was down), it starts at the end: old lines are shown by "статус", not pushed.

Exit codes (one line on stdout):
  0  problem: <log line>       a new GIVEUP, GIVEUP-TASK or RESTART-LEAD-FAILED line
  4  time limit                nothing happened within --max-minutes
  6  already watching: pid N   another watcher runs
"""
import argparse
import os
import sys
import time
from pathlib import Path

# A failed HEAL or HEAL-TASK try is not here: the watcher logs GIVEUP or GIVEUP-TASK after its last try,
# so one incident gives one push.
PROBLEMS = ("GIVEUP", "GIVEUP-TASK", "RESTART-LEAD-FAILED")
LOCK = "watch-log.lock"
POSITION = "watch-log.pos"
FRESH = 600


def pid_alive(pid):
    """Whether a process with this pid exists. ctypes on Windows (os.kill would end the process there)."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return kernel32.GetLastError() == 5  # access denied: it exists
        try:
            code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def take_lock(path):
    """Takes the lock file; returns the pid of a live holder instead, or None when taken."""
    try:
        holder = int(path.read_text(encoding="ascii").strip() or 0)
    except (OSError, ValueError):
        holder = 0
    if holder and holder != os.getpid() and pid_alive(holder):
        return holder
    path.write_text(str(os.getpid()), encoding="ascii")
    return None


def is_problem(line):
    """A log line is `<time> <TAG> <rest>`; the tag decides."""
    parts = line.split(maxsplit=2)
    return len(parts) >= 2 and parts[1] in PROBLEMS


def read_position(path, size, now=None):
    try:
        if (now or time.time()) - path.stat().st_mtime > FRESH:
            return size  # Pult was down: old lines are not news
        position = int(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        return size  # first run: only lines written from now on
    return position if 0 <= position <= size else 0  # the log was cut or replaced: read it from the start


def scan(log, position):
    """New whole lines from position on; returns (first problem line or None, new position)."""
    try:
        with open(log, "rb") as handle:
            handle.seek(position)
            data = handle.read()
    except OSError:
        return None, position
    for raw in data.splitlines(keepends=True):
        if not raw.endswith(b"\n"):
            break  # a line still being written: read it next time
        position += len(raw)
        line = raw.decode("utf-8", "replace").lstrip("﻿").strip()
        if is_problem(line):
            return line, position
    return None, position


def main(argv=None):
    home = Path.home() / ".claude" / "pult"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--log", type=Path, default=home / "logs" / "servers.log")
    parser.add_argument("--state-dir", type=Path, default=home)
    parser.add_argument("--interval", type=float, default=30, help="seconds between reads")
    parser.add_argument("--max-minutes", type=float, default=120)
    args = parser.parse_args(argv)

    args.state_dir.mkdir(parents=True, exist_ok=True)
    lock = args.state_dir / LOCK
    holder = take_lock(lock)
    if holder is not None:
        print(f"already watching: pid {holder}")
        return 6
    pos_file = args.state_dir / POSITION
    try:
        size = args.log.stat().st_size if args.log.exists() else 0
        position = read_position(pos_file, size)
        deadline = time.monotonic() + args.max_minutes * 60
        while True:
            line, position = scan(args.log, position)
            pos_file.write_text(str(position), encoding="ascii")
            if line is not None:
                print(f"problem: {line}")
                return 0
            if time.monotonic() >= deadline:
                print("time limit")
                return 4
            time.sleep(args.interval)
    finally:
        try:
            if lock.read_text(encoding="ascii").strip() == str(os.getpid()):
                lock.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    sys.exit(main())
