"""Stop hook: a project lead's reply to an event keeps the message form.

Scope is narrow on purpose (plans/lead-reply-hook.md): only a lead session (its title starts with «L: », or the old «P: », see `scripts/session_titles.py`), only a
turn not woken by the owner (a session's message, a Pult event, a subagent notice, a timer), and only the turn's
final text. That text must be empty, one of the named one-line exceptions of `dev-kit:project-lead`, or the bold
blocks of "Message templates" with no free text before, between or after them (the question window's closing
question, or its one item with its `Рекомендую:` line, may end the message). A miss is a soft nudge: the hook asks for one short
extra step that sends no new text, so the owner never sees the message twice. The hook never blocks twice in a row
(`stop_hook_active`) and any error ends it with exit code 0 and no output."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import session_titles  # noqa: E402  the new and the old lead and discussion prefixes

TITLES = ("Питання без відповіді", "Статуси сесій", "Стан проєкту")
PROSE_TITLES = ("Стан проєкту",)  # blocks whose body is sentences, not a list
ONE_LINERS = (
    "Зараз нічого не працює і нічого не чекає на тебе.",  # forced output with nothing running
    *(f"Відкрий сесію «{prefix}" for prefix in session_titles.DISCUSS_PREFIXES),  # the one line after starting a discussion
    "Тест пушу:",  # push test readiness step
    "Пуш «Тест",  # push test result question
    "⚠ ЧЕРЕЗ 30 СЕК БУДЕ ПЕРЕЗАВАНТАЖЕННЯ",  # restart lines
    "Обговорення закрите",
)
TITLE_RE = re.compile(r"^\*\*(.+?)\*\*\s*$")
LIST_LINE_RE = re.compile(r"^(\s+\S|-\s|\d+\.\s|і ще \d+ питан)")  # the last one: the window's counter line
CLOSING_RE = re.compile(r"(\?\s*(\([^()]*\))?\s*$)|(\+ або -\s*$)|(^(Рекомендую|немає рекомендації)\b)")

NUDGE = ("Хук форми повідомлень Lead: остання відповідь на подію не тримає форму «Message templates» "
         "(dev-kit:project-lead): {why}. Власник її вже бачив: не надсилай її знову і не виправляй окремим "
         "повідомленням. Закінчи цей крок без тексту, а наступне повідомлення напиши у формі: порожньо або лише "
         "жирні блоки, без вільного тексту поруч.")


def read_entries(path):
    entries = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    return entries


def session_title(entries):
    """The latest custom title or agent name in the transcript."""
    title = ""
    for entry in entries:
        if entry.get("type") == "custom-title":
            title = str(entry.get("customTitle") or title)
        elif entry.get("type") == "agent-name":
            title = str(entry.get("agentName") or title)
    return title


def is_tool_result(entry):
    content = (entry.get("message") or {}).get("content")
    return isinstance(content, list) and any(isinstance(part, dict) and part.get("type") == "tool_result"
                                             for part in content)


def turn_start(entries):
    """Index of the user entry that woke the current turn (not a tool result or a host companion note)."""
    for index in range(len(entries) - 1, -1, -1):
        entry = entries[index]
        if entry.get("type") != "user" or is_tool_result(entry):
            continue
        if entry.get("turnCompanion") or entry.get("ownNote"):
            continue
        return index
    return None


def woken_by_owner(entry):
    origin = entry.get("origin") or {}
    if origin.get("kind") == "human" or entry.get("turnOrigin") == "human":
        return True
    return not entry.get("turnOrigin") and not origin  # an unknown format counts as the owner's: stay narrow


def owner_still_waits(entries, start):
    """Whether the owner's last message has had no final reply before this turn: the turn then answers the owner
    (the Lead's reply to the owner's own question keeps the global caps, not the blocks)."""
    owner = None
    for index in range(start - 1, -1, -1):
        entry = entries[index]
        if entry.get("type") == "user" and not is_tool_result(entry) and woken_by_owner(entry):
            owner = index
            break
    if owner is None:
        return False
    for entry in entries[owner + 1:start]:
        message = entry.get("message") or {}
        if entry.get("type") == "assistant" and message.get("stop_reason") == "end_turn" and any(
                isinstance(part, dict) and part.get("type") == "text" and (part.get("text") or "").strip()
                for part in message.get("content") or []):
            return False
    return True


def final_text(entries, start):
    """Text blocks of the turn's last assistant message."""
    last_id = None
    for entry in entries[start + 1:]:
        if entry.get("type") == "assistant":
            last_id = (entry.get("message") or {}).get("id")
    if last_id is None:
        return ""
    parts = []
    for entry in entries[start + 1:]:
        message = entry.get("message") or {}
        if entry.get("type") != "assistant" or message.get("id") != last_id:
            continue
        for part in message.get("content") or []:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text") or "")
    return "\n".join(parts).strip()


def form_problem(text):
    """None when the text keeps the form, else a short reason in Ukrainian."""
    text = text.strip()
    if not text or text.startswith(ONE_LINERS):
        return None
    paragraphs = [p.strip("\n") for p in re.split(r"\n\s*\n", text) if p.strip()]
    first = TITLE_RE.match(paragraphs[0].splitlines()[0].strip())
    if not first or first.group(1) not in TITLES:
        return "текст перед блоками або замість них"
    blocks = []  # [title, [paragraphs]]
    for paragraph in paragraphs:
        lines = paragraph.splitlines()
        title = TITLE_RE.match(lines[0].strip())
        if title and title.group(1) in TITLES:
            blocks.append([title.group(1), []])
            rest = "\n".join(lines[1:]).strip("\n")
            if rest:
                blocks[-1][1].append(rest)
        else:
            blocks[-1][1].append(paragraph)
    for number, (title, body) in enumerate(blocks):
        if title in PROSE_TITLES:
            continue
        free = [i for i, p in enumerate(body) if not all(LIST_LINE_RE.match(line) for line in p.splitlines())]
        if not free:
            continue
        last_block = number == len(blocks) - 1
        trailing = free == list(range(len(body) - len(free), len(body)))
        if not last_block or not trailing or len(free) > 2:
            return f"вільний текст у блоці «{title}»"
        if not CLOSING_RE.search(body[-1].splitlines()[-1].strip()):
            return f"вільний текст після блоку «{title}»"
    return None


def check(call):
    """The Stop hook's output dict, or None to let the turn end."""
    if call.get("stop_hook_active"):
        return None
    path = call.get("transcript_path")
    if not path:
        return None
    entries = read_entries(path)
    if not session_title(entries).startswith(session_titles.LEAD_PREFIXES):
        return None
    start = turn_start(entries)
    if start is None or woken_by_owner(entries[start]) or owner_still_waits(entries, start):
        return None
    problem = form_problem(final_text(entries, start))
    if problem is None:
        return None
    return {"decision": "block", "reason": NUDGE.format(why=problem)}


def main():
    try:
        call = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        out = check(call)
    except Exception:
        return
    if out:
        sys.stdout.reconfigure(encoding="utf-8")
        json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
    sys.exit(0)
