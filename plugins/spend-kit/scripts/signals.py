"""The waste signals of spend-kit: re-asks and their rework, a helper's model and reasoning against its agent file, a cheap
step redone and duplicated work. Pure functions over parsed transcript entries (dicts): no state, no unit weights of
their own (`spend.py` passes them as `Pricing`), the only file reads are the agent files, the experiment log and a
helper's `meta.json` given as a dict. The spec is the module doc of `spend.py` (section "Waste signals"); this file
holds the rules.

A trace (`read_trace`) is a compact view of one transcript file: the owner messages, the assistant messages with their
units (a message id once), the `Agent` calls, the `Read` calls and the size of every tool result. `read_run` reads a
helper's file the same way. `analyse_session` turns the trace of a main file and the runs of its helpers into events:

    {"kind": "reask" | "mismatch" | "redone" | "dup_shared" | "dup_reread" | "dup_launch", "key": "<kind>|<id>",
     "stamp": datetime or None, "units": float, "count": 0 or 1, "detail": "text"}

`key` is stable between two reads of a growing file, so a caller that keeps the keys it has taken counts an event once.

Copies: the owner-message test is `parts.prompt_kind` of rules-kit, `cleaned` is `talk.cleaned`, REASK_STRONG is
`packets.CORRECTION`'s pattern and REASK_SHORT is the same string rules-kit uses; keep equal (a test compares them)."""
import datetime
import json
import os
import re
from collections import Counter, namedtuple
from pathlib import Path

# Copy of rules-kit `packets.CORRECTION` (the pattern string); keep equal.
REASK_STRONG = (r"не так|я ж (казав|просив|писав)|не зрозумів|я заплутався|вгадуєш|навіщо ти|чому ти|"
                r"\?\?|!!!|that's wrong|i said")
# A bare «?», «що?», «ще раз ...»; matched with `.match` on the cleaned, stripped text (IGNORECASE | DOTALL). Same
# string as rules-kit's copy; keep equal.
REASK_SHORT = r"^\s*(?:\?+|(?:що|шо|what)\s*[?!]*|(?:ще раз|again)\b.*)\s*$"
REASK_FLAGS = re.IGNORECASE | re.DOTALL
REPEAT_MIN_WORDS = 3  # a repeated question has at least this many words ...
REPEAT_JACCARD = 0.6  # ... and shares this share of its words with one of the last REPEAT_LOOKBACK owner messages
REPEAT_LOOKBACK = 3
SAME_TASK_JACCARD = 0.6  # two `Agent` descriptions this alike are the same task
TASK_PREFIXES = ("M:", "C:", "Discuss:", "Обговорення:")  # a session titled so starts with the task, not a reply
AGENT_TOOLS = ("Agent", "Task")
SHELL_TOOLS = ("Bash", "PowerShell")
CHECK_COMMAND = re.compile(r"test|lint|check|pytest|unittest", re.IGNORECASE)  # a shell command that is a check
EXCERPT_CHARS = 120  # a sign's excerpt in an experiment packet
FINISHED_AFTER_S = 600  # a helper whose file did not grow for this long is finished (meta.json `finished` is True)
TOKEN_CHARS = 4  # characters per token, to size a tool result
PLUGINS_ENV = "SPEND_KIT_PLUGINS_DIR"  # a folder of plugin folders (`<it>/<plugin>/agents/<name>.md`), tests only
EXPERIMENTS_NAME = "experiments.jsonl"  # the experiment log in the spend-kit data folder (written by the experiment hook)
MODEL_RANK = {"haiku": 0, "sonnet": 1, "opus": 2, "fable": 3}
EFFORT_RANK = {"low": 0, "medium": 1, "high": 2, "xhigh": 3, "max": 4}
RULE_FILES = ("claude.md", "skill.md", "rules-subscription.md", "claude-facts.md", "messages.md")  # lowercase names
CHEAP_MODELS = ("haiku", "sonnet")
CHEAP_EFFORT = "low"

