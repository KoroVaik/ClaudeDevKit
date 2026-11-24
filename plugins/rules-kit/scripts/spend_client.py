"""Run the `spend-kit` command (plugins/spend-kit) from a rules-kit script as a process: rules-kit never imports
spend-kit's code, it only runs its command or reads its files (`~/.claude/spend-kit/`). The same small runner as
dev-kit's `spend_client.py` (no plugin imports another's code).

    command() -> list | None        the argv that runs `spend-kit` (add the subcommand), None when it is not found
    run(args, timeout) -> CompletedProcess | None
                                    run `spend-kit <args>` and capture its output as UTF-8; None when the command is not
                                    found, cannot start or runs over `timeout` seconds

Where it is looked for: env SPEND_KIT_BIN (a path to `bin/spend-kit` or `scripts/spend.py`), the `spend-kit` file on PATH
(the enabled plugin's `bin` folder), then the folder of the spend-kit plugin next to this one (the repository layout
`plugins/spend-kit`, or the newest version folder in the plugin cache `<marketplace>/spend-kit/<version>`)."""
import os
import subprocess
import sys
from pathlib import Path

BIN_ENV = "SPEND_KIT_BIN"
CREATE_NO_WINDOW = 0x08000000


def sibling_script():
    """`scripts/spend.py` of the spend-kit plugin folder next to this plugin, or None."""
    plugin = Path(__file__).resolve().parents[1]
    direct = plugin.parent / "spend-kit" / "scripts" / "spend.py"
    if direct.is_file():
        return direct
    cached = plugin.parent.parent / "spend-kit"  # cache layout: <marketplace>/<plugin>/<version>
    versions = [p / "scripts" / "spend.py" for p in cached.iterdir()] if cached.is_dir() else []
    versions = [p for p in versions if p.is_file()]
    return max(versions, key=lambda p: p.stat().st_mtime, default=None)


def command():
    """The argv that runs `spend-kit` (see the module doc), or None."""
    found = os.environ.get(BIN_ENV)
    if not found:
        for folder in os.environ.get("PATH", "").split(os.pathsep):
            if folder and (Path(folder) / "spend-kit").is_file():
                found = str(Path(folder) / "spend-kit")
                break
    if not found:
        sibling = sibling_script()
        found = str(sibling) if sibling else None
    return [sys.executable, "-X", "utf8", found] if found and Path(found).is_file() else None


def run(args, timeout):
    """Run `spend-kit <args>`; the finished process with its text output, or None (see the module doc)."""
    argv = command()
    if not argv:
        return None
    try:
        return subprocess.run([*argv, *args], capture_output=True, timeout=timeout, encoding="utf-8", errors="replace",
                              creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        return None
