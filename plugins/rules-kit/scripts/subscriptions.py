"""Rule sets and their subscriptions: parse `rules-subscription.md`, find the sets and answer who owns a file.

A set is a group of rule files with one place where it lives (its root), one project that reviews it and one way a
change lands in it: a plugin folder, the owner's global folder, a project. Each set has a subscription file
`rules-subscription.md` that the retro reads. It is Markdown; only its tables are read, the prose is for readers.

    # Rules subscription: <set name>

    | Setting | Value |                       settings table, before the first `##` heading
    |---|---|
    | set | dev-kit |                          required; the set's name (letters, digits, `.`, `_`, `-`)
    | reviewed by | ClaudeDevKit |             required; the project whose retro handles the set
    | lands by | branch merged by L: ... |     required; how a change reaches the set (free text for the retro)
    | special editor | ... |                    optional; a file with its own editor agent: the retro passes findings

    ## Files                                    required, at least one row
    | Path (glob, relative to the set root) | Type | Part kinds | Section |
    |---|---|---|---|
    | skills/project-lead/SKILL.md | process | skill dev-kit:project-lead | |
    | hooks/*.py | technical | hook dev-kit | |

    ## Signs                                    optional: `| Sign | Kind | Pattern |`, Kind is a type
    ## May change itself                        optional: `| Path | Changes |`, Path is a glob

- Path: a glob relative to the set root, `/` only. `*` and `?` stay inside one folder, `**` as a whole segment
  crosses folders (`.claude/**/*.md`, `skills/**`), `[abc]` is a class. No absolute path, no `..`. Several rows may
  match one file: the first row that matches wins.
- Type: `talk` (how sessions talk to the owner; a script checks every reply), `technical` (tool traces: calls,
  failures, repeats), `process` (a part reader on the part of a session with a sign).
- Part kinds: `skill <plugin>:<name>`, `agent <plugin>:<name>`, `hook <plugin>` (a hook's plugin comes from its command
  path; `hook <plugin>:<name>` names one hook), separated by `,`; empty or `-` for none. A set is a candidate for a
  problem found in the part of a session where one of its part kinds was at work.
- Section (optional column): the text of a `#` or `##` heading of the file, so one file can hold rules of two types:
  a row with a Section types that part of the file, a row with the same Path and no Section types the rest.
- A Sign's Pattern is free text for the retro; text between `«` and `»` is a regular expression and is checked.
  A `|` inside `«...»` needs no escape; elsewhere write `\\|`.
- The subscription file itself is a file of its set (type process) unless a Files row already matches it.

Ownership: every file belongs to the one set whose root is the deepest folder that holds it, and only when that set
lists the file in Files (an unlisted file belongs to no set: code, data, a log). A path inside a project's worktree
(`<project>/.claude/worktrees/<name>/...`) counts as the same path in the project. A project's root is its repository;
its own set is the default (`CLAUDE.md`, `.claude/**/*.md`, type process) when it has a dev-kit profile and no file
`.claude/rules-subscription.md`.

Discovery (`discover`): the plugin folders next to this plugin (`<plugins>/*/rules-subscription.md`; env
RULES_KIT_PLUGINS_DIR replaces `<plugins>`), the owner's global folder (`rules-subscription.md` in env
RULES_KIT_GLOBAL_DIR, else `~/.claude`) and the projects the caller names. A file that does not parse is skipped and
reported in `Registry.errors`; two sets with one name keep the first. `ensure_global` writes the global file from
`templates/global-rules-subscription.md` when it is missing and commits it in the folder's git repository.

No plugin imports another's code; the retro (`retro.py`) imports this module."""
import os
import re
import subprocess
from collections import namedtuple
from pathlib import Path

PLUGINS_ENV = "RULES_KIT_PLUGINS_DIR"
GLOBAL_ENV = "RULES_KIT_GLOBAL_DIR"
FILE_NAME = "rules-subscription.md"
TEMPLATE = Path(__file__).resolve().parent.parent / "templates" / "global-rules-subscription.md"
TYPES = ("talk", "technical", "process")
PART_KINDS = ("skill", "agent", "hook")
SETTINGS = {"set": "set", "reviewed by": "reviewer", "lands by": "lands_by", "special editor": "special_editor"}
REQUIRED = ("set", "reviewed by", "lands by")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
PART_NAME = re.compile(r"^[\w.-]+(:[\w.-]+)?$")
SEPARATOR = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")
WORKTREE = re.compile(r"/\.claude/worktrees/[^/]+", re.IGNORECASE)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
EXPRESSION = re.compile(r"«(.*?)»", re.DOTALL)
DEFAULT_FILES = (("CLAUDE.md", "process"), (".claude/**/*.md", "process"))
GIT_TIMEOUT_S = 30

