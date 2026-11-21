"""Add hard-ban deny lines to a project's `.claude/settings.json` on main, one commit per run, and undo the latest add.

    dev-kit-bans add <repo-path> <deny-line> [<deny-line> ...]
    dev-kit-bans add-approved [<repo-path>]
    dev-kit-bans undo <repo-path>
    dev-kit-bans check <repo-path>

No agent runs `add`, `add-approved` or `undo`: the owner types the command himself (`! dev-kit-bans add-approved` in
the lead's chat). Why: 2026-11-21, the auto-mode guard refused an agent writing permission settings even after the
owner's yes; the owner typing the command is allowed. The agent only prepares `.claude/hard-bans.json`.

`add` only appends deny lines (`Tool(...)`) to `permissions.deny`: it never removes or changes a line or a key. The
repo must be on branch `main` and `.claude/settings.json` must have no uncommitted change (other dirty files stay
untouched and unstaged). Lines already present are skipped; when nothing is new it commits nothing. Each run that adds
lines is one commit of that file alone, subject `hard bans: add <N> deny lines`, trailer `Hard-Bans: add`. The file is
rewritten with a 2-space indent (its line endings and BOM are kept), so a file formatted otherwise changes in format
too. Nothing is pushed.

`add-approved` takes the lines from `<repo>/.claude/hard-bans.json` in the working tree (`{"deny": [...]}`; refused
when absent or invalid; the repo defaults to the git top folder of the current directory) and adds the missing ones
exactly like `add` (same checks), printing each added line. One commit holds `.claude/settings.json` and
`.claude/hard-bans.json` (the latter when it is untracked, staged or changed), trailer `Hard-Bans: add`. With nothing to
add and `hard-bans.json` unchanged it prints "nothing to add" and commits nothing. Other dirty or staged files stay out.

`undo` reverts only the latest ban-adding commit, one step back: the newest commit on main with a `Hard-Bans:`
trailer must be an `add` and the newest commit of the settings file at all, and it must have touched only the settings
file and `.claude/hard-bans.json` (that one too must not have changed since). The revert is checked before it is
committed: the parent's settings must equal the file as it is now minus exactly the lines that commit added. Both
files are set back to the parent's content and committed alone (staged work on other files stays staged and out of the
commit). The revert commit has the trailer `Hard-Bans: undo <sha>`. A second undo is refused: older bans are removed by
the owner by hand. Nothing is pushed.

`check` tells whether the committed `main:.claude/settings.json` passes Pult's gate (same rule as
`Get-LeadPermissionMode` in plugins/pult/scripts/resume-lib.ps1): a deny line starting with `Bash(git push`,
`Bash(rm -rf` or `Bash(docker` and one starting with `PowerShell(git push`, `PowerShell(Remove-Item` or
`PowerShell(docker` (case-insensitive).

Exit codes: 0 ok, 1 refused or not passing, 2 usage or git error.
"""
import argparse
import json
import os
import re
import subprocess
import sys

SETTINGS = ".claude/settings.json"
HARD_BANS = ".claude/hard-bans.json"
BRANCH = "main"
TRAILER = "Hard-Bans"
LINE = re.compile(r"[A-Za-z]+\(.+\)")
BASH_PREFIXES = ("bash(git push", "bash(rm -rf", "bash(docker")
POWERSHELL_PREFIXES = ("powershell(git push", "powershell(remove-item", "powershell(docker")


class Refused(Exception):
    """The request is refused (exit 1)."""


class GitError(Exception):
    """Git failed or the arguments are wrong (exit 2)."""


def git(root, *args, input_text=None, check=True):
    result = subprocess.run(
        ["git", "-C", root, *args], input=None if input_text is None else input_text.encode("utf-8"),
        capture_output=True,
    )
    out = result.stdout.decode("utf-8", "replace")
    if check and result.returncode != 0:
        raise GitError(f"git {' '.join(args[:2])} failed: {result.stderr.decode('utf-8', 'replace').strip()}")
    return result.returncode, out.rstrip("\n")


