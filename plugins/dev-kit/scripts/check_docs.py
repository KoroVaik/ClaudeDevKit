"""Documentation check: structure of epics and features, links, anchors, paths, and the on-demand
reverse index (code path -> features).

The docs layout is fixed by the documentation standard (docs/product.md, docs/epics, docs/features,
docs/tech with docs/tech/map.md, docs/standards, plans). Everything project-specific is read from the
profile `<root>/.claude/dev-kit.md`, section `## documentation`, a table `| Setting | Value |`.

Modes (precedence: open/defects, then who, then the check):
  no flag          full check: prints errors and warnings, exit 1 when there is any error, else 0.
  --pre-commit     the check, then two advisory lists (never an error): features that list a staged code
                   file, and code folders (two levels) that no feature "Built in" and no map line mentions.
  --who PATH       the features whose "Built in" path, folder or glob matches PATH, longest prefix first.
  --open           every unchecked item under "## Open" in epics, features, standards and tech files, and
                   every unchecked item in the plans; two groups (tasks, defects), grouped by code area.
  --defects        with or without --open: only the items starting with "Defect:".
  --by-file        with --open: group by file instead of by code area.
  --root DIR       project root (default: git toplevel of the current folder).

Settings (rows of the profile table; every row is `name | value`):
  scan         `<folder>: <ext> <ext>`  also scan this folder, recursively (repeatable); the root *.md files
               and docs/**/*.md are always scanned
  code-root    `<folder> <depth>`       a code folder; depth = path segments of its code areas, e.g.
               `backend 3` gives backend/Api/Controllers (repeatable); none by default
  skip-dirs    `name, name`             folder names never entered; added to .git, node_modules, bin, obj, dist,
               __pycache__, .venv, venv, .idea, .vs
  area-alias   `<prefix> -> <text>`     a relative path in a doc that starts with the prefix is read as <text>
               plus the rest, e.g. `src/ -> frontend/src/` (repeatable)
  file-ext     `.ext .ext`              extensions that mark the last segment of an area path as a file
               (default: common code and config extensions)
  skills-lock  `<file>` or `none`       JSON file whose "skills" keys are third-party skills under
               .claude/skills, skipped by the scan (default skills-lock.json)
  size-limit, map-limit  `N`            line limits for the size warnings (default 200 and 60)
Code roots drive the pre-commit advisories and the code areas of --open; without them the advisories are
empty and every open item is in the area docs.

Errors: an epic missing from the product overview; a feature not linked from exactly one epic; a feature
without the "Epic:" line (linking to an existing epic) or without the four sections (Purpose, Rules,
Acceptance criteria, Built in); a Markdown link, a docs path mentioned in text or a #anchor that does not
resolve; a backticked path in a feature's "Built in" section or in the tech map that matches nothing.
Warnings never change the exit code: a feature or tech file over the size limit (silenced by a size-ok
marker comment with a reason) and a tech map over the map limit.
Skipped: the skip-dirs, external links, fenced code in Markdown, third-party skills named in the
skills lock. The docs-path mention rule is skipped for CHANGELOG.md and for a Markdown file containing
the comment docs-check: no-path-mentions. A date placeholder such as YYYY-MM-DD cuts a mentioned path.

Order of paths in the output follows the Windows PowerShell culture sort (case-insensitive, punctuation
before digits before letters; '-' and apostrophe are ignored at the first level); text outside ASCII
sorts by code point. Directory listings are read in upper-cased name order. Problems on one file and
line keep the order of the PowerShell sort (see ps_sort).
"""
import argparse
import bisect
import json
import os
import re
import subprocess
import sys
import unicodedata
from urllib.parse import unquote

DOCS = "docs"
PRODUCT_REL = DOCS + "/product.md"
EPICS_REL = DOCS + "/epics"
FEATURES_REL = DOCS + "/features"
TECH_REL = DOCS + "/tech"
STANDARDS_REL = DOCS + "/standards"
MAP_REL = DOCS + "/tech/map.md"
PLANS_REL = "plans"
REQUIRED_SECTIONS = ("Purpose", "Rules", "Acceptance criteria", "Built in")
BUILTIN_SKIP_DIRS = (".git", "node_modules", "bin", "obj", "dist", "__pycache__", ".venv", "venv", ".idea", ".vs")
DEFAULT_FILE_EXT = (
    ".cs", ".csproj", ".sln", ".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".html", ".py", ".ps1", ".sh",
    ".md", ".yml", ".yaml", ".txt", ".toml", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".c", ".h", ".cpp",
    ".swift", ".gd", ".gradle", ".xml", ".sql", ".vue", ".svelte", ".scss",
)
DEFAULT_SIZE_LIMIT = 200
DEFAULT_MAP_LIMIT = 60
DEFAULT_SKILLS_LOCK = "skills-lock.json"
PROFILE_REL = ".claude/dev-kit.md"
PROFILE_SECTION = "documentation"
ADVISORY_CAP = 30

# ---------------------------------------------------------------- settings

SETTING_NAMES = (
    "scan", "code-root", "skip-dirs", "area-alias", "file-ext", "skills-lock", "size-limit", "map-limit",
)
REPEATABLE = {"scan", "code-root", "skip-dirs", "area-alias", "file-ext"}
EXT_RX = re.compile(r"^\.[\w.-]+$")


class Settings:
    """Project settings with the defaults that suit a project without code roots."""

    def __init__(self):
        self.scan = []  # (folder, [extensions]); root and docs are added by scan_plan
        self.code_roots = []  # (folder, depth)
        self.skip_dirs = set(BUILTIN_SKIP_DIRS)
        self.area_aliases = []  # (prefix, replacement)
        self.file_ext = None  # None = DEFAULT_FILE_EXT
        self.skills_lock = DEFAULT_SKILLS_LOCK
        self.size_limit = DEFAULT_SIZE_LIMIT
        self.map_limit = DEFAULT_MAP_LIMIT

    def known_file_ext(self):
        return self.file_ext if self.file_ext is not None else DEFAULT_FILE_EXT


