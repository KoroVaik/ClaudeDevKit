"""The Pult watcher (plugins/pult/scripts/watch-servers.ps1) does not hang on a heal or a lead restart: a HEAL
(start-servers.ps1 -Only), a HEAL-TASK (`claude respawn`) or a restart-leads.ps1 run still going after its bound
(-HealWaitSec, -LeadRestartWaitSec) is stopped with its child processes and logged, and the loop goes on. It also
removes a hold file that a crashed restart-leads.ps1 left (HOLD-STALE), and only that one.
Runs a copy of the pult scripts in a temp folder with a fake `claude` and a stub start-servers.ps1 or restart-leads.ps1,
so no real watcher, lead or Pult process is touched."""
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from datetime import datetime

from test_watch_servers_restart import LEAD, PLUGINS, POWERSHELL, WatcherEnv, lead_said, owner_said, plugin_json

# `claude agents` prints agents.json; `claude respawn <id>` records its pid and sleeps respawn_sleep seconds.
FAKE_CLAUDE = '''import json, os, pathlib, sys, time
d = pathlib.Path(__file__).parent
if sys.argv[1:2] == ["respawn"]:
    (d / "respawn_pid").write_text(str(os.getpid()))
    s = d / "respawn_sleep"
    time.sleep(float(s.read_text()) if s.exists() else 0)
    print("respawned " + sys.argv[2])
    raise SystemExit
print((d / "agents.json").read_text())
'''

# Stands in for start-servers.ps1 -Only: records its arguments and pid, then sleeps $env:TEST_HEAL_SLEEP seconds in a
# child process (a hung `claude --bg`) and says the lead was resumed.
STUB_START = '''param([string[]]$Only, [string]$ConfigFile, [string]$StateDir)
Add-Content -LiteralPath $env:TEST_STARTS_FILE -Value "Only=$($Only -join ',') pid=$PID"
$s = [int]$env:TEST_HEAL_SLEEP
if ($s -gt 0) {
    $c = Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile', '-Command', "Start-Sleep $s" -NoNewWindow -PassThru
    Add-Content -LiteralPath $env:TEST_STARTS_FILE -Value "child=$($c.Id)"
    $c.WaitForExit()
}
Write-Output "Resumed lead: $($Only -join ',')"
'''

TASK = "C: Task"
TASK_SID = "22222222-aaaa-bbbb-cccc-000000000002"


def pid_alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=60)
    return str(pid) in out.stdout


def dead_pid():
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


