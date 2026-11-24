"""Process rules: mark the session parts that show a sign, and write a small packet per marked part for the part
reader agent (`agents/part-reader.md`, model haiku). No model here.

Signs are counted for body parts (`parts.body`: the session, a skill part, a subagent file); a hook event or an Agent
call inside one counts for it, and their sets join its candidates. A part has a sign when
- a general sign fires (GENERAL, the same for every set): `owner correction` (an owner message matches CORRECTION),
  `failed calls` (ERRORS_MIN error results), `repeated call` (one tool with one input REPEAT_MIN times; background
  calls and the plugins' own commands left out, as in the scan), `hook refusal` (REFUSALS_MIN hook refusals),
  `slow call` (a result SLOW_CALL_MIN minutes after its call, WAITING_TOOLS left out), `many calls` (MANY_CALLS);
  the thresholds are the scan's (`retro.py`, "Kinds");
- or a sign of a candidate set fires: a Signs row of kind `process` or `technical` whose Pattern has a regular
  expression (`«...»`); a process sign is matched against the owner's messages and the agent's text of the part, a
  technical one against its tool inputs and error results. Talk signs are left to the talk check (`talk.py`).

A packet (`<data folder>/packets/<session id8>[-<subagent file>]-L<start>.md`, and `.json` beside it for the commands)
holds the part's place, its signs with their evidence, its candidate sets, an excerpt of its lines (EXCERPT_CHARS at
most; the lines around the signs first) and the rule lines of the candidate sets: only the Files rows typed `process`
(of a sectioned file, only its process sections) that name the part's kind (a set found through a part kind) or every
process row (the global and the project set), cut to the lines around the words of the evidence (KEYWORDS words,
WINDOW lines around each hit, FILE_LINES per file, RULE_LINES in all); a file of the part's own kind with no hit gives
its headings instead. Never a whole file.

Sign gap (`gap_line`): when the part reader lays a part to a set whose own signs did not fire for it, the retro's
`rules-kit add --packet` writes a `sign-gap` finding for that set naming the pattern of the general sign that caught
it, so the fix loop adds that sign to the set's subscription."""
import datetime
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import parts
import talk

REPEAT_MIN = 3  # the same as retro.py
ERRORS_MIN = 3
REFUSALS_MIN = 2
SLOW_CALL_MIN = 10
MANY_CALLS = 150
WAITING_TOOLS = {"AskUserQuestion"}
OWN_COMMAND = ("dev-kit-", "rules-kit", "spend-kit")
GENERAL = ("owner correction", "failed calls", "repeated call", "hook refusal", "slow call", "many calls")
CORRECTION = re.compile(r"не так|я ж (казав|просив|писав)|не зрозумів|я заплутався|вгадуєш|навіщо ти|чому ти|"
                        r"\?\?|!!!|that's wrong|i said", re.IGNORECASE)
EXCERPT_CHARS = 12000
LINE_CHARS = 400
NEAR = 4  # entries kept around each sign line when the excerpt is cut
KEYWORDS = 15
WINDOW = 2
FILE_LINES = 40
RULE_LINES = 160
OUTLINE_LINES = 25
WORD = re.compile(r"[^\W\d_][\w-]{4,}")
STOP = set("""about above after again against agent agents allow always among another anything around because before
being below between both cannot claude could doing during each every first found from given going have having here
into itself just later least light might more most must never next none only other otherwise output over same
session sessions should since some still such than that their them then there these they thing this those through
under until upon very want were what when where which while with within without would your write written reads
після якщо тільки треба можна потім зараз тепер через також коли тому цього цьому щоби""".split())


def call_key(name, tool_input):
    return name + " " + json.dumps(tool_input, sort_keys=True, ensure_ascii=False)


def own_call(name, tool_input):
    return name == "Bash" and any(own in str(tool_input.get("command")) for own in OWN_COMMAND)


def parse_time(value):
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


class Marks:
    """What one body part showed: its general signs with their evidence, the sets' own signs, the lines and the parts
    (hook events, Agent calls) inside it that showed something."""

    def __init__(self, part):
        self.part = part
        self.general = {}  # sign -> (kind of the suggested sign, pattern, evidence text)
        self.own = {}  # set -> [sign names]
        self.lines = set()
        self.inner = []
        self.evidence = []  # texts the keywords come from


