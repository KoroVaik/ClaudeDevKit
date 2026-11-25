"""The retro's fix loop on the item files: expiry, the weekly cap, replay packets, the fix record, the post-change check,
reverts and revert requests, the done list and the spend cap. No model here; `retro.py` runs these as its commands
(`rules-kit <command>`, see its module doc) and passes the folders and the rule sets in.

Item file (`<sets folder>/<set>/items/<key>.md`, written by the retro session, `skills/retro/SKILL.md`): a `# ` title
(Ukrainian, the done list quotes it), then `- name: value` lines; this module reads and writes:

    - status: waiting | fixed | worked | reverted | second-try | parked | expired | rejected | handed | no-fix
    - seen: <YYYY-MM-DD> | <session title (id8)>[ / subagent <type>] | <the finding line>
    - fix: <YYYY-MM-DD> | <set> | <commit hash> | <files, relative to the set root, `, `> | <what it removed or merged>
    - revert: <YYYY-MM-DD> | <revert commit hash> | <fix hash>
    - mark: <YYYY-MM-DD> | <status> | <note>

Items of the old retro are read as the new ones: status `disputed` is `waiting` (the loop reviews it again), `trivial-fixed`
is `fixed` (`status_word`; the migration rewrites the status line, `normalize_text`); an old `fix:` line
`<date> | <files> (commit abc) | ...` gives its last hash as the fix commit, and one with no hash is a date-only fix: the
post-change check goes by its date and `revert` says there is nothing to revert.

A new line goes after the last `- ` line of the head (the lines before the first blank line or text line).

- Expiry (`expire`, run by `items`): an item with status `waiting`, exactly one `seen:` line and that sighting
  EXPIRE_DAYS or more days old gets `status: expired` and a done-list line. Urgent items never wait, so never expire.
- Cap (`landed`): the `fixed` and `sign added` lines of the done list for a set in the last 7 days, today included
  (only fixes `fixed` recorded with a commit); FIXES_PER_WEEK per set. Urgent
  fixes land over the cap (the skill says when).
- Possible breakage (`breakage`): a new finding line that names a file of a `fix:` line of an item with status
  `fixed` dated in the last BREAKAGE_DAYS days.
- Replay (`replay`): packets (`packets.write`) of the item's problem parts, found from its `seen:` lines (the session
  id8, a `subagent <type>`, a part label `skill|agent|hook <name>` and `lines <a>-<b>` when the line has them), and of
  up to GOOD_MAX good parts: parts of the same skill or agent (or of the part kinds of the files `--file` names) in the
  sessions of the last GOOD_DAYS days, with no sign (`packets.mark` finds none), one per session, the problem sessions
  and «Retro:» / «Docs:» sessions (the old titles too) left out. Written to `<data>/packets/replay-<key>/`.
- Post-change check (`check`): per item with status `fixed`, whether its last fix commit is in the set's main
  branch (`main`, else the current branch: the owner's global folder) and since when (the oldest entry of the
  branch's reflog that holds it; no reflog: the commit's time), then the sessions started after that moment, newest
  first, CHECK_SESSIONS at most, those with the item's part kinds at work when it has any.
- Revert (`revert`): `git revert --no-edit <last fix hash>` in the current folder (the global set: its folder);
  success adds a `revert:` line and sets `reverted`, or `parked` when the item was reverted before (the second try
  failed too); a failed revert is aborted, nothing recorded. A revert request of the item is removed.
- Revert request (`request`): `<data>/requests/<set>--<key>.json`; `items` of the reviewing project lists them.
- Done list: `<data>/done.jsonl`, one JSON object per action: `{"date", "set", "key", "action", "text"}`; `action`
  one of ACTIONS; `text` one Ukrainian line.
- Spend cap (`budget`): `spend-kit session --id ID` (a process) prints `~X% of the weekly limit`; over BUDGET_PCT is
  `over`; no share (spend-kit missing or failing) is `unknown`. The command exits 0 for `under` and 1 for `over` and
  `unknown`: it fails closed, an unknown spend stops the run like an over one.
- `mark --status parked --note <reason>`: the note is the reason the done list shows; `revert` parks an item itself
  only after the second failed try."""
