"""Test marks check and coverage report: every new test carries a "protects" mark (Flow, Rule, Bug or Edge).

The rule lives in the skill test-change, section "Which tests to write". The mark syntax per language:
  C# xUnit      method-level [Trait("Protects", "Rule")] on a [Fact] / [Theory] method. Class-level
                [Trait("Kind", "Unit"|"Integration")] gives the level, [Trait("Domain", "X")] (repeatable) the domain.
  Vitest        title prefix: it("[Rule] ...") or test("[Rule] ...") with any quote style; describe is not marked.
  Python        a comment line `# protects: Rule` within the 3 lines above `def test_...` (above its decorators).
  Bug           the mark Bug also needs a `// Broke: <what>` (C#, Vitest) or `# Broke: <what>` (Python) comment line
                within the 3 lines above the test (above its attributes or decorators).
  Suspect       a test that may protect nothing gets a `// Suspect: <why>` (C#, Vitest) or `# Suspect: <why>`
                (Python) comment line in the same place as Broke (a test may carry both). The reason is required.
                A suspect line does not replace the protects mark.

Test files are found by pattern: *.cs under a folder whose name ends with Tests, *.test.* and *.spec.* for
ts/tsx/js/jsx, and test_*.py. Never entered: node_modules, bin, obj, dist, .git, __pycache__, venv, .venv, .idea,
.vs, .agent-env, .worktrees, plus the folders of the optional profile row. The profile is
`<root>/.claude/dev-kit.md`, section `## check-tests`, a table `| Setting | Value |` with one setting:
  skip-dirs    `name, name`    more folder names that are never entered

Modes:
  no flag        check: prints `file:line name - problem` and exits 1 on any error, else 0. Errors: a NEW test with no
                 mark; any test (new or old) with an invalid mark value; any Bug test without a Broke line; any
                 Suspect line with an empty reason. A test is
                 new when its name is not in the version of its file at --base REF (a file missing there: all its tests
                 are new; a renamed file is compared with its old path). Old unmarked tests are not errors.
  --report       coverage report, exit 0, no errors: per domain the counts by mark, suspect and level (then the list
                 of suspect tests), then for ASP.NET projects the API endpoints that no integration test mentions.
  --report --json  the same as JSON (every domain cell and the total have "suspects", the top level has the
                 "suspects" list).
  --suspects     prints every suspect test as `file:line name - why`, sorted by file, then a total line; exit 0.
  --suspects --json  the same as a JSON list of {file, line, name, suspect}.
  --base REF     the base of "new" (default HEAD): changed, staged and untracked files are compared with it.
  --root DIR     project root (default: git toplevel of the current folder).

Test name: C# Class.Method, Python Class.test_x (or test_x), Vitest the title. Level: C# the class Kind trait
(else unknown); Vitest E2E when the path has an e2e folder, else Unit; Python Integration when the path or class name
contains "integration", else Unit. Domain: C# the class Domain traits (a test counts once per domain row, so the rows
can add up to more than the total); otherwise the first folder below the test root (a folder named *Tests, test,
tests, __tests__, e2e or src), else "-".

Endpoints (--report only): routes are read from ASP.NET controllers ([Route] on the class with the [controller]
token, [HttpGet("...")] and the other verbs on methods, ~/ and / absolute templates, partial classes) and from minimal
API calls like app.MapGet("/x", ...) (MapGroup prefixes are not applied). An endpoint is covered when a string literal
in an integration test file matches its route: a route parameter such as {id} or {id:guid} matches any segment, and so
does an interpolation hole like {x} or a `" + x + "` concatenation in the test string; the query string and the
HTTP verb are ignored. Integration test files are C# files with a class marked Kind=Integration; a project with no
Kind traits at all uses every C# test file that mentions HttpClient or WebApplicationFactory. This is a path-mention
measure, not proof that every branch of the endpoint runs: a route built in a helper, or a request that is
never sent, still counts.
"""
import argparse
import bisect
import collections
import json
import os
import re
import subprocess
import sys

MARKS = ("Flow", "Rule", "Bug", "Edge")
HOLE = "\x00"
BUILTIN_SKIP_DIRS = (
    ".git", "node_modules", "bin", "obj", "dist", "__pycache__", ".venv", "venv", ".idea", ".vs",
    ".agent-env", ".worktrees",
)
PROFILE_REL = ".claude/dev-kit.md"
PROFILE_SECTION = "check-tests"
SETTING_NAMES = ("skip-dirs",)
LEVEL_ORDER = ("Unit", "Integration", "E2E", "unknown")
PROG = "dev-kit-check-tests"

# ---------------------------------------------------------------- text and profile


def decode_text(data):
    """Decode bytes like .NET ReadAllText: BOM detected and dropped, bad bytes replaced."""
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le", errors="replace")
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16-be", errors="replace")
    return data.decode("utf-8-sig", errors="replace")


def read_text(path):
    with open(path, "rb") as handle:
        return decode_text(handle.read())