def collect(entries, found):
    """Per body part: owner messages, agent text, tool inputs, error results, refusals, calls (by line)."""
    data = defaultdict(lambda: {"owner": [], "text": [], "inputs": [], "errors": [], "refusals": [], "calls": Counter(),
                                "first": {}, "count": 0, "slow": [], "inner": {}})
    calls = {}
    for number, entry in entries:
        at = parts.innermost(found, number)
        if at is None:
            continue
        home = data[id(parts.body(at))]
        if at.kind in ("hook", "agent") and at.parent is not None:
            home["inner"][id(at)] = at
        kind = entry.get("type")
        content = (entry.get("message") or {}).get("content")
        stamp = parse_time(entry.get("timestamp"))
        if parts.prompt_kind(entry) == "owner":
            home["owner"].append((number, parts.text_of(content)))
        if kind == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text":
                    home["text"].append((number, str(block.get("text") or "")))
                elif block.get("type") == "tool_use":
                    name = block.get("name") or "?"
                    tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                    home["count"] += 1
                    home["inputs"].append((number, json.dumps(tool_input, ensure_ascii=False)))
                    calls[block.get("id")] = (name, stamp)
                    if not tool_input.get("run_in_background") and not own_call(name, tool_input):
                        key = call_key(name, tool_input)
                        home["calls"][key] += 1
                        home["first"].setdefault(key, (number, name, tool_input))
        elif kind == "user" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_result":
                    continue
                name, called = calls.get(block.get("tool_use_id"), ("?", None))
                text = parts.result_text(block)
                if block.get("is_error"):
                    home["errors"].append((number, name, text))
                    refusal = parts.hook_refusal(text)
                    if refusal:
                        home["refusals"].append((number, refusal[1]))
                if called and stamp and name not in WAITING_TOOLS:
                    minutes = (stamp - called).total_seconds() / 60
                    if minutes >= SLOW_CALL_MIN:
                        home["slow"].append((number, name, minutes))
    return data


def pattern_of(text, length=40):
    """A regular expression for a sign that would catch this text: its first words, escaped."""
    words = " ".join(str(text).split())[:length].strip()
    return re.escape(words).replace("\\ ", " ")


def mark(entries, found, registry=None, own=None, skip_first=False):
    """`[Marks]` of the body parts of one transcript that show a sign (module doc), in file order. `skip_first`: the
    first owner message is another session's brief (`talk.STARTED_BY_SESSION`), not the owner's words."""
    data = collect(entries, found)
    first_owner = next((number for number, entry in entries if parts.prompt_kind(entry) == "owner"), None)
    marked = []
    for part in found:
        if parts.body(part) is not part or id(part) not in data:
            continue
        item = data[id(part)]
        marks = Marks(part)
        for number, text in item["owner"]:
            if skip_first and number == first_owner:
                continue
            match = CORRECTION.search(talk.cleaned(text))
            if match:
                marks.general.setdefault("owner correction", ("process", re.escape(match.group(0)), text))
                marks.lines.add(number)
                marks.evidence.append(text)
        if len(item["errors"]) >= ERRORS_MIN:
            number, name, text = item["errors"][0]
            marks.general["failed calls"] = ("technical", pattern_of(text), f"{len(item['errors'])} errors, first {name}: {text}")
            marks.lines.update(line for line, _, _ in item["errors"])
            marks.evidence += [f"{name} {text}" for _, name, text in item["errors"][:5]]
        repeated = [(key, count) for key, count in item["calls"].most_common() if count >= REPEAT_MIN]
        if repeated:
            number, name, tool_input = item["first"][repeated[0][0]]
            text = json.dumps(tool_input, ensure_ascii=False)
            marks.general["repeated call"] = ("technical", pattern_of(text), f"{name} x{repeated[0][1]}: {text}")
            marks.lines.add(number)
            marks.evidence.append(f"{name} {text}")
        if len(item["refusals"]) >= REFUSALS_MIN:
            reason = item["refusals"][0][1]
            marks.general["hook refusal"] = ("technical", pattern_of(reason), f"x{len(item['refusals'])}: {reason}")
            marks.lines.update(line for line, _ in item["refusals"])
            marks.evidence.append(reason)
        if item["slow"]:
            number, name, minutes = item["slow"][0]
            marks.general["slow call"] = ("technical", "", f"{name} took {minutes:.0f} min")
            marks.lines.add(number)
        if item["count"] >= MANY_CALLS:
            marks.general["many calls"] = ("process", "", f"{item['count']} tool calls")
        marks.inner = [inner for inner in item["inner"].values()
                       if any(inner.start <= line <= inner.end for line in marks.lines)]
        if registry is not None:
            for name in parts.candidates(part, registry, own, marks.inner):
                subscription = registry.sets.get(name)
                for sign in subscription.signs if subscription else ():
                    if sign.regex is None or sign.kind not in ("process", "technical"):
                        continue
                    pool = item["owner"] + item["text"] if sign.kind == "process" else (
                        item["inputs"] + [(line, text) for line, _, text in item["errors"]])
                    hit = next(((line, text) for line, text in pool if sign.regex.search(text)), None)
                    if hit:
                        marks.own.setdefault(name, []).append(sign.name)
                        marks.lines.add(hit[0])
                        marks.evidence.append(hit[1])
        if marks.general or marks.own:
            marked.append(marks)
    return marked


