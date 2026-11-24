"""SessionEnd hook: write the ending session's spend file (see `scripts/spend.py`, `hook_end`).

It starts `spend.py write-session --path <transcript>` detached and returns at once (the files of a long session take
longer to read than the hook's 10 seconds). It prints nothing and never blocks: any error ends it with exit code 0."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

if __name__ == "__main__":
    try:
        import spend
        spend.hook_main()
    except Exception:
        pass
    sys.exit(0)
