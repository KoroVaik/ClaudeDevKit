"""Show which project-level changes ("migrations") of dev-kit a project has not applied yet, and record the level.

    dev-kit-migrations pending [--project DIR]
    dev-kit-migrations record <n> [--project DIR]

The list is `migrations.md` of the plugin (next to the scripts folder): entries `## <n>. <title>` numbered 1, 2, 3...
in order, each with the fields Added, What, How, Owner choice and Done when (`- Field: text`, the text may go on
in the following lines). The applied level is the row `| migrations applied | <n> |` in the `| Setting | Value |` table
of the `## project-lead` section of the project's `.claude/dev-kit.md`; a missing file, section or row means 0.

`pending` prints one line `<n>. <title>` per entry above the applied level, then `file: <absolute path of
migrations.md>`; it prints `none` when nothing is pending. `record` writes the row (it creates the file, the section
at the end or the table right under the section heading when missing) and leaves all other content as it was; it
refuses a value below the applied level or above the last entry.

Exit code: 0 done, 2 a malformed migrations.md, an unreadable profile, a non-integer applied value or a refused value.
"""
import argparse
import re
import sys
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations.md"
PROFILE = Path(".claude") / "dev-kit.md"
FIELDS = ("Added", "What", "How", "Owner choice", "Done when")
BOM = chr(0xFEFF)
SECTION = "project-lead"
ROW = "migrations applied"
TABLE_HEADER = ["Setting", "Value"]
NEW_PROFILE_HEADING = "# dev-kit profile"
ENTRY_HEADING = re.compile(r"^##\s+(\d+)\.\s*(.*?)\s*$")
FIELD_LINE = re.compile(r"^-\s+(" + "|".join(FIELDS) + r"):\s*(.*?)\s*$")
SEPARATOR = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")
SECTION_HEADING = re.compile(r"^##\s+(.*?)\s*$")


class Problem(Exception):
    """Something to report on stderr: exit code 2."""


def parse(text):
    """The entries of a migrations file as a list of (number, title, fields); Problem when it is malformed."""
    entries = []
    current = None  # [number, title, fields]
    field = None
    in_fence = False
    for lineno, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            if current and field:
                current[2][field] += "\n" + line
            continue
        if not in_fence and line.startswith("## "):
            match = ENTRY_HEADING.match(line)
            if not match:
                raise Problem(f"migrations line {lineno}: heading '{line}' is not '## <number>. <title>'")
            if current:
                entries.append(close(current))
            number, title = int(match.group(1)), match.group(2)
            if number != len(entries) + 1:
                raise Problem(f"migrations line {lineno}: entry {number} where {len(entries) + 1} is expected")
            if not title:
                raise Problem(f"migrations line {lineno}: entry {number} has no title")
            current, field = [number, title, {}], None
            continue
        if current is None:
            continue
        found = None if in_fence else FIELD_LINE.match(line)
        if found:
            field = found.group(1)
            if field in current[2]:
                raise Problem(f"migrations line {lineno}: entry {current[0]} has the field '{field}' twice")
            current[2][field] = found.group(2)
        elif field and (in_fence or line.strip()):
            current[2][field] += "\n" + (line if in_fence else line.strip())
        elif not in_fence:
            field = None
    if current:
        entries.append(close(current))
    return entries


def close(entry):
    number, title, fields = entry
    for name in FIELDS:
        if name not in fields:
            raise Problem(f"migrations entry {number}: the field '{name}' is missing")
        if not fields[name].strip():
            raise Problem(f"migrations entry {number}: the field '{name}' is empty")
    return number, title, fields


def read_text(path, what):
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise Problem(f"{what} {path} cannot be read: {exc}")


def load_entries():
    try:
        return parse(read_text(MIGRATIONS, "the migrations file").lstrip(BOM))
    except Problem as exc:
        raise Problem(f"{MIGRATIONS}: {exc}")


def cells(line):
    return [cell.strip().replace("`", "").strip() for cell in line.strip().strip("|").split("|")]


def split_lines(text):
    return text.splitlines(keepends=True)


def bare(line):
    return line.rstrip("\r\n")


def fenced(lines):
    """For each line whether it is inside a fenced code block or is a fence line."""
    flags, inside = [], False
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            flags.append(True)
        else:
            flags.append(inside)
    return flags


def find_section(lines, flags):
    """(start, end) of the `## project-lead` section: the heading line and the index after its last line."""
    start = None
    for index, line in enumerate(lines):
        match = None if flags[index] else SECTION_HEADING.match(bare(line))
        if not match:
            continue
        if start is not None:
            return start, index
        if match.group(1) == SECTION:
            start = index
    return (start, len(lines)) if start is not None else None