def load_profile(root):
    """Return (skip_dirs list, [error text]) from `## check-tests` of the profile; no profile means no settings."""
    try:
        text = read_text(os.path.join(root, *PROFILE_REL.split("/")))
    except OSError:
        return [], []
    inside = False
    fenced = False
    skip = []
    errors = []
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            continue
        heading = re.match(r"^##\s+(.*?)\s*$", line)
        if heading:
            inside = heading.group(1).lower() == PROFILE_SECTION
            continue
        if not inside or not line.lstrip().startswith("|"):
            continue
        cells = [c.strip().replace("`", "").strip() for c in line.strip().strip("|").split("|")]
        if re.match(r"^:?-+:?$", cells[0] or "-") or cells[0].lower() == "setting":
            continue
        if len(cells) < 2 or not cells[1]:
            errors.append(f"{PROFILE_REL}: row '{' | '.join(cells)}' needs a setting and a value")
        elif cells[0] not in SETTING_NAMES:
            errors.append(f"{PROFILE_REL}: unknown setting '{cells[0]}' (known: {', '.join(SETTING_NAMES)})")
        else:
            names = [n for n in re.split(r"[,\s]+", cells[1]) if n]
            bad = [n for n in names if "/" in n or "\\" in n]
            if bad:
                errors.append(f"{PROFILE_REL}: skip-dirs '{bad[0]}' must be a folder name, not a path")
            skip.extend(names)
    return skip, errors


# ---------------------------------------------------------------- discovery

_JS_TEST_RX = re.compile(r"\.(?:test|spec)\.[cm]?[jt]sx?$", re.I)
_PY_TEST_RX = re.compile(r"^test_.*\.py$", re.I)
_ROOT_MARKERS = ("test", "tests", "__tests__", "e2e", "src")


def kind_of_file(rel):
    """'cs', 'js', 'py' or None for a project-relative path."""
    parts = rel.split("/")
    name, dirs = parts[-1], parts[:-1]
    if name.lower().endswith(".cs") and any(d.lower().endswith("tests") for d in dirs):
        return "cs"
    if _JS_TEST_RX.search(name):
        return "js"
    if _PY_TEST_RX.match(name):
        return "py"
    return None


def discover(root, skip_dirs=()):
    """Project-relative paths (sorted) of the test files under root."""
    skip = {n.lower() for n in BUILTIN_SKIP_DIRS} | {n.lower() for n in skip_dirs}
    found = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d.lower() not in skip)
        rel_dir = os.path.relpath(current, root).replace("\\", "/")
        for name in files:
            rel = name if rel_dir == "." else rel_dir + "/" + name
            if kind_of_file(rel):
                found.append(rel)
    return sorted(found)


def domain_from_path(rel):
    """First folder below the test root (see the docstring), else '-'."""
    dirs = rel.split("/")[:-1]
    for index, name in enumerate(dirs):
        lowered = name.lower()
        if lowered.endswith("tests") or lowered in _ROOT_MARKERS:
            return dirs[index + 1] if index + 1 < len(dirs) else "-"
    return "-"


# ---------------------------------------------------------------- model


class Test:
    def __init__(self, file, line, name, mark, level, domains, broke, suspect=None):
        self.file = file
        self.line = line
        self.name = name
        self.mark = mark  # None, or the raw value (valid when in MARKS)
        self.level = level
        self.domains = domains
        self.broke = broke  # a Broke comment sits within 3 lines above
        self.suspect = suspect  # reason text of a Suspect comment within 3 lines above ('' when empty), else None
        self.owners = []  # C#: class names, innermost first (partial classes get their traits from other files)
        self.kind_found = True
        self.domain_found = True

    @property
    def key(self):
        return self.name


def _line_index(text):
    return [m.start() for m in re.finditer("\n", text)]


def _line_of(newlines, pos):
    return bisect.bisect_left(newlines, pos) + 1


_BROKE_RX = re.compile(r"(?://|#)\s*Broke:\s*\S")
_SUSPECT_RX = re.compile(r"(?://|#)\s*Suspect:[ \t]*(.*)")


def _find_above(lines, head_line, name_line, rx):
    """First match of rx in the lines of the test head or up to 3 comment lines above it, else None.

    lines: raw lines of the file; 1-based head_line (first attribute or decorator) and name_line.
    """
    for i in range(head_line, min(name_line, len(lines) + 1)):
        found = rx.search(lines[i - 1])
        if found:
            return found
    for i in range(head_line - 1, max(0, head_line - 4), -1):  # up to 3 lines above, never past another test's code
        line = lines[i - 1].strip()
        found = rx.search(line)
        if found:
            return found
        if line and not line.startswith(("//", "#", "/*", "*")):
            break
    return None


def _has_broke(lines, head_line, name_line):
    return _find_above(lines, head_line, name_line, _BROKE_RX) is not None


def _suspect_of(lines, head_line, name_line):
    """The reason text of a Suspect comment line ('' when the reason is empty), or None without such a line."""
    found = _find_above(lines, head_line, name_line, _SUSPECT_RX)
    return found.group(1).strip() if found else None


# ---------------------------------------------------------------- C# scanner

_CS_TOKEN_RX = re.compile(r"//[^\n]*|/\*.*?\*/|[$@]*\"\"\"+|[$@]*\"|'(?:\\.[^'\n]{0,8}|[^'\\\n])'", re.S)
_NOT_NL = re.compile(r"[^\n]")


def _blank(text):
    return _NOT_NL.sub(" ", text)


def _skip_hole(text, i):
    """i is just after the '{' of an interpolation hole; return the index after its closing '}'."""
    depth = 1
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i = _scan_string(text, i + 1, "", 1)[0]
            continue
        if c == "'":
            m = re.compile(r"'(?:\\.[^'\n]{0,8}|[^'\\\n])'").match(text, i)
            if m:
                i = m.end()
                continue
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


NAME_MARK = "\x01"


def _hole_value(content):
    """A plain identifier hole keeps its name (between NAME_MARK) so that a const can fill it; else HOLE."""
    content = content.strip()
    return NAME_MARK + content + NAME_MARK if re.fullmatch(r"\w+", content) else HOLE