def _split_list(value):
    return [part for part in re.split(r"[,\s]+", value.strip()) if part]


def _folder(value):
    return value.strip().replace("\\", "/").strip("/")


def _parse_extensions(value):
    exts = [e.lower() for e in _split_list(value)]
    if not exts:
        raise ValueError("no extension given")
    for ext in exts:
        if not EXT_RX.match(ext):
            raise ValueError(f"'{ext}' is not an extension like .cs")
    return exts


def _parse_scan(value):
    folder, sep, rest = value.partition(":")
    folder = _folder(folder)
    if not sep or not folder:
        raise ValueError("expected '<folder>: <extensions>', e.g. 'backend: .cs'")
    if ".." in folder.split("/") or re.match(r"^[A-Za-z]:", folder):
        raise ValueError("folder must be relative to the project root")
    return folder, _parse_extensions(rest)


def _parse_code_root(value):
    match = re.match(r"^(\S+)\s+(\d+)$", value.strip())
    if not match or int(match.group(2)) < 1:
        raise ValueError("expected '<folder> <depth>' with a depth of 1 or more, e.g. 'backend 3'")
    folder = _folder(match.group(1))
    if not folder or ".." in folder.split("/") or re.match(r"^[A-Za-z]:", folder):
        raise ValueError("folder must be relative to the project root")
    return folder, int(match.group(2))


def _parse_skip_dirs(value):
    names = _split_list(value)
    if not names:
        raise ValueError("no folder name given")
    for name in names:
        if "/" in name or "\\" in name:
            raise ValueError(f"'{name}' must be a folder name, not a path")
    return names


def _parse_alias(value):
    match = re.match(r"^(\S+)\s*->\s*(\S+)$", value.strip())
    if not match:
        raise ValueError("expected '<prefix> -> <replacement>', e.g. 'src/ -> frontend/src/'")
    return match.group(1), match.group(2)


def _parse_skills_lock(value):
    value = value.strip()
    if not value or re.search(r"\s", value):
        raise ValueError("expected a project-relative file path or 'none'")
    return value


def _parse_limit(value):
    if not re.match(r"^\d+$", value.strip()) or int(value) < 1:
        raise ValueError("expected a whole number of 1 or more")
    return int(value)


def parse_settings(rows):
    """Turn (name, value) rows into (Settings, [error text])."""
    settings = Settings()
    errors = []
    seen = set()
    for name, value in rows:
        if name not in SETTING_NAMES:
            errors.append(f"unknown setting '{name}' (known: {', '.join(SETTING_NAMES)})")
            continue
        if name not in REPEATABLE and name in seen:
            errors.append(f"setting '{name}' is set twice")
            continue
        seen.add(name)
        try:
            if name == "scan":
                settings.scan.append(_parse_scan(value))
            elif name == "code-root":
                settings.code_roots.append(_parse_code_root(value))
            elif name == "skip-dirs":
                settings.skip_dirs.update(_parse_skip_dirs(value))
            elif name == "area-alias":
                settings.area_aliases.append(_parse_alias(value))
            elif name == "file-ext":
                settings.file_ext = list(settings.file_ext or []) + _parse_extensions(value)
            elif name == "skills-lock":
                settings.skills_lock = _parse_skills_lock(value)
            elif name == "size-limit":
                settings.size_limit = _parse_limit(value)
            elif name == "map-limit":
                settings.map_limit = _parse_limit(value)
        except ValueError as exc:
            errors.append(f"setting '{name}': {exc}")
    return settings, errors


def _strip_fences(text):
    lines = []
    inside = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            inside = not inside
            lines.append("")
        else:
            lines.append("" if inside else line)
    return lines


def _cells(line):
    return [cell.strip().replace("`", "").strip() for cell in line.strip().strip("|").split("|")]