Rule = namedtuple("Rule", "pattern type kinds section")  # one row of Files; kinds: tuple of (kind, name)
Sign = namedtuple("Sign", "name kind pattern regex")  # regex: the compiled text between « and », or None
Owner = namedtuple("Owner", "set rule")


class Problem(ValueError):
    """The subscription file is invalid; the text says what and where."""


def fold(text):
    return text.lower() if os.name == "nt" else text


def canon(path):
    """A path as text with `/` only, a worktree of a project taken for the project, no trailing `/`."""
    text = WORKTREE.sub("", str(path).replace("\\", "/"))
    return re.sub(r"(?<!^)/+", "/", text).rstrip("/") or "/"


def compile_glob(pattern):
    """The compiled form of a path glob (module doc); `Problem` with the reason when it is not valid."""
    if not pattern:
        raise Problem("empty path")
    if "\\" in pattern:
        raise Problem(f"'{pattern}': write the path with `/`, not `\\`")
    if pattern.startswith("/") or re.match(r"^[A-Za-z]:", pattern):
        raise Problem(f"'{pattern}': the path must be relative to the set root")
    segments = pattern.split("/")
    if any(not segment for segment in segments):
        raise Problem(f"'{pattern}': empty path segment")
    if ".." in segments:
        raise Problem(f"'{pattern}': `..` leaves the set root")
    regex = ""
    for number, segment in enumerate(segments):
        last = number == len(segments) - 1
        if segment == "**":
            regex += ".*" if last else "(?:[^/]+/)*"
            continue
        if "**" in segment:
            raise Problem(f"'{pattern}': `**` must be a whole path segment")
        regex += _segment_regex(pattern, segment) + ("" if last else "/")
    return re.compile(regex + r"\Z", re.IGNORECASE if os.name == "nt" else 0)


def _segment_regex(pattern, segment):
    out = ""
    index = 0
    while index < len(segment):
        char = segment[index]
        if char == "*":
            out += "[^/]*"
        elif char == "?":
            out += "[^/]"
        elif char == "[":
            start = index + 1 + (segment[index + 1:index + 2] in ("!", "^"))
            close = segment.find("]", start + 1)
            if close < 0:
                raise Problem(f"'{pattern}': `[` without `]`")
            body = segment[index + 1:close]
            if body[:1] in ("!", "^"):
                body = "^" + body[1:]
            out += "[" + body.replace("[", "\\[") + "]"
            index = close
        elif char == "]":
            raise Problem(f"'{pattern}': `]` without `[`")
        else:
            out += re.escape(char)
        index += 1
    return out


