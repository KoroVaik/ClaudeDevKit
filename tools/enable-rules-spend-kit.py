"""Enable the spend-kit and rules-kit plugins in the user's Claude Code settings and point the status line at spend-kit.

    python -X utf8 tools/enable-rules-spend-kit.py [SETTINGS_FILE] [--dry-run]

SETTINGS_FILE defaults to `~/.claude/settings.json`. The script changes only two things:
- `enabledPlugins`: adds `"spend-kit@korov-dev": true` and `"rules-kit@korov-dev": true` (a missing or false entry
  becomes true); no other plugin entry is touched or removed;
- `statusLine.command`: becomes `python -X utf8 <repo>/plugins/spend-kit/scripts/statusline.py`, where `<repo>` is the
  repository this script lives in (the other keys of `statusLine` stay; a missing `statusLine` becomes
  `{"type": "command", "command": ...}`).
Nothing else is changed or deleted. Before any write the file is copied next to itself as
`settings.json.bak-YYYYMMDD-HHMMSS`. A second run finds nothing to change, writes nothing and makes no backup. It
prints each change, or `nothing to change`; with `--dry-run` it prints the same lines and writes nothing. The settings
file is JSON; one that cannot be read as JSON object is left alone (exit 1).

Run it once after the merge that adds the two plugins: until then the status line (spend-kit) and the retro stop
(`plans/retro-auto-rules-check.md`). Exit codes: 0 done or nothing to do, 1 the settings file is unreadable."""
import argparse
import datetime
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MARKETPLACE = "korov-dev"
PLUGINS = ("spend-kit", "rules-kit")


def status_line_command(repo=REPO):
    return f"python -X utf8 {Path(repo).resolve().as_posix()}/plugins/spend-kit/scripts/statusline.py"


def indent_of(text):
    """The indent of the first indented line of a JSON text (default 2)."""
    for line in text.splitlines():
        stripped = line.lstrip(" \t")
        if stripped and stripped != line and not stripped.startswith(("}", "]")):
            return line[:len(line) - len(stripped)]
    return 2


def wanted_changes(settings, repo=REPO):
    """Apply the changes to `settings` (a dict) in place; the list of lines that say what changed."""
    changes = []
    enabled = settings.get("enabledPlugins")
    if not isinstance(enabled, dict):
        enabled = settings["enabledPlugins"] = {}
    for name in PLUGINS:
        key = f"{name}@{MARKETPLACE}"
        if enabled.get(key) is not True:
            enabled[key] = True
            changes.append(f'enabledPlugins: "{key}" set to true')
    command = status_line_command(repo)
    line = settings.get("statusLine")
    if not isinstance(line, dict):
        line = settings["statusLine"] = {"type": "command"}
    if line.get("command") != command:
        changes.append(f'statusLine.command: {line.get("command")!r} -> {command!r}')
        line["command"] = command
    return changes


def run(path, dry_run=False, repo=REPO, out=None, now=None):
    out = out or sys.stdout
    path = Path(path)
    bom = False
    text = ""
    if path.exists():
        raw = path.read_bytes()
        bom = raw.startswith(b"\xef\xbb\xbf")
        text = raw.decode("utf-8-sig")
    try:
        settings = json.loads(text) if text.strip() else {}
    except ValueError as error:
        print(f"{path}: not valid JSON, left alone ({error})", file=sys.stderr)
        return 1
    if not isinstance(settings, dict):
        print(f"{path}: not a JSON object, left alone", file=sys.stderr)
        return 1
    changes = wanted_changes(settings, repo)
    if not changes:
        print("nothing to change", file=out)
        return 0
    for change in changes:
        print(change, file=out)
    if dry_run:
        print("dry run: nothing written", file=out)
        return 0
    if path.exists():
        stamp = (now or datetime.datetime.now()).strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.bak-{stamp}")
        shutil.copy2(path, backup)
        print(f"backup: {backup}", file=out)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(settings, indent=indent_of(text) if text else 2, ensure_ascii=False) + "\n"
    path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + body.encode("utf-8"))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Enable spend-kit and rules-kit and point the status line at spend-kit.")
    parser.add_argument("settings", nargs="?", default=str(Path.home() / ".claude" / "settings.json"))
    parser.add_argument("--dry-run", action="store_true", help="print the changes and write nothing")
    args = parser.parse_args(argv)
    return run(args.settings, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