def profile_table(text):
    """Return None when the profile has no `## documentation` section, else (header, rows) of its table.

    The heading is found without regard to case so that its rows are still checked; heading_problems
    reports the wrong case.

    header is None when the section holds no table with a `|---|` separator.
    """
    body = []
    inside = False
    found = False
    for line in _strip_fences(text):
        heading = re.match(r"^##\s+(.*?)\s*$", line)
        if heading:
            if inside:
                break
            inside = heading.group(1).lower() == PROFILE_SECTION
            found = found or inside
        elif inside:
            body.append(line)
    if not found:
        return None
    block = []
    for line in body:
        if line.lstrip().startswith("|"):
            block.append(line)
        elif block:
            break
    separator = re.compile(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$")
    if len(block) < 2 or not separator.match(block[1].strip()):
        return None, []
    return _cells(block[0]), [_cells(line) for line in block[2:]]


def heading_problems(text):
    """Level-2 headings that name the section in the wrong case, e.g. `## Documentation`."""
    problems = []
    for line in _strip_fences(text):
        heading = re.match(r"^##\s+(.*?)\s*$", line)
        if heading and heading.group(1).lower() == PROFILE_SECTION and heading.group(1) != PROFILE_SECTION:
            problems.append(f"heading '## {heading.group(1)}' must be written '## {PROFILE_SECTION}'")
    return problems


def profile_errors(text):
    """Problems of the `## documentation` section of a profile text; [] when it has none.

    The check run fails on every one of these, so a typo never turns into silent defaults.
    """
    errors = heading_problems(text)
    table = profile_table(text)
    if table is None:
        return errors
    header, rows = table
    if header is None or header[:2] != ["Setting", "Value"]:
        return errors + ["documentation table with header '| Setting | Value |' and a |---| separator not found"]
    pairs = []
    for row in rows:
        if len(row) < 2 or not row[0] or not row[1]:
            errors.append(f"row '{' | '.join(row)}' needs a setting and a value")
            continue
        pairs.append((row[0], row[1]))
    errors.extend(parse_settings(pairs)[1])
    return errors


def load_settings(root):
    """Read the settings of the project at root; return (Settings, [error text]).

    With any error the settings are the defaults and the caller must not run the check.
    """
    path = os.path.join(root, *PROFILE_REL.split("/"))
    try:
        text = read_text(path)
    except OSError:
        return Settings(), []
    errors = profile_errors(text)
    if errors:
        return Settings(), [f"{PROFILE_REL}: {e}" for e in errors]
    table = profile_table(text)
    if table is None:
        return Settings(), []
    pairs = [(row[0], row[1]) for row in table[1]]
    return parse_settings(pairs)[0], []


# ---------------------------------------------------------------- text helpers

def read_text(path):
    """Read a file like .NET ReadAllText: BOM detected and dropped, bad bytes replaced."""
    with open(path, "rb") as handle:
        data = handle.read()
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le", errors="replace")
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16-be", errors="replace")
    return data.decode("utf-8-sig", errors="replace")


def _blank(match):
    return re.sub(r"[^\r\n]", " ", match.group(0))


FENCE_RX = re.compile(
    r"^[ \t]{0,3}(?P<f>`{3,}|~{3,})[^\r\n]*\r?\n.*?(?:^[ \t]{0,3}(?P=f)[`~]*[ \t]*\r?$|\Z)", re.M | re.S
)
INLINE_CODE_RX = re.compile(r"`[^`\r\n]+`")
LINK_RX = re.compile(
    r"!?\[(?:[^\]\r\n]|\[[^\]\r\n]*\])*\]\(\s*(?P<t1><[^>\r\n]+>|[^)\s]+)"
    r"(?:\s+(?:\"[^\"\r\n]*\"|'[^'\r\n]*'))?\s*\)"
    r"|^[ \t]{0,3}\[[^\]\r\n]+\]:[ \t]*(?P<t2>\S+)",
    re.M,
)
DOCS_PATH_RX = re.compile(r"(?<![\w./\\-])" + DOCS + r"/[\w./*#%-]*")
HEADING_RX = re.compile(r"^ {0,3}#{1,6}[ \t]+(?P<h>[^\r\n]*?)[ \t]*\r?$", re.M)
TITLE_RX = re.compile(r"^#[ \t]+(?P<h>[^\r\n]+?)[ \t]*\r?$", re.M)
EPIC_LINE_RX = re.compile(r"^Epic:[ \t]*(?P<v>[^\r\n]*)", re.M)
BACKTICK_RX = re.compile(r"`([^`\r\n]+)`")
SCHEME_RX = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
SIZE_OK_RX = re.compile(r"<!--\s*size-ok:\s*\S[^>]*-->", re.I)
NO_PATH_MARKER = "<!-- docs-check: no-path-mentions -->"
TRIM_PUNCT = ".,;:#"


def simple_lower(text):
    """Per-character lowercase that never changes the length (like ToLowerInvariant)."""
    out = []
    for char in text:
        lowered = char.lower()
        out.append(lowered if len(lowered) == 1 else char)
    return "".join(out)


def slug_of(heading):
    h = re.sub(r"[ \t]+#+[ \t]*$", "", heading)
    h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h)
    h = re.sub(r"<[^>]+>", "", h)
    h = simple_lower(h.replace("`", "").replace("*", ""))
    h = "".join(c for c in h if unicodedata.category(c)[0] in "LNM" or c.isspace() or c in "_-")
    return h.replace(" ", "-").replace("\t", "-")


_SYMBOLS = " !\"#$%&()*,./:;?@[\\]^_`{|}~+<=>"
_SYMBOL_ORDER = {c: i for i, c in enumerate(_SYMBOLS)}


def culture_key(text):
    """Sort key that follows the Windows PowerShell culture sort: letters by base letter first, then by
    accents, then by the placement of '-' and apostrophe (which the first level ignores)."""
    primary = []
    accents = []
    ignored = []
    position = 0
    for char in text:
        if char in "-'":
            ignored.append((0 if char == "'" else 1, position))
            continue
        position += 1
        if char in _SYMBOL_ORDER:
            primary.append((0, _SYMBOL_ORDER[char]))
        elif "0" <= char <= "9":
            primary.append((1, ord(char)))
        else:
            parts = unicodedata.normalize("NFD", char)
            base = simple_lower(parts[0])
            primary.append((2, ord(base)))
            for mark in parts[1:]:
                accents.append((position, ord(mark)))
    return primary, accents, ignored


def ps_sort(items, compare):
    """Sort like Windows PowerShell 5.1 Sort-Object: the .NET Framework quicksort, which is not stable.

    Problems on the same file and line come out in this order, not in the order they were found; the
    port keeps it so that its output stays identical to the PowerShell script it replaced.
    """
    keys = list(items)

    def swap_if_greater(a, b):
        if a != b and compare(keys[a], keys[b]) > 0:
            keys[a], keys[b] = keys[b], keys[a]

    def quick(left, right):
        while True:
            i, j = left, right
            middle = i + ((j - i) >> 1)
            swap_if_greater(i, middle)
            swap_if_greater(i, j)
            swap_if_greater(middle, j)
            pivot = keys[middle]
            while True:
                while compare(keys[i], pivot) < 0:
                    i += 1
                while compare(pivot, keys[j]) < 0:
                    j -= 1
                if i > j:
                    break
                if i < j:
                    keys[i], keys[j] = keys[j], keys[i]
                i += 1
                j -= 1
                if i > j:
                    break
            if j - left <= right - i:
                if left < j:
                    quick(left, j)
                left = i
            else:
                if i < right:
                    quick(i, right)
                right = j
            if left >= right:
                break

    if len(keys) > 1:
        quick(0, len(keys) - 1)
    return keys


def compare_problems(a, b):
    """Order by file (culture sort), then by line."""
    key_a, key_b = culture_key(a.file), culture_key(b.file)
    if key_a != key_b:
        return -1 if key_a < key_b else 1
    return (a.line > b.line) - (a.line < b.line)


def file_extension(name):
    index = name.rfind(".")
    return name[index:].lower() if 0 <= index < len(name) - 1 else ""


def literal_prefix(glob):
    positions = [i for i in (glob.find("*"), glob.find("?")) if i >= 0]
    return glob[: min(positions)] if positions else glob