import datetime
import json
import os
import re
import subprocess
from pathlib import Path

import packets
import parts
import session_titles
import spend_client

EXPIRE_DAYS = 14
FIXES_PER_WEEK = 5
BREAKAGE_DAYS = 14
GOOD_MAX = 5
GOOD_DAYS = 14
GOOD_FILES = 80  # main transcripts read at most for good parts (newest first)
CHECK_SESSIONS = 20
BUDGET_PCT = 2.0
GIT_TIMEOUT_S = 60
SPEND_TIMEOUT_S = 120
DONE_FILE = "done.jsonl"
REQUESTS_FOLDER = "requests"
PACKETS_FOLDER = "packets"  # the same folder as `rules-kit parts` (retro.PACKETS_FOLDER)
REPLAY_PREFIX = "replay-"
SKIP_TITLES = session_titles.RETRO_PREFIXES + session_titles.DOCS_PREFIXES
ACTIONS = ("fixed", "sign added", "reverted", "second try handed", "parked", "expired", "worked", "handed",
           "revert requested")
MARK_ACTIONS = {"worked": "worked", "second-try": "second try handed", "parked": "parked",
                "handed": "handed"}  # the marks that go to the done list
MARK_WORDS = {"worked": "Перевірено, зміна спрацювала", "second try handed": "Друга спроба передана Lead як задача",
              "parked": "Відкладено", "handed": "Передано як задача або дефект"}  # parked: `mark` adds the note as the reason
STATUS = re.compile(r"^- status:\s*(.*)$")
SEEN = re.compile(r"^- seen:\s*(\d{4}-\d\d-\d\d)\s*\|(.*)$")
FIX = re.compile(r"^- fix:\s*(\d{4}-\d\d-\d\d)\s*\|\s*([^|]*?)\s*\|\s*([0-9a-fA-F]{7,40})\s*\|\s*([^|]*?)\s*(?:\|.*)?$")
FIX_ANY = re.compile(r"^- fix:\s*(\d{4}-\d\d-\d\d)\s*\|")
OLD_FIX = re.compile(r"^- fix:\s*(\d{4}-\d\d-\d\d)\s*\|\s*([^|]*?)\s*(?:\|.*)?$")  # the old retro: `date | files (commit abc) | ...`
OLD_COMMIT = re.compile(r"\(\s*(?:commit\s+)?([0-9a-fA-F]{7,40}(?:\s*,\s*[0-9a-fA-F]{7,40})*)\s*\)")
OLD_STATUSES = {"disputed": "waiting", "trivial-fixed": "fixed"}  # statuses of the old retro, read as the new ones
STATUS_TEXT = re.compile(r"^(- status:\s*)(\S+)(\s*)$")
REVERT = re.compile(r"^- revert:")
ID8 = re.compile(r"\(([0-9a-f]{8})[0-9a-f-]*\)")
SUBAGENT = re.compile(r"/ subagent ([\w:.-]+)")
PART_LABEL = re.compile(r"\b(skill|agent) ([\w.-]+:[\w.-]+)")
LINES = re.compile(r"\blines (\d+)-(\d+)")
REFLOG_TIME = re.compile(r"@\{(\d+)\}")
SHARE = re.compile(r"~?([\d.]+)% of the weekly limit")


def day(value):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def status_word(status):
    """A status as the loop reads it: `disputed` of the old retro is `waiting` (the loop reviews it again),
    `trivial-fixed` is `fixed`."""
    return OLD_STATUSES.get(status.lower(), status)


def normalize_text(text):
    """An item's text with the status line of the old retro rewritten (`status_word`); the rest is kept as it is."""
    lines = text.split("\n")
    for index, line in enumerate(lines):
        match = STATUS_TEXT.match(line.rstrip("\r"))
        if match and status_word(match.group(2)) != match.group(2):
            lines[index] = f"{match.group(1)}{status_word(match.group(2))}" + ("\r" if line.endswith("\r") else "")
            break
    return "\n".join(lines)