# Copies of rules-kit `talk.py` (FENCE, COMMENT, INLINE_CODE, QUOTED); keep equal.
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FENCE = re.compile(r"```.*?(```|\Z)", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
QUOTED = re.compile(r"«[^»\n]*»|“[^”\n]*”|\"[^\"\n]*\"")
WORD = re.compile(r"[^\W\d_]{3,}")

# What `spend.py` knows about prices, so this file needs none: `units(usage, model)`, `weight(model)` (the model's
# weight) and `cache_write` (the weight of a 5-minute cache write token).
Pricing = namedtuple("Pricing", "units weight cache_write")


# ---------------------------------------------------------------- small helpers

def parse_stamp(value):
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def text_of(content):
    """The text of a message's content: a string, or the text blocks of a list (copy of rules-kit `parts.text_of`)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(block.get("text") or "") for block in content
                         if isinstance(block, dict) and block.get("type") == "text")
    return ""


def family(model):
    """`haiku`, `sonnet`, `opus` or `fable` from a model id; None for any other."""
    model = str(model or "").lower()
    return next((name for name in MODEL_RANK if name in model), None)


def words(text):
    """The lowercase words of 3 or more letters of a text, as a set."""
    return set(WORD.findall(str(text or "").lower()))


def jaccard(left, right):
    left, right = words(left), words(right)
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def norm_path(path):
    """A file path as one key: resolved, lowercase, forward slashes."""
    try:
        resolved = str(Path(path).resolve())
    except (OSError, ValueError):
        resolved = os.path.normpath(str(path))
    return resolved.replace("\\", "/").lower()


# ---------------------------------------------------------------- A. re-asks

def owner_text(entry):
    """The text of an owner message, or None for any other line: a `user` line that is not meta, holds no tool result,
    no slash command or local command output, and came from the human (`origin.kind` is `human`)."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list) and any(isinstance(block, dict) and block.get("type") == "tool_result"
                                         for block in content):
        return None
    text = text_of(content)
    if "<command-name>" in text or "<local-command-" in text:
        return None
    origin = entry.get("origin")
    return text if isinstance(origin, dict) and origin.get("kind") == "human" else None


def cleaned(text):
    """The owner's own prose of a message: no code, quote lines, table rows or quoted words (copy of `talk.cleaned`)."""
    text = FENCE.sub("\n", COMMENT.sub("", text or ""))
    lines = [line for line in text.splitlines() if not line.lstrip().startswith((">", "|"))]
    return QUOTED.sub("", INLINE_CODE.sub("", "\n".join(lines)))


def repeated_question(text, previous_texts):
    """True when `text` is a question (it has a `?`) of at least REPEAT_MIN_WORDS words whose word set has a Jaccard of
    REPEAT_JACCARD or more with one of the last REPEAT_LOOKBACK of `previous_texts` (the owner's earlier messages) that
    also has at least REPEAT_MIN_WORDS words (rules-kit's copy does the same; keep equal)."""
    mine = words(text)
    if "?" not in text or len(mine) < REPEAT_MIN_WORDS:
        return False
    for earlier in list(previous_texts)[-REPEAT_LOOKBACK:]:
        other = words(earlier)
        if len(other) < REPEAT_MIN_WORDS:
            continue
        union = mine | other
        if union and len(mine & other) / len(union) >= REPEAT_JACCARD:
            return True
    return False


def reask_kind(text, previous_texts):
    """`strong`, `short` or `repeat` when the owner message `text` is a re-ask, else None. `previous_texts`: the cleaned
    texts of the owner's earlier messages of the session."""
    clean = cleaned(text).strip()
    if re.search(REASK_STRONG, clean, re.IGNORECASE):
        return "strong"
    if re.match(REASK_SHORT, clean, REASK_FLAGS):
        return "short"
    if repeated_question(clean, previous_texts):
        return "repeat"
    return None


def started_by_task(title):
    """True for a session whose title says its first message is the task (`M:`, `C:`, `Discuss:`, `Обговорення:`)."""
    return str(title or "").strip().startswith(TASK_PREFIXES)


