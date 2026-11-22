"""SessionStart hook: feed the project's retro (see `scripts/retro.py`, `hook_start`).

In a project that has a lead it records the lead's session id, starts the daily scan and, when findings wait and the
last review is old, a background retro session. It prints nothing and never blocks: any error ends it with exit
code 0."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

if __name__ == "__main__":
    try:
        import retro
        retro.hook_main("start")
    except Exception:
        pass
    sys.exit(0)