class Item:
    """One item file: its set, key, title, status and the lines this module reads."""

    def __init__(self, path, set_name):
        self.path = Path(path)
        self.set = set_name
        self.key = self.path.stem
        try:
            self.lines = self.path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        except OSError:
            self.lines = []

    @property
    def title(self):
        return next((line[2:].strip() for line in self.lines if line.startswith("# ")), self.key)

    @property
    def status(self):
        return status_word(next((STATUS.match(line).group(1).strip() for line in self.lines if STATUS.match(line)), "?"))

    def seen(self):
        """`[(date, rest of the line)]` of the `seen:` lines."""
        return [(day(match.group(1)), match.group(2)) for match in map(SEEN.match, self.lines) if match]

    def fixes(self):
        """`[(date, set, hash, [files])]` of the `fix:` lines, in file order. A line of the old retro (`date | files
        (commit abc) | ...`) gives the last hash of its parenthesis (set `""`); one with no hash is a date-only fix:
        its hash is None (the check goes by its date, there is nothing to revert)."""
        found = []
        for line in self.lines:
            match = FIX.match(line)
            if match:
                files = [name.strip() for name in match.group(4).split(",") if name.strip()]
                found.append((day(match.group(1)), match.group(2), match.group(3), files))
                continue
            old = OLD_FIX.match(line)
            if old:
                commit = OLD_COMMIT.search(old.group(2))
                names = OLD_COMMIT.sub("", old.group(2))
                files = [name.strip() for name in names.split(",") if name.strip()]
                last = re.split(r"\s*,\s*", commit.group(1))[-1] if commit else None
                found.append((day(old.group(1)), "", last, files))
        return found

    def fix_dates(self):
        return [day(match.group(1)) for match in map(FIX_ANY.match, self.lines) if match]

    def reverted_before(self):
        return any(REVERT.match(line) for line in self.lines)

    def write(self):
        self.path.write_text("\n".join(self.lines) + "\n", encoding="utf-8")

    def set_status(self, status):
        for index, line in enumerate(self.lines):
            if STATUS.match(line):
                self.lines[index] = f"- status: {status}"
                return
        self.add(f"- status: {status}")

    def add(self, line):
        """Insert a `- ` line after the last `- ` line of the head (module doc); with none, after the title."""
        at = None
        for index, text in enumerate(self.lines):
            if text.startswith("- "):
                at = index + 1
            elif at is not None and not text.startswith("#"):
                break
        if at is None:
            at = next((index + 1 for index, text in enumerate(self.lines) if text.startswith("# ")), 0)
        self.lines.insert(at, line)


def item_paths(sets_root, key, set_name=None):
    """The item files named `key` in every set folder (or only in `set_name`)."""
    folders = [Path(sets_root) / set_name] if set_name else sorted(Path(sets_root).iterdir()) if Path(sets_root).is_dir() else []
    return [folder / "items" / f"{key}.md" for folder in folders if (folder / "items" / f"{key}.md").is_file()]


def find_item(sets_root, key, set_name=None):
    """`(Item, None)` or `(None, error text)`: no such item, or the key is in two sets and no set was given."""
    found = item_paths(sets_root, key, set_name)
    if not found:
        return None, f"no item {key}" + (f" in set {set_name}" if set_name else "")
    if len(found) > 1:
        return None, f"item {key} is in several sets ({', '.join(path.parent.parent.name for path in found)}): add --set"
    return Item(found[0], found[0].parent.parent.name), None


def items_of(sets_root, names):
    for name in names:
        folder = Path(sets_root) / name / "items"
        for path in sorted(folder.glob("*.md")) if folder.is_dir() else []:
            yield Item(path, name)


# The done list


