"""Talk rules checked by script on every reply to the owner, with no model and no owner correction needed.

A reply is the last assistant text of a turn the owner opened (`parts.prompt_kind` "owner": a `user` line with
`origin.kind: "human"`); a turn ends at the next owner message, slash command or message of another kind. Only the
sessions the owner talks with are checked: the caller leaves out subagent files and «Retro:» or «Docs:»
sessions, and drops a hit with `first_prompt` in a session whose title starts with STARTED_BY_SESSION (an «M:» or a
«Discuss:» session gets its first prompt from the lead, not from the owner; the old «C:» and «Обговорення:» count too).

Before any check the text that is not the agent's own prose is left out: fenced code, inline code, quote lines (`>`),
table rows, and text in «», “” or "" quotes (a verbatim quote may keep a dash).
Checks, each the finding kind `talk <check>`:
- `dash`: an em dash or an en dash;
- `long reply`: a block (the reply, or one `### ` block of a reply to several questions) with more than MAX_SENTENCES
  sentences of prose; list items, headings, the closing question and the recommendation, hint and launch lines
  (SKIP_LINE: «помічник:», «сесія:», their English forms and the old «агент:») are not counted;
- `long list`: a list of more than MAX_ITEMS items; `long item`: an item over MAX_ITEM_WORDS words (a name or path is
  one word; a batch item's «Рекомендую» part is not counted; nested items are left out);
- `not ukrainian`: the owner's message is mostly Cyrillic and a prose paragraph of more than two sentences is not;
- `yes-no first`: the owner asked one yes/no question (the last sentence, 2-25 words, no question word first, no «чи»
  or "or" between two options) and the reply does not start with «так», «ні», yes or no.

`rule_refs` finds the rule line of each check in the rule sets: the talk-typed Files rows of the subscriptions (their
Section, else the whole file; then the whole files of those rows) searched for the words of PROBES; with no match, the
owner's global set, its CLAUDE.md and the section FALLBACK names."""
import re
from collections import namedtuple
from pathlib import Path

import parts
import session_titles
import subscriptions

CHECKS = ("dash", "long reply", "long list", "long item", "not ukrainian", "yes-no first")
MAX_SENTENCES = 5
MAX_ITEMS = 5
MAX_ITEM_WORDS = 15
QUESTION_WORDS_MAX = 25
STARTED_BY_SESSION = session_titles.MANAGER_PREFIXES + session_titles.DISCUSS_PREFIXES
EXCERPT_CHARS = 80
PROBES = {  # check -> (words of the rule line, the section of the fallback)
    "dash": ("em dash", "No em dash"),
    "long reply": ("Ordinary reply", "Chat replies"),
    "long list": ("at most 5 items", "Chat replies"),
    "long item": ("at most 15", "Chat replies"),
    "not ukrainian": ("Reply in Ukrainian whenever", "Reply language"),
    "yes-no first": ("yes/no question gets", "Check before you act or agree"),
}
FALLBACK_FILE = "CLAUDE.md"
DASH = re.compile(r"[—–]")
ECHO = re.compile(r"^\s*\[SYSTEM NOTIFICATION|<task-notification>")  # the model echoed a host notice: no reply of its own
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)  # the app's `<!-- reply N -->` mark before a quoted message
FENCE = re.compile(r"```.*?(```|\Z)", re.DOTALL)
INLINE_CODE = re.compile(r"`[^`\n]*`")
QUOTED = re.compile(r"«[^»\n]*»|“[^”\n]*”|\"[^\"\n]*\"")
ITEM = re.compile(r"^(\s*)([-*+•]|\d+[.)])\s+(.*)$")
HEADING = re.compile(r"^\s*#{1,6}\s")
BLOCK_HEADING = re.compile(r"^\s*###\s")
SKIP_LINE = re.compile(r"^\W*(Рекомендую|Recommend|немає рекомендації|no recommendation|In English:|I read it as:|"
                       r"Better:|помічник:|helper:|сесія:|session:|агент:|agent:|👆|Чекаю на підтвердження|Waiting for confirmation)", re.IGNORECASE)
