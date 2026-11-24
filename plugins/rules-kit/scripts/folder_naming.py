"""The name of a project's folder and its main checkout, the same rule as dev-kit's `dev_kit_state.py` (no plugin imports
another's code, so this is a copy; the Pult watcher reproduces the name by the same convention).

    folder_name(start) -> str          `<repo-folder-name>-<10 hex>`, the name of the project's folder under any root
    main_checkout(start) -> Path|None  the main checkout of the repository of `start` (parent of the git common dir)

The project key is the absolute, normalized `git rev-parse --git-common-dir` of `start`, the same for every worktree
of one repository; outside a git repository it is the resolved `start` path. The folder is
`<repo-folder-name>-<first 10 hex of sha1 of the key>`. On Windows its git calls start with CREATE_NO_WINDOW. Nothing
runs on import. `main_checkout` is None when git cannot tell (not a repository, a deleted folder); for a bare
repository it is the git folder itself."""
import hashlib
import os
import subprocess
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000  # Windows process creation flag: a console program started by a hidden process opens no window


def git_common_dir(start):
    """The real path of the git common dir of `start`, or None when git cannot tell."""
    start = Path(start).resolve()
    try:
        result = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=start, capture_output=True,
                                text=True, encoding="utf-8", timeout=30,
                                creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)  # no console flashes in hooks
        common = result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        common = ""
    return Path(os.path.realpath(start / common)) if common else None


def project_key(start):
    """The normalized absolute path that identifies the project of `start`."""
    common = git_common_dir(start)
    return os.path.normcase(str(common if common else os.path.realpath(Path(start).resolve())))


def main_checkout(start):
    """The main checkout of the repository of `start`: the parent of its git common dir; None outside a repository."""
    common = git_common_dir(start)
    if common is None:
        return None
    return common.parent if common.name.lower() == ".git" else common


def folder_name(start):
    """`<repo folder name>-<10 hex>` of the project of `start`: the same for every worktree of one repository."""
    key = project_key(start)
    # The repository folder is the parent of the .git folder; a bare repo or a non-git folder uses its own name.
    base = Path(key)
    name = base.parent.name if base.name.lower() == ".git" else base.name
    return f"{name}-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:10]}"
