"""Per-project state folder of dev-kit (session registry, queue lock files), kept outside the repository.

    project_state_dir(start) -> Path

The project key is the absolute, normalized `git rev-parse --git-common-dir` of `start`, the same for every worktree
of one repository; outside a git repository it is the resolved `start` path. The folder is
`<root>/<repo-folder-name>-<first 10 hex of sha1 of the key>`, where `<root>` is env DEV_KIT_STATE_DIR if set, else
`~/.claude/dev-kit`. The folder is created on demand. Nothing runs on import.
"""
import hashlib
import os
import subprocess
from pathlib import Path

STATE_ENV = "DEV_KIT_STATE_DIR"


def project_key(start):
    """The normalized absolute path that identifies the project of `start`."""
    start = Path(start).resolve()
    try:
        result = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=start, capture_output=True,
                                text=True, encoding="utf-8")
        common = result.stdout.strip() if result.returncode == 0 else ""
    except OSError:
        common = ""
    path = (start / common) if common else start
    return os.path.normcase(os.path.realpath(path))


def project_state_dir(start):
    key = project_key(start)
    # The repository folder is the parent of the .git folder; a bare repo or a non-git folder uses its own name.
    base = Path(key)
    name = base.parent.name if base.name.lower() == ".git" else base.name
    root = Path(os.environ[STATE_ENV]) if os.environ.get(STATE_ENV) else Path.home() / ".claude" / "dev-kit"
    folder = root / f"{name}-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
