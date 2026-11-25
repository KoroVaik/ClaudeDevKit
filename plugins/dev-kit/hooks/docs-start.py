"""SessionStart hook: start the weekly «Docs:» session of the project (see `scripts/docs_weekly.py`, `hook-start`).

In a project that has a lead it starts the background docs session when it is due and the retro's run file shows no retro
to wait for. It prints nothing and never blocks: any error ends it with exit code 0."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

if __name__ == "__main__":
    try:
        import docs_weekly
        docs_weekly.hook_main()
    except Exception:
        pass
    sys.exit(0)