def glob_regex(glob):
    parts = ["^"]
    i = 0
    while i < len(glob):
        c = glob[i]
        if c == "*":
            if i + 1 < len(glob) and glob[i + 1] == "*":
                if i + 2 < len(glob) and glob[i + 2] == "/":
                    parts.append("(?:.*/)?")
                    i += 3
                else:
                    parts.append(".*")
                    i += 2
            else:
                parts.append("[^/]*")
                i += 1
        elif c == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(c))
            i += 1
    parts.append("$")
    return re.compile("".join(parts), re.I)


def unescape(text):
    try:
        return unquote(text, errors="strict")
    except UnicodeDecodeError:
        return text


class Doc:
    def __init__(self, full, rel, text):
        self.full = full
        self.rel = rel
        self.text = text
        self.is_md = full.lower().endswith(".md")
        self.masked = FENCE_RX.sub(_blank, text) if self.is_md else text
        self.newlines = [m.start() for m in re.finditer("\n", text)]
        self.links = None
        self.slugs = None

    def line_of(self, pos):
        return bisect.bisect_left(self.newlines, pos) + 1


class Link:
    def __init__(self, target, index, length):
        self.target = target
        self.index = index
        self.length = length


def links_in(text):
    code = INLINE_CODE_RX.sub(_blank, text)
    result = []
    for match in LINK_RX.finditer(code):
        group = "t1" if match.group("t1") is not None else "t2"
        result.append(Link(match.group(group), match.start(group), match.end(group) - match.start(group)))
    return result


class Entry:
    def __init__(self, token, line):
        path = token
        index = path.find("#")
        if index >= 0:
            path = path[:index]
        path = path.strip().rstrip("/")
        if path.startswith("./"):
            path = path[2:]
        path = path.lstrip("/")
        self.token = token
        self.path = path
        self.is_glob = "*" in path or "?" in path
        self.line = line
        self.prefix_len = len(literal_prefix(path))
        self.rx = glob_regex(path) if self.is_glob else None


def entry_match(entry, path):
    """Length of the matching prefix, or -1 when the entry does not cover the path."""
    if entry.path == "":
        return -1
    if not entry.is_glob:
        lowered = path.lower()
        own = entry.path.lower()
        if lowered == own or lowered.startswith(own + "/"):
            return len(entry.path)
        if own.startswith(lowered + "/"):
            return len(path)
        return -1
    current = path
    while current != "":
        if entry.rx.match(current):
            return entry.prefix_len
        cut = current.rfind("/")
        if cut < 0:
            break
        current = current[:cut]
    if literal_prefix(entry.path).lower().startswith(path.lower() + "/"):
        return len(path)
    return -1


class Feature:
    def __init__(self, doc, name, entries):
        self.doc = doc
        self.name = name
        self.entries = entries


class Problem:
    def __init__(self, rule, file, line, message):
        self.rule = rule
        self.file = file
        self.line = line
        self.message = message


class OpenItem:
    def __init__(self, line, text):
        self.line = line
        self.text = text


class OpenFile:
    def __init__(self, doc, name, items, kind):
        self.doc = doc
        self.name = name
        self.items = items
        self.kind = kind


# ---------------------------------------------------------------- the checker