def _scan_string(text, i, prefix, quotes):
    """i is just after the opening quote(s); return (index after the string, value with HOLE for each hole)."""
    n = len(text)
    interp = "$" in prefix
    if quotes >= 3:
        end = text.find('"' * quotes, i)
        if end < 0:
            return n, text[i:]
        body = text[i:end]
        end += quotes
        while end < n and text[end] == '"':
            end += 1
        if interp:
            body = re.sub(r"\{+([^{}]*)\}+", lambda m: _hole_value(m.group(1)), body)
        return end, body
    verbatim = "@" in prefix
    out = []
    while i < n:
        c = text[i]
        if c == '"':
            if verbatim and text[i + 1:i + 2] == '"':
                out.append('"')
                i += 2
                continue
            return i + 1, "".join(out)
        if c == "\\" and not verbatim:
            out.append(text[i:i + 2])
            i += 2
            continue
        if interp and c == "{":
            if text[i + 1:i + 2] == "{":
                out.append("{")
                i += 2
                continue
            end = _skip_hole(text, i + 1)
            out.append(_hole_value(text[i + 1:end - 1]))
            i = end
            continue
        if interp and c == "}" and text[i + 1:i + 2] == "}":
            out.append("}")
            i += 2
            continue
        out.append(c)
        i += 1
    return n, "".join(out)


def cs_scan(text):
    """Return (code, masked, strings), all but strings with the length of text.

    code: comments blanked. masked: comments blanked and the inside of strings and chars blanked (safe for
    structure regexes and brace matching). strings: [(start, end, value)] with HOLE for interpolation holes
    (a hole that is a plain name is NAME_MARK + name + NAME_MARK).
    """
    code, masked, strings = [], [], []
    pos = 0
    while True:
        m = _CS_TOKEN_RX.search(text, pos)
        if not m:
            break
        gap = text[pos:m.start()]
        code.append(gap)
        masked.append(gap)
        tok = m.group(0)
        if tok.startswith("//") or tok.startswith("/*"):
            code.append(_blank(tok))
            masked.append(_blank(tok))
            pos = m.end()
        elif tok[0] == "'":
            code.append(tok)
            masked.append("'" + _blank(tok[1:-1]) + "'")
            pos = m.end()
        else:
            prefix = tok.rstrip('"')
            quotes = len(tok) - len(prefix)
            if "@" in prefix:
                quotes = 1
            open_end = m.start() + len(prefix) + quotes
            end, value = _scan_string(text, open_end, prefix, quotes)
            raw = text[m.start():end]
            inner = open_end - m.start()
            code.append(raw)
            masked.append(raw[:inner] + _blank(raw[inner:-1]) + raw[-1:] if len(raw) > inner else raw)
            strings.append((m.start(), end, value))
            pos = end
    tail = text[pos:]
    code.append(tail)
    masked.append(tail)
    return "".join(code), "".join(masked), strings


def _group_end(masked, start):
    """Index after the ']' that closes the '[' at start, or -1."""
    depth = 0
    for i in range(start, min(len(masked), start + 4000)):
        c = masked[i]
        if c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
            if depth == 0:
                return i + 1
    return -1


def _group_start(masked, close):
    """Index of the '[' that matches the ']' at close, or -1."""
    depth = 0
    for i in range(close, max(-1, close - 4000), -1):
        c = masked[i]
        if c == "]":
            depth += 1
        elif c == "[":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _enclosing_group(masked, pos):
    """(start, end) of the [...] group that holds position pos, or None."""
    depth = 0
    for i in range(pos, max(-1, pos - 2000), -1):
        c = masked[i]
        if c == "]":
            depth += 1
        elif c == "[":
            if depth == 0:
                end = _group_end(masked, i)
                return (i, end) if end > pos else None
            depth -= 1
    return None


def _groups_before(masked, pos):
    groups = []
    while True:
        j = pos
        while j > 0 and masked[j - 1].isspace():
            j -= 1
        if j == 0 or masked[j - 1] != "]":
            break
        start = _group_start(masked, j - 1)
        if start < 0:
            break
        groups.append((start, j))
        pos = start
    groups.reverse()
    return groups


def _groups_after(masked, pos):
    groups = []
    n = len(masked)
    while True:
        j = pos
        while j < n and masked[j].isspace():
            j += 1
        if j >= n or masked[j] != "[":
            break
        end = _group_end(masked, j)
        if end < 0:
            break
        groups.append((j, end))
        pos = end
    return groups


def _attr_block(masked, group):
    """All attribute groups of the member that holds the group (start, end)."""
    return _groups_before(masked, group[0]) + [group] + _groups_after(masked, group[1])


_FACT_RX = re.compile(r"(?<![\w.])(?:\w+\.)*\w*(?:Fact|Theory)\b")
_TRAIT_RX = re.compile(r'Trait\s*\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\)')
_CLASS_RX = re.compile(r"(?<![\w.])(?:record\s+(?:class|struct)|class|record|struct)\s+(\w+)")
_MODIFIERS_RX = re.compile(
    r"(?:\b(?:public|internal|private|protected|sealed|abstract|static|partial|unsafe|file|new|readonly)\s+)*\Z"
)
_SIGNATURE_RX = re.compile(
    r"\s*(?:(?:public|private|protected|internal|static|async|override|virtual|sealed|new|unsafe|extern|partial)\s+)*"
    r"(?:[\w<>\[\],.?]+(?:\s*,\s*[\w<>\[\],.?]+)*\s+)?(\w+)\s*(?:<[^<>]*>)?\s*\("
)


