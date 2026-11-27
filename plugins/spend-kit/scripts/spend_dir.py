"""The data folder of spend-kit and the one-time move of the files it took over from dev-kit.

Folder: env SPEND_KIT_DIR, else `~/.claude/spend-kit` (local, outside any repository). It holds `usage-log.jsonl` (the
status line's weekly readings), `state.json` (the transcript offsets, per-day units, the weekly limit fit and the
critical problems shown), `api-calls.jsonl` (the API client's spend log) and `sessions/<session id>.json` (see
`spend.py`).

Move: spend-kit's files used to live in `~/.claude/dev-kit/`. When a file is missing in the new folder and the old
one exists, `migrate_file` copies it once (the old file stays). The old folder is env SPEND_KIT_OLD_DIR, else
`~/.claude/dev-kit`; when SPEND_KIT_DIR is set and SPEND_KIT_OLD_DIR is not, there is no old folder (tests and other
throwaway runs never read the real `~/.claude`).

The API spend log `api-calls.jsonl` and the weekly credit-check log `credits.md` are copied the same way
(`migrate_api_files`). Programs of other projects append API spend lines to the old path by their own code, so the old
`api-calls.jsonl` stays in use: `old_api_log` names it and the API client reads both (see `api_client.py`)."""
import contextlib
import json
import os
import shutil
import time
from pathlib import Path

DIR_ENV = "SPEND_KIT_DIR"
OLD_ENV = "SPEND_KIT_OLD_DIR"
API_LOG = "api-calls.jsonl"
CREDITS = "credits.md"


def data_dir():
    return Path(os.environ[DIR_ENV]) if os.environ.get(DIR_ENV) else Path.home() / ".claude" / "spend-kit"


def old_dir():
    """The folder dev-kit used for these files, or None."""
    if os.environ.get(OLD_ENV):
        return Path(os.environ[OLD_ENV])
    return None if os.environ.get(DIR_ENV) else Path.home() / ".claude" / "dev-kit"


def write_json(path, data):
    """Write a JSON file atomically: a temp file of this process, then replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def lock_age(path):
    """Seconds since the lock file was made, or None when there is none."""
    try:
        return time.time() - path.stat().st_mtime
    except OSError:
        return None


@contextlib.contextmanager
def file_lock(path, wait, stale):
    """Hold a lock file (made with O_EXCL; one older than `stale` s is taken over); yields False after `wait` s."""
    path.parent.mkdir(parents=True, exist_ok=True)
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


def migrate_file(name, target, old_name=None):
    """Copy the old folder's `old_name` (default `name`) to `target` once: only when `target` is missing."""
    old = old_dir()
    if old is None or target.exists():
        return
    source = old / (old_name or name)
    try:
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    except OSError:
        pass


def migrate_api_files():
    """Copy the API spend log and the credit-check log to the data folder once (each only when missing there)."""
    folder = data_dir()
    migrate_file(API_LOG, folder / API_LOG)
    migrate_file(CREDITS, folder / CREDITS)


def old_api_log():
    """The API spend log in the old folder (other projects' programs still append there), or None when there is no
    old folder."""
    old = old_dir()
    return None if old is None else old / API_LOG