def repo_root(path):
    if not os.path.isdir(path):
        raise GitError(f"not a folder: {path}")
    code, top = git(path, "rev-parse", "--show-toplevel", check=False)
    if code != 0 or not top:
        raise GitError(f"not a git repository: {path}")
    if not os.path.samefile(top, path):
        raise Refused(f"{path} is inside a repository but is not its top folder ({top})")
    return top


def require_main(root):
    code, branch = git(root, "symbolic-ref", "--short", "-q", "HEAD", check=False)
    if code != 0 or branch != BRANCH:
        raise Refused(f"the checkout is not on branch {BRANCH} (it is on {branch or 'a detached HEAD'})")


def require_clean_settings(root):
    _, status = git(root, "status", "--porcelain", "--", SETTINGS)
    if status.strip():
        raise Refused(f"{SETTINGS} has uncommitted changes")


def read_text(path):
    """Return (text, line ending, has BOM) of the file; an absent file is an empty text."""
    if not os.path.exists(path):
        return "", "\n", False
    with open(path, "rb") as f:
        raw = f.read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
    return text, ("\r\n" if "\r\n" in text else "\n"), bom


def parse(text, where):
    if not text.strip():
        return {}
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise Refused(f"{where} does not parse as JSON: {exc}")
    if not isinstance(data, dict):
        raise Refused(f"{where} is not a JSON object")
    return data


def deny_list(data, where, create=False):
    permissions = data.get("permissions")
    if permissions is None:
        if not create:
            return []
        permissions = data["permissions"] = {}
    if not isinstance(permissions, dict):
        raise Refused(f"{where}: permissions is not an object")
    deny = permissions.get("deny")
    if deny is None:
        if not create:
            return []
        deny = permissions["deny"] = []
    if not isinstance(deny, list):
        raise Refused(f"{where}: permissions.deny is not a list")
    return deny


def write_settings(path, data, newline, bom):
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    if newline == "\r\n":
        text = text.replace("\n", "\r\n")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write((b"\xef\xbb\xbf" if bom else b"") + text.encode("utf-8"))


def commit_files(root, message, paths, stage=True):
    """Commit exactly these files (the index may hold other staged work, which stays staged)."""
    if stage:  # an undo has staged its revert already (it may be the deletion of a file)
        git(root, "add", "--", *paths)
    git(root, "commit", "--only", "-q", "-F", "-", "--", *paths, input_text=message)
    return git(root, "rev-parse", "HEAD")[1]


def clean_lines(lines):
    """The deny lines stripped, checked and without duplicates."""
    clean, seen = [], set()
    for line in lines:
        if not isinstance(line, str):
            raise Refused(f"not a deny line of the form Tool(...): {line!r}")
        line = line.strip()
        if not LINE.fullmatch(line):
            raise Refused(f"not a deny line of the form Tool(...): {line!r}")
        if line not in seen:
            seen.add(line)
            clean.append(line)
    return clean


def append_lines(root, clean):
    """Write the lines that settings.json lacks (nothing else changes); return the new ones."""
    file_path = os.path.join(root, *SETTINGS.split("/"))
    text, newline, bom = read_text(file_path)
    data = parse(text, SETTINGS)
    deny = deny_list(data, SETTINGS, create=True)
    new = [line for line in clean if line not in deny]
    if new:
        deny.extend(new)
        write_settings(file_path, data, newline, bom)
    return new


def add_message(new):
    body = "\n".join(f"- {line}" for line in new)
    return f"hard bans: add {len(new)} deny lines\n\n{body}\n\n{TRAILER}: add\n"


def cmd_add(path, lines):
    clean = clean_lines(lines)
    if not clean:
        raise GitError("no deny lines given")
    root = repo_root(path)
    require_main(root)
    require_clean_settings(root)
    new = append_lines(root, clean)
    if not new:
        print("nothing to add")
        return 0
    print(commit_files(root, add_message(new), [SETTINGS]))
    return 0