def split_row(line):
    """The cells of a table row; `\\|` is a `|`, and a `|` inside `«...»` does not split."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    cells, current, depth, index = [], [], 0, 0
    while index < len(text):
        char = text[index]
        if char == "\\" and text[index + 1:index + 2] == "|":
            current.append("|")
            index += 2
            continue
        if char == "«":
            depth += 1
        elif char == "»" and depth:
            depth -= 1
        if char == "|" and not depth:
            cells.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    cells.append("".join(current))
    return [unwrap(cell.strip()) for cell in cells]


def unwrap(cell):
    """A cell written in backticks as code, without them."""
    return cell[1:-1].strip() if len(cell) >= 2 and cell[0] == "`" and cell[-1] == "`" and cell.count("`") == 2 else cell


def read_blocks(text):
    """The tables of `text` outside code fences as `(heading, header cells, [(line, cells)], line of the header)`;
    `heading` is the text of the last `##` heading before the table (None before the first one); a table with no
    `|---|` separator row has header None."""
    blocks = []
    heading = None
    block = []
    inside = False

    def flush():
        if not block:
            return
        first = block[0]
        if len(block) >= 2 and SEPARATOR.match(block[1][2]):
            blocks.append((heading, first[1], [(n, cells) for n, cells, _ in block[2:]], first[0]))
        else:
            blocks.append((heading, None, [], first[0]))
        block.clear()

    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("```"):
            flush()
            inside = not inside
            continue
        if inside:
            continue
        if line.lstrip().startswith("|"):
            block.append((number, split_row(line), line.strip()))
            continue
        flush()
        match = HEADING.match(line)
        if match and len(match.group(1)) == 2:
            heading = match.group(2)
    flush()
    return blocks


def parse_kinds(cell):
    """The part kinds of a cell: a tuple of (kind, name); `Problem` for an unknown kind or a bad name."""
    kinds = []
    for entry in re.split(r"[,;]", cell):
        entry = entry.strip()
        if not entry or entry == "-":
            continue
        words = entry.split()
        if len(words) != 2 or words[0] not in PART_KINDS:
            raise Problem(f"part kind '{entry}': write `skill <plugin>:<name>`, `agent <plugin>:<name>` or `hook <plugin>`")
        kind, name = words
        if not PART_NAME.match(name) or (kind != "hook" and ":" not in name):
            raise Problem(f"part kind '{entry}': a {kind} is named `<plugin>:<name>`" if kind != "hook"
                          else f"part kind '{entry}': a hook is named `<plugin>` or `<plugin>:<name>`")
        kinds.append((kind, name))
    return tuple(kinds)


class Subscription:
    """One parsed subscription (see the module doc). `root` is the set's folder; `source` the file it came from."""

    def __init__(self, name, reviewer, lands_by, special_editor, root, files, signs=(), may_change=(), source=None):
        self.name = name
        self.reviewer = reviewer
        self.lands_by = lands_by
        self.special_editor = special_editor
        self.root = Path(root)
        self.files = tuple(files)
        self.signs = tuple(signs)
        self.may_change = tuple(may_change)  # (path glob, changes text)
        self.source = Path(source) if source else None
        self._globs = {}

    def glob(self, pattern):
        if pattern not in self._globs:
            self._globs[pattern] = compile_glob(pattern)
        return self._globs[pattern]

    def rel(self, path):
        """The path relative to the root with `/`, "" for the root itself, None when it lies outside the root."""
        base, target = canon(self.root), canon(path)
        if fold(target) == fold(base):
            return ""
        prefix = base if base.endswith("/") else base + "/"
        return target[len(prefix):] if fold(target).startswith(fold(prefix)) else None

    def rules_for(self, rel):
        """The Files rows that match the relative path, in file order."""
        return [rule for rule in self.files if self.glob(rule.pattern).match(rel)]

    def lists(self, path):
        rel = self.rel(path)
        return bool(rel) and bool(self.rules_for(rel))

    def type_of(self, path, section=None):
        """The type of the file, or of one of its sections; None when the set does not list the file. A Section row
        wins for its heading, the first row with no Section types the rest of the file."""
        rel = self.rel(path)
        rules = self.rules_for(rel) if rel else []
        for rule in rules:
            if section is not None and rule.section == section:
                return rule.type
        for rule in rules:
            if rule.section is None:
                return rule.type
        return rules[0].type if rules and section is None else None

    def sections(self, path):
        """`{heading: type}` of the file's typed sections (empty for a file with one type)."""
        rel = self.rel(path)
        return {rule.section: rule.type for rule in self.rules_for(rel)
                if rule.section is not None} if rel else {}

    def rules_of_part(self, kind, name):
        """The Files rows that name the part kind (a hook `plugin:name` also matches a row `hook plugin`)."""
        found = []
        for rule in self.files:
            for rule_kind, rule_name in rule.kinds:
                if rule_kind == kind and (rule_name == name or (kind == "hook" and rule_name == name.split(":")[0])):
                    found.append(rule)
                    break
        return found

    def may_change_path(self, path):
        """The `Changes` texts of the May change itself rows that match the path (empty: the agent never edits it)."""
        rel = self.rel(path)
        return [changes for pattern, changes in self.may_change if rel and self.glob(pattern).match(rel)]

    def reviewed_by(self, project_name):
        return fold(self.reviewer.strip()) == fold(str(project_name).strip())


