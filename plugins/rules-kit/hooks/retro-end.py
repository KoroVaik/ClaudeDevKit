"""SessionEnd hook: collect the ending session's findings (see `scripts/retro.py`, `hook_end`).

In a project that has a lead it starts a detached scan of the session's transcript and returns at once. It prints
nothing and never blocks: any error ends it with exit code 0."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

if __name__ == "__main__":
    try:
        import retro
        retro.hook_main("end")
    except Exception:
        pass
    sys.exit(0)
