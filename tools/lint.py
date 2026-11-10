"""Lint the ClaudeDevKit marketplace: manifests, hooks, skills, agents, slot tables and project profiles
(including the `## documentation` settings table)."""
import json
import re
import sys
from pathlib import Path

CORE_PLUGIN = "dev-kit"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "plugins" / CORE_PLUGIN / "scripts"))
import check_docs  # noqa: E402  the documentation settings are validated by the code that reads them
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REFERENCE = re.compile(r"^([\w-]+):([\w.-]+)$")
SEPARATOR = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")
BLOCK_SCALARS = {">", "|", ">-", "|-"}
PROFILE_SECTIONS_SKIPPED = {"All agents", "Slots"}
CORE_HEADER = ["Slot", "What it must do"]
EXTENSION_HEADER = ["Slot", "Skill"]
PROFILE_HEADER = ["Slot", "Skill or command"]
# Tables that a skill reads from a profile section: the section name -> the headers its tables may have.
PROFILE_TABLES = {
    "manager": [["Task", "Skill"], ["Type", "Model", "When", "Returns"]],
    "fix-bug": [["The report sounds like...", "It is a...", "UI check, if authorized"]],
    "user-check": [["Setting", "Value"]],
}


class Findings:
    def __init__(self):
        self.items = []

    def error(self, path, message):
        self.items.append(("error", str(path), message))

    def warning(self, path, message):
        self.items.append(("warning", str(path), message))

    def count(self, level):
        return sum(1 for item in self.items if item[0] == level)


def rel(root, path):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def read_text(root, path, findings):
    """Read a file as UTF-8 (a BOM is dropped); report a failure and return None."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        findings.error(rel(root, path), f"not valid UTF-8: {exc.reason}")
    except OSError as exc:
        findings.error(rel(root, path), f"cannot read file: {exc.strerror}")
    return None


def read_json(root, path, findings):
    """Read a JSON object; report a failure and return None."""
    text = read_text(root, path, findings)
    if text is None:
        return None
    try:
        data = json.loads(text)
    except ValueError as exc:
        findings.error(rel(root, path), f"invalid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        findings.error(rel(root, path), "JSON root must be an object")
        return None
    return data


def strip_quotes(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text):
    """Return the simple `key: value` fields between the leading `---` lines, or None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    fields = {}
    key = None
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        match = re.match(r"^([\w-]+)\s*:\s*(.*)$", line)
        if match:
            key = match.group(1)
            value = match.group(2).strip()
            fields[key] = "" if value in BLOCK_SCALARS else strip_quotes(value)
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return None


def strip_fences(text):
    """Blank out fenced code blocks (the fence lines included), keeping the line count."""
    lines = []
    inside = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            inside = not inside
            lines.append("")
        else:
            lines.append("" if inside else line)
    return "\n".join(lines)


def table_cells(line):
    return [cell.strip().replace("`", "").strip() for cell in line.strip().strip("|").split("|")]


def parse_table(text):
    """Return (header, rows) of the first table in text, or None.

    A table is a run of contiguous `|` lines outside fenced code. It must have a `|---|`
    separator as its second line; without one there is no usable header.
    """
    block = []
    for line in strip_fences(text).splitlines():
        if line.lstrip().startswith("|"):
            block.append(line)
        elif block:
            break
    if len(block) < 2 or not SEPARATOR.match(block[1].strip()):
        return None
    return table_cells(block[0]), [table_cells(line) for line in block[2:]]


def parse_tables(text):
    """Return (header, rows) of every table in text; header is None for a block without a |---| separator."""
    blocks, block = [], []
    for line in strip_fences(text).splitlines() + [""]:
        if line.lstrip().startswith("|"):
            block.append(line)
        elif block:
            blocks.append(block)
            block = []
    tables = []
    for block in blocks:
        if len(block) < 2 or not SEPARATOR.match(block[1].strip()):
            tables.append((None, []))
        else:
            tables.append((table_cells(block[0]), [table_cells(line) for line in block[2:]]))
    return tables


def section(text, title):
    """Return the body of the `## title` section, or None if there is no such section."""
    body = []
    inside = False
    for line in strip_fences(text).splitlines():
        heading = re.match(r"^##\s+(.*?)\s*$", line)
        if heading:
            if inside:
                break
            inside = heading.group(1) == title
        elif inside:
            body.append(line)
    return "\n".join(body) if inside else None


def headings(text):
    return [m.group(1) for m in re.finditer(r"^##\s+(.*?)\s*$", strip_fences(text), re.MULTILINE)]


def plugin_dirs(root):
    return sorted(p for p in (root / "plugins").glob("*") if p.is_dir())


def skill_names(root, plugin):
    folders = (root / "plugins" / plugin / "skills").glob("*")
    return {folder.name for folder in folders if (folder / "SKILL.md").is_file()}


def agent_names(root, plugin):
    return {agent.stem for agent in (root / "plugins" / plugin / "agents").glob("**/*.md")}