def _brace_map(masked):
    pairs = {}
    stack = []
    for m in re.finditer(r"[{}]", masked):
        if m.group(0) == "{":
            stack.append(m.start())
        elif stack:
            pairs[stack.pop()] = m.start()
    return pairs


class _CsClass:
    def __init__(self, name, pos, open_pos, close_pos, traits, route):
        self.name = name
        self.pos = pos
        self.open = open_pos
        self.close = close_pos
        self.traits = traits  # [(name, value)]
        self.route = route  # first [Route("...")] template or None

    def trait_values(self, name):
        return [v for n, v in self.traits if n == name]


def _traits_in(code, groups):
    found = []
    for s, e in groups:
        found.extend(_TRAIT_RX.findall(code[s:e]))
    return found


def _route_in(code, groups):
    for s, e in groups:
        m = _ROUTE_ATTR_RX.search(code[s:e])
        if m:
            return m.group(1)
    return None


def _cs_classes(code, masked):
    braces = _brace_map(masked)
    classes = []
    for m in _CLASS_RX.finditer(masked):
        before = masked[:m.start()].rstrip()
        if before.endswith((":", ",")):
            continue  # where T : class
        match = re.compile(r"[{;]").search(masked, m.end())
        if not match or match.group(0) != "{" or match.start() not in braces:
            continue
        window_start = max(0, m.start() - 200)
        mod = _MODIFIERS_RX.search(masked, window_start, m.start())
        start = mod.start() if mod else m.start()
        groups = _groups_before(masked, start)
        classes.append(_CsClass(m.group(1), m.start(), match.start(), braces[match.start()],
                                _traits_in(code, groups), _route_in(code, groups)))
    return classes


def _innermost(classes, pos):
    inside = [c for c in classes if c.open < pos < c.close]
    return sorted(inside, key=lambda c: c.open, reverse=True)


def parse_cs(rel, text, registry=None):
    """The xUnit tests of a C# file.

    registry, when given, collects {class name: {"Kind": [...], "Domain": [...]}} of every class of the file, so
    that a partial class gets the traits written in another file (see resolve_partials).
    """
    code, masked, _ = cs_scan(text)
    classes = _cs_classes(code, masked) if "Trait" in masked or "Fact" in masked or "Theory" in masked else []
    if registry is not None:
        for cls in classes:
            for trait in ("Kind", "Domain"):
                known = registry.setdefault(cls.name, {}).setdefault(trait, [])
                known.extend(v for v in cls.trait_values(trait) if v not in known)
    if "Fact" not in masked and "Theory" not in masked:
        return []
    newlines = _line_index(text)
    lines = text.splitlines()
    tests = []
    seen = set()
    for m in _FACT_RX.finditer(masked):
        before = masked[:m.start()].rstrip()
        if not before.endswith(("[", ",")):
            continue
        group = _enclosing_group(masked, m.start())
        if not group:
            continue
        block = _attr_block(masked, group)
        if block[0][0] in seen:
            continue
        sig = _SIGNATURE_RX.match(masked, block[-1][1])
        if not sig:
            continue
        seen.add(block[0][0])
        name_pos = sig.start(1)
        chain = _innermost(classes, name_pos)
        method_traits = _traits_in(code, block)

        def pick(trait):
            own = [v for n, v in method_traits if n == trait]
            if own:
                return own
            for cls in chain:
                values = cls.trait_values(trait)
                if values:
                    return values
            return []

        protects = [v for n, v in method_traits if n == "Protects"]
        mark = None if not protects else (protects[0] if len(protects) == 1 else "+".join(protects))
        kinds = pick("Kind")
        domains = pick("Domain")
        owner = chain[0].name + "." if chain else ""
        name_line = _line_of(newlines, name_pos)
        head_line = _line_of(newlines, block[0][0])
        test = Test(rel, name_line, owner + sig.group(1), mark, kinds[0] if kinds else "unknown",
                    list(domains) or [domain_from_path(rel)], _has_broke(lines, head_line, name_line),
                    _suspect_of(lines, head_line, name_line))
        test.owners = [c.name for c in chain]
        test.kind_found = bool(kinds)
        test.domain_found = bool(domains)
        tests.append(test)
    return tests


def resolve_partials(tests_by_file, registry):
    """Fill the level and domains of C# tests whose class traits sit in another file (partial classes)."""
    for tests in tests_by_file.values():
        for test in tests:
            for owner in test.owners:
                traits = registry.get(owner, {})
                if not test.kind_found and traits.get("Kind"):
                    test.level = traits["Kind"][0]
                    test.kind_found = True
                if not test.domain_found and traits.get("Domain"):
                    test.domains = list(traits["Domain"])
                    test.domain_found = True


# ---------------------------------------------------------------- Vitest and Python

_VITEST_RX = re.compile(
    r"(?<![\w.$])(?:it|test)(?:\.(?:only|skip|todo|concurrent|fails|sequential))*"
    r"(?:\.each\s*(?:\((?:[^()]|\([^()]*\))*\)|`[^`]*`))?\s*\(\s*([\"'`])((?:\\.|(?!\1)[^\\])*)\1",
    re.S,
)
_TITLE_MARK_RX = re.compile(r"^\s*\[([^\]]*)\]")


