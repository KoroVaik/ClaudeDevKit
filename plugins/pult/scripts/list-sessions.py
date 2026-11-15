"""List every live (not archived) session of the Claude desktop app Code tab, across projects.

    python scripts/list-sessions.py

One line each: `title | project folder | state | last activity age`. The state is busy, idle or closed, plus the
status the app shows (blocked, completed, review_ready) when it has one. Sources: the app's `local_*.json` files
and the CLI's `~/.claude/sessions/<pid>.json`; a session is running when a pid file has its `cliSessionId` as
`sessionId` and that process is alive. Read only. Env overrides: DEV_KIT_DESKTOP_SESSIONS_DIR,
DEV_KIT_CLI_SESSIONS_DIR. Exit code 2 when the app's sessions folder is missing.
"""
import json
import os
import sys
import time
from pathlib import Path

# Layout of the desktop app data checked on 2026-11-15.
DESKTOP_DIR = Path(os.environ.get("DEV_KIT_DESKTOP_SESSIONS_DIR") or
                   Path.home() / "AppData" / "Local" / "Claude-Data" / "claude_pzs8sxrjxfjjc" / "claude-code-sessions")
DESKTOP_GLOB = "*/*/local_*.json"  # <accountUuid>/<orgUuid>/local_<id>.json
CLI_DIR = Path(os.environ.get("DEV_KIT_CLI_SESSIONS_DIR") or Path.home() / ".claude" / "sessions")  # <pid>.json


def pid_alive(pid):
    """True when a process with this pid exists. Never os.kill(pid, 0): on Windows it kills the process."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel = ctypes.windll.kernel32
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return kernel.GetLastError() == 5  # access denied: the process exists
        code = ctypes.c_ulong()
        ok = kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(code))
        kernel.CloseHandle(ctypes.c_void_p(handle))
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def read_json(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def running_by_cli_id():
    """{cliSessionId: status} of the CLI processes that are alive (status: busy or idle)."""
    found = {}
    for path in CLI_DIR.glob("*.json"):
        data = read_json(path)
        if data and data.get("sessionId") and pid_alive(data.get("pid")):
            found[data["sessionId"]] = data.get("status") or "idle"
    return found


def age_text(ms, now_ms):
    if not isinstance(ms, (int, float)):
        return "?"
    seconds = max(0, int((now_ms - ms) / 1000))
    for limit, size, unit in ((60, 1, "s"), (3600, 60, "m"), (86400, 3600, "h")):
        if seconds < limit:
            return f"{seconds // size}{unit}"
    return f"{seconds // 86400}d"


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    if not DESKTOP_DIR.is_dir():
        print(f"list-sessions: the desktop sessions folder {DESKTOP_DIR} does not exist (is the Claude desktop app "
              f"installed? set DEV_KIT_DESKTOP_SESSIONS_DIR to override)", file=sys.stderr)
        return 2
    now_ms = time.time() * 1000
    running = running_by_cli_id()
    rows = []
    for path in DESKTOP_DIR.glob(DESKTOP_GLOB):
        data = read_json(path)
        if not data or data.get("isArchived"):
            continue
        summary = data.get("postTurnSummary") if isinstance(data.get("postTurnSummary"), dict) else {}
        state = running.get(data.get("cliSessionId"), "closed")
        if summary.get("status_category"):
            state += f" + {summary['status_category']}"
        project = Path(data["cwd"]).name if data.get("cwd") else "?"
        activity = data.get("lastActivityAt")
        rows.append((activity if isinstance(activity, (int, float)) else 0,
                     f"{data.get('title') or '(no title)'} | {project} | {state} | {age_text(activity, now_ms)}"))
    for _, line in sorted(rows, key=lambda row: row[0], reverse=True):
        print(line)
    if not rows:
        print("no desktop sessions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