def parse(text, root, source=None):
    """A `Subscription` from the text of a subscription file; `Problem` listing every error found."""
    where = f"{source}: " if source else ""
    errors = []
    settings = {}
    files, signs, may_change = [], [], []
    seen_files, seen_signs, have_files = set(), set(), False
    for heading, header, rows, number in read_blocks(text.lstrip("﻿")):
        if header is None:
            errors.append(f"line {number}: a table needs a `|---|` separator as its second line")
            continue
        low = [cell.lower() for cell in header]
        if heading is None:
            if low != ["setting", "value"]:
                errors.append(f"line {number}: the settings table needs the header `| Setting | Value |`")
                continue
            for line, cells in rows:
                key = cells[0].lower() if cells else ""
                if len(cells) != 2:
                    errors.append(f"line {line}: a settings row needs 2 cells")
                elif key not in SETTINGS:
                    errors.append(f"line {line}: unknown setting '{cells[0]}' (known: {', '.join(SETTINGS)})")
                elif key in settings:
                    errors.append(f"line {line}: setting '{key}' is listed twice")
                else:
                    settings[key] = cells[1]
        elif heading == "Files":
            have_files = True
            if not (low[0].startswith("path") and low[1:3] == ["type", "part kinds"] and low[3:] in ([], ["section"])):
                errors.append(f"line {number}: the Files table needs the columns Path, Type, Part kinds and optionally Section")
                continue
            for line, cells in rows:
                if len(cells) != len(header):
                    errors.append(f"line {line}: a Files row needs {len(header)} cells, it has {len(cells)}")
                    continue
                pattern, kind_type, kinds_cell = cells[0], cells[1].lower(), cells[2]
                section = (cells[3] or None) if len(cells) > 3 else None
                try:
                    compile_glob(pattern)
                except Problem as exc:
                    errors.append(f"line {line}: bad path glob: {exc}")
                    continue
                if kind_type not in TYPES:
                    errors.append(f"line {line}: unknown type '{cells[1]}' (use {', '.join(TYPES)})")
                    continue
                try:
                    kinds = parse_kinds(kinds_cell)
                except Problem as exc:
                    errors.append(f"line {line}: {exc}")
                    continue
                if (pattern, section) in seen_files:
                    errors.append(f"line {line}: path '{pattern}'{f' with section {section}' if section else ''} is listed twice")
                    continue
                seen_files.add((pattern, section))
                files.append(Rule(pattern, kind_type, kinds, section))
        elif heading == "Signs":
            if low != ["sign", "kind", "pattern"]:
                errors.append(f"line {number}: the Signs table needs the header `| Sign | Kind | Pattern |`")
                continue
            for line, cells in rows:
                if len(cells) != 3 or not cells[0] or not cells[2]:
                    errors.append(f"line {line}: a Signs row needs a sign, a kind and a pattern")
                elif cells[1].lower() not in TYPES:
                    errors.append(f"line {line}: unknown type '{cells[1]}' (use {', '.join(TYPES)})")
                elif cells[0] in seen_signs:
                    errors.append(f"line {line}: sign '{cells[0]}' is listed twice")
                else:
                    expression = EXPRESSION.search(cells[2])
                    try:
                        compiled = re.compile(expression.group(1)) if expression else None
                    except re.error as exc:
                        errors.append(f"line {line}: sign '{cells[0]}': bad regular expression: {exc}")
                        continue
                    seen_signs.add(cells[0])
                    signs.append(Sign(cells[0], cells[1].lower(), cells[2], compiled))
        elif heading == "May change itself":
            if low != ["path", "changes"]:
                errors.append(f"line {number}: the May change itself table needs the header `| Path | Changes |`")
                continue
            for line, cells in rows:
                if len(cells) != 2 or not cells[1]:
                    errors.append(f"line {line}: a May change itself row needs a path and what may change")
                    continue
                try:
                    compile_glob(cells[0])
                except Problem as exc:
                    errors.append(f"line {line}: bad path glob: {exc}")
                    continue
                may_change.append((cells[0], cells[1]))
        else:
            errors.append(f"line {number}: a table under the heading '{heading}' (tables belong under Files, Signs "
                          f"or May change itself, the settings table before the first `##`)")
    for key in REQUIRED:
        if not settings.get(key):
            errors.append(f"setting '{key}' is missing" + (" (the set has no name)" if key == "set" else ""))
    if settings.get("set") and not NAME.match(settings["set"]):
        errors.append(f"set name '{settings['set']}': use letters, digits, `.`, `_` and `-` only (it names a folder)")
    if not have_files or not files:
        errors.append("the Files table is missing or has no row")
    if errors:
        raise Problem(where + "; ".join(errors))
    subscription = Subscription(settings["set"], settings["reviewed by"], settings["lands by"],
                                settings.get("special editor", ""), root, files, signs, may_change, source)
    if source:  # the subscription file is a file of its set
        own = subscription.rel(source)
        if own and not subscription.rules_for(own):
            subscription.files += (Rule(own, "process", (), None),)
    return subscription


