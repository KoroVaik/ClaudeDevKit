"""Start the project's application with its run-app commands, or tear it down with its stop-app commands.

    dev-kit-app start|stop|list [--project <folder>]

The commands are the `run-app` and `stop-app` rows of the `## Slots` table in the project's `.claude/dev-kit.md`,
one row per command, both lists written in start order. `start` runs the run-app rows in order and stops at the first
failure; `stop` runs the stop-app rows in reverse and goes on after a failure, so as much as possible is torn down;
`list` prints both lists. A row runs only when its whole value is one command in backticks; a skill or prose is
followed by hand, and the runner then refuses before running anything. Each command runs in the project root through
the system shell. What a command may stop (the owner's processes) is decided by the project's own helpers; this only
sequences them. Exit code: 0 done, 1 a command failed, 2 not run (no profile, a row that is not a command).
"""
import argparse
import os
import re
import subprocess
import sys

PROFILE = os.path.join(".claude", "dev-kit.md")
START, STOP = "run-app", "stop-app"
COMMAND = re.compile(r"^`([^`]+)`$")


class NotRun(Exception):
    """The run cannot start: exit code 2."""


def find_root(start):
    folder = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(folder, PROFILE)):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            raise NotRun(f"no {PROFILE} in {os.path.abspath(start)} or above")
        folder = parent


def _cells(line):
    # A command may hold a pipe written as \| inside the table cell.
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [cell.strip().replace("\\|", "|") for cell in cells]


def slot_rows(text):
    """Return (slot, raw value) for every row of the `## Slots` table, in file order."""
    rows, inside, fenced, table = [], False, False, []
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = re.match(r"^##\s+(.*?)\s*$", line)
        if heading:
            if inside:
                break
            inside = heading.group(1) == "Slots"
            continue
        if not inside:
            continue
        if line.lstrip().startswith("|"):
            table.append(line)
        elif table:
            break
    for line in table[2:]:
        cells = _cells(line)
        rows.append((cells[0], cells[1] if len(cells) > 1 else ""))
    return rows


def command_of(value):
    """The command of a row whose whole value is one command in backticks, else None."""
    match = COMMAND.match(value.strip())
    return match.group(1).strip() if match else None


def commands(text, slot):
    """The commands of a slot, in file order; NotRun if a row is not a plain command."""
    found = []
    for name, value in slot_rows(text):
        if name != slot:
            continue
        command = command_of(value)
        if command is None:
            raise NotRun(f"{slot} row '{value}' is not one command in backticks; follow it by hand")
        found.append(command)
    return found


def run(command, root):
    print(f"> {command}", flush=True)
    return subprocess.run(command, shell=True, cwd=root).returncode


def start(text, root):
    steps = commands(text, START)
    if not steps:
        raise NotRun(f"the profile fills no {START}")
    for command in steps:
        code = run(command, root)
        if code != 0:
            print(f"{START}: '{command}' failed with exit code {code}; the later commands did not run. "
                  f"Run 'dev-kit-app stop' when the work is done.", flush=True)
            return 1
    print(f"{START}: {len(steps)} command(s) done.", flush=True)
    return 0


def stop(text, root):
    steps = commands(text, STOP)
    if not steps:
        print(f"{STOP}: the profile fills no {STOP}; nothing was stopped.", flush=True)
        return 0
    failed = [command for command in reversed(steps) if run(command, root) != 0]
    for command in failed:
        print(f"{STOP}: '{command}' failed.", flush=True)
    if not failed:
        print(f"{STOP}: {len(steps)} command(s) done, in reverse order.", flush=True)
    return 1 if failed else 0


def show(text):
    for slot, order in ((START, "in this order"), (STOP, "in reverse of this order")):
        rows = [value for name, value in slot_rows(text) if name == slot]
        print(f"{slot} ({order}):" if rows else f"{slot}: not filled")
        for value in rows:
            command = command_of(value)
            print(f"  {command}" if command else f"  not a command, followed by hand: {value}")
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="dev-kit-app", description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["start", "stop", "list"])
    parser.add_argument("--project", default=".", help="the project folder or a folder inside it")
    args = parser.parse_args(argv)
    try:
        root = find_root(args.project)
        with open(os.path.join(root, PROFILE), encoding="utf-8-sig") as profile:
            text = profile.read()
        if args.action == "list":
            return show(text)
        return start(text, root) if args.action == "start" else stop(text, root)
    except NotRun as exc:
        print(f"dev-kit-app: not run: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
