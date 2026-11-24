"""The data folder of rules-kit and the one-time copy of what the retro kept in dev-kit's folder.

Folder: env RULES_KIT_DIR, else `~/.claude/rules-kit` (local, outside any repository). It holds the retro's global
`state.json`, `notes.md`, the scan logs, one item folder per project (`<repo-folder-name>-<10 hex>/`, see
`retro.py`) and `runs/<project folder>.json`, the file the retro writes for the plugins that wait for its run (dev-kit's
weekly docs session reads it; see `retro.py`, "Run file").

Move: the retro used to keep all of this in `~/.claude/dev-kit/retro/`. `migrate` copies that folder once, on the first
run (the old folder stays as it is; a file that exists in the new folder is never overwritten) and leaves the marker
file `.moved-from-dev-kit`, so a later run does not copy again. The old folder is env RULES_KIT_OLD_DIR, else
`~/.claude/dev-kit/retro`; when RULES_KIT_DIR is set and RULES_KIT_OLD_DIR is not, there is no old folder (tests and other
throwaway runs never read the real `~/.claude`). Lock files and temp files are not copied."""
import os
import shutil
from pathlib import Path

DIR_ENV = "RULES_KIT_DIR"
OLD_ENV = "RULES_KIT_OLD_DIR"
MARKER = ".moved-from-dev-kit"
SKIPPED = (".lock", ".tmp")


def data_dir():
    return Path(os.environ[DIR_ENV]) if os.environ.get(DIR_ENV) else Path.home() / ".claude" / "rules-kit"


def old_dir():
    """The folder the retro used in dev-kit, or None."""
    if os.environ.get(OLD_ENV):
        return Path(os.environ[OLD_ENV])
    return None if os.environ.get(DIR_ENV) else Path.home() / ".claude" / "dev-kit" / "retro"


def migrate(folder):
    """Copy the old retro folder into `folder` once (see the module doc); never raises."""
    old = old_dir()
    try:
        if old is None or not old.is_dir() or (folder / MARKER).exists():
            return
        for source in sorted(old.rglob("*")):
            if source.is_dir() or source.name.endswith(SKIPPED):
                continue
            target = folder / source.relative_to(old)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        (folder / MARKER).write_text("copied from the dev-kit retro folder\n", encoding="utf-8")
    except OSError:
        pass  # the next run tries again: files already copied stay, nothing is overwritten
