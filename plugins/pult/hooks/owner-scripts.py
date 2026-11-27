"""Hook for the `.cmd` files an agent writes for the owner to run (docs/features/clean-up-scripts-made-for-the-owner.md).

The owner's global rule: such a file goes only into the folder `Claude` on the desktop and the agent deletes it after
the owner's «Готово». This hook backs that rule up in every session on the machine (pult is a user-scope plugin):

- `pre` (PreToolUse, Write): refuses a `.cmd` or `.bat` file written on the desktop outside the folder `Claude`.
- `post` (PostToolUse, Write|Edit): records a `.cmd` or `.bat` file written into the folder `Claude`, with its time and
  the hash of its text, in `~/.claude/pult/owner-scripts.json`.
- `start` (SessionStart): deletes a recorded file older than a day whose text still has the recorded hash, and drops
  records of files that are gone or changed. A file the agent did not record (the owner's own) is never touched; a
  changed file counts as the owner's.

Never fails: any error lets the call through with exit code 0 and no output."""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

SCRIPT_EXT = (".cmd", ".bat")
MAX_AGE = 24 * 3600  # seconds a recorded file may stay before a session start deletes it


def home():
    return Path.home()


def desktops():
    """The desktop folders: the usual one and OneDrive's."""
    return [home() / "Desktop", home() / "OneDrive" / "Desktop"]


def script_folder():
    return home() / "Desktop" / "Claude"


def ledger_path():
    return home() / ".claude" / "pult" / "owner-scripts.json"


def log_path():
    return home() / ".claude" / "pult" / "logs" / "owner-scripts.log"


def norm(path):
    """Absolute path as a lower-case string with forward slashes, to compare folders."""
    return os.path.normcase(os.path.abspath(str(path))).replace("\\", "/").rstrip("/").lower()


def inside(path, folder):
    return norm(path).startswith(norm(folder) + "/")


def is_script(path):
    return str(path).lower().endswith(SCRIPT_EXT)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_ledger():
    try:
        data = json.loads(ledger_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_ledger(data):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def log(line):
    try:
        path = log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S") + " " + line + "\n")
    except Exception:
        pass


def target(call):
    return str((call.get("tool_input") or {}).get("file_path") or "")


def pre(call):
    path = target(call)
    if not path or not is_script(path) or inside(path, script_folder()):
        return
    if not any(inside(path, d) for d in desktops()):
        return
    reason = (f"write this file into the folder Claude on the desktop ({script_folder().as_posix()}), not elsewhere on "
              "the desktop: the owner's global rule keeps scripts made for him there, and only files written there are "
              "cleaned up when left behind")
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                      "permissionDecisionReason": reason}}, sys.stdout)


def post(call):
    path = target(call)
    if not path or not is_script(path) or not inside(path, script_folder()) or not Path(path).is_file():
        return
    data = load_ledger()
    key = norm(path)
    entry = data.get(key) or {"path": str(Path(path)), "written": time.time(), "session": call.get("session_id", ""),
                              "cwd": call.get("cwd", "")}
    entry["hash"] = file_hash(path)
    data[key] = entry
    save_ledger(data)


def start(call):
    data = load_ledger()
    if not data:
        return
    now = time.time()
    keep = {}
    for key, entry in data.items():
        path = Path(entry.get("path") or key)
        try:
            if not path.is_file():
                continue  # deleted already, by the agent or the owner
            if file_hash(path) != entry.get("hash"):
                log(f"KEEP-CHANGED {path}")  # changed since the agent wrote it: now the owner's
                continue
            if now - float(entry.get("written") or now) < MAX_AGE:
                keep[key] = entry
                continue
            path.unlink()
            log(f"DELETED {path} (written {time.strftime('%Y-%m-%d %H:%M', time.localtime(entry['written']))}, "
                f"cwd {entry.get('cwd', '')})")
        except Exception:
            keep[key] = entry  # try again at the next start
    if keep != data:
        save_ledger(keep)


def main():
    try:
        mode = sys.argv[1] if len(sys.argv) > 1 else ""
        call = json.loads(sys.stdin.buffer.read().decode("utf-8-sig") or "{}")
        {"pre": pre, "post": post, "start": start}[mode](call)
    except Exception:
        return


if __name__ == "__main__":
    main()
    sys.exit(0)
