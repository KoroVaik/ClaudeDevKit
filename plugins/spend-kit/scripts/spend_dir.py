"""The data folder of spend-kit and the one-time move of the files it took over from dev-kit.

Folder: env SPEND_KIT_DIR, else `~/.claude/spend-kit` (local, outside any repository). It holds `usage-log.jsonl` (the
status line's weekly readings), `state.json` (the transcript offsets, per-day units, the weekly limit fit and the
critical problems shown), `api-calls.jsonl` (the API client's spend log) and `sessions/<session id>.json` (see
`spend.py`).

Move: spend-kit's files used to live in `~/.claude/dev-kit/`. When a file is missing in the new folder and the old
one exists, `migrate_file` copies it once (the old file stays). The old folder is env SPEND_KIT_OLD_DIR, else
`~/.claude/dev-kit`; when SPEND_KIT_DIR is set and SPEND_KIT_OLD_DIR is not, there is no old folder (tests and other
throwaway runs never read the real `~/.claude`)."""
import os
import shutil
from pathlib import Path

DIR_ENV = "SPEND_KIT_DIR"
OLD_ENV = "SPEND_KIT_OLD_DIR"


def data_dir():
    return Path(os.environ[DIR_ENV]) if os.environ.get(DIR_ENV) else Path.home() / ".claude" / "spend-kit"


def old_dir():
    """The folder dev-kit used for these files, or None."""
    if os.environ.get(OLD_ENV):
        return Path(os.environ[OLD_ENV])
    return None if os.environ.get(DIR_ENV) else Path.home() / ".claude" / "dev-kit"


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
