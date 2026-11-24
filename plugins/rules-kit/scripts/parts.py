"""Split a session transcript into parts by what is at work, with no model: a skill, an agent or a hook.

A transcript is the `*.jsonl` file of one session (`~/.claude/projects/<project>/<id>.jsonl`) or of one subagent run
(`<id>/subagents/agent-<x>.jsonl`; its type is `agentType` of `agent-<x>.meta.json` beside it). The fields read
(checked on the ClaudeDevKit transcripts of 2026-11-23..24, Claude Code 2.1.330-331):
- a Skill call: an `assistant` line with a `tool_use` block `name: "Skill"`, `input.skill` (`dev-kit:manager`);
- a skill started by a slash command: a `user` line whose text holds `<command-name>/dev-kit:project-lead</command-name>`;
  a built-in command (BUILTIN_COMMANDS) is no skill, and `/clear` ends the skill at work;
- an Agent call: a `tool_use` block `name: "Agent"`, `input.subagent_type` (none: `general-purpose`), up to its
  `tool_result` (same `tool_use_id`); the subagent's own file is a part of that agent;
- a hook event: an `attachment` line whose `attachment.type` starts with `hook_` (`hookName`, `hookEvent`, `command`,
  `content`), a `system` line `stop_hook_summary` with `hookErrors` or `preventedContinuation`, or an error tool result
  whose text starts `<Event>:<Tool> hook error: <reason>` (a hook refusal, e.g. a PreToolUse deny).
The transcript hides a plugin hook's command (`"command": "command hook"`), so a hook's plugin comes from its command path
only when one is shown (`[<command>]: ` before the reason, or a real `command`), else from the reason's words: the one
plugin whose `hooks/`, `scripts/` or `rules/` files hold some run of the reason's first words literally (`HookIndex`).
None when neither tells.

Parts: the whole file is the root part (`session`, or `agent <type>` for a subagent file); a skill part runs from its
start to the line before a `/clear`, else to the file's end, and a skill started while another is at work lies inside
it (a lead's skill stays at work while it runs a handoff skill; a skill already at work is not opened again); an Agent
call part and a hook part lie inside the latest skill at work (their `parent`). `innermost` gives the part at work on
a line, `body` the session, skill or subagent part around it. A part's candidate sets (`candidates`): the sets whose Files rows name its part kind,
then those of its parents, then the owner's global set and the session's project set (`subscriptions.py`).

An owner message (`prompt_kind` "owner") is a `user` line with `origin.kind: "human"` that is no slash command, tool
result or loaded skill text (`isMeta`); a message of another session (`origin.kind: "peer"`), a background task
(`task-notification`) or a coordinator is "other"."""
import json
import re
from pathlib import Path

import subscriptions

SKILL_TOOL = "Skill"
AGENT_TOOL = "Agent"
DEFAULT_AGENT = "general-purpose"
BODY_KINDS = ("session", "skill")  # with a subagent file's root: the parts a sign is counted for (`body`)
BUILTIN_COMMANDS = {
    "clear", "compact", "model", "config", "resume", "help", "status", "cost", "context", "usage", "effort", "fast",
    "memory", "permissions", "hooks", "agents", "mcp", "plugin", "plugins", "reload-plugins", "remote-control",
    "rename", "init", "login", "logout", "exit", "doctor", "ide", "terminal-setup", "vim", "theme", "export",
    "add-dir", "statusline", "bashes", "todos", "upgrade", "release-notes", "output-style", "feedback", "bug", "rewind",
}
END_COMMANDS = {"clear"}  # the context is gone: no skill is at work after it
COMMAND = re.compile(r"<command-name>\s*/?([^<\s]+)\s*</command-name>")
HOOK_ERROR = re.compile(r"^\s*([A-Za-z]+(?::[\w.*|-]+)?) hook error: (.*)", re.DOTALL)
COMMAND_PREFIX = re.compile(r"^\[(.+?)\]:\s*(.*)", re.DOTALL)
CACHE_PATH = re.compile(r"/plugins/cache/[^/]+/([^/]+)/")
PLUGIN_PATH = re.compile(r"/plugins/([\w.-]+)/(?:hooks|scripts|bin|rules)/")
HIDDEN_COMMANDS = ("command hook", "callback", "")  # what a transcript shows instead of a plugin hook's command
INDEX_FOLDERS = ("hooks", "scripts", "rules")
INDEX_SUFFIXES = (".py", ".ps1", ".psm1", ".mjs", ".js", ".sh", ".md")
CHUNK = re.compile(r"[\"'`()\[\]{}:;,.!?\n«»]+")
GLOB_CHARS = re.compile(r"[*?\[]")
MAX_FILES = 200  # the files one Files row may expand to (a project's `.claude/**/*.md`)