def parse_vitest(rel, text):
    newlines = _line_index(text)
    lines = text.splitlines()
    level = "E2E" if "e2e" in [p.lower() for p in rel.split("/")[:-1]] else "Unit"
    domain = domain_from_path(rel)
    tests = []
    for m in _VITEST_RX.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        prefix = text[line_start:m.start()]
        if "//" in prefix or prefix.lstrip().startswith(("*", "/*")):
            continue
        title = m.group(2)
        mark_match = _TITLE_MARK_RX.match(title)
        mark = mark_match.group(1).strip() if mark_match else None
        line = _line_of(newlines, m.start())
        tests.append(Test(rel, line, title, mark, level, [domain], _has_broke(lines, line, line),
                          _suspect_of(lines, line, line)))
    return tests


_PY_DEF_RX = re.compile(r"^(\s*)(?:async\s+)?def\s+(test\w*)\s*\(")
_PY_CLASS_RX = re.compile(r"^(\s*)class\s+(\w+)")
_PY_PROTECTS_RX = re.compile(r"^\s*#\s*protects:\s*([^\s,;.]+)", re.I)


def parse_python(rel, text):
    lines = text.splitlines()
    domain = domain_from_path(rel)
    tests = []
    classes = []  # (indent, name)
    for index, raw in enumerate(lines):
        cm = _PY_CLASS_RX.match(raw)
        if cm:
            indent = len(cm.group(1).expandtabs(4))
            classes = [c for c in classes if c[0] < indent] + [(indent, cm.group(2))]
            continue
        dm = _PY_DEF_RX.match(raw)
        if not dm:
            continue
        indent = len(dm.group(1).expandtabs(4))
        classes = [c for c in classes if c[0] < indent]
        head = index
        while head > 0 and lines[head - 1].lstrip().startswith("@"):
            head -= 1
        mark = None
        for i in range(max(0, head - 3), index):
            pm = _PY_PROTECTS_RX.match(lines[i])
            if pm:
                mark = pm.group(1)
        owner = classes[-1][1] + "." if classes else ""
        integration = "integration" in rel.lower() or (classes and "integration" in classes[-1][1].lower())
        tests.append(Test(rel, index + 1, owner + dm.group(2), mark, "Integration" if integration else "Unit",
                          [domain], _has_broke(lines, head + 1, index + 1), _suspect_of(lines, head + 1, index + 1)))
    return tests


def parse_file(rel, text):
    kind = kind_of_file(rel)
    if kind == "cs":
        return parse_cs(rel, text)
    if kind == "js":
        return parse_vitest(rel, text)
    if kind == "py":
        return parse_python(rel, text)
    return []


# ---------------------------------------------------------------- git and the check


class GitError(Exception):
    pass


def _git(root, *args):
    try:
        result = subprocess.run(
            ["git", "-C", root, "-c", "core.quotepath=off", *args], capture_output=True, check=False
        )
    except OSError as exc:
        raise GitError(f"git is not available: {exc}")
    return result


def changed_files(root, base):
    """{new project-relative path: base path or None for a file missing at base}, relative to root."""
    if _git(root, "rev-parse", "--verify", "--quiet", base + "^{commit}").returncode != 0:
        raise GitError(f"base '{base}' is not a commit of the repository at {root}")
    changed = {}
    diff = _git(root, "diff", "--name-status", "-z", "-M", "--relative", base, "--", ".")
    if diff.returncode != 0:
        raise GitError("git diff failed: " + diff.stderr.decode("utf-8", "replace").strip())
    parts = diff.stdout.decode("utf-8", "replace").split("\0")
    i = 0
    while i < len(parts) and parts[i]:
        status = parts[i]
        if status[0] in "RC" and i + 2 < len(parts):
            changed[parts[i + 2]] = parts[i + 1]
            i += 3
        else:
            if i + 1 < len(parts):
                changed[parts[i + 1]] = None if status[0] == "A" else parts[i + 1]
            i += 2
    untracked = _git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", ".")
    for path in untracked.stdout.decode("utf-8", "replace").split("\0"):
        if path:
            changed[path] = None
    return changed


def base_text(root, base, base_path):
    if base_path is None:
        return None
    result = _git(root, "show", f"{base}:./{base_path}")
    return decode_text(result.stdout) if result.returncode == 0 else None


def mark_problem(test):
    """Problem text for a test's mark (independent of new/old), or None."""
    if test.mark is None:
        return None
    if test.mark not in MARKS:
        return f"invalid mark '{test.mark}' (use one of {', '.join(MARKS)})"
    if test.mark == "Bug" and not test.broke:
        return "Bug test has no 'Broke: <what>' comment line within the 3 lines above"
    return None


def suspect_problem(test):
    """Problem text for a Suspect comment line with no reason (new or old test), or None."""
    if test.suspect == "":
        return "Suspect line has no reason (write 'Suspect: <why>')"
    return None


def suspect_list(tests_by_file):
    """The suspect tests as dicts {file, line, name, suspect}, sorted by file, then line."""
    found = [t for tests in tests_by_file.values() for t in tests if t.suspect is not None]
    found.sort(key=lambda t: (t.file, t.line))
    return [{"file": t.file, "line": t.line, "name": t.name, "suspect": t.suspect} for t in found]


def format_suspects(suspects):
    out = [f"{s['file']}:{s['line']} {s['name']} - {s['suspect'] or '(no reason)'}" for s in suspects]
    out.append(f"suspect tests: {len(suspects)}")
    return out