class WatchServersHealTest(WatcherEnv, unittest.TestCase):
    def setUp(self):
        super().setUp()
        (self.scripts / "start-servers.ps1").write_text(STUB_START, encoding="ascii")
        (self.bin / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="ascii")
        (self.bin / "agents.json").write_text("[]", encoding="utf-8")  # the lead is down
        self.heal_sleep = 0

    def env(self):
        return dict(super().env(), TEST_HEAL_SLEEP=str(self.heal_sleep))

    def run_rounds(self, rounds, heal_wait=3):
        t = time.monotonic()
        log = self.run_watch(rounds, "-HealWaitSec", str(heal_wait))
        return log, time.monotonic() - t

    def stub_lines(self):
        return self.starts()

    def hold(self):
        return self.tmp / "pult" / "hold"

    def write_hold(self, text):
        self.hold().parent.mkdir(parents=True, exist_ok=True)
        self.hold().write_text(text, encoding="utf-8")

    def test_hung_heal_is_stopped_logged_and_the_loop_goes_on(self):
        self.heal_sleep = 120
        log, took = self.run_rounds(4)
        timeouts = [l for l in log if " HEAL-TIMEOUT " in l]
        self.assertEqual(2, len(timeouts), log)  # rounds 2 and 4: the loop went on after the first one
        self.assertIn(LEAD, timeouts[0])
        self.assertLess(took, 100)
        self.assertEqual(2, len([l for l in log if " HEAL " in l]), log)
        self.assertFalse([l for l in log if "HEAL-FAILED" in l], log)
        lines = self.stub_lines()
        pids = [int(l.split("pid=")[1]) for l in lines if l.startswith("Only=")]
        children = [int(l.split("=")[1]) for l in lines if l.startswith("child=")]
        self.assertEqual(2, len(pids), lines)
        for pid in pids + children:  # the run and its child are stopped
            self.assertFalse(pid_alive(pid), pid)

    def test_heal_that_ends_in_time_passes_the_lead_name_and_is_not_a_failure(self):
        log, _ = self.run_rounds(2, heal_wait=60)
        self.assertEqual(1, len([l for l in log if " HEAL " in l]), log)
        self.assertFalse([l for l in log if "HEAL-TIMEOUT" in l or "HEAL-FAILED" in l], log)
        self.assertTrue(self.stub_lines()[0].startswith(f"Only={LEAD} pid="), self.stub_lines())

    def task_closed(self):
        """An active task session of a project that the session list shows closed (no pid)."""
        folder = self.state / "proj-1"
        folder.mkdir(exist_ok=True)
        (folder / "sessions.json").write_text(json.dumps([{"id": TASK_SID, "name": TASK, "status": "active"}]),
                                              encoding="utf-8")
        (self.bin / "agents.json").write_text(json.dumps([
            {"pid": os.getpid(), "kind": "background", "name": LEAD, "sessionId": "11111111-aaaa-bbbb-cccc-000000000001",
             "id": "11111111", "state": "blocked", "status": "idle"},
            {"kind": "background", "name": TASK, "sessionId": TASK_SID, "id": "22222222", "state": "closed"}]),
            encoding="utf-8")

    def test_hung_task_respawn_is_stopped_and_logged(self):
        self.task_closed()
        (self.bin / "respawn_sleep").write_text("120")
        log, took = self.run_rounds(2)
        self.assertEqual(1, len([l for l in log if " HEAL-TASK " in l]), log)
        timeouts = [l for l in log if "HEAL-TASK-TIMEOUT" in l]
        self.assertEqual(1, len(timeouts), log)
        self.assertIn("22222222", timeouts[0])
        self.assertLess(took, 60)
        self.assertFalse(pid_alive(int((self.bin / "respawn_pid").read_text())))

    def test_task_respawn_in_time_is_not_a_failure(self):
        self.task_closed()
        log, _ = self.run_rounds(2)
        self.assertEqual(1, len([l for l in log if " HEAL-TASK " in l]), log)
        self.assertFalse([l for l in log if "HEAL-TASK-TIMEOUT" in l or "HEAL-TASK-FAILED" in l], log)

    def test_hold_of_a_crashed_restart_leads_run_is_removed(self):
        text = f"restart-leads.ps1 {datetime.now():%Y-%m-%dT%H:%M:%S} pid {dead_pid()}"
        self.write_hold(text)
        log, _ = self.run_rounds(1)
        self.assertFalse(self.hold().exists())
        self.assertEqual(1, len([l for l in log if f"HOLD-STALE ({text})" in l]), log)
        self.assertFalse([l for l in log if "HOLD on" in l], log)

    def test_hold_whose_pid_is_now_another_process_is_removed(self):
        self.write_hold(f"restart-leads.ps1 2000-01-01T00:00:00 pid {os.getpid()}")
        log, _ = self.run_rounds(1)
        self.assertFalse(self.hold().exists())
        self.assertTrue([l for l in log if "HOLD-STALE" in l], log)

    def test_hold_of_a_running_restart_leads_run_stays(self):
        self.write_hold(f"restart-leads.ps1 {datetime.now():%Y-%m-%dT%H:%M:%S} pid {os.getpid()}")
        log, _ = self.run_rounds(2)
        self.assertTrue(self.hold().exists())
        self.assertTrue([l for l in log if "HOLD on" in l], log)
        self.assertFalse([l for l in log if "HOLD-STALE" in l or " HEAL " in l], log)

    def test_hold_of_stop_servers_and_one_with_no_pid_stay(self):
        for text in ("stop-servers.ps1 2000-01-01T00:00:00", "restart-leads.ps1 2000-01-01T00:00:00"):
            with self.subTest(text=text):
                self.write_hold(text)
                log, _ = self.run_rounds(1)
                self.assertTrue(self.hold().exists())
                self.assertFalse([l for l in log if "HOLD-STALE" in l], log)

    def test_once_leaves_a_stale_hold(self):
        self.write_hold(f"restart-leads.ps1 2000-01-01T00:00:00 pid {dead_pid()}")
        subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(self.scripts / "watch-servers.ps1"), "-Once", "-ConfigFile", str(self.config),
                        "-StateDir", str(self.tmp / "pult"), "-DevKitStateDir", str(self.state),
                        "-DaemonLog", str(self.tmp / "daemon.log"), "-DevKitDir", str(self.plugins / "dev-kit")],
                       env=self.env(), check=True, capture_output=True, timeout=240)
        self.assertTrue(self.hold().exists())

    def test_restart_leads_names_its_pid_in_the_hold(self):
        shutil.copy(PLUGINS / "pult" / "scripts" / "restart-leads.ps1", self.scripts / "restart-leads.ps1")
        (self.scripts / "start-servers.ps1").write_text("param()\n", encoding="ascii")  # leaves the hold in place
        subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(self.scripts / "restart-leads.ps1"), "-Name", LEAD, "-ConfigFile", str(self.config),
                        "-StateDir", str(self.tmp / "pult")],
                       env=self.env(), capture_output=True, timeout=240)
        text = self.hold().read_text(encoding="utf-8-sig").strip()
        self.assertRegex(text, r"^restart-leads\.ps1 \d{4}-\d\d-\d\dT\d\d:\d\d:\d\d pid \d+$")


