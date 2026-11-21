"""The Pult watcher (plugins/pult/scripts/watch-servers.ps1, Invoke-HandoffCheck) moves a lead that left a handoff marker
(`sessions.py handoff save`) to a fresh lead: it stops the old one and runs start-servers.ps1 -Handoff <file>. Runs the
real watcher and the real sessions.py on a temp copy of the pult scripts with a fake `claude` on PATH (it records
`claude stop` and, like the real one, drops the lead from the session list) and a stub start-servers.ps1, so no real
session or Pult process is touched. The "lead" is this test process (its pid is alive)."""
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # also when run by module name, not only by discover
from test_watch_servers_restart import LEAD, POWERSHELL, WatcherEnv  # noqa: E402

SID = "11111111-aaaa-bbbb-cccc-000000000001"
FILE = "handoff-1.md"

FAKE_CLAUDE = '''import pathlib, sys
d = pathlib.Path(__file__).parent
if sys.argv[1:2] == ["stop"]:
    with open(d / "stops.txt", "a") as f:
        f.write(" ".join(sys.argv[2:]) + "\\n")
    if not (d / "stop-keeps").exists():  # a stop that works: the lead is gone from the list
        (d / "agents.json").write_text("[]")
    print("stopped")
    raise SystemExit
print((d / "agents.json").read_text())
'''