RECOMMEND = re.compile(r"\b(Рекомендую|Recommend|немає рекомендації|no recommendation)\b", re.IGNORECASE)
BRACKET = re.compile(r"\([^()]*\)")
BRACKET_WORDS = 6  # a question's example or consequence in brackets (the owner's "Question" rule)
SENTENCE_END = re.compile(r"(?<=[.!?…])[\"'»)\]*_]*\s+(?=[\"'«(\[*_]*[^\W_a-zа-яіїєґ])")
LETTER = re.compile(r"[^\W\d_]")
YES_NO = re.compile(r"^(так|ні|yes|no)\b", re.IGNORECASE)
LEADING = {"а", "і", "й", "ну", "так", "and", "so", "but", "ok", "ок"}
QUESTION_WORDS = {
    "що", "шо", "як", "яка", "яке", "які", "який", "якого", "якій", "яким", "якою", "яку", "чому", "навіщо", "нащо",
    "де", "куди", "звідки", "коли", "хто", "кого", "кому", "ким", "скільки", "котрий", "котра", "котре", "чий", "чия",
    "чиє", "чиї", "what", "why", "how", "where", "when", "who", "whom", "which", "whose",
}
Ref = namedtuple("Ref", "set path rel line section")


def cleaned(text):
    """The agent's own prose of a text: no code, quote lines, table rows or quoted words (module doc)."""
    text = FENCE.sub("\n", COMMENT.sub("", text or ""))
    lines =[line for line in text.splitlines() if not line.lstrip().startswith((">", "|"))]
    return QUOTED.sub("", INLINE_CODE.sub("", "\n".join(lines)))


def sentences(text):
    """The sentences of a run of prose (a paragraph joined into one line)."""
    return [part for part in SENTENCE_END.split(" ".join(text.split())) if LETTER.search(part)]


def cyrillic_share(text):
    letters = LETTER.findall(text)
    return (sum("Ѐ" <= char <= "ӿ" for char in letters) / len(letters)) if letters else 0.0


def is_ukrainian(text):
    return len(LETTER.findall(text)) >= 2 and cyrillic_share(text) >= 0.5


def blocks(text):
    """The `### ` blocks of a reply (the whole reply when it has none), each a list of its lines."""
    found = [[]]
    for line in text.splitlines():
        if BLOCK_HEADING.match(line) and any(item.strip() for item in found[-1]):
            found.append([])
        found[-1].append(line)
    return found


def layout(lines):
    """`(paragraphs, lists)` of a block: prose paragraphs as joined text, lists as lists of top-level item texts."""
    paragraphs, lists = [], []
    prose, items = [], None

    def end_prose():
        if prose:
            paragraphs.append(" ".join(prose))
            prose.clear()

    for line in lines:
        item = ITEM.match(line)
        if not line.strip():
            end_prose()
            continue
        if HEADING.match(line) or SKIP_LINE.match(line):
            end_prose()
            items = None
            continue
        if item:
            end_prose()
            if len(item.group(1)) >= 2 and items:
                continue  # a nested item
            if items is None:
                items = []
                lists.append(items)
            items.append(item.group(3))
            continue
        if items is not None and line.startswith((" ", "\t")) and items:
            items[-1] += " " + line.strip()
            continue
        items = None
        prose.append(line.strip())
    end_prose()
    return paragraphs, lists


def without_extras(text):
    """A question's text without its «Рекомендую» part and its bracket example of at most BRACKET_WORDS words."""
    head = RECOMMEND.split(text, maxsplit=1)[0]
    return BRACKET.sub(lambda match: "" if len(match.group(0).split()) <= BRACKET_WORDS else match.group(0), head)


def item_words(item):
    return len(without_extras(item).replace("**", "").split())


def is_yes_no(text):
    """Whether an owner message is one yes/no question (module doc)."""
    found = sentences(cleaned(text).replace("\n", " "))
    if not found or not found[-1].rstrip().endswith("?") or sum(part.rstrip().endswith("?") for part in found) != 1:
        return False
    words = [word.strip(".,!?:;()*\"'").lower() for word in found[-1].split()]
    words = [word for word in words if word]
    while words and words[0] in LEADING and len(words) > 1:
        words = words[1:]
    if not 2 <= len(words) <= QUESTION_WORDS_MAX or words[0] in QUESTION_WORDS:
        return False
    return "чи" not in words[1:] and "or" not in words


def reply_start(text):
    """The first words of a reply with its Markdown marks taken off."""
    return re.sub(r"^[\s#*_>`-]+", "", text or "")