class Checker:
    def __init__(self, root, settings=None):
        self.root = os.path.abspath(root).rstrip("\\/")
        self.settings = settings or Settings()
        self.errors = []
        self.warnings = []
        self._seen_errors = set()
        self._seen_warnings = set()
        self._docs = {}
        self._features = None
        self.skip_names = {name.lower() for name in self.settings.skip_dirs}
        self.skip_full = self._skill_dirs()

    # -- paths and files

    def _skill_dirs(self):
        lock = self.settings.skills_lock
        if not lock or lock.lower() == "none":
            return set()
        path = self.full(lock)
        if not os.path.isfile(path):
            return set()
        try:
            with open(path, "rb") as handle:
                data = json.loads(handle.read().decode("utf-8-sig"))
        except ValueError as exc:
            print(f"dev-kit-check-docs: {lock} is not valid JSON: {exc}", file=sys.stderr)
            sys.exit(2)
        skills = data.get("skills") if isinstance(data, dict) else None
        if not isinstance(skills, dict):
            return set()
        return {os.path.normcase(self.full(".claude/skills/" + name)) for name in skills}

    def full(self, rel):
        return os.path.abspath(self.root + "/" + rel)

    def rel(self, full):
        if len(full) <= len(self.root):
            return "."
        return full[len(self.root):].lstrip("\\/").replace("\\", "/")

    @staticmethod
    def _entries(directory):
        """Files and folders of a directory in upper-cased name order (the order NTFS lists them)."""
        try:
            with os.scandir(directory) as scan:
                found = sorted(scan, key=lambda e: e.name.upper())
        except OSError:
            return [], []
        files = []
        dirs = []
        for entry in found:
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False
            (dirs if is_dir else files).append(os.path.join(directory, entry.name))
        return files, dirs

    def _skipped(self, directory):
        return (
            os.path.basename(directory).lower() in self.skip_names
            or os.path.normcase(directory) in self.skip_full
        )

    def files_in(self, directory, exts, recurse):
        result = []
        if not os.path.isdir(directory):
            return result
        stack = [directory]
        while stack:
            current = stack.pop()
            files, dirs = self._entries(current)
            result.extend(f for f in files if file_extension(os.path.basename(f)) in exts)
            if recurse:
                stack.extend(d for d in dirs if not self._skipped(d))
        return result

    def subdirs(self, directory):
        _, dirs = self._entries(directory)
        return [d for d in dirs if os.path.basename(d).lower() not in self.skip_names]

    def md_files(self, rel_dir):
        return self.files_in(self.full(rel_dir), (".md",), False)

    # -- problems

    def add_error(self, rule, file, line, message, key=None):
        key = key or f"{rule}|{file}|{line}|{message}"
        if key not in self._seen_errors:
            self._seen_errors.add(key)
            self.errors.append(Problem(rule, file, line, message))

    def add_warning(self, rule, file, line, message):
        key = f"{rule}|{file}|{line}|{message}"
        if key not in self._seen_warnings:
            self._seen_warnings.add(key)
            self.warnings.append(Problem(rule, file, line, message))

    # -- documents, links, anchors

    def doc(self, full):
        key = os.path.normcase(full)
        if key not in self._docs:
            self._docs[key] = Doc(full, self.rel(full), read_text(full))
        return self._docs[key]

    def links(self, doc):
        if doc.links is None:
            doc.links = links_in(doc.masked)
        return doc.links

    def slugs(self, doc):
        if doc.slugs is None:
            slugs = set()
            counts = {}
            for match in HEADING_RX.finditer(doc.masked):
                slug = slug_of(match.group("h"))
                if slug in counts:
                    counts[slug] += 1
                    slugs.add(f"{slug}-{counts[slug]}")
                else:
                    counts[slug] = 0
                    slugs.add(slug)
            doc.slugs = slugs
        return doc.slugs

    def test_anchor(self, full, anchor):
        return simple_lower(unescape(anchor)) in self.slugs(self.doc(full))

    def resolve_target(self, base_full, target):
        """None for an external or empty target, else (full path, anchor)."""
        t = target.strip()
        if t.startswith("<") and t.endswith(">") and len(t) >= 2:
            t = t[1:-1]
        if t == "" or t.startswith("//") or SCHEME_RX.match(t):
            return None
        anchor = None
        index = t.find("#")
        if index >= 0:
            anchor = t[index + 1:]
            t = t[:index]
        question = t.find("?")
        if question >= 0:
            t = t[:question]
        t = unescape(t)
        if t == "":
            full = base_full
        elif t.startswith("/"):
            full = self.full(t.lstrip("/"))
        else:
            full = os.path.abspath(os.path.dirname(base_full) + "/" + t)
        return full, anchor

    @staticmethod
    def exists(full):
        return os.path.exists(full)

    def anchor_missing(self, full, anchor):
        return bool(anchor) and os.path.isfile(full) and full.lower().endswith(".md") and not self.test_anchor(full, anchor)

    # -- paths in text

    def glob_exists(self, glob):
        prefix = literal_prefix(glob)
        slash = prefix.rfind("/")
        base_rel = prefix[:slash] if slash >= 0 else ""
        base_full = self.full(base_rel) if base_rel else self.root
        if not os.path.isdir(base_full):
            return False
        rx = glob_regex(glob)
        if "**" in glob:
            max_depth = float("inf")
        else:
            max_depth = len(glob.split("/")) - len([s for s in base_rel.split("/") if s])
        stack = [(base_full, 1)]
        while stack:
            directory, depth = stack.pop()
            try:
                names = os.listdir(directory)
            except OSError:
                continue
            for name in names:
                entry = os.path.join(directory, name)
                if rx.match(self.rel(entry)):
                    return True
                if depth < max_depth and os.path.isdir(entry) and name.lower() not in self.skip_names:
                    stack.append((entry, depth + 1))
        return False

    def test_path_token(self, path):
        """Error text for a repo-relative path (optionally with #anchor), or None."""
        anchor = None
        index = path.find("#")
        if index >= 0:
            anchor = path[index + 1:]
            path = path[:index]
        path = path.strip().rstrip("/")
        if path.startswith("./"):
            path = path[2:]
        if path == "":
            return None
        if "*" in path or "?" in path:
            if self.glob_exists(path):
                return None
            return f"pattern matches nothing: {path}"
        full = self.full(path)
        if not self.exists(full):
            return f"path does not exist: {path}"
        if self.anchor_missing(full, anchor):
            return f"anchor #{anchor} not found in {path}"
        return None

    # -- scan: links, anchors, docs paths

    def scan_plan(self):
        plan = {".": ((".md",), False), DOCS: ((".md",), True)}
        for folder, exts in self.settings.scan:
            plan[folder] = (tuple(exts), folder != ".")
        files = []
        for folder, (exts, recurse) in plan.items():
            directory = self.root if folder == "." else self.full(folder)
            files.extend(self.files_in(directory, exts, recurse))
        return files

    def scan_check(self):
        for file in self.scan_plan():
            doc = self.doc(file)
            path_text = doc.masked
            if doc.is_md:
                chars = list(doc.masked)
                for link in self.links(doc):
                    line = doc.line_of(link.index)
                    resolved = self.resolve_target(file, link.target)
                    if resolved is not None:
                        full, anchor = resolved
                        if not self.exists(full):
                            self.add_error("link", doc.rel, line, f"link target does not exist: {link.target}")
                        elif self.anchor_missing(full, anchor):
                            self.add_error("anchor", doc.rel, line, f"anchor #{anchor} not found in {self.rel(full)}")
                    chars[link.index:link.index + link.length] = " " * link.length
                path_text = "".join(chars)
            if DOCS + "/" not in path_text:
                continue
            if doc.is_md and (os.path.basename(file).lower() == "changelog.md" or NO_PATH_MARKER in doc.text):
                continue
            for match in DOCS_PATH_RX.finditer(path_text):
                path = match.group(0)
                cut = path.find("YYYY")
                if cut >= 0:
                    path = path[:cut]
                path = path.rstrip(TRIM_PUNCT)
                line = doc.line_of(match.start())
                problem = self.test_path_token(path)
                if problem:
                    self.add_error("docs-path", doc.rel, line, problem, f"path|{doc.rel}|{line}|{path}")

    # -- features, epics, map

    @staticmethod
    def section_text(doc, name):
        match = re.search(r"^##[ \t]+" + re.escape(name) + r"[ \t]*\r?$", doc.masked, re.M)
        if not match:
            return None
        start = match.end()
        following = re.compile(r"^#{1,2}[ \t]", re.M).search(doc.masked, start)
        end = following.start() if following else len(doc.masked)
        return start, doc.masked[start:end]

    @staticmethod
    def path_tokens(doc, text, offset):
        result = []
        for match in BACKTICK_RX.finditer(text):
            token = match.group(1).strip()
            if "/" not in token or re.search(r"\s", token) or "://" in token:
                continue
            result.append((token, doc.line_of(offset + match.start())))
        return result

    @staticmethod
    def title_of(doc, file):
        title = TITLE_RX.search(doc.masked)
        if title:
            return title.group("h")
        return os.path.splitext(os.path.basename(file))[0]

    def features(self):
        if self._features is None:
            result = []
            for file in self.md_files(FEATURES_REL):
                doc = self.doc(file)
                entries = []
                built = self.section_text(doc, "Built in")
                if built:
                    entries = [Entry(token, line) for token, line in self.path_tokens(doc, built[1], built[0])]
                result.append(Feature(doc, self.title_of(doc, file), entries))
            self._features = result
        return self._features

    @staticmethod
    def same(a, b):
        return a.lower() == b.lower()

    def structure_check(self):
        epics_dir = self.full(EPICS_REL)
        epics = self.md_files(EPICS_REL)
        features = self.features()

        product_full = self.full(PRODUCT_REL)
        if os.path.isfile(product_full) and epics:
            product = self.doc(product_full)
            linked = []
            for link in self.links(product):
                resolved = self.resolve_target(product_full, link.target)
                if resolved:
                    linked.append(resolved[0])
            for epic in epics:
                if not any(self.same(item, epic) for item in linked):
                    self.add_error("epic-listed", self.rel(epic), 1, f"epic is not linked from {PRODUCT_REL}")

        epic_targets = {}
        for epic in epics:
            targets = []
            for link in self.links(self.doc(epic)):
                resolved = self.resolve_target(epic, link.target)
                if resolved:
                    targets.append(resolved[0])
            epic_targets[epic] = targets

        for feature in features:
            doc = feature.doc
            owners = [e for e in epics if any(self.same(t, doc.full) for t in epic_targets[e])]
            if not owners:
                self.add_error("feature-epic-link", doc.rel, 1, "feature is not linked from any epic")
            elif len(owners) > 1:
                names = ", ".join(self.rel(o) for o in owners)
                self.add_error(
                    "feature-epic-link", doc.rel, 1, f"feature is linked from {len(owners)} epics, expected one: {names}"
                )

            epic_line = EPIC_LINE_RX.search(doc.masked)
            if not epic_line:
                self.add_error("feature-epic-line", doc.rel, 1, 'missing the "Epic:" line')
            else:
                line = doc.line_of(epic_line.start())
                targets = []
                for link in links_in(epic_line.group("v")):
                    resolved = self.resolve_target(doc.full, link.target)
                    if resolved:
                        targets.append(resolved)
                if not targets:
                    self.add_error("feature-epic-line", doc.rel, line, 'the "Epic:" line has no link to an epic')
                else:
                    target = targets[0][0]
                    is_epic = self.same(os.path.dirname(target), epics_dir) and target.lower().endswith(".md")
                    if os.path.isfile(target) and not is_epic:
                        self.add_error(
                            "feature-epic-line", doc.rel, line, f'the "Epic:" link does not point to a file in {EPICS_REL}'
                        )
                    elif not self.exists(target):
                        self.add_error(
                            "feature-epic-line", doc.rel, line, f'the "Epic:" link points to a missing epic: {self.rel(target)}'
                        )

            headings = [m.group(0).strip() for m in HEADING_RX.finditer(doc.masked)]
            for section in REQUIRED_SECTIONS:
                has = False
                for heading in headings:
                    if re.match(r"^##[ \t]+", heading) and not heading.startswith("###"):
                        title = re.sub(r"[ \t]+#+$", "", re.sub(r"^##[ \t]+", "", heading))
                        if title == section:
                            has = True
                            break
                if not has:
                    self.add_error("feature-sections", doc.rel, 1, f'missing the section "## {section}"')

            for entry in feature.entries:
                problem = self.test_path_token(entry.token)
                if problem:
                    key = f"path|{doc.rel}|{entry.line}|{entry.token.rstrip(TRIM_PUNCT)}"
                    self.add_error("built-in", doc.rel, entry.line, f"Built in: {problem}", key)

        map_full = self.full(MAP_REL)
        if os.path.isfile(map_full):
            map_doc = self.doc(map_full)
            for token, line in self.path_tokens(map_doc, map_doc.masked, 0):
                problem = self.test_path_token(token)
                if problem:
                    self.add_error("map", map_doc.rel, line, f"map: {problem}", f"path|{map_doc.rel}|{line}|{token.rstrip(TRIM_PUNCT)}")

    def size_check(self):
        limit = self.settings.size_limit
        map_limit = self.settings.map_limit
        map_full = self.full(MAP_REL)
        for file in self.md_files(FEATURES_REL) + self.md_files(TECH_REL):
            doc = self.doc(file)
            lines = len(doc.newlines) + 1
            if doc.text.endswith("\n"):
                lines -= 1
            if lines > limit and not SIZE_OK_RX.search(doc.text):
                self.add_warning(
                    "size", doc.rel, 1,
                    f"{lines} lines (limit {limit}). Is this one feature, or can a part change without reading the "
                    "rest and own its acceptance criteria? Is everything here a business rule, or do executors, "
                    "formats and commands belong in tech? If both answers are yes, add <!-- size-ok: reason -->.",
                )
            if self.same(doc.full, map_full) and lines > map_limit:
                self.add_warning(
                    "map-size", doc.rel, 1,
                    f"map has {lines} lines (limit {map_limit}): keep only the top level, one line per process, "
                    "code folder and data store.",
                )

    def run_check(self):
        """Run the check; return the output lines."""
        self.scan_check()
        self.structure_check()
        self.size_check()
        out = []
        for problem in ps_sort(self.errors, compare_problems):
            out.append(f"{problem.file}:{problem.line}: error [{problem.rule}] {problem.message}")
        for problem in ps_sort(self.warnings, compare_problems):
            out.append(f"{problem.file}:{problem.line}: warning [{problem.rule}] {problem.message}")
        suffix = ""
        if self.errors:
            counts = {}
            for problem in self.errors:
                counts[problem.rule] = counts.get(problem.rule, 0) + 1
            suffix = " (" + ", ".join(f"{rule}={counts[rule]}" for rule in sorted(counts, key=culture_key)) + ")"
        out.append(f"docs check: {len(self.errors)} errors{suffix}, {len(self.warnings)} warnings")
        return out

    # -- reverse index

    def find_features(self, path):
        hits = []
        for feature in self.features():
            best = None
            for entry in feature.entries:
                length = entry_match(entry, path)
                if length >= 0 and (best is None or length > best[0]):
                    best = (length, entry.token)
            if best:
                hits.append((best[0], feature, best[1]))
        hits.sort(key=lambda h: (-h[0], culture_key(h[1].doc.rel)))
        return hits

    def to_repo_path(self, value):
        path = value.strip().replace("\\", "/")
        if re.match(r"^[A-Za-z]:/", path) or (path.startswith("/") and os.path.isabs(path)):
            full = os.path.abspath(path)
            lowered = full.lower()
            if lowered == self.root.lower() or lowered.startswith(self.root.lower() + os.sep):
                path = self.rel(full)
            else:
                path = full.replace("\\", "/")
        if path.startswith("./"):
            path = path[2:]
        return path.strip("/")

    def show_who(self, path):
        hits = self.find_features(path)
        if not hits:
            return [f"No feature lists {path}."]
        return [f"{feature.doc.rel}  ({feature.name})  via {token}" for _, feature, token in hits]

    def _code_prefixes(self):
        return [(folder + "/").lower() for folder, _ in self.settings.code_roots]

    def pre_commit_advice(self):
        roots = self.settings.code_roots
        if not roots:
            return []
        out = []
        try:
            result = subprocess.run(
                ["git", "-C", self.root, "-c", "core.quotepath=off", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
                capture_output=True, encoding="utf-8", errors="replace", check=False,
            )
            staged = result.stdout.splitlines() if result.returncode == 0 else []
        except OSError:
            staged = []
        prefixes = self._code_prefixes()
        code = [p for p in staged if p.lower().startswith(tuple(prefixes))]
        lines = []
        for path in code:
            for _, feature, _ in self.find_features(path):
                lines.append(f"  {path} - feature {feature.doc.rel} lists this path: did its rules change?")
        if lines:
            out.append("Advisory: staged code listed by features")
            out.extend(lines[:ADVISORY_CAP])
            if len(lines) > ADVISORY_CAP:
                out.append(f"  ... and {len(lines) - ADVISORY_CAP} more")

        entries = [entry for feature in self.features() for entry in feature.entries]
        map_full = self.full(MAP_REL)
        if os.path.isfile(map_full):
            folders = "|".join(re.escape(folder) for folder, _ in roots)
            rx = re.compile(r"(?<![\w-])(?:" + folders + r")/[\w./*?-]*")
            for match in rx.finditer(self.doc(map_full).masked):
                entries.append(Entry(match.group(0).rstrip(".,;:"), 0))
        uncovered = []
        for folder, _ in roots:
            for level_one in self.subdirs(self.full(folder)):
                for directory in [level_one] + self.subdirs(level_one):
                    rel = self.rel(directory)
                    if not any(entry_match(entry, rel) >= 0 for entry in entries):
                        uncovered.append(rel)
        if uncovered:
            out.append(f"Advisory: {len(uncovered)} code folders that no feature 'Built in' and no map line mentions")
            out.extend(f"  {rel}" for rel in uncovered[:ADVISORY_CAP])
            if len(uncovered) > ADVISORY_CAP:
                out.append(f"  ... and {len(uncovered) - ADVISORY_CAP} more")
        return out

    # -- open items

    @staticmethod
    def open_items(doc, whole_file):
        lines = doc.masked.split("\n")
        items = []
        in_open = whole_file
        current = None
        for index, raw in enumerate(lines):
            line = raw.rstrip("\r")
            if re.match(r"^ {0,3}#{1,6}[ \t]", line):
                current = None
                if not whole_file and re.match(r"^ {0,3}#{1,2}[ \t]", line):
                    in_open = bool(re.match(r"^##[ \t]+Open[ \t]*$", line, re.I))
                continue
            if not in_open:
                continue
            match = re.match(r"^\s*[-*+][ \t]+\[ \][ \t]*(?P<t>.*)$", line)
            if match:
                current = OpenItem(index + 1, match.group("t").strip())
                items.append(current)
            elif line.strip() == "" or re.match(r"^\s*(?:[-*+]|\d+[.)])[ \t]", line):
                current = None
            elif current:
                current.text = (current.text + " " + line.strip()).strip()
        return items

    def area_of(self, token):
        """Area of a code path, or None when the path is not under a code root."""
        path = token.strip()
        index = path.find("#")
        if index >= 0:
            path = path[:index]
        if path.startswith("./"):
            path = path[2:]
        path = path.lstrip("/").rstrip("/")
        for prefix, replacement in self.settings.area_aliases:
            if path.startswith(prefix):
                path = replacement + path[len(prefix):]
                break
        known = self.settings.known_file_ext()
        for folder, depth in self.settings.code_roots:
            if not path.lower().startswith(folder.lower() + "/"):
                continue
            segments = path.split("/")
            keep = []
            for k, segment in enumerate(segments):
                if len(keep) >= depth:
                    break
                if any(c in segment for c in "*?{}"):
                    break
                if k == len(segments) - 1 and (file_extension(segment) in known or segment == "Dockerfile"):
                    break
                keep.append(segment)
            return "/".join(keep)
        return None

    def areas_of(self, paths):
        areas = []
        for path in paths:
            area = self.area_of(path)
            if area and area not in areas:
                areas.append(area)
        return areas

    @staticmethod
    def lead_paths(doc):
        lines = doc.masked.split("\n")
        i = 0
        while i < len(lines) and not re.match(r"^#[ \t]", lines[i]):
            i += 1
        i = 0 if i >= len(lines) else i + 1
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        joined = []
        while i < len(lines) and lines[i].strip() != "" and not re.match(r"^ {0,3}#{1,6}[ \t]", lines[i]):
            joined.append(lines[i].strip())
            i += 1
        paths = []
        for match in re.finditer(r"`([^`]+)`", "".join(joined)):
            token = match.group(1).strip()
            if "/" in token and not re.search(r"\s", token) and "://" not in token:
                paths.append(token)
        return paths

    def map_paths(self, doc):
        map_full = self.full(MAP_REL)
        if not os.path.isfile(map_full):
            return []
        link = re.compile(r"\]\(" + re.escape(os.path.basename(doc.full)) + r"(?:#[^)]*)?\)", re.I)
        paths = []
        for line in self.doc(map_full).masked.split("\n"):
            for segment in line.split(";"):
                if not link.search(segment):
                    continue
                paths.extend(m.group(1) for m in re.finditer(r"`([^`\s]+/[^`\s]*)`", segment))
        return paths

    def file_areas(self, open_file):
        areas = []
        if open_file.kind == "feature":
            for feature in self.features():
                if self.same(feature.doc.full, open_file.doc.full):
                    areas = self.areas_of([e.path for e in feature.entries])
                    break
        else:
            areas = self.areas_of(self.lead_paths(open_file.doc))
            if not areas and open_file.kind == "tech":
                areas = self.areas_of(self.map_paths(open_file.doc))
        return areas or ["docs"]

    def open_files(self):
        groups = (
            (EPICS_REL, False, "doc"),
            (FEATURES_REL, False, "feature"),
            (STANDARDS_REL, False, "doc"),
            (TECH_REL, False, "tech"),
            (PLANS_REL, True, "doc"),
        )
        result = []
        for rel_dir, whole, kind in groups:
            files = sorted(self.md_files(rel_dir), key=lambda f: culture_key(self.rel(f)))
            for file in files:
                doc = self.doc(file)
                items = self.open_items(doc, whole)
                if items:
                    result.append(OpenFile(doc, self.title_of(doc, file), items, kind))
        return result

    def write_open_group(self, files, by_file):
        out = []
        if by_file:
            for open_file in files:
                out.append(f"{open_file.doc.rel}  ({open_file.name})")
                out.extend(f"  {item.line}: {item.text}" for item in open_file.items)
            return out
        by_area = {}
        for open_file in files:
            areas = self.file_areas(open_file)
            also = "  [also: " + ", ".join(areas[1:]) + "]" if len(areas) > 1 else ""
            slot = by_area.setdefault(areas[0].lower(), (areas[0], []))
            for item in open_file.items:
                text = (also + ("  " if also else "") + item.text).lstrip()
                slot[1].append((open_file.doc.rel, item.line, text))
        for area, rows in sorted(by_area.values(), key=lambda v: culture_key(v[0])):
            rows = sorted(rows, key=lambda r: (culture_key(r[0]), r[1]))
            out.append(f"{area}  ({len(rows)} {'item' if len(rows) == 1 else 'items'})")
            out.extend(f"  {rel}:{line}  {text}" for rel, line, text in rows)
        return out

    @staticmethod
    def select_items(files, defects):
        result = []
        for open_file in files:
            items = [i for i in open_file.items if bool(re.match(r"^Defect:", i.text, re.I)) == defects]
            if items:
                result.append(OpenFile(open_file.doc, open_file.name, items, open_file.kind))
        return result

    def show_open(self, by_file, defects_only):
        everything = self.open_files()
        tasks = self.select_items(everything, False)
        defects = self.select_items(everything, True)
        task_count = sum(len(f.items) for f in tasks)
        defect_count = sum(len(f.items) for f in defects)
        out = []
        if not defects_only:
            out.append(f"Tasks ({task_count})")
            out.extend(self.write_open_group(tasks, by_file))
        out.append(f"Defects ({defect_count})")
        out.extend(self.write_open_group(defects, by_file))
        if defects_only:
            out.append(f"open defects: {defect_count}")
        else:
            out.append(f"open items: {task_count + defect_count} ({task_count} tasks, {defect_count} defects)")
        return out


# ---------------------------------------------------------------- command line

def git_toplevel():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, encoding="utf-8", errors="replace", check=False
        )
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None