class Part:
    """One part of a transcript: what is at work (`kind`, `name`, `plugin`) on lines `start`..`end` (1-based, both
    included) of one file. `detail`: a hook's reason or text, an Agent call's tool_use id."""

    def __init__(self, kind, name, plugin, start, end, parent=None, detail=""):
        self.kind = kind
        self.name = name
        self.plugin = plugin
        self.start = start
        self.end = end
        self.parent = parent
        self.detail = detail

    @property
    def depth(self):
        return 0 if self.parent is None else self.parent.depth + 1

    def label(self):
        if self.kind == "session":
            return "session"
        if self.kind == "hook":
            return f"hook {self.name}" + (f" ({self.plugin})" if self.plugin else "")
        return f"{self.kind} {self.name}"

    def __repr__(self):
        return f"Part({self.label()}, {self.start}-{self.end})"


def plugin_of(name):
    """`dev-kit` of `dev-kit:manager`; None for a name with no plugin."""
    return name.split(":", 1)[0] if isinstance(name, str) and ":" in name else None


def text_of(content):
    """The text of a message's content: a string, or the text blocks of a list."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(block.get("text") or "") for block in content
                         if isinstance(block, dict) and block.get("type") == "text")
    return ""


def result_text(block):
    """The text of a tool result block (a string, or a list of text blocks)."""
    return text_of(block.get("content"))


def read_entries(lines, first=1):
    """`(line number, entry)` of raw JSON lines numbered from `first`; a line that does not parse is skipped."""
    found = []
    for index, raw in enumerate(lines):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        if isinstance(entry, dict):
            found.append((first + index, entry))
    return found


def read_file(path):
    """The entries of a whole transcript file; [] when it cannot be read."""
    try:
        with open(path, "rb") as handle:
            return read_entries(handle.read().splitlines())
    except OSError:
        return []


def title_of(entries):
    """The last `custom-title` of the entries, or ""."""
    title = ""
    for _, entry in entries:
        if entry.get("type") == "custom-title":
            title = entry.get("customTitle") or title
    return title


def agent_type(path):
    """The subagent type of a subagent transcript (its `.meta.json`), else "subagent"."""
    try:
        data = json.loads(Path(path).with_suffix(".meta.json").read_text(encoding="utf-8"))
        return str(data.get("agentType") or "").strip() or "subagent"
    except (OSError, ValueError, AttributeError):
        return "subagent"


def slash_command(text):
    """The command name of a slash-command line (`dev-kit:project-lead`, `clear`), or None."""
    match = COMMAND.search(text or "")
    return match.group(1).strip().lstrip("/") if match else None


def prompt_kind(entry):
    """For a `user` line: "owner", "command" (a slash command), "other" (another session, a background task, a
    coordinator); None for a line that opens no turn (a tool result, a loaded skill text, other meta lines)."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return None
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, list) and any(isinstance(block, dict) and block.get("type") == "tool_result"
                                         for block in content):
        return None
    text = text_of(content)
    if "<command-name>" in text:
        return "command"
    if "<local-command-" in text:
        return None
    origin = entry.get("origin")
    return "owner" if isinstance(origin, dict) and origin.get("kind") == "human" else "other"


def hook_refusal(text):
    """`(event, reason, command)` of an error result a hook gave (`PreToolUse:Bash hook error: ...`), else None."""
    match = HOOK_ERROR.match(text or "")
    if not match:
        return None
    reason = match.group(2).strip()
    command = None
    prefix = COMMAND_PREFIX.match(reason)
    if prefix:
        command, reason = prefix.group(1), prefix.group(2).strip()
    return match.group(1), reason, command