# Stands in for restart-leads.ps1: writes the hold with its pid as the real one does, records its pid, then sleeps
# $env:TEST_RESTART_SLEEP seconds in a child process (a hung `claude stop` or start) and says the lead was resumed.
STUB_RESTART_HANG = '''param($Name, $Ready, $ConfigFile, $StateDir)
New-Item -ItemType Directory -Force $StateDir | Out-Null
Set-Content -LiteralPath (Join-Path $StateDir 'hold') -Encoding UTF8 -Value "restart-leads.ps1 $(Get-Date -Format s) pid $PID"
Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "Name=$Name pid=$PID"
$s = [int]$env:TEST_RESTART_SLEEP
if ($s -gt 0) {
    $c = Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile', '-Command', "Start-Sleep $s" -NoNewWindow -PassThru
    Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "child=$($c.Id)"
    $c.WaitForExit()
}
Remove-Item -LiteralPath (Join-Path $StateDir 'hold') -Force
Write-Output "Resumed lead: $($Name -join ',')"
'''


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult watcher runs on Windows PowerShell")
class WatchServersRestartTimeoutTest(WatcherEnv, unittest.TestCase):
    """An idle lead stale in an extension (web-kit 1.0.0 -> 1.1.0, a critical release, in round 2) is restarted through
    the stub."""

    def setUp(self):
        super().setUp()
        (self.scripts / "restart-leads.ps1").write_text(STUB_RESTART_HANG, encoding="ascii")
        self.releases({"1.1.0": "critical"}, "web-kit")
        self.lead_chat(owner_said("go", 60), lead_said("Done."))  # a quiet lead: a critical release restarts it at once
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"),
                        "write": plugin_json("1.1.0")}]})
        self.restart_sleep = 0

    def env(self):
        return dict(super().env(), TEST_RESTART_SLEEP=str(self.restart_sleep))

    def hold(self):
        return self.tmp / "pult" / "hold"

    # protects: Bug
    def test_hung_restart_is_stopped_its_hold_removed_and_the_loop_goes_on(self):
        self.restart_sleep = 120
        t = time.monotonic()
        log = self.run_watch(4, "-LeadRestartWaitSec", "3")
        took = time.monotonic() - t
        self.assertLess(took, 100)
        self.assertEqual(4, self.claude_calls(), "the watcher must go on with its rounds")
        timeouts = [l for l in log if " RESTART-LEAD-TIMEOUT " in l]
        self.assertEqual(1, len(timeouts), log)  # a failed restart is not tried again on the same versions
        self.assertIn(f"RESTART-LEAD-TIMEOUT {LEAD} (no end in 3 s, stopped)", timeouts[0])
        self.assertFalse(self.hold().exists())
        self.assertEqual(1, len([l for l in log if " HOLD-STALE " in l]), log)
        self.assertFalse([l for l in log if "RESTART-LEAD-FAILED" in l], log)
        calls = self.restart_calls()
        pids = [int(l.split("pid=")[1]) for l in calls if l.startswith("Name=")]
        children = [int(l.split("=")[1]) for l in calls if l.startswith("child=")]
        self.assertEqual(1, len(pids), calls)
        self.assertTrue(calls[0].startswith(f"Name={LEAD} pid="), calls)
        for pid in pids + children:  # the run and its child are stopped
            self.assertFalse(pid_alive(pid), pid)

    # protects: Flow
    def test_restart_that_ends_in_time_is_not_a_failure(self):
        log = self.run_watch(3, "-LeadRestartWaitSec", "60")
        self.assertEqual(1, len([l for l in log if f" RESTART-LEAD {LEAD} " in l]), log)
        self.assertFalse([l for l in log if "RESTART-LEAD-TIMEOUT" in l or "RESTART-LEAD-FAILED" in l
                          or "HOLD-STALE" in l], log)
        self.assertFalse(self.hold().exists())


if __name__ == "__main__":
    unittest.main()