def render(number, entry):
    """One line of an excerpt, or None for a line that shows nothing to the reader."""
    kind = entry.get("type")
    content = (entry.get("message") or {}).get("content")
    out = []
    prompt = parts.prompt_kind(entry)
    if prompt in ("owner", "command"):
        out.append(f"owner: {parts.text_of(content)}")
    elif prompt == "other":
        origin = entry.get("origin") if isinstance(entry.get("origin"), dict) else {}
        out.append(f"message ({origin.get('kind') or 'other'}): {parts.text_of(content)}")
    elif kind == "assistant" and isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text" and str(block.get("text") or "").strip():
                out.append(f"agent: {block.get('text')}")
            elif block.get("type") == "tool_use":
                out.append(f"call {block.get('name')}: {json.dumps(block.get('input'), ensure_ascii=False)}")
    elif kind == "user" and isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                out.append(f"result{' ERROR' if block.get('is_error') else ''}: {parts.result_text(block)}")
    elif kind == "attachment" and str((entry.get("attachment") or {}).get("type") or "").startswith("hook_"):
        attachment = entry["attachment"]
        out.append(f"hook {attachment.get('hookName') or attachment.get('type')}: {attachment.get('content')}")
    if not out:
        return None
    return "\n".join(f"L{number} " + " ".join(text.split())[:LINE_CHARS] for text in out)


def excerpt(entries, part, lines):
    """The rendered lines of a part, cut to EXCERPT_CHARS: the lines around the sign lines first, then from the start."""
    rendered = [(number, text) for number, entry in entries if part.start <= number <= part.end
                for text in [render(number, entry)] if text]
    if sum(len(text) + 1 for _, text in rendered) <= EXCERPT_CHARS:
        return "\n".join(text for _, text in rendered)
    keep = set()
    sign_index = [index for index, (number, _) in enumerate(rendered) if number in lines]
    for index in sign_index:
        keep.update(range(max(0, index - NEAR), min(len(rendered), index + NEAR + 1)))
    size = sum(len(rendered[index][1]) + 1 for index in keep)
    for index in range(len(rendered)):
        if size >= EXCERPT_CHARS:
            break
        if index not in keep:
            keep.add(index)
            size += len(rendered[index][1]) + 1
    out, last = [], -1
    used = 0
    for index in sorted(keep):
        text = rendered[index][1]
        if used + len(text) > EXCERPT_CHARS and used:
            out.append("...")
            break
        if last >= 0 and index != last + 1:
            out.append("...")
        out.append(text)
        used += len(text) + 1
        last = index
    return "\n".join(out)


def keywords(texts, extra=()):
    """The KEYWORDS most frequent words of the evidence (no stop words), lower-case."""
    counts = Counter()
    for text in list(texts) + list(extra):
        counts.update(word.lower() for word in WORD.findall(str(text)) if word.lower() not in STOP)
    return [word for word, _ in counts.most_common(KEYWORDS)]


def names_part(rule, chain):
    """Whether a Files row names one of the `(kind, name)` pairs (a row `hook <plugin>:<name>` names its plugin's hook)."""
    return any(kind in chain or (kind[0] == "hook" and ("hook", kind[1].split(":")[0]) in chain) for kind in rule.kinds)


def process_rows(subscription, chain):
    """`(rows, by kind)`: the `process` Files rows of a set that a packet reads: those naming one of the part kinds
    `chain` when the set names any of them in any row, else every process row."""
    if any(names_part(rule, chain) for rule in subscription.files):
        return [rule for rule in subscription.files if rule.type == "process" and names_part(rule, chain)], True
    return [rule for rule in subscription.files if rule.type == "process"], False


