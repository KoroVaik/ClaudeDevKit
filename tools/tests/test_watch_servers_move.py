"""The Pult watcher (plugins/pult/scripts/watch-servers.ps1, Invoke-TaskMoveCheck) moves a registry session (a Manager)
that left a handoff marker (`sessions.py handoff save --session <id>`) to a fresh context as a plain `--bg` job: stop,
`/clear` resume, stop, resume with the load prompt, then the registry record takes the new session id. Runs the real
watcher and the real sessions.py on a temp copy of the pult scripts with a fake `claude` on PATH (it keeps the session
list, writes the new transcript a /clear writes and records every call), so no real session is touched. The "lead" is
this test process (its pid is alive)."""
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # also when run by module name, not only by discover
from test_watch_servers_restart import LEAD, LEAD_SID, POWERSHELL, WatcherEnv  # noqa: E402

TASK_SID = "22222222-aaaa-bbbb-cccc-000000000002"
SHORT = TASK_SID[:8]
NAME = "M: task"
FILE = "move-1.md"

FAKE_CLAUDE = '''import json, os, pathlib, sys
d = pathlib.Path(__file__).parent
argv = sys.argv[1:]
if argv[:1] == ["agents"]:
    print((d / "agents.json").read_text())
    raise SystemExit
with open(d / "calls.txt", "a", encoding="utf-8") as f:
    f.write(json.dumps(argv) + "\\n")
agents = json.loads((d / "agents.json").read_text())
plan = json.loads((d / "plan.json").read_text()) if (d / "plan.json").exists() else {}
task = next(a for a in agents if a["name"] == "M: task")
def save():
    (d / "agents.json").write_text(json.dumps(agents))
if argv[:1] == ["stop"]:
    if argv[1] == task["id"] and not plan.get("stop_keeps"):
        task.update(pid=None, status=None, state="stopped")
        save()
    print("stopped")
elif argv[:1] == ["rm"]:
    print("removed")
elif "--resume" in argv:
    step = "clear" if argv[-1] == "/clear" else "load"
    how = plan.get(step, "ok")
    if how == "fail":
        print("error: boom")
        raise SystemExit(1)
    if how != "noreturn":
        if step == "clear" and how == "ok":
            # As seen live (2026-11-23): /clear writes a new transcript file; the job keeps its sessionId but points at
            # the new file, and the session list shows the new file's id as the sessionId (the short id stays).
            new = "cccccccc-aaaa-bbbb-cccc-000000000001"
            state = pathlib.Path(os.environ["DEV_KIT_JOBS_DIR"]) / task["id"] / "state.json"
            job = json.loads(state.read_text())
            job["linkScanPath"] = str(d / (new + ".jsonl"))
            job["resumeSessionId"] = new
            state.write_text(json.dumps(job))
            task["sessionId"] = new
        task.update(pid=4242, status="idle", state="idle")
        save()
    print("note: woke session " + task["id"] + " with its saved options.")
'''


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult watcher runs on Windows PowerShell")
class WatchServersTaskMoveTest(WatcherEnv, unittest.TestCase):
    def setUp(self):
        super().setUp()
        (self.bin / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="ascii")
        self.set_task("idle")
        job = self.tmp / "jobs" / SHORT
        job.mkdir(parents=True)
        (job / "state.json").write_text(json.dumps({
            "sessionId": TASK_SID, "resumeSessionId": TASK_SID, "name": NAME, "linkScanPath": str(self.tmp / f"{TASK_SID}.jsonl"),
            "respawnFlags": ["--name", NAME, "--model", "opus"]}), encoding="utf-8")
        self.sessions("add", "--id", TASK_SID, "--name", NAME, "--worktree", str(self.project), "--task", "t.md")

    def set_task(self, status, session_id=TASK_SID):
        entry = {"pid": 4242, "kind": "background", "name": NAME, "sessionId": session_id, "id": SHORT,
                 "state": "working" if status == "busy" else "idle", "status": status}
        lead = {"pid": os.getpid(), "kind": "background", "name": LEAD, "sessionId": LEAD_SID, "id": LEAD_SID[:8],
                "state": "blocked", "status": "idle"}
        (self.bin / "agents.json").write_text(json.dumps([lead, entry]), encoding="utf-8")

    def sessions(self, *words):
        out = subprocess.run([sys.executable, str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                              str(self.project), *words], env=dict(os.environ, DEV_KIT_STATE_DIR=str(self.state)),
                             check=True, capture_output=True, text=True, timeout=60)
        return out.stdout.strip()

    def registry_ids(self):
        return [r["id"] for r in json.loads(next(self.state.rglob("sessions.json")).read_text(encoding="utf-8"))]

    def fake_calls(self):
        """The `claude` calls of the move (the one-shot sender's `-p` calls, which tell the lead of a stopped session, left out)."""
        f = self.bin / "calls.txt"
        calls = [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []
        return [c for c in calls if c[:1] != ["-p"]]

    def fake_plan(self, **plan):
        (self.bin / "plan.json").write_text(json.dumps(plan), encoding="utf-8")

    def lines(self, log, kind):
        return [line for line in log if f" {kind} " in line]

    CLEAR = ["--bg", "--resume", TASK_SID, "--", "/clear"]
    LOAD = ["--bg", "--resume", TASK_SID, "--", f"/continue-work-in-another-context load {FILE}"]

    # protects: Flow
    def test_go_marker_of_an_idle_manager_moves_it_to_a_fresh_context_and_rekeys_the_registry(self):
        # The move ask's answer (`handoff save --session <id> --go`): stop, /clear, stop, load, same job, no new session.
        self.sessions("handoff", "save", "--session", TASK_SID, "--file", FILE, "--go")
        log = self.run_watch(2, "-HandoffClearWaitSec", "10")
        self.assertEqual([["stop", SHORT], self.CLEAR, ["stop", SHORT], self.LOAD], self.fake_calls())
        new = "cccccccc-aaaa-bbbb-cccc-000000000001"
        self.assertEqual([new], self.registry_ids(), "the record follows the job's new session id")
        self.assertEqual("none", self.sessions("handoff", "status", "--session", TASK_SID))
        self.assertEqual("none", self.sessions("handoff", "status", "--session", new))
        moved = self.lines(log, "MOVE")
        self.assertEqual(1, len(moved), log)
        self.assertTrue(moved[0].endswith(f" MOVE {NAME} {TASK_SID} {FILE}"), moved)
        self.assertFalse([line for line in log if "FALLBACK" in line or "FAILED" in line], log)
        # Counted from the end of the move, under both ids: an idle moved session is not asked to move again at once.
        state = json.loads((self.tmp / "pult" / "wake-state.json").read_text(encoding="utf-8"))
        for key in (TASK_SID, new):
            self.assertLess(abs(time.time() - state["MoveAsked"][key]), 300, state)

    # protects: Rule
    def test_saved_marker_of_an_idle_manager_moves_it_but_a_busy_one_waits_with_the_reason(self):
        self.sessions("handoff", "save", "--session", TASK_SID, "--file", FILE)
        self.set_task("busy")
        log = self.run_watch(3)
        self.assertEqual([], self.fake_calls(), "a running turn, helper or background shell is not a safe point")
        wait = self.lines(log, "HANDOFF-WAIT")
        self.assertEqual(1, len(wait), log)
        self.assertTrue(wait[0].endswith(f" HANDOFF-WAIT {NAME} {FILE} (busy)"), wait)
        self.set_task("idle")
        log = self.run_watch(1, "-HandoffClearWaitSec", "10")
        self.assertEqual(4, len(self.fake_calls()), log)

    # protects: Rule
    def test_marker_under_the_id_the_list_shows_moves_a_session_registered_by_its_short_id(self):
        # The lead registers the short id `claude --bg` prints; the session runs `handoff save --session` with its own
        # full id: the watcher finds that marker, and the rekey turns the short id into the new full id.
        self.sessions("end", "--id", TASK_SID)
        self.sessions("add", "--id", SHORT, "--name", NAME, "--worktree", str(self.project), "--task", "t.md")
        self.sessions("handoff", "save", "--session", TASK_SID, "--file", FILE, "--go")
        log = self.run_watch(1, "-HandoffClearWaitSec", "10")
        self.assertEqual(4, len(self.fake_calls()), log)
        self.assertIn("cccccccc-aaaa-bbbb-cccc-000000000001", self.registry_ids())
        self.assertNotIn(SHORT, self.registry_ids())
        self.assertEqual("none", self.sessions("handoff", "status", "--session", TASK_SID))

    # protects: Rule
    def test_failing_clear_falls_back_to_the_load_resume_alone_and_keeps_the_old_context(self):
        # Nothing is lost: the job is resumed with the load prompt only, its old context stays.
        self.fake_plan(clear="fail")
        self.sessions("handoff", "save", "--session", TASK_SID, "--file", FILE, "--go")
        log = self.run_watch(2, "-HandoffClearWaitSec", "10")
        self.assertEqual([["stop", SHORT], self.CLEAR, ["stop", SHORT], self.LOAD], self.fake_calls())
        fallback = self.lines(log, "MOVE-FALLBACK")
        self.assertEqual(1, len(fallback), log)
        self.assertIn(f"MOVE-FALLBACK {NAME} the /clear resume failed: exit 1 (error: boom)", fallback[0])
        self.assertEqual(1, len(self.lines(log, "MOVE")), log)
        self.assertEqual([TASK_SID], self.registry_ids(), "no clear, so the session id stayed")
        self.assertEqual("none", self.sessions("handoff", "status", "--session", TASK_SID))

    # protects: Rule
    def test_clear_turn_that_does_not_end_in_time_falls_back_and_stops_the_session_first(self):
        self.fake_plan(clear="stays")  # woken, but the job never points at a new transcript
        self.sessions("handoff", "save", "--session", TASK_SID, "--file", FILE, "--go")
        log = self.run_watch(1, "-HandoffClearWaitSec", "2")
        calls = self.fake_calls()
        self.assertEqual([self.CLEAR, ["stop", SHORT], self.LOAD], calls[1:], "never two runs of one session")
        self.assertIn("did not end in 2 s", self.lines(log, "MOVE-FALLBACK")[0])

    # protects: Rule
    def test_session_that_does_not_stop_is_reported_critical_and_not_tried_again(self):
        self.fake_plan(stop_keeps=True)
        self.sessions("handoff", "save", "--session", TASK_SID, "--file", FILE, "--go")
        log = self.run_watch(3, "-HandoffStopWaitSec", "1")
        self.assertEqual([["stop", SHORT]], self.fake_calls(), "one try per marker")
        failed = self.lines(log, "MOVE-FAILED")
        self.assertEqual(1, len(failed), log)
        self.assertTrue(failed[0].endswith(f" MOVE-FAILED {NAME}: still running after the stop"), failed)
        self.assertNotEqual("none", self.sessions("handoff", "status", "--session", TASK_SID), "the marker stays")
        self.assertEqual([f"move failed: {NAME} | {FILE}"], self.lead_lines("move failed:"), "the lead hears of it once")

    def failed_load(self, how):
        self.fake_plan(load=how)
        self.sessions("handoff", "save", "--session", TASK_SID, "--file", FILE, "--go")
        log = self.run_watch(2, "-HandoffClearWaitSec", "10", "-TaskComeBackWaitSec", "2")
        failed = self.lines(log, "MOVE-FAILED")
        self.assertEqual(1, len(failed), log)
        self.assertFalse(self.lines(log, "MOVE"), "a move that did not end is not logged as done")
        self.assertEqual([TASK_SID], self.registry_ids(), "the registry is rekeyed only for a job that came back")
        self.assertNotEqual("none", self.sessions("handoff", "status", "--session", TASK_SID), "the marker stays")
        self.assertEqual(4, len(self.fake_calls()), "one try per marker")
        self.assertEqual([f"move failed: {NAME} | {FILE}"], self.lead_lines("move failed:"))
        return failed[0]

    def lead_lines(self, start):
        """The lines of the lead's pending wake items that start with `start` (the sender here cannot deliver, so they stay)."""
        pending = json.loads((self.tmp / "pult" / "wake-pending.json").read_text(encoding="utf-8"))
        items = [i for i in (pending if isinstance(pending, list) else [pending]) if i and i["Target"] == LEAD]
        return [line for i in items for line in i["Lines"] if line.startswith(start)]

    # protects: Flow
    def test_failed_move_tells_the_lead_once_so_it_starts_a_fresh_session_from_the_handoff(self):
        # The marker stays and a restarted watcher tries it again, but the lead already knows: the line is per marker in a run.
        self.failed_load("fail")
        self.run_watch(2, "-HandoffClearWaitSec", "10", "-TaskComeBackWaitSec", "2")
        self.assertEqual([f"move failed: {NAME} | {FILE}"], self.lead_lines("move failed:"))

    # protects: Rule
    def test_failed_load_resume_is_reported_critical(self):
        self.assertIn(f"MOVE-FAILED {NAME}: the load resume failed: exit 1 (error: boom)", self.failed_load("fail"))

    # protects: Rule
    def test_job_that_does_not_come_back_after_the_load_resume_is_reported_critical(self):
        self.assertIn(f"MOVE-FAILED {NAME}: the session did not come back after the load resume",
                      self.failed_load("noreturn"))


if __name__ == "__main__":
    unittest.main()
