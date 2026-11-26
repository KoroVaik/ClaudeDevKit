"""Make the Claude app show each lead under its current name.

    python -I -X utf8 sync-app-titles.py "L: Zhratva" "L: Prishch" ...

The app lists a background session by the title of its Remote Control session on claude.ai, set once when the
session first connects. Renaming the job (resume-lib.ps1, Set-LeadStateName), a resume with new flags or `/rename`
does not change it (plugins/dev-kit/claude-facts.md, "The app's session title is set once, at the first Remote
Control connect"). So for each name given: the newest job in ~/.claude/jobs whose state.json "name" is that name and
that has a "bridgeSessionId" gets its title read (GET /v1/code/sessions/<id>) and, when it differs, set to the name
(PUT with {"title": ...}), the same call Claude Code makes when it retitles a session. Auth: the owner's Claude login
(~/.claude/.credentials.json, claudeAiOauth.accessToken). Nothing is written locally.

One line per name: `TITLE <old> -> <new> <job>` (changed), `TITLE-OK <name> <job>` (already right),
`TITLE-SKIP <name>: <reason>` (no job, no link) or `TITLE-FAILED <name> <job>: <reason>`. Exit code 0, or 1 when any
call failed (an expired login token gives 401; the next run tries again).
Env overrides (tests): DEV_KIT_JOBS_DIR, DEV_KIT_CREDENTIALS_FILE, DEV_KIT_SESSIONS_API (base URL).
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

JOBS = Path(os.environ.get("DEV_KIT_JOBS_DIR") or Path.home() / ".claude" / "jobs")
CREDS = Path(os.environ.get("DEV_KIT_CREDENTIALS_FILE") or Path.home() / ".claude" / ".credentials.json")
API = (os.environ.get("DEV_KIT_SESSIONS_API") or "https://api.anthropic.com").rstrip("/")


def newest_jobs():
    """name -> (job folder name, bridgeSessionId) of the most recently updated job with that name and a link."""
    found = {}
    for f in JOBS.glob("*/state.json"):
        try:
            s = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        name, bridge = s.get("name"), s.get("bridgeSessionId")
        if not isinstance(name, str) or not isinstance(bridge, str) or not bridge:
            continue
        at = str(s.get("updatedAt") or "")
        if name not in found or at > found[name][0]:
            found[name] = (at, f.parent.name, bridge)
    return {n: (job, bridge) for n, (_, job, bridge) in found.items()}


def call(method, bridge, token, body=None):
    req = urllib.request.Request(f"{API}/v1/code/sessions/{bridge}", method=method,
                                 data=None if body is None else json.dumps(body).encode("utf-8"), headers={
        "Authorization": "Bearer " + token, "anthropic-version": "2023-06-01", "Content-Type": "application/json",
        "anthropic-beta": "ccr-byoc-2025-07-29,oauth-2025-04-20", "User-Agent": "claude-cli (pult)"})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read() or b"{}")


def main(names):
    try:
        token = json.loads(CREDS.read_text(encoding="utf-8"))["claudeAiOauth"]["accessToken"]
    except (OSError, ValueError, KeyError, TypeError) as e:
        print(f"TITLE-FAILED *: no login token ({type(e).__name__})")
        return 1
    jobs, failed = newest_jobs(), False
    for name in names:
        if name not in jobs:
            print(f"TITLE-SKIP {name}: no job with a Remote Control link")
            continue
        job, bridge = jobs[name]
        try:
            d = call("GET", bridge, token)
            old = (d.get("response_shape") or d).get("title")
            if old == name:
                print(f"TITLE-OK {name} {job}")
                continue
            call("PUT", bridge, token, {"title": name})
            print(f"TITLE {old} -> {name} {job}")
        except Exception as e:  # network, HTTP status, bad JSON: reported, the next run retries
            failed = True
            print(f"TITLE-FAILED {name} {job}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
