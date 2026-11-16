"""Make one static HTML page with the state of all projects: their sessions and what waits on the owner.

    python scripts/status-page.py [--out FILE] [--agents-json FILE]

Projects are the lead entries (Lead = $true) of `servers.psd1` next to this script. Per project the page shows
the live sessions from `claude agents --json` whose folder is the project folder or under it (worktrees
included), each with its state, and the bullets of the "Open questions" section of the project's PROGRESS.md.
Sessions of other folders go to "Інші папки". Read only: it never messages, starts or stops a session.

Default output: ~/.claude/pult/status.html. `--agents-json` reads a saved `claude agents --json` output
instead of running the command (for tests). Exit code 2 when the session list cannot be read.
"""
import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVERS = HERE / "servers.psd1"
DEFAULT_OUT = Path.home() / ".claude" / "pult" / "status.html"

# What the owner sees for each state. Background sessions carry `state` (working, blocked, done, ...);
# interactive ones only `status` (busy, idle). State "blocked" with status "idle" only means the turn
# ended, not that the session waits on the owner (hub.md, "Traps"), so it is shown as free. Words per the
# hub rules: "вільна" / "зайнята", never "працює". What waits on the owner comes from PROGRESS.md only.
STATE_LABELS = {
    "busy": ("зайнята", "busy"),
    "idle": ("вільна", "idle"),
    "done": ("завершена", "done"),
}


def read_leads(path=SERVERS):
    """[(name, folder)] of the lead entries in servers.psd1, in file order."""
    leads = []
    text = path.read_text(encoding="utf-8-sig")
    for entry in re.findall(r"@\{([^{}]*)\}", text):
        if not re.search(r"\bLead\s*=\s*\$true\b", entry, re.I):
            continue
        session = re.search(r"\bSession\s*=\s*'([^']*)'", entry)
        folder = re.search(r"\bPath\s*=\s*'([^']*)'", entry)
        if session and folder:
            name = re.sub(r"^P:\s*", "", session.group(1))
            leads.append((name, Path(folder.group(1))))
    return leads


def read_agents(saved=None):
    """The list `claude agents --json` prints, or None when it cannot be read."""
    if saved:
        raw = Path(saved).read_text(encoding="utf-8-sig")
    else:
        exe = shutil.which("claude")
        if not exe:
            return None
        try:
            done = subprocess.run([exe, "agents", "--json"], capture_output=True, timeout=60,
                                  encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired):
            return None
        if done.returncode != 0:
            return None
        raw = done.stdout
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    return data if isinstance(data, list) else None


def state_of(agent):
    """One of the STATE_LABELS keys."""
    state = (agent.get("state") or "").lower()
    status = (agent.get("status") or "").lower()
    if status == "busy" or (state == "working" and not status):
        return "busy"
    if state == "done":
        return "done"
    return "idle"


def under(child, parent):
    try:
        Path(child).resolve().relative_to(parent.resolve())
        return True
    except (ValueError, OSError):
        return False


def open_questions(folder):
    """Top-level bullets of the "Open questions" section of PROGRESS.md, or None when there is no file."""
    path = folder / "PROGRESS.md"
    if not path.is_file():
        return None
    items, inside = [], False
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("#"):
            inside = line.lstrip("#").strip().lower() == "open questions"
            continue
        if not inside:
            continue
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif items and line.startswith("  ") and line.strip():
            items[-1] += " " + line.strip()
    return items