def check_entry(root, where, entry, names, findings):
    """Check one marketplace entry; return its resolved source folder or None."""
    if not isinstance(entry, dict):
        findings.error(where, "plugin entry must be an object")
        return None
    name = entry.get("name")
    if not isinstance(name, str) or not name:
        findings.error(where, "plugin entry without a name")
        return None
    if name in names:
        findings.error(where, f"plugin '{name}' is listed twice")
    names.add(name)
    source = entry.get("source")
    if not isinstance(source, str) or not source:
        findings.error(where, f"plugin {name}: source must be a non-empty string")
        return None
    manifest = root / source / ".claude-plugin" / "plugin.json"
    if not manifest.is_file():
        findings.error(where, f"plugin {name}: {rel(root, manifest)} not found")
    else:
        data = read_json(root, manifest, findings)
        if data is not None and data.get("name") != name:
            findings.error(rel(root, manifest), f"name '{data.get('name')}' differs from marketplace entry '{name}'")
    return (root / source).resolve()


def check_marketplace(root, findings):
    """Return the names of the marketplace entries."""
    path = root / ".claude-plugin" / "marketplace.json"
    where = rel(root, path)
    data = read_json(root, path, findings)
    if data is None:
        return set()
    entries = data.get("plugins")
    if not isinstance(entries, list) or not entries:
        findings.error(where, "plugins list is missing or empty")
        return set()
    names = set()
    sources = {check_entry(root, where, entry, names, findings) for entry in entries}
    for folder in plugin_dirs(root):
        if folder.resolve() not in sources:
            findings.error(rel(root, folder), "folder is not referenced by any marketplace entry")
    return names


def check_skills(root, findings):
    for folder in sorted(p for p in root.glob("plugins/*/skills/*") if p.is_dir()):
        skill = folder / "SKILL.md"
        where = rel(root, skill)
        if not skill.is_file():
            findings.error(rel(root, folder), "SKILL.md not found")
            continue
        text = read_text(root, skill, findings)
        if text is None:
            continue
        fields = parse_frontmatter(text)
        if fields is None:
            findings.error(where, "missing or unclosed frontmatter")
            continue
        description = fields.get("description", "")
        if not description:
            findings.error(where, "description is missing or empty")
        elif not description.startswith("Use when"):
            findings.error(where, "description must start with 'Use when'")
        if fields.get("name") and fields["name"] != folder.name:
            findings.error(where, f"name '{fields['name']}' differs from folder '{folder.name}'")


def check_agents(root, findings):
    for agent in sorted(p for p in root.glob("plugins/*/agents/**/*.md") if p.is_file()):
        where = rel(root, agent)
        text = read_text(root, agent, findings)
        if text is None:
            continue
        fields = parse_frontmatter(text)
        if fields is None:
            findings.error(where, "missing or unclosed frontmatter")
            continue
        for key in ("name", "description", "model"):
            if not fields.get(key):
                findings.error(where, f"{key} is missing or empty")
        if fields.get("name") and fields["name"] != agent.stem:
            findings.error(where, f"name '{fields['name']}' differs from file name '{agent.stem}'")


def check_hooks(root, findings):
    for path in sorted(root.glob("plugins/*/hooks/hooks.json")):
        read_json(root, path, findings)


def read_slot_table(root, path, header, findings):
    """Return the rows of the slot table at the top of a slots file, or None after reporting."""
    text = read_text(root, path, findings)
    if text is None:
        return None
    table = parse_table(text)
    if table is None or table[0] != header:
        shown = "| " + " | ".join(header) + " |"
        findings.error(rel(root, path), f"table with header '{shown}' and a |---| separator not found")
        return None
    return table[1]


def check_core_slots(root, findings):
    """Return the list of core slot names."""
    path = root / "plugins" / CORE_PLUGIN / "slots.md"
    if not path.is_file():
        findings.error(rel(root, path), "core slots file not found")
        return []
    rows = read_slot_table(root, path, CORE_HEADER, findings)
    slots = []
    for row in rows or []:
        name = row[0]
        if not KEBAB.match(name):
            findings.error(rel(root, path), f"slot '{name}' is not kebab-case")
        if name in slots:
            findings.error(rel(root, path), f"slot '{name}' is listed twice")
        slots.append(name)
    return slots


def check_extension_slots(root, plugins, core_slots, findings):
    filled = {}
    for plugin_dir in plugin_dirs(root):
        path = plugin_dir / "slots.md"
        if plugin_dir.name == CORE_PLUGIN or not path.is_file():
            continue
        where = rel(root, path)
        for row in read_slot_table(root, path, EXTENSION_HEADER, findings) or []:
            slot, skill_ref = row[0], row[1] if len(row) > 1 else ""
            if slot not in core_slots:
                findings.error(where, f"slot '{slot}' is not in the core list")
            reference = REFERENCE.match(skill_ref)
            if not reference or reference.group(1) not in plugins:
                findings.error(where, f"skill '{skill_ref}' must be <plugin>:<skill> of a marketplace plugin")
            elif reference.group(2) not in skill_names(root, reference.group(1)):
                findings.error(where, f"skill '{skill_ref}' does not exist")
            if slot in filled and filled[slot] != plugin_dir.name:
                findings.warning(where, f"slot '{slot}' is also filled by {filled[slot]}")
            filled.setdefault(slot, plugin_dir.name)