# Records its call; the output is the test's (env TEST_START_OUTPUT). A failed start brings the old lead back to the
# session list, as the next HEAL would, so a second handoff try would find it live and ready again.
STUB_START = '''param([string[]]$Restarted, [string[]]$Only, [string]$ConfigFile, [string]$StateDir, [string]$Handoff)
Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "start Only=$($Only -join ',') Handoff=$Handoff"
if ($env:TEST_START_OUTPUT -notlike 'Started lead*') {
    Copy-Item -LiteralPath (Join-Path $env:TEST_BIN 'agents.bak') -Destination (Join-Path $env:TEST_BIN 'agents.json') -Force
}
Write-Output ($env:TEST_START_OUTPUT -replace '\\{name\\}', ($Only -join ','))
'''


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult watcher runs on Windows PowerShell")
class WatchServersHandoffTest(WatcherEnv, unittest.TestCase):
    def setUp(self):
        super().setUp()
        (self.scripts / "restart-leads.ps1").unlink()
        (self.scripts / "start-servers.ps1").write_text(STUB_START, encoding="ascii")
        (self.bin / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="ascii")
        self.start_output = "Started lead: {name}"
        # The lead's project holds hard-ban lines on main and the user accepted the bypass disclaimer (a fake user
        # folder, so the settings of this machine are not read): the gate before the stop passes.
        self.user_home = self.tmp / "user"
        (self.user_home / ".claude").mkdir(parents=True)
        (self.user_home / ".claude" / "settings.json").write_text(
            json.dumps({"skipDangerousModePermissionPrompt": True}), encoding="utf-8")
        self.commit_bans()
        self.agents("idle")
        (self.projects / "p1").mkdir()
        self.transcript = self.projects / "p1" / f"{SID}.jsonl"
        self.transcript.write_text(json.dumps({"type": "assistant"}) + "\n", encoding="utf-8")
        self.age_transcript(6)

    def commit_bans(self, deny=("Bash(rm -rf data*)", "PowerShell(Remove-Item*data*)")):
        settings = self.project / ".claude" / "settings.json"
        before = settings.read_text(encoding="utf-8")
        settings.write_text(json.dumps({"permissions": {"deny": list(deny)}}), encoding="utf-8")
        for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                     ["add", ".claude/settings.json"], ["commit", "-q", "-m", "bans"]):
            subprocess.run(["git", "-C", str(self.project), *args], check=True, capture_output=True)
        settings.write_text(before, encoding="utf-8")  # the working copy keeps the enabledPlugins

    def agents(self, status):
        super().agents(status)
        shutil.copy(self.bin / "agents.json", self.bin / "agents.bak")

    def env(self):
        return dict(super().env(), USERPROFILE=str(self.user_home), TEST_BIN=str(self.bin),
                    TEST_START_OUTPUT=self.start_output)

    def run_watch(self, rounds, *extra):
        subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(self.scripts / "watch-servers.ps1"),
                        "-Rounds", str(rounds), "-IntervalSec", "0", "-ConfigFile", str(self.config),
                        "-StateDir", str(self.tmp / "pult"), "-DevKitStateDir", str(self.state),
                        "-DaemonLog", str(self.tmp / "daemon.log"), "-DevKitDir", str(self.plugins / "dev-kit"),
                        "-RestartExe", str(self.bin / "stub.cmd"), *extra],
                       env=self.env(), check=True, capture_output=True, timeout=240)
        return (self.tmp / "pult" / "logs" / "servers.log").read_text(encoding="utf-8-sig").splitlines()

    def age_transcript(self, minutes):
        when = time.time() - minutes * 60
        os.utime(self.transcript, (when, when))

    def handoff(self, *words):
        out = subprocess.run([sys.executable, str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                              str(self.project), "handoff", *words],
                             env=dict(os.environ, DEV_KIT_STATE_DIR=str(self.state)), check=True, capture_output=True,
                             text=True, timeout=60)
        return out.stdout.strip()

    def stops(self):
        f = self.bin / "stops.txt"
        return f.read_text(encoding="utf-8").splitlines() if f.exists() else []

    def starts(self):
        return [line for line in self.restart_calls() if line.startswith("start ")]

    def marker_left(self):
        return self.handoff("status") != "none"

    # protects: Flow
    def test_saved_handoff_of_an_idle_quiet_lead_stops_it_and_starts_a_fresh_one(self):
        self.handoff("save", "--file", FILE)
        log = self.run_watch(2)
        self.assertEqual(["11111111"], self.stops())
        self.assertEqual([f"start Only={LEAD} Handoff={FILE}"], self.starts())
        self.assertFalse(self.marker_left(), "the marker is cleared once the fresh lead runs")
        moved = [line for line in log if " HANDOFF " in line]
        self.assertEqual(1, len(moved), log)
        self.assertTrue(moved[0].endswith(f" HANDOFF {LEAD} {SID} {FILE}"), moved)
        last = json.loads((self.tmp / "pult" / "wake-state.json").read_text(encoding="utf-8"))["LastWake"][LEAD]
        self.assertLess(time.time() - last, 120, "the new lead counts as just woken")
        self.assertFalse([line for line in log if "HANDOFF-FAILED" in line or "HANDOFF-WAIT" in line], log)

    # protects: Rule
    def test_saved_handoff_waits_while_the_transcript_is_not_quiet_and_says_so_once(self):
        # The lead may still be working through its notes: it is moved only after 5 quiet minutes.
        self.age_transcript(1)
        self.handoff("save", "--file", FILE)
        log = self.run_watch(2)
        self.assertEqual([], self.stops())
        self.assertEqual([], self.starts())
        waits = [line for line in log if " HANDOFF-WAIT " in line]
        self.assertEqual(1, len(waits), log)
        self.assertTrue(waits[0].endswith(f" HANDOFF-WAIT {LEAD} {FILE}"), waits)
        self.assertTrue(self.marker_left())

    # protects: Flow
    def test_go_handoff_skips_the_quiet_minutes(self):
        self.age_transcript(1)
        self.handoff("save", "--file", FILE)
        self.handoff("go")
        log = self.run_watch(2)
        self.assertEqual(["11111111"], self.stops())
        self.assertEqual([f"start Only={LEAD} Handoff={FILE}"], self.starts())
        self.assertTrue(any(line.endswith(f" HANDOFF {LEAD} {SID} {FILE}") for line in log), log)

    # protects: Rule
    def test_busy_lead_is_not_stopped(self):
        self.agents("busy")
        self.handoff("save", "--file", FILE, "--go")
        log = self.run_watch(2)
        self.assertEqual([], self.stops())
        self.assertEqual([], self.starts())
        self.assertTrue(self.marker_left())
        self.assertFalse([line for line in log if "HANDOFF-FAILED" in line], log)

    # protects: Rule
    def test_lead_that_was_just_sent_a_message_is_not_stopped(self):
        # A message sent a moment ago is not handled yet: stopping would lose it.
        (self.tmp / "pult").mkdir(exist_ok=True)
        (self.tmp / "pult" / "wake-state.json").write_text(
            json.dumps({"PultNote": True, "LastWake": {LEAD: time.time() - 30}}), encoding="utf-8")
        self.handoff("save", "--file", FILE, "--go")
        self.run_watch(2)
        self.assertEqual([], self.stops())

    # protects: Rule
    def test_nothing_is_stopped_while_the_hold_file_is_there(self):
        (self.tmp / "pult").mkdir(exist_ok=True)
        (self.tmp / "pult" / "hold").write_text("a stop is going on", encoding="utf-8")
        self.handoff("save", "--file", FILE, "--go")
        self.run_watch(2)
        self.assertEqual([], self.stops())

    # protects: Rule
    def test_failed_start_is_reported_once_keeps_the_marker_and_is_not_tried_again(self):
        self.start_output = "Start failed, exit 1: {name}: boom"
        self.handoff("save", "--file", FILE)
        log = self.run_watch(4)
        failed = [line for line in log if " HANDOFF-FAILED " in line]
        self.assertEqual(1, len(failed), log)
        self.assertTrue(failed[0].endswith(f" HANDOFF-FAILED {LEAD}: Start failed, exit 1: {LEAD}: boom"), failed)
        self.assertEqual(["11111111"], self.stops(), "one try per marker, though the old lead is live again")
        self.assertEqual([f"start Only={LEAD} Handoff={FILE}"], self.starts())
        self.assertTrue(self.marker_left(), "the marker stays for the owner or the lead")

    # protects: Rule
    def test_lead_still_running_after_the_stop_is_reported_and_no_fresh_lead_is_started(self):
        (self.bin / "stop-keeps").write_text("1", encoding="utf-8")  # claude stop leaves the session in the list
        self.handoff("save", "--file", FILE)
        log = self.run_watch(3, "-HandoffStopWaitSec", "1")
        failed = [line for line in log if " HANDOFF-FAILED " in line]
        self.assertEqual(1, len(failed), log)
        self.assertTrue(failed[0].endswith(f" HANDOFF-FAILED {LEAD}: still running after the stop"), failed)
        self.assertEqual([], self.starts(), "two leads of one name must never run")
        self.assertEqual(1, len(self.stops()))
        self.assertTrue(self.marker_left())

    # protects: Rule
    def test_lead_without_hard_bans_on_main_is_not_stopped_for_a_handoff(self):
        # The start would be refused after the stop: the lead would stay down.
        subprocess.run(["git", "-C", str(self.project), "rm", "-q", "-r", "--cached", ".claude"], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(self.project), "commit", "-q", "-m", "drop"], check=True, capture_output=True)
        self.handoff("save", "--file", FILE, "--go")
        log = self.run_watch(3)
        self.assertEqual([], self.stops())
        self.assertEqual(1, len([line for line in log if " NO-BANS " in line]), log)
        self.assertFalse([line for line in log if "HANDOFF-FAILED" in line], log)

    # protects: Rule
    def test_no_bans_answer_of_the_start_is_not_a_failure(self):
        self.start_output = ("NO-BANS {name} (no .claude/settings.json committed on main): lead not started. "
                             "Hub: show the owner the exact lines")
        self.handoff("save", "--file", FILE)
        log = self.run_watch(2)
        self.assertEqual(1, len([line for line in log if " NO-BANS " in line]), log)
        self.assertFalse([line for line in log if "HANDOFF-FAILED" in line], log)
        self.assertTrue(self.marker_left())

    # protects: Rule
    def test_lead_without_a_marker_is_left_alone(self):
        log = self.run_watch(2)
        self.assertEqual([], self.stops())
        self.assertFalse([line for line in log if "HANDOFF" in line], log)


if __name__ == "__main__":
    unittest.main()