def default_repo():
    """The git top folder of the current directory."""
    cwd = os.getcwd()
    code, top = git(cwd, "rev-parse", "--show-toplevel", check=False)
    if code != 0 or not top:
        raise GitError(f"not a git repository: {cwd}")
    return top


def read_approved(root):
    """The deny lines of the working tree's .claude/hard-bans.json (the set the owner approved)."""
    file_path = os.path.join(root, *HARD_BANS.split("/"))
    if not os.path.isfile(file_path):
        raise Refused(f"{HARD_BANS} is absent in {root}: the lead writes it after the owner's yes")
    data = parse(read_text(file_path)[0], HARD_BANS)
    deny = data.get("deny")
    if not isinstance(deny, list) or not deny:
        raise Refused(f'{HARD_BANS} must be an object with a non-empty list "deny"')
    return clean_lines(deny)


def cmd_add_approved(path):
    root = repo_root(path) if path else default_repo()
    require_main(root)
    require_clean_settings(root)
    clean = read_approved(root)
    new = append_lines(root, clean)
    _, status = git(root, "status", "--porcelain", "--", HARD_BANS)
    bans_changed = bool(status.strip())  # untracked, staged or edited: it goes into the commit
    if not new and not bans_changed:
        print("nothing to add")
        return 0
    paths = ([SETTINGS] if new else []) + ([HARD_BANS] if bans_changed else [])
    if new:
        message = add_message(new)
    else:
        message = f"hard bans: record approved set\n\n- {HARD_BANS}\n\n{TRAILER}: add\n"
    for line in new:
        print(f"added: {line}")
    print(commit_files(root, message, paths))
    return 0


def trailer_of(root, sha):
    """The value of the Hard-Bans trailer of a commit ('' when it has none)."""
    _, value = git(root, "log", "-1", f"--format=%(trailers:key={TRAILER},valueonly)", sha)
    return value.strip()


def show_settings(root, rev):
    code, text = git(root, "show", f"{rev}:{SETTINGS}", check=False)
    return text if code == 0 else ""


def normalized(data):
    """The settings without an empty deny list or an empty permissions object (a file that an add created)."""
    data = json.loads(json.dumps(data))
    permissions = data.get("permissions")
    if isinstance(permissions, dict):
        if permissions.get("deny") == []:
            del permissions["deny"]
        if not permissions:
            del data["permissions"]
    return data