def find_reasks(owners, title=""):
    """`[(position in owners, kind)]` of the re-asks among the owner messages `[{"text": ...}, ...]` of one session;
    the first message of a session that a task title marks is skipped."""
    found, earlier = [], []
    for position, owner in enumerate(owners):
        clean = cleaned(owner["text"]).strip()
        skip = position == 0 and started_by_task(title)
        kind = None if skip else reask_kind(owner["text"], earlier)
        if kind:
            found.append((position, kind))
        earlier.append(clean)
    return found


# ---------------------------------------------------------------- traces of a transcript file

def read_trace(entries, price, main_only=False):
    """The compact view of one transcript file from its parsed entries (module doc). `main_only` leaves out side chain
    lines, the subagent messages a main file may keep. Keys: owners, messages, agents, reads, results, title, cwd,
    first, last, efforts, first_effort, checks. `line` of an owner message, `Agent` call, tool result or check is the
    file line number (`_line` of the entry, as `spend.entries_of` sets it), else the entry's position + 1."""
    owners, messages, agents, reads, results, checks = [], [], [], [], {}, []
    seen, efforts = set(), Counter()
    title, cwd, first, last, first_effort = "", None, None, None, None
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        line = entry.get("_line") or index + 1
        if cwd is None and isinstance(entry.get("cwd"), str) and entry["cwd"]:
            cwd = entry["cwd"]
        kind = entry.get("type")
        if kind == "custom-title":
            title = entry.get("customTitle") or title
            continue
        if kind not in ("user", "assistant") or (main_only and entry.get("isSidechain")):
            continue
        stamp = parse_stamp(entry.get("timestamp"))
        if stamp:
            first = first or stamp
            last = stamp
        message = entry.get("message") if isinstance(entry.get("message"), dict) else {}
        content = message.get("content")
        if kind == "user":
            text = owner_text(entry)
            if text is not None:
                owners.append({"i": index, "line": line, "stamp": stamp, "text": text})
            for block in content if isinstance(content, list) else []:
                if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("tool_use_id"):
                    shown = text_of(block.get("content"))
                    results[block["tool_use_id"]] = {"stamp": stamp, "chars": len(shown), "line": line,
                                                     "error": bool(block.get("is_error")),
                                                     "text": shown[:EXCERPT_CHARS] if block.get("is_error") else ""}
            continue
        model, usage, mid = message.get("model"), message.get("usage"), message.get("id")
        if isinstance(entry.get("effort"), str) and first_effort is None:
            first_effort = entry["effort"].lower()
        if isinstance(usage, dict) and model != "<synthetic>" and not (mid and mid in seen):
            if mid:
                seen.add(mid)
            if isinstance(entry.get("effort"), str):
                efforts[entry["effort"].lower()] += 1
            messages.append({"i": index, "stamp": stamp, "id": mid or f"#{index}", "model": model,
                             "units": price.units(usage, model), "weight": price.weight(model)})
        for block in content if isinstance(content, list) else []:
            if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                continue
            given = block.get("input") if isinstance(block.get("input"), dict) else {}
            if block.get("name") in AGENT_TOOLS:
                agents.append({"i": index, "line": line, "stamp": stamp, "id": block.get("id"),
                               "type": str(given.get("subagent_type") or ""),
                               "description": str(given.get("description") or "")})
            elif block.get("name") in SHELL_TOOLS:
                checks.append({"i": index, "line": line, "id": block.get("id"), "stamp": stamp,
                               "command": str(given.get("command") or "")})
            elif block.get("name") == "Read" and isinstance(given.get("file_path"), str) and given["file_path"]:
                reads.append({"i": index, "stamp": stamp, "id": block.get("id"), "path": norm_path(given["file_path"]),
                              "weight": price.weight(model)})
    return {"owners": owners, "messages": messages, "agents": agents, "reads": reads, "results": results,
            "title": title, "cwd": cwd, "first": first, "last": last, "efforts": efforts, "first_effort": first_effort,
            "checks": checks}


def top_family(messages):
    """The model family with the most units among `messages`, else None."""
    units = Counter()
    for message in messages:
        units[family(message["model"]) or "other"] += message["units"]
    return units.most_common(1)[0][0] if units else None