def build_parser():
    parser = argparse.ArgumentParser(
        prog="dev-kit-check-docs",
        description="Documentation check: structure, links, anchors, paths and the code-path-to-features index.",
    )
    parser.add_argument("--pre-commit", action="store_true", help="after the check, print the advisory lists")
    parser.add_argument("--who", metavar="PATH", help="print the features that list PATH and exit 0")
    parser.add_argument("--open", action="store_true", help="print all open items (tasks, then defects) and exit 0")
    parser.add_argument("--defects", action="store_true", help="print only the open defects")
    parser.add_argument("--by-file", action="store_true", help="with --open: group by file instead of code area")
    parser.add_argument("--root", metavar="DIR", help="project root (default: git toplevel of the current folder)")
    return parser


def main(argv=None, out=None):
    args = build_parser().parse_args(argv)
    out = out or sys.stdout
    root = args.root or git_toplevel()
    if not root:
        print("dev-kit-check-docs: not inside a git repository; pass --root DIR", file=sys.stderr)
        return 2
    settings, problems = load_settings(os.path.abspath(root))
    if problems:
        for problem in problems:
            print(f"dev-kit-check-docs: {problem}", file=sys.stderr)
        return 2
    checker = Checker(root, settings)
    if args.open or args.defects:
        lines = checker.show_open(args.by_file, args.defects)
        code = 0
    elif args.who:
        lines = checker.show_who(checker.to_repo_path(args.who))
        code = 0
    else:
        lines = checker.run_check()
        if args.pre_commit:
            lines.extend(checker.pre_commit_advice())
        code = 1 if checker.errors else 0
    for line in lines:
        print(line, file=out)
    return code


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
