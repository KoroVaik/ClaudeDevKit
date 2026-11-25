"""The Pult watcher (plugins/pult/scripts/watch-servers.ps1) logs a live lead or task session that stopped on the
usage limit: LIMIT once per stop, LIMIT-END when it goes on. Runs the real script with a fake `claude` on PATH."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
WATCH = ROOT / "plugins" / "pult" / "scripts" / "watch-servers.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")

LEAD = "11111111-aaaa-bbbb-cccc-000000000001"
TASK = "22222222-aaaa-bbbb-cccc-000000000002"


def notice(uuid):
    return {"type": "assistant", "uuid": uuid, "apiError": "usage_limit_reached", "error": "rate_limit",
            "isApiErrorMessage": True, "apiErrorParams": {"rate_limit_info": {"resetsAt": None}},
            "message": {"role": "assistant", "model": "<synthetic>", "content": [{"type": "text", "text": "limit"}]}}


def reply(text):
    return {"type": "assistant", "message": {"role": "assistant", "model": "m", "content": [{"type": "text", "text": text}]}}


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult watcher runs on Windows PowerShell")
class WatchServersLimitTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "claude.cmd").write_text('@type "%~dp0agents.json"\r\n', encoding="ascii")
        self.projects = self.tmp / "projects" / "p1"
        self.projects.mkdir(parents=True)
        self.state = self.tmp / "devkit-state"
        registry = self.state / "proj-0123456789"
        registry.mkdir(parents=True)
        # The task id carries a CR, as when it was pasted from `claude --bg` output.
        (registry / "sessions.json").write_text(json.dumps(
            [{"id": TASK + "\r", "name": "C: task", "status": "active"}]), encoding="utf-8")
        (self.bin / "agents.json").write_text(json.dumps([
            {"pid": 999999, "kind": "background", "name": "L: Lead", "sessionId": LEAD, "id": LEAD[:8], "state": "blocked"},
            {"pid": 999998, "kind": "background", "name": "C: task", "sessionId": TASK, "id": TASK[:8], "state": "blocked"},
        ]), encoding="utf-8")
        self.config = self.tmp / "servers.psd1"
        self.config.write_text("@{ Servers = @( @{ Session = 'L: Lead'; Lead = $true; Path = '%s' } ) }\n" % self.tmp,
                               encoding="utf-8-sig")

    def transcript(self, session_id, entries):
        (self.projects / f"{session_id}.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\n",
                                                          encoding="utf-8")

    def run_watch(self, rounds):
        env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
                   DEV_KIT_USAGE_LOG=str(self.tmp / "usage"),
                   DEV_KIT_PROJECTS_DIR=str(self.projects.parent))
        subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(WATCH),
                        "-Rounds", str(rounds), "-IntervalSec", "0", "-ConfigFile", str(self.config),
                        "-StateDir", str(self.tmp / "pult"), "-DevKitStateDir", str(self.state),
                        "-DaemonLog", str(self.tmp / "daemon.log")],
                       env=env, check=True, capture_output=True, timeout=180)
        log = (self.tmp / "pult" / "logs" / "servers.log").read_text(encoding="utf-8-sig")
        # the resume messages (LIMIT-RESUME...) are tested in test_watch_servers_wake.py
        return [line.split(" ", 1)[1] for line in log.splitlines()
                if (" LIMIT" in line and " LIMIT-RESUME" not in line) or " WARN" in line]

    # protects: Flow
    def test_limit_is_logged_once_per_stop_for_leads_and_task_sessions(self):
        self.transcript(LEAD, [reply("x"), notice("lead-stop")])
        self.transcript(TASK, [reply("y"), notice("task-stop")])
        lines = self.run_watch(2)
        self.assertEqual(sorted([f"LIMIT L: Lead {LEAD} (resets unknown)", f"LIMIT C: task {TASK} (resets unknown)"]),
                         sorted(lines))

    # protects: Flow
    def test_limit_end_when_the_session_goes_on(self):
        self.transcript(LEAD, [reply("working")])
        self.transcript(TASK, [reply("y"), notice("task-stop")])
        later = self.tmp / "later.jsonl"  # the task session was told to go on: the fake claude swaps it in on round 2
        later.write_text(json.dumps(reply("going on")) + "\n", encoding="utf-8")
        target = self.projects / f"{TASK}.jsonl"
        (self.bin / "claude.cmd").write_text(
            f'@if exist "%~dp0seen" copy /y "{later}" "{target}" >nul\r\n'
            '@echo.>"%~dp0seen"\r\n@type "%~dp0agents.json"\r\n', encoding="ascii")
        self.assertEqual([f"LIMIT C: task {TASK} (resets unknown)", f"LIMIT-END C: task {TASK}"], self.run_watch(2))


if __name__ == "__main__":
    unittest.main()