def load(path, root):
    """Read and parse the file at `path`; `Problem` also for a file that cannot be read."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise Problem(f"{path}: cannot read: {exc}") from exc
    return parse(text, root, path)


def default_project(root):
    """The set of a project with a dev-kit profile and no subscription file (module doc)."""
    folder = Path(root).name
    name = re.sub(r"[^A-Za-z0-9._-]", "-", folder).lstrip(".-_") or "project"  # the name is a folder name too
    files = [Rule(pattern, kind, (), None) for pattern, kind in DEFAULT_FILES]
    return Subscription(name, folder, "the project's lead merge", "", root, files)


def plugins_dir():
    return Path(os.environ[PLUGINS_ENV]) if os.environ.get(PLUGINS_ENV) else Path(__file__).resolve().parents[2]


def global_dir():
    return Path(os.environ[GLOBAL_ENV]) if os.environ.get(GLOBAL_ENV) else Path.home() / ".claude"


class Registry:
    """The sets found by `discover`, by name, and what they can answer."""

    def __init__(self):
        self.sets = {}
        self.errors = []

    def add(self, subscription):
        if subscription.name in self.sets:
            self.errors.append(f"{subscription.source or subscription.root}: set '{subscription.name}' is already "
                               f"defined by {self.sets[subscription.name].source or self.sets[subscription.name].root}")
        else:
            self.sets[subscription.name] = subscription

    def owner(self, path):
        """`Owner(set, rule)` of a file: the set with the deepest root that holds it, when that set lists it;
        None for a file no set lists."""
        best = None
        for subscription in self.sets.values():
            if subscription.rel(path) is not None and (best is None or len(canon(subscription.root)) > len(canon(best.root))):
                best = subscription
        if best is None:
            return None
        rel = best.rel(path)
        rules = best.rules_for(rel) if rel else []
        if not rules:
            return None
        return Owner(best, next((rule for rule in rules if rule.section is None), rules[0]))

    def type_of(self, path, section=None):
        owner = self.owner(path)
        return owner.set.type_of(path, section) if owner else None

    def candidates(self, kind, name):
        """The sets that name the part kind (`skill`, `agent` or `hook`) in a Files row, in discovery order."""
        return [subscription for subscription in self.sets.values() if subscription.rules_of_part(kind, name)]

    def reviewed_by(self, project_name):
        return [subscription for subscription in self.sets.values() if subscription.reviewed_by(project_name)]

    def set_at(self, root):
        """The set whose root is exactly this folder (a project's own set), or None."""
        for subscription in self.sets.values():
            if fold(canon(subscription.root)) == fold(canon(root)):
                return subscription
        return None


def discover(plugins=None, global_folder=None, project_roots=()):
    """All sets: the plugin folders, the global folder and the projects (module doc). Never raises."""
    registry = Registry()
    plugins = Path(plugins) if plugins else plugins_dir()
    try:
        folders = sorted(path for path in plugins.iterdir() if (path / FILE_NAME).is_file())
    except OSError:
        folders = []
    for folder in folders:
        _add_file(registry, folder / FILE_NAME, folder)
    global_folder = Path(global_folder) if global_folder else global_dir()
    if (global_folder / FILE_NAME).is_file():
        _add_file(registry, global_folder / FILE_NAME, global_folder)
    for root in project_roots:
        root = Path(root)
        path = root / ".claude" / FILE_NAME
        if path.is_file():
            _add_file(registry, path, root)
        else:
            registry.add(default_project(root))
    return registry


def _add_file(registry, path, root):
    try:
        registry.add(load(path, root))
    except Problem as exc:
        registry.errors.append(str(exc))


def ensure_global(global_folder=None, template=None):
    """Create the global subscription from the template when it is missing and commit it when the folder is a git
    repository (no push). True when the file was created; never raises."""
    folder = Path(global_folder) if global_folder else global_dir()
    path = folder / FILE_NAME
    try:
        if path.exists():
            return False
        text = Path(template or TEMPLATE).read_text(encoding="utf-8")
        folder.mkdir(parents=True, exist_ok=True)
        with open(path, "x", encoding="utf-8") as handle:
            handle.write(text)
    except (OSError, UnicodeDecodeError):
        return False
    _commit(folder, path)
    return True


def _commit(folder, path):
    """Commit `path` in `folder`'s own git repository (the folder is the repository's top), if it is one."""
    try:
        top = subprocess.run(["git", "-C", str(folder), "rev-parse", "--show-toplevel"], capture_output=True, text=True,
                             timeout=GIT_TIMEOUT_S)
        if top.returncode != 0 or fold(canon(top.stdout.strip())) != fold(canon(folder)):
            return
        subprocess.run(["git", "-C", str(folder), "add", "--", path.name], capture_output=True, timeout=GIT_TIMEOUT_S)
        subprocess.run(["git", "-C", str(folder), "commit", "-q", "-m",
                        "Rules subscription: the owner's global set, written by the rules-kit retro on its first run "
                        "(owner, 2026-11-24: rule sets and subscriptions)", "--", path.name],
                       capture_output=True, timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError):
        pass