def record(data_dir, set_name, key, action, text, when=None):
    """Append one action to the done list (module doc)."""
    entry = {"date": (when or datetime.date.today()).isoformat(), "set": set_name, "key": key, "action": action,
             "text": " ".join(str(text).split())}
    with open(Path(data_dir) / DONE_FILE, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_done(data_dir, days=None, today=None):
    """The done-list entries, oldest first; with `days`, those of the last `days` days, today included."""
    path = Path(data_dir) / DONE_FILE
    try:
        raw = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    since = (today or datetime.date.today()) - datetime.timedelta(days=days - 1) if days else None
    found = []
    for line in raw:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and (since is None or (day(entry.get("date")) or since) >= since):
            found.append(entry)
    return found


def list_lines(data_dir, days=None):
    """Plain lines of the done list for Pult: `<date> | <set> | <text> (<key>, <action>)`."""
    return [f"{entry.get('date')} | {entry.get('set')} | {entry.get('text')} ({entry.get('key')}, {entry.get('action')})"
            for entry in read_done(data_dir, days)]


# Expiry, cap, breakage


def expire(data_dir, sets_root, names, today=None):
    """Expire the one-off items of the sets `names` (module doc); returns `[(set, key)]`."""
    today = today or datetime.date.today()
    done = []
    for item in items_of(sets_root, names):
        seen = item.seen()
        if item.status.lower() != "waiting" or len(seen) != 1 or not seen[0][0]:
            continue
        if (today - seen[0][0]).days < EXPIRE_DAYS:
            continue
        item.set_status("expired")
        item.add(f"- mark: {today.isoformat()} | expired | seen once, not again in {EXPIRE_DAYS} days")
        item.write()
        record(data_dir, item.set, item.key, "expired",
               f"Закрито без змін, бо не повторилось {EXPIRE_DAYS} днів: {item.title}", today)
        done.append((item.set, item.key))
    return done


def landed(data_dir, name, today=None):
    """The fixes the retro landed for the set in the last 7 days, today included (the weekly cap counts them): the
    `fixed` and `sign added` lines of the done list, which `fixed` writes with the commit it recorded. The hand-written
    `fix:` lines of `check-<slug>` items (other sessions' plugin commits) are not the retro's fixes and do not count."""
    return sum(1 for entry in read_done(data_dir, 7, today)
               if entry.get("set") == name and entry.get("action") in ("fixed", "sign added"))


def recent_fixes(sets_root, names, today=None):
    """`[(set, key, [files])]` of the items with status `fixed` whose last fix is BREAKAGE_DAYS days old or less."""
    today = today or datetime.date.today()
    found = []
    for item in items_of(sets_root, names):
        fixes = item.fixes()
        if item.status.lower() == "fixed" and fixes and fixes[-1][0] and (today - fixes[-1][0]).days <= BREAKAGE_DAYS:
            found.append((item.set, item.key, fixes[-1][3]))
    return found


def breakage(line, fixes):
    """The key of the recent fix whose file the finding line names, or None."""
    text = line.replace("\\", "/")
    for _, key, files in fixes:
        if any(name and name.replace("\\", "/") in text for name in files):
            return key
    return None


# Git


def git(repo, *args):
    """`(code, stdout)` of a git command in `repo`; `(None, error)` when git cannot run."""
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=GIT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return None, str(exc)
    return done.returncode, (done.stdout if done.returncode == 0 else done.stderr or done.stdout).strip()


def set_repo(subscription, global_root, cwd=None):
    """The folder a set's commits are made in: the global set's own folder, else `cwd` (the retro's worktree)."""
    if subscription is not None and Path(os.path.realpath(subscription.root)) == Path(os.path.realpath(global_root)):
        return subscription.root
    return Path(cwd or os.getcwd())


def in_worktree(repo):
    """Whether `repo` is a linked worktree (its git common dir differs from its git dir), not a main checkout."""
    code, common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    code_dir, gitdir = git(repo, "rev-parse", "--path-format=absolute", "--git-dir")
    if code != 0 or code_dir != 0:
        return False
    return Path(os.path.realpath(common)) != Path(os.path.realpath(gitdir))


def revert_refusal(repo, global_root):
    """Why a revert must not run in `repo`, or None: a revert commit in a main checkout would land on main with no
    merge, so it runs only in a worktree, except in the owner's global folder (`global_root`, its own git repo), where
    it runs in place."""
    if Path(os.path.realpath(repo)) == Path(os.path.realpath(global_root)) or in_worktree(repo):
        return None
    return (f"{repo} is a main checkout, not a worktree: a revert there would land on main with no merge; "
            f"call EnterWorktree first and run the revert there")


def uncommitted(repo, files):
    """The files (of `files`, relative to `repo`) that have uncommitted changes, or None when git cannot tell. The
    global set is edited in place in the owner's own repository, so a file the owner is changing is never touched."""
    code, out = git(repo, "status", "--porcelain", "--", *files)
    if code != 0:
        return None
    return [line.strip().split(None, 1)[-1].strip('"') for line in out.splitlines() if line.strip()]  # `XY path`


def commit_files(repo, files, message):
    """Commit only `files` in `repo` (`git commit -- <files>`: whatever else is staged or changed there stays out);
    `(hash, None)` or `(None, error)`."""
    code, out = git(repo, "add", "--", *files)
    if code != 0:
        return None, f"git add failed in {repo}: {out}"
    code, out = git(repo, "commit", "-q", "-m", message, "--", *files)
    if code != 0:
        return None, f"git commit failed in {repo}: {out}"
    code, head = git(repo, "rev-parse", "HEAD")
    return (head, None) if code == 0 else (None, f"git rev-parse failed in {repo}: {head}")


def restore_files(repo, files):
    """Undo the uncommitted edit of `files` only (a rejected fix): `git checkout HEAD -- <files>`, which also drops a
    staged change; `(True, '')` or `(False, error)`."""
    code, out = git(repo, "checkout", "HEAD", "--", *files)
    return (code == 0), ("" if code == 0 else f"git checkout failed in {repo}: {out}")


def main_branch(repo):
    code, _ = git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/main")
    if code == 0:
        return "main"
    code, name = git(repo, "symbolic-ref", "--short", "HEAD")
    return name if code == 0 and name else None


def reached(repo, commit):
    """`(branch, datetime)` when `commit` is in the repo's main branch (module doc, "Post-change check"); `(branch,
    None)` when it is not yet; `(None, None)` when the repo or branch cannot be read."""
    branch = main_branch(repo)
    if not branch:
        return None, None
    code, _ = git(repo, "merge-base", "--is-ancestor", commit, branch)
    if code != 0:
        return branch, None
    moment = None
    code, log = git(repo, "reflog", "show", "--date=unix", "--format=%H %gd", f"refs/heads/{branch}")
    for line in log.splitlines() if code == 0 else []:  # newest first; `%gd` with unix dates: `main@{<seconds>}`
        head, _, ref = line.partition(" ")
        stamp = REFLOG_TIME.search(ref)
        if not stamp or git(repo, "merge-base", "--is-ancestor", commit, head)[0] != 0:
            break
        moment = stamp.group(1)
    if moment is None:
        code, moment = git(repo, "show", "-s", "--format=%ct", commit)
        if code != 0:
            return branch, None
    try:
        return branch, datetime.datetime.fromtimestamp(int(moment.strip()), datetime.timezone.utc)
    except ValueError:
        return branch, None


# Transcripts


def main_transcripts(projects_root, since=None):
    """`[(mtime, path)]` of the main transcripts, newest first; with `since` (a timestamp) those changed after it."""
    found = []
    for path in Path(projects_root).glob("*/*.jsonl") if Path(projects_root).is_dir() else []:
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if since is None or mtime >= since:
            found.append((mtime, path))
    return sorted(found, reverse=True)


def started(entries):
    """The time of a transcript's first dated line, or None."""
    for _, entry in entries:
        stamp = packets.parse_time(entry.get("timestamp")) if entry.get("timestamp") else None
        if stamp:
            return stamp if stamp.tzinfo else stamp.replace(tzinfo=datetime.timezone.utc)
    return None


def kinds_at_work(found):
    return {(part.kind, part.name) for part in found if part.kind in ("skill", "agent") and part.name}


def subagent_files(main):
    return sorted((Path(main).with_suffix("") / "subagents").glob("*.jsonl"))


# Replay


def seen_place(text):
    """`(id8, subagent type, (kind, name), (start, end))` a `seen:` line names; parts it does not name are None."""
    id8 = ID8.search(text)
    agent = SUBAGENT.search(text)
    label = PART_LABEL.search(text.split("| part:", 1)[-1] if "| part:" in text else text)
    lines = LINES.search(text)
    return (id8.group(1) if id8 else None, agent.group(1) if agent else None,
            (label.group(1), label.group(2)) if label else None,
            (int(lines.group(1)), int(lines.group(2))) if lines else None)


def pick_part(found, entries, registry, own, kind_name, lines):
    """The part a sighting names: by its first line, else its label, else the first marked body part, else the root."""
    if lines:
        hit = [part for part in found if part.start == lines[0]] or [
            part for part in found if part.start <= lines[0] <= part.end]
        if hit:
            return parts.body(max(hit, key=lambda part: part.depth)), None
    if kind_name:
        hit = [part for part in found if (part.kind, part.name) == kind_name]
        if hit:
            return hit[0], None
    marked = packets.mark(entries, found, registry, own)
    if marked:
        return marked[0].part, marked[0]
    return (found[0] if found else None), None


def file_kinds(registry, files):
    """The `(kind, name)` part kinds of the Files rows that own these files."""
    kinds = set()
    for name in files:
        owner = registry.owner(name)
        if owner:
            kinds.update(kind for kind in owner.rule.kinds if kind[0] in ("skill", "agent"))
    return kinds


def replay(item, registry, projects_root, data_dir, project_of=None, files=(), today=None):
    """Write the replay packets of an item (module doc); returns `[(role, path, label)]`, role `problem` or `good`."""
    folder = Path(data_dir) / PACKETS_FOLDER / f"{REPLAY_PREFIX}{item.key}"
    for old in folder.glob("*") if folder.is_dir() else []:
        try:
            old.unlink()
        except OSError:
            pass
    hooks = parts.HookIndex()
    written = []
    problem_sessions = set()
    kinds = set(file_kinds(registry, files))
    for _, text in item.seen():
        id8, agent, kind_name, lines = seen_place(text)
        if not id8:
            continue
        for main in sorted(Path(projects_root).glob(f"*/{id8}*.jsonl")):
            problem_sessions.add(main.stem)
            own = own_set(project_of, main)
            title = parts.title_of(parts.read_file(main))
            label = f"{title} ({main.stem[:8]})" if title else main.stem
            if agent:
                paths = [(path, "agent", parts.agent_type(path)) for path in subagent_files(main)
                         if parts.agent_type(path) == agent]
            else:
                paths = [(main, "session", "")]
            for path, root_kind, name in paths[:3]:
                entries = parts.read_file(path)
                found = parts.split(entries, root_kind, name, hooks)
                part, marks = pick_part(found, entries, registry, own, kind_name, lines)
                if part is None:
                    continue
                if part.kind in ("skill", "agent") and part.name:
                    kinds.add((part.kind, part.name))
                marks = marks or packets.Marks(part)
                packet, _ = packets.write(folder, path, label + (f" / subagent {name}" if root_kind == "agent" else ""),
                                          entries, marks, registry, own)
                written.append(("problem", packet, f"{label} | {part.label()} lines {part.start}-{part.end}"))
                break
    since = datetime.datetime.combine((today or datetime.date.today()) - datetime.timedelta(days=GOOD_DAYS),
                                      datetime.time()).timestamp()
    good = 0
    for _, main in main_transcripts(projects_root, since)[:GOOD_FILES]:
        if good >= GOOD_MAX:
            break
        if main.stem in problem_sessions:
            continue
        entries = parts.read_file(main)
        title = parts.title_of(entries).strip()
        if title.startswith(SKIP_TITLES):
            continue
        own = own_set(project_of, main)
        label = f"{title} ({main.stem[:8]})" if title else main.stem
        candidates = [(main, entries, "session", "")] + [(path, None, "agent", parts.agent_type(path))
                                                         for path in subagent_files(main)]
        for path, found_entries, root_kind, name in candidates:
            if root_kind == "agent" and kinds and ("agent", name) not in kinds:
                continue
            found_entries = found_entries if found_entries is not None else parts.read_file(path)
            found = parts.split(found_entries, root_kind, name, hooks)
            bodies = [part for part in found if parts.body(part) is part]
            wanted = [part for part in bodies if (part.kind, part.name) in kinds] if kinds else bodies[:1]
            if not wanted:
                continue
            marked = {id(marks.part) for marks in packets.mark(found_entries, found, registry, own)}
            clean = [part for part in wanted if id(part) not in marked]
            if not clean:
                continue
            part = clean[0]
            packet, _ = packets.write(folder, path, label + (f" / subagent {name}" if root_kind == "agent" else ""),
                                      found_entries, packets.Marks(part), registry, own)
            written.append(("good", packet, f"{label} | {part.label()} lines {part.start}-{part.end}"))
            good += 1
            break
    return written


def own_set(project_of, path):
    return project_of(path) if project_of else None


# Post-change check


def check(item, subscription, projects_root, today=None):
    """The post-change check of one fixed item (module doc): `(text, [session lines])`."""
    fixes = item.fixes()
    if not fixes:
        return "no fix commit recorded", []
    commit = fixes[-1][2]
    if commit is None:  # a fix of the old retro with no commit: the check goes by the date of the fix
        stamp = fixes[-1][0]
        if stamp is None:
            return "date-only fix with no readable date", []
        moment = datetime.datetime.combine(stamp, datetime.time()).astimezone()
        label = f"date-only fix (no commit) of {stamp.isoformat()}, no revert possible"
        branch = None
    else:
        label = commit[:8]
        repo = subscription.root if subscription is not None else None
        if repo is None:
            return f"{label}: the set {item.set} is not known, its repository cannot be read", []
        branch, moment = reached(repo, commit)
        if branch is None:
            return f"{label}: no git repository or branch at {repo}", []
        if moment is None:
            return f"{label}: not in {branch} yet", []
    kinds = set()
    for _, text in item.seen():
        kind_name = seen_place(text)[2]
        if kind_name:
            kinds.add(kind_name)
    hooks = parts.HookIndex()
    sessions = []
    for _, main in main_transcripts(projects_root, moment.timestamp()):
        if len(sessions) >= CHECK_SESSIONS:
            break
        entries = parts.read_file(main)
        begin = started(entries)
        title = parts.title_of(entries).strip()
        if not begin or begin < moment or title.startswith(SKIP_TITLES):
            continue
        if kinds:
            at_work = kinds_at_work(parts.split(entries, "session", "", hooks))
            at_work |= {("agent", parts.agent_type(path)) for path in subagent_files(main)}
            if not at_work & kinds:
                continue
        sessions.append(f"{begin.astimezone().strftime('%Y-%m-%d %H:%M')} | {title or '-'} ({main.stem[:8]}) | {main}")
    where = f"in {branch} since" if branch else "after"
    return f"{label}: {where} {moment.astimezone().strftime('%Y-%m-%d %H:%M')}", sessions


def has_new_sessions(item, subscription, projects_root, since=None):
    """Whether a session started after the item's last fix reached its branch (a date-only fix: after its date) and
    after `since` (the last review), a «Retro:» or «Docs:» session (or an old-titled one) not counted: the post-change check of the
    item has something new to read. False when the fix cannot be placed."""
    fixes = item.fixes()
    if not fixes:
        return False
    if fixes[-1][2] is None:
        if fixes[-1][0] is None:
            return False
        moment = datetime.datetime.combine(fixes[-1][0], datetime.time()).astimezone()
    else:
        repo = subscription.root if subscription is not None else None
        moment = reached(repo, fixes[-1][2])[1] if repo is not None else None
        if moment is None:
            return False
    floor = max(moment, since) if since else moment
    for _, main in main_transcripts(projects_root, floor.timestamp()):
        entries = parts.read_file(main)
        begin = started(entries)
        if begin and begin >= floor and not parts.title_of(entries).strip().startswith(SKIP_TITLES):
            return True
    return False


# Fix record, revert, requests


def fixed(item, data_dir, set_name, commit, files, what="", sign=False, today=None):
    """Record a landed fix (module doc): the `fix:` line, status `fixed`, a done-list line."""
    today = today or datetime.date.today()
    item.add(f"- fix: {today.isoformat()} | {set_name} | {commit} | {', '.join(files)} | {' '.join(what.split()) or '-'}")
    item.set_status("fixed")
    item.write()
    action = "sign added" if sign else "fixed"
    text = (f"Додано ознаку в підписку {set_name}: {item.title}" if sign else
            f"Виправлено правило ({', '.join(files) or set_name}): {item.title}")
    record(data_dir, set_name, item.key, action, text, today)


def changed_files(repo, commit, subscription):
    """The files of a commit, relative to the set root when the set holds them, else to the repository."""
    code, out = git(repo, "show", "--name-only", "--format=", commit)
    if code != 0:
        return None
    code, top = git(repo, "rev-parse", "--show-toplevel")
    names = []
    for name in out.splitlines():
        name = name.strip()
        if not name:
            continue
        rel = subscription.rel(Path(top) / name) if subscription is not None and code == 0 else None
        names.append(rel or name)
    return names


def revert(item, data_dir, repo, today=None):
    """Revert the item's last fix commit in `repo` (module doc); `(ok, text)`."""
    today = today or datetime.date.today()
    fixes = item.fixes()
    if not fixes:
        return False, f"item {item.key} has no fix commit to revert"
    commit = fixes[-1][2]
    if commit is None:
        return False, (f"item {item.key}: its last fix is a date-only record of the old retro (no commit), so there is "
                       f"nothing to revert; mark it by hand (`rules-kit mark`)")
    code, out = git(repo, "revert", "--no-edit", commit)
    if code != 0:
        git(repo, "revert", "--abort")
        return False, f"git revert {commit[:8]} failed in {repo}: {out}"
    code, head = git(repo, "rev-parse", "HEAD")
    second = item.reverted_before()
    item.add(f"- revert: {today.isoformat()} | {head if code == 0 else '?'} | {commit}")
    item.set_status("parked" if second else "reverted")
    item.write()
    record(data_dir, item.set, item.key, "reverted", f"Повернуто зміну, бо не спрацювала: {item.title}", today)
    if second:
        record(data_dir, item.set, item.key, "parked", f"Відкладено після двох невдалих спроб: {item.title}", today)
    remove_request(data_dir, item.set, item.key)
    return True, f"reverted {commit[:8]} in {repo}; status {'parked' if second else 'reverted'}"


def mark(item, data_dir, status, note="", today=None):
    """Set a status by hand with a `mark:` line; the statuses of MARK_ACTIONS also go to the done list."""
    today = today or datetime.date.today()
    item.set_status(status)
    item.add(f"- mark: {today.isoformat()} | {status} | {' '.join(note.split()) or '-'}")
    item.write()
    action = MARK_ACTIONS.get(status)
    if action:
        words = MARK_WORDS[action]
        if action == "parked":  # the reason is the note, not always two failed tries
            words = f"Відкладено, причина: {' '.join(note.split())}" if note.strip() else "Відкладено"
        record(data_dir, item.set, item.key, action, f"{words}: {item.title}", today)


def request_path(data_dir, set_name, key):
    return Path(data_dir) / REQUESTS_FOLDER / f"{set_name}--{key}.json"


def request(item, data_dir, sender=""):
    """Write a revert request for the item (module doc)."""
    path = request_path(data_dir, item.set, item.key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"set": item.set, "key": item.key, "date": datetime.date.today().isoformat(),
                                "from": sender}, ensure_ascii=False), encoding="utf-8")
    record(data_dir, item.set, item.key, "revert requested", f"Власник попросив повернути: {item.title}")
    return path


def requests(data_dir, names):
    """`[(set, key)]` of the revert requests of the sets `names`."""
    folder = Path(data_dir) / REQUESTS_FOLDER
    found = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        set_name, _, key = path.stem.partition("--")
        if set_name in names and key:
            found.append((set_name, key))
    return found


def remove_request(data_dir, set_name, key):
    try:
        request_path(data_dir, set_name, key).unlink()
    except OSError:
        pass


# Spend cap


def budget(session_id, limit=BUDGET_PCT):
    """`(word, share or None, text)`: `under`, `over` or `unknown` (spend-kit missing or silent)."""
    done = spend_client.run(["session", "--id", session_id], SPEND_TIMEOUT_S)
    match = SHARE.search(done.stdout) if done is not None and done.returncode == 0 else None
    if not match:
        return "unknown", None, "spend-kit gave no share for this session"
    share = float(match.group(1))
    return ("over" if share >= limit else "under"), share, f"{share:g}% of the weekly limit, cap {limit:g}%"