def new_tests(root, base, tests_by_file):
    """The set of ids of the tests that are new relative to base."""
    changed = changed_files(root, base)
    fresh = set()
    for rel, tests in tests_by_file.items():
        if rel not in changed:
            continue
        old = base_text(root, base, changed[rel])
        counts = collections.Counter(t.key for t in parse_file(rel, old)) if old is not None else {}
        seen = collections.Counter()
        for test in tests:
            seen[test.key] += 1
            if seen[test.key] > counts.get(test.key, 0):
                fresh.add(id(test))
    return fresh


def load_tests(root, skip_dirs=()):
    """{rel: [Test]} for every test file of the project, in file order."""
    result = {}
    registry = {}
    for rel in discover(root, skip_dirs):
        try:
            text = read_text(os.path.join(root, *rel.split("/")))
        except OSError:
            continue
        result[rel] = parse_cs(rel, text, registry) if kind_of_file(rel) == "cs" else parse_file(rel, text)
    resolve_partials(result, registry)
    return result


def run_check(root, base, tests_by_file):
    """Return (problem lines, number of new tests)."""
    fresh = new_tests(root, base, tests_by_file)
    lines = []
    for tests in tests_by_file.values():
        for test in tests:
            problem = mark_problem(test)
            if problem is None and test.mark is None and id(test) in fresh:
                problem = "new test has no protects mark (Flow, Rule, Bug or Edge)"
            if problem:
                lines.append(f"{test.file}:{test.line} {test.name} - {problem}")
            problem = suspect_problem(test)
            if problem:
                lines.append(f"{test.file}:{test.line} {test.name} - {problem}")
    return lines, len(fresh)


# ---------------------------------------------------------------- endpoints

_HTTP_RX = re.compile(r"(?<![\w.])Http(Get|Post|Put|Delete|Patch|Head|Options)\b")
_HTTP_TEMPLATE_RX = re.compile(r'\s*\(\s*"([^"]*)"')
_ROUTE_ATTR_RX = re.compile(r'(?<![\w.])Route\s*\(\s*"([^"]*)"')
_MINIMAL_RX = re.compile(r'\.Map(Get|Post|Put|Delete|Patch)\s*\(\s*"([^"]*)"')


class Endpoint:
    def __init__(self, verb, route, file, line, controller):
        self.verb = verb
        self.route = route
        self.file = file
        self.line = line
        self.controller = controller
        self.covered = False

    def as_dict(self):
        return {
            "verb": self.verb, "route": self.route, "controller": self.controller,
            "file": self.file, "line": self.line, "covered": self.covered,
        }


def _combine_route(class_route, template, controller, action):
    def sub(value):
        value = re.sub(r"\[controller\]", controller.lower(), value, flags=re.I)
        return re.sub(r"\[action\]", action.lower(), value, flags=re.I)

    template = sub(template)
    if template.startswith("~/") or template.startswith("/"):
        full = template.lstrip("~").lstrip("/")
    else:
        full = "/".join(p.strip("/") for p in (sub(class_route or ""), template) if p.strip("/"))
    return "/" + re.sub(r"/{2,}", "/", full).strip("/")


def collect_endpoints(files):
    """files: [(rel, text)] of non-test C# files. Return [Endpoint], controllers and minimal APIs."""
    class_routes = {}
    methods = []  # (verb, template, route attr, class name, action, rel, line)
    minimal = []
    for rel, text in files:
        if "Http" not in text and ".Map" not in text:
            continue
        code, masked, _ = cs_scan(text)
        newlines = _line_index(text)
        classes = _cs_classes(code, masked)
        for cls in classes:
            if cls.route is not None and cls.name not in class_routes:
                class_routes[cls.name] = cls.route
        done = set()
        for m in _HTTP_RX.finditer(masked):
            if not masked[:m.start()].rstrip().endswith(("[", ",")):
                continue
            group = _enclosing_group(masked, m.start())
            if not group:
                continue
            block = _attr_block(masked, group)
            tm = _HTTP_TEMPLATE_RX.match(code, m.end())
            template = tm.group(1) if tm else None
            route_attr = _route_in(code, block)
            if template is None:
                template = route_attr or ""
            sig = _SIGNATURE_RX.match(masked, block[-1][1])
            action = sig.group(1) if sig else ""
            chain = _innermost(classes, m.start())
            cls = chain[0].name if chain else ""
            key = (block[0][0], m.group(1))
            if key in done:
                continue
            done.add(key)
            methods.append((m.group(1).upper(), template, cls, action, rel, _line_of(newlines, m.start())))
        for m in _MINIMAL_RX.finditer(code):
            if masked[m.start():m.start() + 4] != code[m.start():m.start() + 4]:
                continue
            minimal.append((m.group(1).upper(), m.group(2), rel, _line_of(newlines, m.start())))
    endpoints = []
    seen = set()
    for verb, template, cls, action, rel, line in methods:
        controller = cls[:-len("Controller")] if cls.endswith("Controller") else cls
        route = _combine_route(class_routes.get(cls), template, controller, action)
        key = (verb, route, rel, line)
        if key not in seen:
            seen.add(key)
            endpoints.append(Endpoint(verb, route, rel, line, cls or "-"))
    for verb, template, rel, line in minimal:
        route = "/" + re.sub(r"/{2,}", "/", template).strip("/")
        key = (verb, route, rel, line)
        if key not in seen:
            seen.add(key)
            endpoints.append(Endpoint(verb, route, rel, line, "(minimal API)"))
    return endpoints


def _hole_pattern(segment):
    """The segment with every top-level {...} group (braces nest) replaced by HOLE."""
    out = []
    depth = 0
    for c in segment:
        if c == "{":
            if depth == 0:
                out.append(HOLE)
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        elif depth == 0:
            out.append(c)
    return "".join(out)