def role_exists(root, plugins, name):
    """True if name is an agent or skill of a marketplace plugin; `plugin:name` is looked up in that plugin."""
    reference = REFERENCE.match(name)
    if reference:
        plugin, short = reference.groups()
        return plugin in plugins and short in skill_names(root, plugin) | agent_names(root, plugin)
    return any(name in skill_names(root, p) | agent_names(root, p) for p in plugins)


def check_profile_value(root, plugins, where, value, findings):
    if not value:
        findings.error(where, "slot with an empty value")
        return
    value = value.removeprefix("/")
    plugin = next((p for p in plugins if value.startswith((p + ":", p + "/"))), None)
    if plugin is None:
        return
    reference = REFERENCE.match(value)
    if not reference:
        findings.error(where, f"'{value}' must be written as <plugin>:<name>")
    elif reference.group(2) not in skill_names(root, plugin) | agent_names(root, plugin):
        findings.error(where, f"'{value}' is not a skill or agent of {plugin}")


def check_profile_tables(root, plugins, where, text, findings):
    """Check the tables of the profile sections that a skill reads (PROFILE_TABLES)."""
    for name, allowed in PROFILE_TABLES.items():
        body = section(text, name)
        for header, rows in parse_tables(body) if body is not None else []:
            if header not in allowed:
                shown = " or ".join("| " + " | ".join(h) + " |" for h in allowed)
                findings.error(where, f"section '{name}': table must have header {shown} and a |---| separator")
                continue
            for row in rows:
                if len(row) != len(header):
                    findings.error(where, f"section '{name}': row '{row[0]}' has {len(row)} cells, expected {len(header)}")
                elif name == "manager":
                    column = 0 if header[0] == "Type" else 1
                    for value in filter(None, (v.strip() for v in row[column].split(","))):
                        check_profile_value(root, plugins, where, value, findings)


def check_profile(root, plugins, core_slots, profile, findings):
    where = rel(root, profile)
    text = read_text(root, profile, findings)
    if text is None:
        return
    slots_body = section(text, "Slots")
    if slots_body is not None:
        table = parse_table(slots_body)
        if table is None or table[0] != PROFILE_HEADER:
            findings.error(where, "Slots table with header '| Slot | Skill or command |' and a |---| separator not found")
        for row in table[1] if table and table[0] == PROFILE_HEADER else []:
            if row[0] not in core_slots:
                findings.error(where, f"slot '{row[0]}' is not in the core list")
            check_profile_value(root, plugins, where, row[1] if len(row) > 1 else "", findings)
    check_profile_tables(root, plugins, where, text, findings)
    for message in check_docs.profile_errors(text):
        findings.error(where, f"documentation section: {message}")
    for heading in headings(text):
        if heading not in PROFILE_SECTIONS_SKIPPED and not role_exists(root, plugins, heading):
            findings.error(where, f"section '{heading}' names no agent or skill of a marketplace plugin")


def check_profiles(root, plugins, core_slots, projects, findings):
    for project, folder in projects.items():
        profile = Path(folder) / ".claude" / "dev-kit.md"
        if not profile.is_file():
            findings.warning(project, f"no profile at {profile} (not yet migrated)")
            continue
        check_profile(root, plugins, core_slots, profile, findings)


def load_projects(root, findings):
    path = root / "tools" / "projects.json"
    if not path.is_file():
        return {}
    data = read_json(root, path, findings) or {}
    bad = [name for name, folder in data.items() if not isinstance(folder, str)]
    for name in bad:
        findings.error(rel(root, path), f"project '{name}': folder must be a string")
    return {name: folder for name, folder in data.items() if name not in bad}


def lint(root, projects=None):
    """Run every check; projects maps a project name to its folder (None reads tools/projects.json)."""
    root = Path(root)
    findings = Findings()
    if projects is None:
        projects = load_projects(root, findings)
    plugins = check_marketplace(root, findings)
    check_hooks(root, findings)
    check_skills(root, findings)
    check_agents(root, findings)
    core_slots = check_core_slots(root, findings)
    check_extension_slots(root, plugins, core_slots, findings)
    check_profiles(root, plugins, core_slots, projects, findings)
    return findings


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    findings = lint(root)
    for level, path, message in findings.items:
        print(f"{level}: {path}: {message}")
    errors, warnings = findings.count("error"), findings.count("warning")
    print(f"{errors} error(s), {warnings} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
