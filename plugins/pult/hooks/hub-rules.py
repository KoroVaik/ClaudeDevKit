"""SessionStart hook: give the Pult hub rules to a session that runs in the home folder.

This hook runs in every session on the machine (plugins/dev-kit/claude-facts.md, "A `SessionStart` hook of a
user-scope plugin runs in every session on the machine"). It stays silent unless the
session's cwd is exactly the home folder (a project folder under home gets nothing). The rules are `rules/hub.md`;
`{PLUGIN}` in them is replaced with this plugin's folder, `{VERSION}` with its version (`.claude-plugin/plugin.json`,
`unknown` when unreadable) and `{DEVKIT}` with the dev-kit plugin's folder (a sibling
of this plugin; in the plugin cache the newest version folder that holds `bin/dev-kit-sessions`).
Never fails: any error ends it with exit code 0 and no output."""
import json
import os
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
RULES = PLUGIN / "rules" / "hub.md"


def norm(path):
    """Resolved path as a lower-case string with forward slashes, to compare folders."""
    return os.path.normcase(str(Path(path).resolve())).replace("\\", "/").rstrip("/").lower()


def dev_kit_folder():
    """The dev-kit plugin folder next to this plugin (source layout), or its newest cached version folder."""
    sibling = PLUGIN.parent / "dev-kit"
    if (sibling / "bin" / "dev-kit-sessions").is_file():
        return sibling
    cached = PLUGIN.parent.parent / "dev-kit"  # cache layout: <marketplace>/<plugin>/<version>
    versions = [p for p in cached.iterdir() if (p / "bin" / "dev-kit-sessions").is_file()] if cached.is_dir() else []
    return max(versions, key=lambda p: p.stat().st_mtime, default=sibling)


def plugin_version():
    """This plugin's version from its manifest, or `unknown`."""
    try:
        return str(json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8-sig"))["version"])
    except Exception:
        return "unknown"


def main():
    try:
        call = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))  # unreadable input: no output
        cwd = str(call.get("cwd") or "")  # a missing field falls back to the process cwd
        if norm(cwd or os.getcwd()) != norm(Path.home()):
            return
        text = RULES.read_text(encoding="utf-8")
        text = text.replace("{VERSION}", plugin_version())
        text = text.replace("{PLUGIN}", PLUGIN.as_posix()).replace("{DEVKIT}", dev_kit_folder().resolve().as_posix())
        sys.stdout.reconfigure(encoding="utf-8")
        json.dump({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}}, sys.stdout)
    except Exception:
        return


if __name__ == "__main__":
    main()
    sys.exit(0)