def _route_segments(template):
    segments = []
    depth = 0
    current = []
    for c in template.strip("/"):
        if c == "{":
            depth += 1
        elif c == "}":
            depth = max(0, depth - 1)
        if c == "/" and depth == 0:
            segments.append("".join(current))
            current = []
        else:
            current.append(c)
    segments.append("".join(current))
    return [s for s in segments if s != ""]


def _wild(a, b):
    """Patterns a and b, both with HOLE as a wildcard, can describe the same text (approximation)."""
    def rx(pattern):
        return re.compile(".*".join(re.escape(p) for p in pattern.split(HOLE)), re.S)

    return bool(rx(a).fullmatch(b.replace(HOLE, "x")) or rx(b).fullmatch(a.replace(HOLE, "x")))


def _match_segments(route, lit):
    if not route:
        return not lit
    head = route[0]
    if head.startswith("{*"):
        return True
    optional = head.startswith("{") and head.endswith("?}") and _hole_pattern(head) == HOLE
    if optional and _match_segments(route[1:], lit):
        return True
    if not lit:
        return False
    pattern = _hole_pattern(head).lower()
    given = lit[0].lower()
    if pattern == HOLE or given == HOLE:
        same = True
    else:
        same = _wild(pattern, given)
    return same and _match_segments(route[1:], lit[1:])


def route_matches(template, literal):
    """True when the path in a test string (HOLE marks an interpolation hole) can be a request to the route."""
    lit = [s for s in literal.strip("/").split("/") if s != ""]
    return _match_segments(_route_segments(template), lit)


def normalise_literal(raw):
    """The URL path of a string literal (query dropped, HOLE kept), or None when it is not a path."""
    if re.search(r"\s", raw.replace(HOLE, "")):
        return None
    raw = re.sub(r"^https?://[^/]*", "", raw)
    for cut in ("?", "#"):
        index = raw.find(cut)
        if index >= 0:
            raw = raw[:index]
    if raw.startswith(HOLE + "/"):
        raw = raw[1:]
    if "/" not in raw:
        return None
    return raw.strip("/") or None


_CONCAT_RX = re.compile(r"\s*\+\s*(?:[\w.\[\]()!?]+\s*\+\s*)?")
_TAIL_RX = re.compile(r"\s*\+\s*[\w.]")


_LEAD_RX = re.compile(r"(?<![\w.])(\w+)\s*\+\s*\Z")
_CONST_RX = re.compile(r"\b(?:const|readonly)\s+string\s+(\w+)\s*=\s*\Z")
_NAME_RX = re.compile(NAME_MARK + r"(\w+)" + NAME_MARK)


def string_literals(text):
    """Every string literal of a C# text, with concatenations and interpolation joined.

    A name (in `{name}` or `name + "..."`) is filled from a `const string name = "..."` of the same file; every
    other unknown part is HOLE.
    """
    _, masked, strings = cs_scan(text)
    consts = {}
    result = []
    i = 0
    while i < len(strings):
        start, end, value = strings[i]
        j = i + 1
        while j < len(strings):
            between = masked[end:strings[j][0]]
            if not _CONCAT_RX.fullmatch(between):
                break
            if "+" in between.strip()[1:]:
                value += HOLE
            value += strings[j][2]
            end = strings[j][1]
            j += 1
        if _TAIL_RX.match(masked, end):
            value += HOLE
        lead = _LEAD_RX.search(masked, max(0, start - 80), start)
        if lead:
            value = NAME_MARK + lead.group(1) + NAME_MARK + value
            start = lead.start()
        value = _NAME_RX.sub(lambda m: consts.get(m.group(1), HOLE), value)
        decl = _CONST_RX.search(masked, max(0, start - 80), start)
        if decl:
            consts[decl.group(1)] = value
        result.append(value)
        i = j
    return result


def integration_files(root, tests_by_file):
    """Project-relative C# test files whose string literals count for the endpoint coverage."""
    cs = [rel for rel in tests_by_file if kind_of_file(rel) == "cs"]
    texts = {}
    for rel in cs:
        texts[rel] = read_text(os.path.join(root, *rel.split("/")))
    has_kind = any(t.level != "unknown" for rel in cs for t in tests_by_file[rel])
    if has_kind:
        return [rel for rel in cs if any(t.level == "Integration" for t in tests_by_file[rel])], texts
    return [rel for rel in cs if "HttpClient" in texts[rel] or "WebApplicationFactory" in texts[rel]], texts


def endpoint_coverage(root, tests_by_file, skip_dirs=()):
    """Return [Endpoint] with .covered set."""
    skip = {n.lower() for n in BUILTIN_SKIP_DIRS} | {n.lower() for n in skip_dirs}
    sources = []
    for current, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d.lower() not in skip)
        rel_dir = os.path.relpath(current, root).replace("\\", "/")
        for name in files:
            rel = name if rel_dir == "." else rel_dir + "/" + name
            if name.lower().endswith(".cs") and kind_of_file(rel) is None:
                try:
                    sources.append((rel, read_text(os.path.join(current, name))))
                except OSError:
                    pass
    endpoints = collect_endpoints(sources)
    files, texts = integration_files(root, tests_by_file)
    literals = set()
    for rel in files:
        for value in string_literals(texts[rel]):
            path = normalise_literal(value)
            if path:
                literals.add(path)
    for endpoint in endpoints:
        endpoint.covered = any(route_matches(endpoint.route, lit) for lit in literals)
    return endpoints