def read_run(entries, meta, price, run_id=""):
    """A helper run from its file's entries and its `meta.json` (a dict): type, the `Agent` call it answers
    (`tool_use_id`), `description`, `model` (the family with the most units), `effort` (of its first assistant line),
    `units`, `units_by_id`, `reads` (path, size in characters, time, model weight), `started`, `ended`, `finished`."""
    trace = read_trace(entries, price)
    meta = meta if isinstance(meta, dict) else {}
    reads = [{"path": read["path"], "chars": trace["results"].get(read["id"], {}).get("chars", 0),
              "stamp": read["stamp"], "weight": read["weight"]} for read in trace["reads"]]
    return {"id": run_id, "type": str(meta.get("agentType") or "").strip() or "?",
            "tool_use_id": meta.get("toolUseId") or None, "description": str(meta.get("description") or ""),
            "model": top_family(trace["messages"]), "effort": trace["first_effort"],
            "units": sum(message["units"] for message in trace["messages"]),
            "units_by_id": {message["id"]: message["units"] for message in trace["messages"]},
            "reads": reads, "started": trace["first"], "ended": trace["last"],
            "marked_finished": meta.get("finished") is True}


def is_finished(run, now):
    """A run is finished when its meta says so, or its file did not grow for FINISHED_AFTER_S seconds."""
    if run["marked_finished"]:
        return True
    return bool(run["ended"] and now and (now - run["ended"]).total_seconds() >= FINISHED_AFTER_S)


# ---------------------------------------------------------------- C. model and reasoning against the agent file

def front_matter(text):
    """The `key: value` lines of a file's front matter, keys and values lowercase."""
    lines = str(text or "").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    found = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        if value.strip():
            found[key.strip().lower()] = value.strip().strip("'\"").lower()
    return found