def find_table(lines, flags, start, end):
    """(first, after) line indexes of the `| Setting | Value |` table inside lines[start:end], or None."""
    index = start
    while index < end:
        if flags[index] or not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        first = index
        while index < end and not flags[index] and lines[index].lstrip().startswith("|"):
            index += 1
        if index - first >= 2 and SEPARATOR.match(bare(lines[first + 1]).strip()) \
                and cells(lines[first]) == TABLE_HEADER:
            return first, index
    return None


def find_row(lines, table):
    first, after = table
    return next((index for index in range(first + 2, after) if cells(lines[index])[0] == ROW), None)


def applied_level(project):
    """The applied level of a project: 0 when the profile, the section, the table or the row is missing."""
    path = Path(project) / PROFILE
    if not path.is_file():
        return 0
    lines = split_lines(read_text(path, "the profile").lstrip(BOM))
    flags = fenced(lines)
    section = find_section(lines, flags)
    table = find_table(lines, flags, section[0] + 1, section[1]) if section else None
    row = find_row(lines, table) if table else None
    if row is None:
        return 0
    value = cells(lines[row])[1:]
    if not value or not re.fullmatch(r"\d+", value[0]):
        raise Problem(f"{path}: the value of '{ROW}' is not a whole number: '{value[0] if value else ''}'")
    return int(value[0])


def new_table(value, newline):
    return [f"| {TABLE_HEADER[0]} | {TABLE_HEADER[1]} |{newline}", f"|---|---|{newline}", f"| {ROW} | {value} |{newline}"]


def with_newline(line, newline):
    return line if line.endswith(("\n", "\r")) else line + newline


def updated_profile(text, value):
    """The profile text with the row set to value; everything else stays as it was."""
    bom = BOM if text.startswith(BOM) else ""
    lines = split_lines(text[len(bom):])
    newline = "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"
    if not "".join(lines).strip():
        lines = [NEW_PROFILE_HEADING + newline]
    flags = fenced(lines)
    section = find_section(lines, flags)
    if section is None:
        lines[-1] = with_newline(lines[-1], newline)
        if bare(lines[-1]).strip():
            lines.append(newline)
        lines +=[f"## {SECTION}{newline}", newline] + new_table(value, newline)
        return bom + "".join(lines)
    start, end = section
    table = find_table(lines, flags, start + 1, end)
    if table is None:
        lines[start] = with_newline(lines[start], newline)
        at, before = start + 1, []
        if at < len(lines) and not bare(lines[at]).strip():
            at += 1
        else:
            before = [newline]
        after = [newline] if at < len(lines) and bare(lines[at]).strip() else []
        lines[at:at] = before + new_table(value, newline) + after
        return bom + "".join(lines)
    row = find_row(lines, table)
    if row is not None:
        ending = lines[row][len(bare(lines[row])):]
        lines[row] = f"| {ROW} | {value} |{ending}"
    else:
        last = table[1] - 1
        lines[last] = with_newline(lines[last], newline)
        lines.insert(table[1], f"| {ROW} | {value} |{newline}")
    return bom + "".join(lines)


def cmd_pending(args):
    entries = load_entries()
    applied = applied_level(args.project)
    pending = [entry for entry in entries if entry[0] > applied]
    if not pending:
        print("none")
        return 0
    for number, title, _ in pending:
        print(f"{number}. {title}")
    print(f"file: {MIGRATIONS.resolve()}")
    return 0


def cmd_record(args):
    entries = load_entries()
    applied = applied_level(args.project)
    last = entries[-1][0] if entries else 0
    if args.n < applied:
        raise Problem(f"{args.n} is below the applied level {applied}")
    if args.n > last:
        raise Problem(f"{args.n} is above the last entry {last}")
    path = Path(args.project) / PROFILE
    text = read_text(path, "the profile") if path.is_file() else ""
    new = updated_profile(text, args.n)
    if new != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(new.encode("utf-8"))
    print(f"migrations applied: {args.n}")
    return 0


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="dev-kit-migrations", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action", required=True)
    pending = sub.add_parser("pending")
    record = sub.add_parser("record")
    record.add_argument("n", type=int)
    for command in (pending, record):
        command.add_argument("--project", default=".", help="the project folder (default: current)")
    args = parser.parse_args(argv)
    try:
        return {"pending": cmd_pending, "record": cmd_record}[args.action](args)
    except Problem as exc:
        print(f"dev-kit-migrations: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