def cmd_undo(path):
    root = repo_root(path)
    require_main(root)
    require_clean_settings(root)
    _, listing = git(root, "log", BRANCH, "--format=%H", "--", SETTINGS)
    commits = listing.split()
    for index, sha in enumerate(commits):
        value = trailer_of(root, sha)
        if value:
            break
    else:
        raise Refused(f"no hard-bans commit touches {SETTINGS} on {BRANCH}")
    if value.startswith("undo"):
        raise Refused("the latest hard-bans commit is an undo: only one step back; "
                      "older bans are removed by the owner by hand")
    if not value.startswith("add"):
        raise Refused(f"unknown {TRAILER} trailer on {sha[:10]}: {value!r}")
    if index != 0:
        raise Refused(f"{commits[0][:10]} changed {SETTINGS} after the hard-bans commit {sha[:10]}; not undoing")
    _, files = git(root, "show", "--no-renames", "--name-only", "--format=", sha)
    touched = files.split()
    if SETTINGS not in touched or not set(touched) <= {SETTINGS, HARD_BANS}:
        raise Refused(f"commit {sha[:10]} touched more than {SETTINGS} and {HARD_BANS}; not undoing")
    if HARD_BANS in touched:
        _, bans_log = git(root, "log", BRANCH, "-1", "--format=%H", "--", HARD_BANS)
        _, bans_status = git(root, "status", "--porcelain", "--", HARD_BANS)
        if bans_log != sha or bans_status.strip():
            raise Refused(f"{HARD_BANS} changed after the hard-bans commit {sha[:10]}; not undoing")

    file_path = os.path.join(root, *SETTINGS.split("/"))
    before = parse(read_text(file_path)[0], SETTINGS)
    parent_data = parse(show_settings(root, sha + "^"), "the parent's settings")
    commit_data = parse(show_settings(root, sha), "the commit's settings")
    added = [line for line in deny_list(commit_data, "the commit's settings") if line not in deny_list(parent_data, "the parent's settings")]
    expected = json.loads(json.dumps(before))
    expected_deny = deny_list(expected, SETTINGS)
    if any(line not in expected_deny for line in added):
        raise Refused("the lines the commit added are no longer all in the file; not undoing")
    if expected_deny:
        expected["permissions"]["deny"] = [line for line in expected_deny if line not in added]

    if normalized(parent_data) != normalized(expected):
        raise Refused("the revert would not only remove the lines that commit added; nothing changed")
    # Restore the parent's content of the touched files: only these paths of the index change, so other staged work stays.
    paths = [SETTINGS] + ([HARD_BANS] if HARD_BANS in touched else [])
    for name in paths:
        if git(root, "cat-file", "-e", f"{sha}^:{name}", check=False)[0] == 0:
            git(root, "checkout", f"{sha}^", "--", name)
        else:
            git(root, "rm", "-q", "-f", "--", name)
    _, subject = git(root, "log", "-1", "--format=%s", sha)
    message = f'Revert "{subject}"\n\nThis reverts commit {sha}.\n\n{TRAILER}: undo {sha}\n'
    try:
        print(commit_files(root, message, paths, stage=False))
    except GitError:
        git(root, "checkout", "HEAD", "--", *paths, check=False)  # both files were clean, so nothing is lost
        raise
    return 0


def passes_gate(deny):
    lowered = [line.lower() for line in deny if isinstance(line, str)]
    bash = any(line.startswith(BASH_PREFIXES) for line in lowered)
    powershell = any(line.startswith(POWERSHELL_PREFIXES) for line in lowered)
    return bash, powershell


def cmd_check(path):
    root = repo_root(path)
    if git(root, "rev-parse", "-q", "--verify", f"refs/heads/{BRANCH}", check=False)[0] != 0:
        raise GitError(f"there is no branch {BRANCH}")
    text = show_settings(root, BRANCH)
    if not text.strip():
        print(f"not passing: no {SETTINGS} committed on {BRANCH}")
        return 1
    try:
        data = json.loads(text)
        deny = deny_list(data, f"{BRANCH}:{SETTINGS}")
    except (ValueError, AttributeError, Refused):
        print(f"not passing: {BRANCH}:{SETTINGS} does not parse or has no usable permissions.deny")
        return 1
    bash, powershell = passes_gate(deny)
    if bash and powershell:
        print(f"passing: {BRANCH}:{SETTINGS} has Bash and PowerShell hard-ban deny lines")
        return 0
    missing = [name for name, found in (("Bash", bash), ("PowerShell", powershell)) if not found]
    print(f"not passing: no {' and '.join(missing)} hard-ban deny line on {BRANCH}")
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="dev-kit-bans", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="add deny lines and commit them on main")
    add.add_argument("repo")
    add.add_argument("lines", nargs="+", metavar="deny-line")
    approved = sub.add_parser("add-approved", help="add the lines of .claude/hard-bans.json and commit both files on main")
    approved.add_argument("repo", nargs="?", default=None, help="default: the git top folder of the current directory")
    undo = sub.add_parser("undo", help="revert the latest ban-adding commit (one step back)")
    undo.add_argument("repo")
    check = sub.add_parser("check", help="tell whether committed main passes Pult's gate")
    check.add_argument("repo")
    args = parser.parse_args(argv)
    try:
        if args.command == "add":
            return cmd_add(args.repo, args.lines)
        if args.command == "add-approved":
            return cmd_add_approved(args.repo)
        if args.command == "undo":
            return cmd_undo(args.repo)
        return cmd_check(args.repo)
    except Refused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