def rule_lines(registry, names, chain_kinds, words):
    """The rule lines a packet shows: `[(set, path, rel, [(line, text) or None for a gap])]` (module doc)."""
    out = []
    total = 0
    for name in names:
        subscription = registry.sets.get(name)
        if subscription is None:
            continue
        rows, by_kind = process_rows(subscription, chain_kinds)
        seen = set()
        for rule in rows:
            for path in parts.expand(subscription, rule):
                if str(path) in seen or total >= RULE_LINES:
                    continue
                seen.add(str(path))
                lines = parts.read_lines(path)
                marks = parts.headings(lines)
                typed = subscription.sections(path)
                scores = []
                for number, line in enumerate(lines, 1):
                    section = parts.section_of(marks, number)
                    if typed and subscription.type_of(path, section) != "process":
                        continue
                    low = line.lower()
                    score = sum(word in low for word in words)
                    if score:
                        scores.append((score, number))
                scores.sort(key=lambda pair: (-pair[0], pair[1]))
                chosen = set()
                for score, number in scores:
                    if len(chosen) >= FILE_LINES or (score < 2 and len(chosen) >= FILE_LINES // 2):
                        break
                    chosen.update(range(max(1, number - WINDOW), min(len(lines), number + WINDOW) + 1))
                if not chosen and by_kind:
                    chosen = set(sorted(marks)[:OUTLINE_LINES])
                if not chosen:
                    continue
                picked, last = [], None
                for number in sorted(chosen)[:max(0, min(FILE_LINES, RULE_LINES - total))]:
                    if last is not None and number != last + 1:
                        picked.append(None)
                    picked.append((number, lines[number - 1]))
                    last = number
                total += sum(1 for line in picked if line)
                out.append((name, path, subscription.rel(path), picked))
    return out


def chain_kinds(part, inner):
    """The `(kind, name)` pairs a subscription's Part kinds may name for a part, its parents and the parts inside it."""
    found = set()
    for item in list(inner) + [part]:
        walk = item
        while walk is not None:
            if walk.kind == "hook" and walk.plugin:
                found.add(("hook", walk.plugin))
            elif walk.kind in ("skill", "agent") and walk.name:
                found.add((walk.kind, walk.name))
            walk = walk.parent
    return found


def packet_name(transcript, part):
    path = Path(transcript)
    if path.parent.name == "subagents":
        return f"{path.parent.parent.name[:8]}-{path.stem}-L{part.start}"
    return f"{path.stem[:8]}-L{part.start}"


def write(folder, transcript, session_label, entries, marks, registry, own):
    """Write the packet of one marked part (module doc); returns its path and its JSON data."""
    part = marks.part
    sets = parts.candidates(part, registry, own, marks.inner)
    words = keywords(marks.evidence, [part.name.replace(":", " ")] + [inner.name for inner in marks.inner])
    rules = rule_lines(registry, sets, chain_kinds(part, marks.inner), words)
    lines = [f"# Part packet: {session_label} / {part.label()}", "",
             f"- transcript: {transcript} (lines {part.start}-{part.end})",
             f"- part: {part.label()}" + (f" (plugin {part.plugin})" if part.plugin else ""),
             f"- inside it: {', '.join(inner.label() for inner in marks.inner) or 'nothing marked'}",
             f"- candidate sets: {', '.join(sets) or 'none'}"]
    for sign, (_, _, evidence) in marks.general.items():
        lines.append(f"- sign: {sign}: " + " ".join(str(evidence).split())[:LINE_CHARS])
    for name, signs in marks.own.items():
        lines.append(f"- sign of set {name}: {', '.join(signs)}")
    lines += ["", "## Excerpt", "", excerpt(entries, part, marks.lines), "", "## Rule lines", ""]
    if not rules:
        lines.append("(none matched)")
    for name, path, rel, picked in rules:
        lines.append(f"### {name} | {rel or path}")
        lines += ["..." if item is None else f"{item[0]}: {item[1]}" for item in picked]
        lines.append("")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (packet_name(transcript, part) + ".md")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    data = {"session": session_label, "transcript": str(transcript), "part": part.label(),
            "lines": [part.start, part.end], "candidates": sets, "own_signs": marks.own,
            "general": [{"sign": sign, "kind": kind, "pattern": pattern, "evidence": " ".join(str(evidence).split())[:200]}
                        for sign, (kind, pattern, evidence) in marks.general.items()]}
    path.with_suffix(".json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return path, data


def load(path):
    """The JSON data of a packet (its `.md` or `.json` path), or None."""
    try:
        data = json.loads(Path(path).with_suffix(".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def gap_line(data, set_name, day):
    """The `sign-gap` finding for a set the part reader named, when none of that set's own signs fired for the part;
    None when one did or the packet shows no general sign."""
    if not data or (data.get("own_signs") or {}).get(set_name):
        return None
    general = [item for item in data.get("general") or [] if isinstance(item, dict)]
    if not general:
        return None
    first = next((item for item in general if item.get("pattern")), general[0])
    pattern = f"«{first['pattern']}»" if first.get("pattern") else f"({first.get('evidence', '')[:80]})"
    signs = ", ".join(str(item.get("sign")) for item in general)
    text = (f"{set_name}: the part {data.get('part')} of {data.get('session')} (lines {data.get('lines', ['?', '?'])[0]}-"
            f"{data.get('lines', ['?', '?'])[-1]}) was found only by the general signs ({signs}); a {first.get('kind')} "
            f"sign in its subscription would catch it: {first.get('sign')}: {pattern}")
    return f"- {day} | from rules-kit | sign-gap | " + " ".join(text.replace("|", "/").split())