class HookIndex:
    """Which plugin a hook belongs to, from its command path or the words of its text (see the module doc)."""

    def __init__(self, plugins=None):
        self.plugins = Path(plugins) if plugins else subscriptions.plugins_dir()
        self._texts = None

    def texts(self):
        if self._texts is None:
            self._texts = {}
            try:
                folders = sorted(path for path in self.plugins.iterdir() if path.is_dir())
            except OSError:
                folders = []
            for folder in folders:
                parts = []
                for sub in INDEX_FOLDERS:
                    for path in sorted((folder / sub).rglob("*")) if (folder / sub).is_dir() else []:
                        if path.suffix in INDEX_SUFFIXES and path.is_file() and "__pycache__" not in path.parts:
                            try:
                                parts.append(path.read_text(encoding="utf-8", errors="replace"))
                            except OSError:
                                continue
                if parts:
                    self._texts[folder.name] = " ".join(" ".join(parts).split()).lower()
        return self._texts

    def plugin(self, text, command=None):
        """The plugin of a hook: by its command path, else by the first run of its text's words that the files of
        exactly one plugin hold; None when neither tells."""
        for value in (command, text):
            path = str(value or "").replace("\\", "/")
            if not path or path.strip() in HIDDEN_COMMANDS:
                continue
            match = CACHE_PATH.search(path) or PLUGIN_PATH.search(path)
            if match:
                return match.group(1)
            if value is command:
                try:
                    rel = Path(path.strip('"')).resolve().relative_to(self.plugins.resolve())
                    return rel.parts[0] if rel.parts else None
                except (OSError, ValueError):
                    pass
        texts = self.texts()
        for chunk in CHUNK.split(text or ""):
            words = chunk.split()
            if len(words) < 2 or len(" ".join(words)) < 10:
                continue
            probe = " ".join(words[:4]).lower()
            owners = [name for name, body in texts.items() if probe in body]
            if len(owners) == 1:
                return owners[0]
        return None


def split(entries, root_kind="session", root_name="", hooks=None):
    """The parts of one transcript's entries (`read_entries`), the root part first (see the module doc)."""
    if not entries:
        return []
    first, last = entries[0][0], entries[-1][0]
    root = Part(root_kind, root_name, plugin_of(root_name) if root_kind == "agent" else None, first, last)
    found = [root]
    stack = []  # the skills at work, the latest last
    calls = {}

    def at_work():
        return stack[-1] if stack else root

    def close_skills(number):
        for skill in stack:
            skill.end = max(skill.start, number - 1)
        stack.clear()

    def open_skill(name, number):
        if any(skill.name == name for skill in stack):
            return  # already at work
        stack.append(Part("skill", name, plugin_of(name), number, last, at_work()))
        found.append(stack[-1])

    for number, entry in entries:
        kind = entry.get("type")
        content = (entry.get("message") or {}).get("content")
        if kind == "assistant" and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                if block.get("name") == SKILL_TOOL and str(tool_input.get("skill") or "").strip():
                    open_skill(str(tool_input["skill"]).strip().lstrip("/"), number)
                elif block.get("name") == AGENT_TOOL:
                    agent = str(tool_input.get("subagent_type") or "").strip() or DEFAULT_AGENT
                    part = Part("agent", agent, plugin_of(agent), number, number, at_work(), str(block.get("id") or ""))
                    found.append(part)
                    calls[block.get("id")] = part
        elif kind == "user":
            if isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_result":
                        continue
                    call = calls.pop(block.get("tool_use_id"), None)
                    if call:
                        call.end = number
                    refusal = hook_refusal(result_text(block)) if block.get("is_error") else None
                    if refusal:
                        event, reason, command = refusal
                        found.append(Part("hook", event, hooks.plugin(reason, command) if hooks else None, number,
                                          number, at_work(), reason))
            if prompt_kind(entry) == "command":
                command = slash_command(text_of(content))
                if command in END_COMMANDS:
                    close_skills(number)
                elif command and (":" in command or command not in BUILTIN_COMMANDS):
                    open_skill(command, number)
        elif kind == "attachment":
            attachment = entry.get("attachment")
            if isinstance(attachment, dict) and str(attachment.get("type") or "").startswith("hook_"):
                text = attachment.get("content")
                text = " ".join(map(str, text)) if isinstance(text, list) else str(text or attachment.get("stderr") or "")
                event = str(attachment.get("hookName") or attachment.get("hookEvent") or attachment.get("type"))
                found.append(Part("hook", event, hooks.plugin(text, attachment.get("command")) if hooks else None,
                                  number, number, at_work(), text))
        elif kind == "system" and entry.get("subtype") == "stop_hook_summary" and (
                entry.get("hookErrors") or entry.get("preventedContinuation")):
            text = " ".join(map(str, entry.get("hookErrors") or [])) or str(entry.get("stopReason") or "")
            commands = [info.get("command") for info in entry.get("hookInfos") or [] if isinstance(info, dict)]
            plugin = None
            if hooks:
                plugin = next(filter(None, (hooks.plugin("", command) for command in commands)), None) or hooks.plugin(text)
            found.append(Part("hook", "Stop", plugin, number, number, at_work(), text))
    return found