def excerpt(text, index):
    start = max(0, index - EXCERPT_CHARS // 2)
    return " ".join(text[start:start + EXCERPT_CHARS].split()).replace("|", "/")


def check_reply(owner_text, reply):
    """The checks a reply breaks: `[(check, excerpt)]`."""
    prose = cleaned(reply)
    hits = []
    dash = DASH.search(prose)
    if dash:
        hits.append(("dash", excerpt(prose, dash.start())))
    all_blocks = blocks(prose)
    ukrainian_owner = is_ukrainian(cleaned(owner_text))
    for number, block in enumerate(all_blocks):
        paragraphs, lists = layout(block)
        paragraphs = [text for text in (without_extras(paragraph).strip() for paragraph in paragraphs) if text]
        counted =[sentences(paragraph) for paragraph in paragraphs]
        if number == len(all_blocks) - 1 and counted and counted[-1] and counted[-1][-1].rstrip().endswith("?"):
            counted[-1] = counted[-1][:-1]  # the closing question
        total = sum(len(found) for found in counted)
        if total > MAX_SENTENCES:
            hits.append(("long reply", f"{total} sentences: " + excerpt(" ".join(paragraphs), 0)))
        for items in lists:
            if len(items) > MAX_ITEMS:
                hits.append(("long list", f"{len(items)} items: " + excerpt(items[0], 0)))
            long_items = [item for item in items if item_words(item) > MAX_ITEM_WORDS]
            if long_items:
                hits.append(("long item", f"{item_words(long_items[0])} words: " + excerpt(long_items[0], 0)))
        if ukrainian_owner:
            for paragraph, found in zip(paragraphs, [sentences(paragraph) for paragraph in paragraphs]):
                if len(found) > 2 and not is_ukrainian(paragraph) and cyrillic_share(paragraph) < 0.5:
                    hits.append(("not ukrainian", excerpt(paragraph, 0)))
                    break
    if is_yes_no(owner_text) and not YES_NO.match(reply_start(reply)):
        hits.append(("yes-no first", excerpt(" ".join(owner_text.split()), 0) + " -> " + excerpt(reply_start(reply), 0)))
    seen = set()
    return [hit for hit in hits if not (hit[0] in seen or seen.add(hit[0]))]


def owner_turns(entries, at_start=True):
    """`(prompt line, owner text, reply line, reply text, first_prompt)` of each turn the owner opened that got a reply;
    `first_prompt`: the first owner message of the file (only when the entries start the file, `at_start`)."""
    turns = []
    current = None
    seen_owner = not at_start

    def close():
        if current and current["reply"] is not None:
            turns.append((current["line"], current["text"], current["reply_line"], current["reply"], current["first"]))

    for number, entry in entries:
        kind = parts.prompt_kind(entry)
        if kind is not None:
            close()
            current = None
            if kind == "owner":
                current = {"line": number, "text": parts.text_of((entry.get("message") or {}).get("content")),
                           "reply": None, "reply_line": None, "first": not seen_owner}
                seen_owner = True
            continue
        if current is None or entry.get("type") != "assistant":
            continue
        content = (entry.get("message") or {}).get("content")
        text = parts.text_of(content) if isinstance(content, list) else ""
        if text.strip() and not ECHO.search(text):
            current["reply"], current["reply_line"] = text, number
    close()
    return turns


def check_entries(entries, at_start=True):
    """The talk hits of a transcript's entries: dicts `check`, `line` (the reply's), `excerpt`, `first_prompt`."""
    hits = []
    for _, owner_text, reply_line, reply, first in owner_turns(entries, at_start):
        for check, text in check_reply(owner_text, reply):
            hits.append({"check": check, "line": reply_line, "excerpt": text, "first_prompt": first})
    return hits


def rule_refs(registry):
    """`{check: Ref}`: where each talk check's rule stands (module doc)."""
    rows = []  # (subscription, path, section or None)
    owner = parts.global_set(registry)
    for subscription in sorted(registry.sets.values(), key=lambda found: found.name != owner):  # the global rules first
        for rule in subscription.files:
            if rule.type == "talk":
                rows += [(subscription, path, rule.section) for path in parts.expand(subscription, rule)]
    texts = {}
    found = {}
    for whole in (False, True):
        for subscription, path, section in rows:
            if str(path) not in texts:
                texts[str(path)] = parts.read_lines(path)
            lines = texts[str(path)]
            marks = parts.headings(lines)
            span = (1, len(lines))
            if section and not whole:
                span = parts.section_range(lines, marks, section)
                if not span:
                    continue
            for check, (probe, _) in PROBES.items():
                if check in found:
                    continue
                for number in range(span[0], span[1] + 1):
                    if probe.lower() in lines[number - 1].lower():
                        found[check] = Ref(subscription.name, Path(path), subscription.rel(path), number,
                                           parts.section_of(marks, number))
                        break
    root =registry.sets[owner].root if owner else subscriptions.global_dir()
    for check, (_, section) in PROBES.items():
        found.setdefault(check, Ref(owner, Path(root) / FALLBACK_FILE, FALLBACK_FILE, 0, section))
    return found


def ref_text(ref):
    return f"{ref.rel or ref.path}:{ref.line} ({ref.section})" if ref.line else f"{ref.rel or ref.path} ({ref.section})"
