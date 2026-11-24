"""Find the `claude` command (a copy of dev-kit's `sessions.find_claude`: no plugin imports another's code), to start the
background retro session.

    find_claude() -> str | None    on PATH (on Windows an npm install is claude.CMD, which a bare name misses), else the
                                   first usual install place that holds it; None when there is none"""
import os
import shutil
from pathlib import Path


def claude_candidates():
    """The usual install places of the claude command, for a shell whose PATH lacks it (a subagent's or a hidden
    window's): the native installer, the npm global folders, Homebrew and /usr/local."""
    home = Path.home()
    places = [home / ".local" / "bin", home / ".claude" / "local", home / ".npm-global" / "bin",
              Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    for env in ("APPDATA", "LOCALAPPDATA"):
        if os.environ.get(env):
            places.append(Path(os.environ[env]) / "npm")
    names = ("claude.exe", "claude.cmd", "claude") if os.name == "nt" else ("claude",)
    return [place / name for place in places for name in names]


def find_claude():
    """The claude command: on PATH, else the first usual install place that holds it; None when there is none."""
    found = shutil.which("claude")
    if found:
        return found
    return next((str(path) for path in claude_candidates() if path.is_file()), None)