def innermost(found, line):
    """The part at work on a line: the deepest part that holds it, the latest started when two are as deep."""
    best = None
    for part in found:
        if part.start <= line <= part.end and (best is None or (part.depth, part.start) > (best.depth, best.start)):
            best = part
    return best


def body(part):
    """The session, skill or subagent part around a part (a hook event or an Agent call lies inside one)."""
    while part is not None and part.parent is not None and part.kind not in BODY_KINDS:
        part = part.parent
    return part


def kind_sets(part, registry):
    """The names of the sets whose Files rows name this part's own kind (a hook by its plugin)."""
    reference = part.plugin if part.kind == "hook" else part.name
    if part.kind not in subscriptions.PART_KINDS or not reference:
        return []
    return [found.name for found in registry.candidates(part.kind, reference)]


def global_set(registry):
    """The name of the owner's global set, or None."""
    found = registry.set_at(subscriptions.global_dir())
    return found.name if found else None


def candidates(part, registry, own=None, extra=()):
    """The candidate sets of a part (module doc), most specific first; `extra`: other parts whose kind sets join after
    the part's own (the hook events and Agent calls inside a body part that showed a sign)."""
    names = []
    chain = []
    walk = part
    while walk is not None:
        chain.append(walk)
        walk = walk.parent
    for item in chain[:1] + list(extra) + chain[1:]:
        for name in kind_sets(item, registry):
            if name not in names:
                names.append(name)
    for name in (global_set(registry), own):
        if name and name not in names:
            names.append(name)
    return names


def target(part, registry, own=None):
    """The set a technical finding on this part goes to: the first set that names the part's kind (or a parent's),
    else the session's project set."""
    walk = part
    while walk is not None:
        names = kind_sets(walk, registry)
        if names:
            return names[0]
        walk = walk.parent
    return own


def expand(subscription, rule):
    """The files a Files row matches under its set's root (a worktree folder left out), at most MAX_FILES."""
    root = Path(subscription.root)
    if not GLOB_CHARS.search(rule.pattern):
        path = root / rule.pattern
        return [path] if path.is_file() else []
    found = []
    try:
        for path in sorted(root.glob(rule.pattern)):
            if len(found) >= MAX_FILES:
                break
            rel = path.relative_to(root).parts
            if path.is_file() and "worktrees" not in rel and subscription.rules_for("/".join(rel))[:1] == [rule]:
                found.append(path)
    except (OSError, ValueError):
        pass
    return found


HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def headings(lines):
    """`{line number: (level, text)}` of the Markdown headings of a file's lines, outside code fences."""
    found = {}
    fence = False
    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        match = None if fence else HEADING.match(line)
        if match:
            found[number] = (len(match.group(1)), match.group(2))
    return found


def section_of(found_headings, line):
    """The text of the nearest `#` or `##` heading above a line (the unit a Section row types), or None."""
    best = None
    for number, (level, text) in found_headings.items():
        if number <= line and level <= 2 and (best is None or number > best[0]):
            best = (number, text)
    return best[1] if best else None


def section_range(lines, found_headings, title):
    """`(first, last)` line numbers of the section whose heading text is `title` (up to the next heading of the same
    or a higher level), or None."""
    for number, (level, text) in sorted(found_headings.items()):
        if text == title:
            end = len(lines)
            for other, (other_level, _) in sorted(found_headings.items()):
                if other > number and other_level <= level:
                    end = other - 1
                    break
            return number, end
    return None


def read_lines(path):
    try:
        return Path(path).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