# ---------------------------------------------------------------- report


def build_report(tests_by_file):
    all_tests = [t for tests in tests_by_file.values() for t in tests]

    def cell():
        return {"tests": 0, "marks": {m: 0 for m in MARKS} | {"none": 0, "invalid": 0}, "suspects": 0, "levels": {}}

    def add(entry, test):
        entry["tests"] += 1
        entry["suspects"] += test.suspect is not None
        key = test.mark if test.mark in MARKS else ("none" if test.mark is None else "invalid")
        entry["marks"][key] += 1
        entry["levels"][test.level] = entry["levels"].get(test.level, 0) + 1

    domains = {}
    total = cell()
    for test in all_tests:
        add(total, test)
        for domain in test.domains:
            add(domains.setdefault(domain, cell()), test)
    return {
        "files": sum(1 for tests in tests_by_file.values() if tests),
        "total": total,
        "domains": dict(sorted(domains.items(), key=lambda kv: kv[0].lower())),
        "suspects": suspect_list(tests_by_file),
    }


def format_report(report, endpoints):
    levels = list(LEVEL_ORDER)
    for entry in [report["total"], *report["domains"].values()]:
        for level in entry["levels"]:
            if level not in levels:
                levels.append(level)
    total = report["total"]
    out = [
        f"tests: {total['tests']} in {report['files']} files; marked {sum(total['marks'][m] for m in MARKS)}, "
        f"no mark {total['marks']['none']}, invalid mark {total['marks']['invalid']}, suspect {total['suspects']}",
    ]
    headers = ["domain", "tests", *MARKS, "none", "invalid", "suspect", *levels]
    rows = [headers]
    for name, entry in [*report["domains"].items(), ("TOTAL", total)]:
        rows.append([name, str(entry["tests"]), *(str(entry["marks"][m]) for m in MARKS),
                     str(entry["marks"]["none"]), str(entry["marks"]["invalid"]), str(entry["suspects"]),
                     *(str(entry["levels"].get(level, 0)) for level in levels)])
    widths = [max(len(r[i]) for r in rows) for i in range(len(headers))]
    for row in rows:
        out.append("  ".join(cell.ljust(widths[0]) if i == 0 else cell.rjust(widths[i])
                             for i, cell in enumerate(row)))
    out.append("(a test with several Domain traits is counted in each of its domain rows)")
    if report["suspects"]:
        out.append("suspect tests (a Suspect: line above the test; they may protect nothing):")
        out.extend("  " + line for line in format_suspects(report["suspects"])[:-1])
    if endpoints is None:
        return out
    if not endpoints:
        out.append("endpoints: none found")
        return out
    covered = sum(1 for e in endpoints if e.covered)
    out.append(f"{covered} of {len(endpoints)} endpoints have an integration test (a route mentioned in a test string; "
               "not proof that every branch runs)")
    for e in endpoints:
        if not e.covered:
            out.append(f"  {e.verb} {e.route}  {e.controller}  {e.file}:{e.line}")
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
        prog=PROG, description="Test marks check (new tests carry a protects mark) and the coverage report."
    )
    parser.add_argument("--report", action="store_true", help="print the coverage report (exit 0) instead of the check")
    parser.add_argument("--suspects", action="store_true",
                        help="list the tests with a Suspect: comment line (exit 0) instead of the check")
    parser.add_argument("--json", action="store_true", help="with --report or --suspects: print JSON")
    parser.add_argument("--base", metavar="REF", default="HEAD", help="what 'new' is measured against (default HEAD)")
    parser.add_argument("--root", metavar="DIR", help="project root (default: git toplevel of the current folder)")
    return parser


def main(argv=None, out=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.json and not (args.report or args.suspects):
        parser.error("--json needs --report or --suspects")
    if args.report and args.suspects:
        parser.error("--report and --suspects cannot be used together")
    out = out or sys.stdout
    root = args.root or git_toplevel()
    if not root:
        print(f"{PROG}: not inside a git repository; pass --root DIR", file=sys.stderr)
        return 2
    root = os.path.abspath(root)
    skip_dirs, problems = load_profile(root)
    if problems:
        for problem in problems:
            print(f"{PROG}: {problem}", file=sys.stderr)
        return 2
    tests_by_file = load_tests(root, skip_dirs)
    if args.suspects:
        suspects = suspect_list(tests_by_file)
        if args.json:
            print(json.dumps(suspects, indent=2, ensure_ascii=False), file=out)
        else:
            for line in format_suspects(suspects):
                print(line, file=out)
        return 0
    if args.report:
        report = build_report(tests_by_file)
        has_cs = any(kind_of_file(rel) == "cs" for rel in tests_by_file)
        endpoints = endpoint_coverage(root, tests_by_file, skip_dirs) if has_cs else None
        if args.json:
            payload = dict(report)
            if endpoints is not None:
                payload["endpoints"] = {
                    "total": len(endpoints),
                    "covered": sum(1 for e in endpoints if e.covered),
                    "list": [e.as_dict() for e in endpoints],
                }
            print(json.dumps(payload, indent=2, ensure_ascii=False), file=out)
        else:
            for line in format_report(report, endpoints):
                print(line, file=out)
        return 0
    try:
        lines, fresh = run_check(root, args.base, tests_by_file)
    except GitError as exc:
        print(f"{PROG}: {exc}", file=sys.stderr)
        return 2
    for line in lines:
        print(line, file=out)
    print(f"tests check: {len(lines)} errors, {fresh} new tests checked", file=out)
    return 1 if lines else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
