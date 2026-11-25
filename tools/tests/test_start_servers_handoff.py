"""start-servers.ps1 -Handoff <file> (plugins/pult/scripts/start-servers.ps1): starts one lead fresh, never resumed, with
the handoff file named in its first prompt. Runs the real script on a copy of the pult scripts with a fake `claude` on
PATH and a fake user folder, so no real session starts."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")
LEAD = "L: Lead"

FAKE_CLAUDE = '''import json, os, pathlib, sys
d = pathlib.Path(__file__).parent
argv = sys.argv[1:]
if argv[:1] == ["agents"]:
    print((d / "agents.json").read_text())
    raise SystemExit
with open(d / "calls.txt", "a", encoding="utf-8") as f:
    f.write(json.dumps(argv) + "\\n")
agents = json.loads((d / "agents.json").read_text())
def live(on, session_id=None):  # the lead's entry gets a pid (woken) or loses it (stopped)
    for a in agents:
        if a["name"] in ("L: Lead", "P: Lead"):
            a["pid"], a["status"] = (os.getpid(), "idle") if on else (None, None)
            if session_id:
                a["sessionId"] = session_id
    (d / "agents.json").write_text(json.dumps(agents))
plan = json.loads((d / "plan.json").read_text()) if (d / "plan.json").exists() else {}
if argv[:1] == ["stop"]:
    if not plan.get("stop_keeps"):
        live(False)
    print("stopped")
elif argv[:1] == ["rm"]:
    print("removed")
elif "--resume" in argv:
    step = "clear" if argv[-1] == "/clear" else "handoff"
    how = plan.get(step, "ok")
    if how == "copy":
        print("note: session 11111111 is already running in the background, so this started a copy as abcdef12.")
    elif how == "fail":
        print("error: boom")
        raise SystemExit(1)
    else:
        if step == "clear" and how == "ok":
            # As seen live (2026-11-23): /clear writes a new transcript file; the job keeps its sessionId but points at
            # the new file, and the session list shows the new file's id as the sessionId (the short id stays). Each
            # /clear writes another file.
            count = d / "clears.txt"
            n = int(count.read_text()) + 1 if count.exists() else 1
            count.write_text(str(n))
            new = "cccccccc-aaaa-bbbb-cccc-%012d" % n
            state = pathlib.Path(os.environ["USERPROFILE"]) / ".claude" / "jobs" / "11111111" / "state.json"
            job = json.loads(state.read_text())
            job["linkScanPath"] = str(d / (new + ".jsonl"))
            job["resumeSessionId"] = new
            state.write_text(json.dumps(job))
            live(True, new)
        else:
            live(True)
        print("note: woke session 11111111 with its saved options.")
else:
    print("started")
'''
SID = "11111111-aaaa-bbbb-cccc-000000000001"
NEW = "99999999-aaaa-bbbb-cccc-000000000009"  # the id of the transcript an earlier move's /clear wrote


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult scripts run on Windows PowerShell")
class StartServersHandoffTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.scripts = self.tmp / "scripts"
        shutil.copytree(ROOT / "plugins" / "pult" / "scripts", self.scripts, ignore=shutil.ignore_patterns("__pycache__"))
        self.user = self.tmp / "user"
        (self.user / ".claude" / "jobs").mkdir(parents=True)
        (self.user / ".claude" / "settings.json").write_text(json.dumps({"skipDangerousModePermissionPrompt": True}))
        self.project = self.tmp / "project"
        (self.project / ".claude").mkdir(parents=True)
        (self.project / ".claude" / "settings.json").write_text(json.dumps({"permissions": {"deny": [
            "Bash(rm -rf data*)", "PowerShell(Remove-Item*data*)"]}}))
        for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                     ["add", "."], ["commit", "-q", "-m", "bans"]):
            subprocess.run(["git", "-C", str(self.project), *args], check=True, capture_output=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="ascii")
        (self.bin / "claude.cmd").write_text(f'@"{sys.executable}" "%~dp0fake_claude.py" %*\r\n', encoding="ascii")
        # An older stopped session of the same name and folder: a normal start would resume it.
        (self.bin / "agents.json").write_text(json.dumps([
            {"kind": "background", "name": LEAD, "sessionId": "22222222-aaaa-bbbb-cccc-000000000002", "id": "22222222",
             "cwd": str(self.project), "startedAt": 1, "state": "stopped"}]), encoding="utf-8")
        self.config = self.tmp / "servers.psd1"
        self.config.write_text("@{ Servers = @( @{ Session = '%s'; Lead = $true; Path = '%s' } ) }\n"
                               % (LEAD, self.project), encoding="utf-8-sig")
        self.state = self.tmp / "pult"

    def run_start(self, *extra):
        env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", ""), USERPROFILE=str(self.user))
        out = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                              str(self.scripts / "start-servers.ps1"), "-ConfigFile", str(self.config),
                              "-StateDir", str(self.state), *extra],
                             env=env, capture_output=True, text=True, timeout=120)
        return out.returncode, out.stdout + out.stderr

    def claude_calls(self):
        f = self.bin / "calls.txt"
        return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    def log(self):
        return (self.state / "logs" / "servers.log").read_text(encoding="utf-8-sig")

    # protects: Flow
    def test_handoff_starts_the_lead_fresh_with_the_file_in_the_prompt(self):
        code, out = self.run_start("-Only", LEAD, "-Handoff", "handoff-3.md")
        self.assertEqual(0, code, out)
        self.assertIn(f"Started lead: {LEAD}", out)
        calls = self.claude_calls()
        self.assertEqual(1, len(calls), calls)
        self.assertNotIn("--resume", calls[0], "a resume would bring back the full conversation")
        self.assertIn("--remote-control", calls[0])
        self.assertEqual("/dev-kit:project-lead handoff: handoff-3.md", calls[0][-1])
        self.assertIn(f"STARTED {LEAD} handoff handoff-3.md", self.log())

    def stopped_lead(self, plan, name=LEAD):
        """The lead the watcher just stopped: a stopped list entry, its job state, and how the fake claude answers.
        `name`: what the session is still called (a lead started before the rename is "P: Lead")."""
        (self.bin / "agents.json").write_text(json.dumps([
            {"kind": "background", "name": name, "sessionId": SID, "id": SID[:8], "cwd": str(self.project),
             "startedAt": 2, "state": "stopped", "pid": None}]), encoding="utf-8")
        job = self.user / ".claude" / "jobs" / SID[:8]
        job.mkdir(parents=True)
        (job / "state.json").write_text(json.dumps({
            "sessionId": SID, "resumeSessionId": SID, "name": name, "linkScanPath": str(self.tmp / f"{SID}.jsonl"),
            "respawnFlags": ["--remote-control", name, "--name", name, "--model", "haiku"]}), encoding="utf-8")
        (self.bin / "plan.json").write_text(json.dumps(plan), encoding="utf-8")

    def job_state(self):
        return json.loads((self.user / ".claude" / "jobs" / SID[:8] / "state.json").read_text(encoding="utf-8"))

    # protects: Flow
    def test_stopped_lead_with_the_old_name_is_resumed_under_the_new_name(self):
        # Plan: running leads are renamed "P: X" -> "L: X" by one resume that keeps their history.
        self.stopped_lead({}, name="P: Lead")
        code, out = self.run_start("-Only", LEAD)
        self.assertEqual(0, code, out)
        self.assertIn(f"Resumed lead: {LEAD}", out)
        # The resume keeps no extra flag (a resume with any flag starts a copy): the saved options carry the name.
        self.assertEqual([["--bg", "--resume", SID, "--", "/dev-kit:project-lead"]], self.claude_calls())
        job = self.job_state()
        self.assertEqual(LEAD, job["name"])
        self.assertEqual(["--remote-control", LEAD, "--name", LEAD, "--model", "opus", "--effort", "medium",
                          "--permission-mode", "bypassPermissions"], job["respawnFlags"])
        self.assertIn(f"RENAMED P: Lead -> {LEAD} {SID}", self.log())

    # protects: Rule
    def test_session_with_the_new_name_is_resumed_before_one_with_the_old_name(self):
        # The old name is only a fallback: an "L: Lead" session of the folder wins, the "P: Lead" job stays as it is.
        self.stopped_lead({}, name="P: Lead")
        agents = json.loads((self.bin / "agents.json").read_text())
        agents.append({"kind": "background", "name": LEAD, "sessionId": "22222222-aaaa-bbbb-cccc-000000000002",
                       "id": "22222222", "cwd": str(self.project), "startedAt": 1, "state": "stopped"})
        (self.bin / "agents.json").write_text(json.dumps(agents), encoding="utf-8")
        code, out = self.run_start("-Only", LEAD)
        self.assertEqual(0, code, out)
        self.assertEqual("22222222-aaaa-bbbb-cccc-000000000002", self.claude_calls()[0][2])
        self.assertEqual("P: Lead", self.job_state()["name"])
        self.assertNotIn("RENAMED", self.log())

    # protects: Rule
    def test_running_lead_with_the_old_name_is_not_started_again(self):
        # The watcher and logon runs must never start a second lead of the project while "P: Lead" runs.
        self.stopped_lead({}, name="P: Lead")
        agents = json.loads((self.bin / "agents.json").read_text())
        agents[0]["pid"] = os.getpid()
        (self.bin / "agents.json").write_text(json.dumps(agents), encoding="utf-8")
        code, out = self.run_start("-Only", LEAD)
        self.assertEqual(0, code, out)
        self.assertIn(f"Already running: {LEAD}", out)
        self.assertEqual([], self.claude_calls())

    # protects: Flow
    def test_handoff_move_of_a_lead_with_the_old_name_renames_it_and_moves_it(self):
        self.stopped_lead({}, name="P: Lead")
        code, out = self.run_move()
        self.assertEqual(0, code, out)
        self.assertIn(f"Resumed lead: {LEAD}", out)
        self.assertEqual([["--bg", "--resume", SID, "--", "/clear"], ["stop", SID[:8]],
                          ["--bg", "--resume", SID, "--", "/dev-kit:project-lead handoff: h.md"]], self.claude_calls())
        self.assertEqual(LEAD, self.job_state()["name"])
        self.assertIn(f"RENAMED P: Lead -> {LEAD} {SID}", self.log())

    def run_move(self, *extra):
        return self.run_start("-Only", LEAD, "-Handoff", "h.md", "-HandoffSessionId", SID, *extra)

    # protects: Flow
    def test_handoff_with_a_session_id_clears_and_resumes_the_same_session(self):
        # No new session, so no phone push (plans/push-noise.md).
        self.stopped_lead({})
        code, out = self.run_move()
        self.assertEqual(0, code, out)
        self.assertIn(f"Resumed lead: {LEAD}", out)
        self.assertEqual([["--bg", "--resume", SID, "--", "/clear"], ["stop", SID[:8]],
                          ["--bg", "--resume", SID, "--", "/dev-kit:project-lead handoff: h.md"]], self.claude_calls())
        log = self.log()
        self.assertIn(f"RESUMED {LEAD} {SID} handoff h.md", log)
        self.assertNotIn("HANDOFF-FALLBACK", log)
        flags = json.loads((self.user / ".claude" / "jobs" / SID[:8] / "state.json").read_text())["respawnFlags"]
        self.assertEqual("opus", flags[flags.index("--model") + 1], "the lead wakes on its own model")

    def moved_before(self):
        """A lead already moved once: the list shows the new transcript's id, the job keeps its first id."""
        agents = json.loads((self.bin / "agents.json").read_text())
        agents[0]["sessionId"] = NEW
        (self.bin / "agents.json").write_text(json.dumps(agents), encoding="utf-8")
        state = self.user / ".claude" / "jobs" / SID[:8] / "state.json"
        job = json.loads(state.read_text())
        job.update(resumeSessionId=NEW, linkScanPath=str(self.tmp / f"{NEW}.jsonl"))
        state.write_text(json.dumps(job), encoding="utf-8")

    # protects: Bug
    def test_lead_moved_before_is_moved_again_by_its_jobs_own_id(self):
        # Live run, 2026-11-23: after a /clear the list showed the new id, the stop matched none and two leads loomed.
        self.stopped_lead({"clear": "stays"})
        self.moved_before()
        code, out = self.run_start("-Only", LEAD, "-Handoff", "h.md", "-HandoffSessionId", NEW, "-HandoffClearWaitSec", "2")
        self.assertEqual(0, code, out)
        calls = self.claude_calls()
        self.assertEqual(["--bg", "--resume", SID, "--", "/clear"], calls[0], "resumed by the job's own id")
        self.assertEqual(["stop", SID[:8]], calls[1], "stopped by the short id, though the list shows another sessionId")
        self.assert_fresh_fallback(out, "did not end in 2 s")

    # protects: Bug
    def test_second_move_of_a_lead_succeeds(self):
        # Its /clear moves the job's resumeSessionId and the list's sessionId on from the id the watcher passed: the
        # move must still see the turn end, stop the session and resume it with the handoff prompt.
        self.stopped_lead({})
        self.moved_before()
        code, out = self.run_start("-Only", LEAD, "-Handoff", "h.md", "-HandoffSessionId", NEW)
        self.assertEqual(0, code, out)
        self.assertIn(f"Resumed lead: {LEAD}", out)
        self.assertEqual([["--bg", "--resume", SID, "--", "/clear"], ["stop", SID[:8]],
                          ["--bg", "--resume", SID, "--", "/dev-kit:project-lead handoff: h.md"]], self.claude_calls())
        self.assertNotIn("HANDOFF-FALLBACK", self.log())
        job = json.loads((self.user / ".claude" / "jobs" / SID[:8] / "state.json").read_text())
        self.assertNotIn(job["resumeSessionId"], (SID, NEW), "the fake's /clear wrote a third id")

    # protects: Bug
    def test_plain_resume_of_a_lead_moved_before_uses_the_jobs_own_id(self):
        self.stopped_lead({})
        self.moved_before()
        code, out = self.run_start("-Only", LEAD)
        self.assertEqual(0, code, out)
        self.assertEqual([["--bg", "--resume", SID, "--", "/dev-kit:project-lead"]], self.claude_calls())

    def assert_fresh_fallback(self, out, reason):
        self.assertIn(f"Started lead: {LEAD}", out)
        fresh = self.claude_calls()[-1]
        self.assertIn("--remote-control", fresh)
        self.assertNotIn("--resume", fresh)
        self.assertEqual("/dev-kit:project-lead handoff: h.md", fresh[-1])
        fallback = [line for line in self.log().splitlines() if " HANDOFF-FALLBACK " in line]
        self.assertEqual(1, len(fallback), self.log())
        self.assertIn(f"HANDOFF-FALLBACK {LEAD} ", fallback[0])
        self.assertIn(reason, fallback[0])

    # protects: Rule
    def test_clear_resume_that_starts_a_copy_removes_it_and_starts_fresh(self):
        self.stopped_lead({"clear": "copy"})
        code, out = self.run_move()
        self.assertEqual(0, code, out)
        calls = self.claude_calls()
        self.assertIn(["stop", "abcdef12"], calls)
        self.assertIn(["rm", "abcdef12"], calls)
        self.assert_fresh_fallback(out, "claude started a copy abcdef12")

    # protects: Rule
    def test_clear_turn_that_does_not_end_in_time_stops_the_session_and_starts_fresh(self):
        self.stopped_lead({"clear": "stays"})  # woken, but the job never points at a new transcript
        code, out = self.run_move("-HandoffClearWaitSec", "2")
        self.assertEqual(0, code, out)
        self.assertIn(["stop", SID[:8]], self.claude_calls(), "never two leads of one name")
        self.assertNotIn(["--bg", "--resume", SID, "--", "/dev-kit:project-lead handoff: h.md"], self.claude_calls())
        self.assert_fresh_fallback(out, "did not end in 2 s")

    # protects: Rule
    def test_failed_handoff_resume_starts_fresh(self):
        self.stopped_lead({"handoff": "fail"})
        code, out = self.run_move()
        self.assertEqual(0, code, out)
        self.assert_fresh_fallback(out, "the handoff resume failed: exit 1 (error: boom)")

    # protects: Rule
    def test_session_that_does_not_stop_is_not_replaced_by_a_fresh_lead(self):
        self.stopped_lead({"stop_keeps": True})
        code, out = self.run_move("-HandoffStopWaitSec", "1")
        self.assertIn(f"Not started, still running after the stop: {LEAD}", out)
        self.assertFalse([c for c in self.claude_calls() if "--remote-control" in c], "two leads of one name")
        self.assertIn(f"STILL-RUNNING {LEAD} {SID}", self.log())

    # protects: Rule
    def test_handoff_needs_exactly_one_only_name(self):
        for extra in (["-Handoff", "h.md"], ["-Only", f"{LEAD},L: Other", "-Handoff", "h.md"]):
            code, out = self.run_start(*extra)
            self.assertEqual(1, code, out)
            self.assertIn("-Handoff", out)
        self.assertEqual([], self.claude_calls(), "nothing is started when the arguments are wrong")

    # protects: Rule
    def test_handoff_with_a_bad_file_name_starts_nothing(self):
        code, out = self.run_start("-Only", LEAD, "-Handoff", "..\\x.md")
        self.assertNotEqual(0, code, out)
        self.assertEqual([], self.claude_calls())


if __name__ == "__main__":
    unittest.main()