def plain(markdown):
    """Markdown links and code marks turned to plain text."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", markdown)
    return text.replace("`", "")


def age_text(ms, now_ms):
    if not isinstance(ms, (int, float)):
        return ""
    seconds = max(0, int((now_ms - ms) / 1000))
    for limit, size, unit in ((3600, 60, "хв"), (86400, 3600, "год")):
        if seconds < limit:
            return f"{seconds // size} {unit}"
    return f"{seconds // 86400} дн"


ORDER = {"busy": 0, "idle": 1, "done": 2}

CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:12px;background:#f6f6f4;color:#222}
h1{font-size:1.2em;margin:4px 0 2px}
.time{color:#666;font-size:.85em;margin-bottom:12px}
section{background:#fff;border-radius:10px;padding:10px 12px;margin-bottom:12px;box-shadow:0 1px 2px #0001}
h2{font-size:1.05em;margin:0 0 6px}
.count{color:#a33;font-weight:normal;font-size:.9em}
ul{margin:0;padding-left:0;list-style:none}
li{padding:6px 0;border-top:1px solid #eee}
li:first-child{border-top:0}
.tag{display:inline-block;font-size:.8em;padding:1px 7px;border-radius:9px;margin-right:6px;white-space:nowrap}
.busy{background:#e1effd;color:#135}
.idle{background:#eee;color:#555}
.done{background:#e3f6e3;color:#252}
.meta{color:#888;font-size:.8em}
h3{font-size:.9em;margin:10px 0 4px;color:#444}
.none{color:#888;font-size:.9em}
@media (prefers-color-scheme:dark){body{background:#111;color:#ddd}section{background:#1c1c1c}
li{border-color:#333}.time,.meta,.none{color:#999}h3{color:#bbb}}
"""


def render(leads, agents, now_ms):
    groups = {name: [] for name, _ in leads}
    other = []
    for agent in agents:
        cwd = agent.get("cwd") or ""
        owner = next((name for name, folder in leads if cwd and under(cwd, folder)), None)
        (groups[owner] if owner else other).append(agent)

    def session_list(items):
        if not items:
            return '<p class="none">Сесій немає.</p>'
        rows = []
        for agent in sorted(items, key=lambda a: (ORDER[state_of(a)], -(a.get("startedAt") or 0))):
            key = state_of(agent)
            label, css = STATE_LABELS[key]
            where = Path(agent.get("cwd") or "").name
            meta = " · ".join(x for x in (
                "фонова" if agent.get("kind") == "background" else "відкрита",
                f"папка {where}" if where else "",
                f"почата {age_text(agent.get('startedAt'), now_ms)} тому" if agent.get("startedAt") else "",
            ) if x)
            rows.append(f'<li><span class="tag {css}">{label}</span>{html.escape(agent.get("name") or "(без назви)")}'
                        f'<div class="meta">{html.escape(meta)}</div></li>')
        return "<ul>" + "".join(rows) + "</ul>"

    parts = []
    for name, folder in leads:
        items = groups[name]
        questions = open_questions(folder)
        count = f"чекає на тебе: {len(questions)}" if questions else ""
        head = f'<h2>{html.escape(name)} <span class="count">{html.escape(count)}</span></h2>'
        if questions is None:
            q = '<p class="none">PROGRESS.md немає.</p>'
        elif not questions:
            q = '<p class="none">Відкритих питань немає.</p>'
        else:
            q = "<ul>" + "".join(f"<li>{html.escape(plain(x))}</li>" for x in questions) + "</ul>"
        parts.append(f"<section>{head}<h3>Сесії</h3>{session_list(items)}"
                     f"<h3>Чекає на тебе (відкриті питання з PROGRESS.md)</h3>{q}</section>")
    if other:
        parts.append(f"<section><h2>Інші папки</h2>{session_list(other)}</section>")

    stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(now_ms / 1000))
    return ("<!doctype html><html lang=\"uk\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>Стан проєктів</title><style>{CSS}</style></head><body>"
            f"<h1>Стан проєктів</h1><div class=\"time\">Знято {stamp}. Сторінка не оновлюється сама.</div>"
            + "".join(parts) + "</body></html>\n")


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--agents-json", help="a saved `claude agents --json` output to read instead")
    args = parser.parse_args()
    agents = read_agents(args.agents_json)
    if agents is None:
        print("status-page: could not read `claude agents --json` (is the claude CLI on PATH?)", file=sys.stderr)
        return 2
    page = render(read_leads(), agents, time.time() * 1000)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(page, encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