def read_json(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def plugin_agent_folders(plugin, home=None):
    """The `agents` folders that can hold a plugin's agent files, best first: the env override alone when set; else the
    directory marketplace holding the plugin, its install folder, the sibling plugin folder of spend-kit (the way
    dev-kit's `narrow-agents.py` finds them)."""
    if os.environ.get(PLUGINS_ENV):
        return [Path(os.environ[PLUGINS_ENV]) / plugin / "agents"]
    home = Path(home) if home else Path.home()
    folders = []
    for entry in read_json(home / ".claude" / "plugins" / "known_marketplaces.json").values():
        source = entry.get("source") if isinstance(entry, dict) else None
        location = entry.get("installLocation") if isinstance(entry, dict) else None
        if isinstance(source, dict) and source.get("source") == "directory" and isinstance(location, str) and location:
            plugins = read_json(Path(location) / ".claude-plugin" / "marketplace.json").get("plugins")
            for item in plugins if isinstance(plugins, list) else []:
                relative = item.get("source") if isinstance(item, dict) else None
                if item.get("name") == plugin and isinstance(relative, str) and relative.startswith("."):
                    folders.append(Path(location) / relative / "agents")
    installed = read_json(home / ".claude" / "plugins" / "installed_plugins.json").get("plugins")
    for key, entries in (installed.items() if isinstance(installed, dict) else []):
        if key.partition("@")[0] == plugin:
            folders += [Path(item["installPath"]) / "agents" for item in entries
                        if isinstance(item, dict) and isinstance(item.get("installPath"), str)]
    folders.append(Path(__file__).resolve().parents[2] / plugin / "agents")
    return folders


def agent_settings(kind, cwd, home=None):
    """`{"model": ..., "effort": ...}` (lowercase, only what the agent's file sets; `inherit` counts as unset) of an
    agent type, or None when no file is found. `plugin:name` -> the plugin's `agents/name.md`; a bare `name` ->
    `<cwd>/.claude/agents/name.md`, then `~/.claude/agents/name.md`."""
    plugin, colon, name = str(kind or "").partition(":")
    if colon:
        folders = plugin_agent_folders(plugin, home)
    else:
        name = plugin
        home = Path(home) if home else Path.home()
        folders = ([Path(cwd) / ".claude" / "agents"] if cwd else []) + [home / ".claude" / "agents"]
    for folder in folders:
        path = folder / f"{name}.md"
        try:
            text = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        found = front_matter(text)
        return {key: found[key] for key in ("model", "effort") if found.get(key) and found[key] != "inherit"}
    return None


def read_experiments(folder):
    """The `tool_use_id`s of the runs in the experiment log `<folder>/experiments.jsonl` (one JSON per line with at least
    `tool_use_id`, `type`, `variant`, `model`, `effort`, `time`, `session`); a missing file or a bad line gives none."""
    found = set()
    try:
        lines = (Path(folder) / EXPERIMENTS_NAME).read_text(encoding="utf-8").splitlines()
    except OSError:
        return found
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and entry.get("tool_use_id"):
            found.add(entry["tool_use_id"])
    return found


def model_rank(model):
    """The rank of a model id or family (haiku < sonnet < opus < fable), None for an unknown one."""
    model = str(model or "").lower()
    return next((position for name, position in MODEL_RANK.items() if name in model), None)


def effort_rank(effort):
    """The rank of a reasoning level (low < medium < high < xhigh < max), None for an unknown one."""
    return EFFORT_RANK.get(str(effort or "").lower())


def label(model, effort):
    return " ".join(part for part in (model.capitalize() if model else "", effort or "") if part)


def mismatch(run, settings):
    """The sentence `<type> ran on <Model> <effort>, its file says <model> <effort>` when the run's model family or
    effort ranks above its agent file's, else None. `settings` is `agent_settings`'s result (None: no file)."""
    if not settings:
        return None
    run_model, file_model = model_rank(run["model"]), model_rank(settings.get("model"))
    run_effort, file_effort = effort_rank(run["effort"]), effort_rank(settings.get("effort"))
    higher = ((run_model is not None and file_model is not None and run_model > file_model)
              or (run_effort is not None and file_effort is not None and run_effort > file_effort))
    if not higher:
        return None
    return (f"{run['type']} ran on {label(run['model'], run['effort'])}, "
            f"its file says {label(settings.get('model'), settings.get('effort'))}")


def is_cheap(run):
    return run["model"] in CHEAP_MODELS or run["effort"] == CHEAP_EFFORT


# ---------------------------------------------------------------- the events of a session

def span_units(trace, runs_by_call, start, end, counted):
    """The units of the main messages with a line number in [start, end) plus the whole units of each helper file whose
    `toolUseId` is an `Agent` call of that span; a message id once over `counted`."""
    units = 0.0
    for message in trace["messages"]:
        if message["i"] >= start and (end is None or message["i"] < end) and message["id"] not in counted:
            counted.add(message["id"])
            units += message["units"]
    for call in trace["agents"]:
        run = runs_by_call.get(call["id"])
        if run and call["i"] >= start and (end is None or call["i"] < end):
            for mid, value in run["units_by_id"].items():
                if mid not in counted:
                    counted.add(mid)
                    units += value
    return units


def reask_events(trace, runs_by_call, reasks):
    """One event per re-ask (`reasks` from `find_reasks`) with its rework units: the main messages from it to the next
    owner message plus the whole helper files launched in that span (a message id once)."""
    events, counted = [], set()
    owners = trace["owners"]
    for position, kind in reasks:
        end = owners[position + 1]["i"] if position + 1 < len(owners) else None
        units = span_units(trace, runs_by_call, owners[position]["i"], end, counted)
        events.append({"kind": "reask", "key": f"reask|{owners[position]['i']}", "stamp": owners[position]["stamp"],
                       "units": units, "count": 1, "detail": kind})
    return events


def next_owner(owners, after):
    """The first owner message after the time `after`, or None."""
    return next((owner for owner in owners if owner["stamp"] and after and owner["stamp"] > after), None)


def redone_events(trace, runs, reasks, calls, now):
    """A finished cheap run (Sonnet, Haiku or low reasoning) followed, before the next owner message after it ended, by
    a re-ask (that owner message is one) or by another `Agent` call of the same type for the same task."""
    events = []
    asked = {trace["owners"][position]["i"] for position, _ in reasks}
    for run in runs:
        if not (is_finished(run, now) and is_cheap(run) and run["ended"]):
            continue
        call = calls.get(run["tool_use_id"]) or {}
        kind = call.get("type") or run["type"]
        task = call.get("description") or run["description"]
        later = next_owner(trace["owners"], run["ended"])
        again = later is not None and later["i"] in asked
        returned = (trace["results"].get(run["tool_use_id"]) or {}).get("stamp") or run["ended"]
        if not again:  # a launch counts only when it starts after the first run's tool result (not a parallel one)
            again = any(other["id"] != run["tool_use_id"] and other["type"] == kind and other["stamp"]
                        and other["stamp"] > returned and (later is None or other["stamp"] < later["stamp"])
                        and jaccard(other["description"], task) >= SAME_TASK_JACCARD for other in trace["agents"])
        if again:
            events.append({"kind": "redone", "key": f"redone|{run['id']}", "stamp": run["ended"],
                           "units": run["units"], "count": 1,
                           "detail": f"{run['type']} ran on {label(run['model'], run['effort'])}, then its step was redone"})
    return events


def is_rule_file(path):
    """True for a file every agent is told to read (a normalized path): CLAUDE.md, .claude/dev-kit.md, any SKILL.md,
    agents/*.md, rules-subscription.md, claude-facts.md, messages.md. Reading these twice is not duplicated work."""
    parts = str(path).split("/")
    name = parts[-1]
    return (name in RULE_FILES or (name == "dev-kit.md" and parts[-2:-1] == [".claude"])
            or (name.endswith(".md") and parts[-2:-1] == ["agents"]))


def read_units(chars, weight, price):
    """A duplicate read's cost: its result in tokens priced as a 5-minute cache write, times the reader's model weight."""
    return chars / TOKEN_CHARS * price.cache_write * weight


def duplicate_events(trace, runs, price, now):
    """(1) files read by 2 or more helper runs, (2) files the main chain reads after a helper that read them returned,
    (3) an `Agent` call repeating an earlier finished one (same type, description Jaccard >= SAME_TASK_JACCARD). The
    units are an estimate (see the module doc of `spend.py`)."""
    events = []
    done = sorted((run for run in runs if is_finished(run, now)),
                  key=lambda run: run["started"].timestamp() if run["started"] else 0)
    readers = {}  # path -> [(run, first read)]
    for run in done:
        seen = set()
        for read in run["reads"]:
            if read["path"] not in seen and not is_rule_file(read["path"]):
                seen.add(read["path"])
                readers.setdefault(read["path"], []).append((run, read))
    for path, found in readers.items():
        for number, (run, read) in enumerate(found[1:]):
            events.append({"kind": "dup_shared", "key": f"shared|{path}|{run['id']}", "stamp": read["stamp"],
                           "units": read_units(read["chars"], read["weight"], price), "count": 1 if number == 0 else 0,
                           "detail": path})
    taken = set()
    for read in trace["reads"]:
        if read["path"] in taken or read["path"] not in readers or not read["stamp"]:
            continue
        if any(run["ended"] and run["ended"] <= read["stamp"] for run, _ in readers[read["path"]]):
            taken.add(read["path"])
            chars = trace["results"].get(read["id"], {}).get("chars", 0)
            events.append({"kind": "dup_reread", "key": f"reread|{read['path']}", "stamp": read["stamp"],
                           "units": read_units(chars, read["weight"], price), "count": 1, "detail": read["path"]})
    by_call = {run["tool_use_id"]: run for run in runs if run["tool_use_id"]}
    for number, call in enumerate(trace["agents"]):
        for earlier in trace["agents"][:number]:
            before = by_call.get(earlier["id"])
            if before:  # the helper's own file says when it finished (a background call's result comes at once)
                returned = before["ended"] if is_finished(before, now) else None
            else:
                returned = (trace["results"].get(earlier["id"]) or {}).get("stamp")
            if (earlier["type"] == call["type"] and returned and call["stamp"] and returned <= call["stamp"]
                    and jaccard(earlier["description"], call["description"]) >= SAME_TASK_JACCARD):
                again = by_call.get(call["id"])
                events.append({"kind": "dup_launch", "key": f"launch|{call['id']}", "stamp": call["stamp"],
                               "units": again["units"] if again else 0.0, "count": 1, "detail": call["type"]})
                break
    return events


def analyse_session(trace, runs, price, now, title="", cwd="", experiments=(), settings=None):
    """The signals of one main transcript and the runs of its helpers (`read_run` results):
    `{"events": [...], "model": family, "effort": most common effort, "open_runs": runs not finished yet}`.

    The trace's own title and `cwd` win; `title` and `cwd` are the fallback; `experiments` are the `tool_use_id`s in the experiment log (their runs
    give no `mismatch`); `settings(type, cwd)` finds an agent file (default `agent_settings`)."""
    title = trace["title"] or title
    cwd = trace["cwd"] or cwd or ""
    settings = settings or agent_settings
    by_call = {run["tool_use_id"]: run for run in runs if run["tool_use_id"]}
    calls = {call["id"]: call for call in trace["agents"]}
    reasks = find_reasks(trace["owners"], title)
    events = reask_events(trace, by_call, reasks)
    for run in runs:
        if not is_finished(run, now) or run["tool_use_id"] in experiments:
            continue
        text = mismatch(run, settings(run["type"], cwd))
        if text:
            events.append({"kind": "mismatch", "key": f"mismatch|{run['id']}", "stamp": run["ended"],
                           "units": run["units"], "count": 1, "detail": text})
    events += redone_events(trace, runs, reasks, calls, now)
    events += duplicate_events(trace, runs, price, now)
    effort = trace["efforts"].most_common(1)
    return {"events": events, "model": top_family(trace["messages"]), "effort": effort[0][0] if effort else None,
            "open_runs": sum(not is_finished(run, now) for run in runs)}


# ---------------------------------------------------------------- signs after a run (the experiments)

def excerpt(text):
    """A short one-line excerpt of a text."""
    return " ".join(str(text or "").split())[:EXCERPT_CHARS]


def failed_checks(trace, after=None, before=None):
    """The failed checks of a trace as signs `{"kind": "failed check", "line", "text"}`: a Bash or PowerShell command
    matching CHECK_COMMAND whose tool result is an error, its result between the times `after` and `before` (open ends
    when None)."""
    found = []
    for check in trace["checks"]:
        result = trace["results"].get(check["id"])
        if not (result and result["error"] and CHECK_COMMAND.search(check["command"])):
            continue
        stamp = result["stamp"]
        if (after and (not stamp or stamp <= after)) or (before and stamp and stamp >= before):
            continue
        found.append({"kind": "failed check", "line": result["line"],
                      "text": excerpt(f"{check['command']} -> {result['text']}")})
    return found


def reask_signs(trace, reasks):
    return [{"kind": "re-ask", "line": trace["owners"][position]["line"],
             "text": excerpt(trace["owners"][position]["text"])} for position, _ in reasks]


def run_signs(trace, reasks, call_id):
    """The signs after a helper run, in its parent session: after the tool result of its `Agent` call (id `call_id`) and
    before the next owner message: that message is a re-ask, another `Agent` call of the same type, a failed check."""
    result = trace["results"].get(call_id)
    if not result or not result["stamp"]:
        return []
    later = next_owner(trace["owners"], result["stamp"])
    until = later["stamp"] if later else None
    asked = {trace["owners"][position]["i"] for position, _ in reasks}
    call = next((item for item in trace["agents"] if item["id"] == call_id), None)
    signs = []
    if later and later["i"] in asked:
        signs.append({"kind": "re-ask", "line": later["line"], "text": excerpt(later["text"])})
    for other in trace["agents"] if call else []:
        if (other["id"] != call_id and other["type"] == call["type"] and other["stamp"] and other["stamp"] > result["stamp"]
                and (until is None or other["stamp"] < until)):
            signs.append({"kind": "launch again", "line": other["line"], "text": excerpt(other["description"])})
    return sorted(signs + failed_checks(trace, result["stamp"], until), key=lambda sign: sign["line"])


def session_signs(trace, reasks):
    """The signs of a whole session (a Manager run): its re-asks and failed checks."""
    return sorted(reask_signs(trace, reasks) + failed_checks(trace), key=lambda sign: sign["line"])
