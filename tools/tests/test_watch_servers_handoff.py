"""The Pult watcher (plugins/pult/scripts/watch-servers.ps1, Invoke-HandoffCheck) moves a lead that left a handoff marker
(`sessions.py handoff save`) to a fresh context: it stops the old one and runs start-servers.ps1 -Handoff <file>
-HandoffSessionId <id> (which moves it within the same session, or starts a fresh lead when that fails). Runs the
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
from test_watch_servers_restart import LEAD, POWERSHELL, WatcherEnv, day, owner_said  # noqa: E402


def pid_alive(pid):
    out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, timeout=60)
    return str(pid) in out.stdout


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
STUB_START = '''param([string[]]$Restarted, [string[]]$Only, [string]$ConfigFile, [string]$StateDir, [string]$Handoff,
    [string]$HandoffSessionId, [int]$HandoffClearWaitSec, [int]$HandoffStopWaitSec)
Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "start Only=$($Only -join ',') Handoff=$Handoff Session=$HandoffSessionId"
$s = [int]$env:TEST_HANDOFF_SLEEP
if ($Handoff -and $s -gt 0) {  # a hung move: its child (a /clear or resume that never ends) keeps it going
    $c = Start-Process -FilePath powershell.exe -ArgumentList '-NoProfile', '-Command', "Start-Sleep $s" -NoNewWindow -PassThru
    Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "pid=$PID child=$($c.Id)"
    $c.WaitForExit()
}
if ($env:TEST_START_OUTPUT -notlike 'Started lead*') {  # a failed start, or the same session resumed: live again
    Copy-Item -LiteralPath (Join-Path $env:TEST_BIN 'agents.bak') -Destination (Join-Path $env:TEST_BIN 'agents.json') -Force
}
Write-Output ($env:TEST_START_OUTPUT -replace '\\{name\\}', ($Only -join ','))
'''


# Stands in for restart-leads.ps1 (a plain restart of a lead that left no handoff): records the call.
STUB_PLAIN_RESTART = '''param($Name, $Ready, $ConfigFile, $StateDir)
Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "restart Name=$Name Ready=$Ready"
Write-Output "Resumed lead: $($Name -join ',')"
'''


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult watcher runs on Windows PowerShell")
class WatchServersHandoffTest(WatcherEnv, unittest.TestCase):
    def setUp(self):
        super().setUp()
        (self.scripts / "restart-leads.ps1").unlink()
        (self.scripts / "start-servers.ps1").write_text(STUB_START, encoding="ascii")
        (self.bin / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="ascii")
        self.start_output = "Started lead: {name}"
        self.handoff_sleep = 0
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
                    TEST_START_OUTPUT=self.start_output, TEST_HANDOFF_SLEEP=str(self.handoff_sleep))

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

    def owner_wrote(self, minutes_ago):
        self.transcript.write_text(json.dumps(owner_said("still here", minutes_ago)) + "\n", encoding="utf-8")

    # protects: Flow
    def test_saved_handoff_of_a_quiet_lead_moves_it_within_the_same_session(self):
        # No new session, so no phone push (plans/push-noise.md); start-servers.ps1 does the /clear move.
        self.start_output = "Resumed lead: {name}"
        (self.tmp / "pult").mkdir(exist_ok=True)
        (self.tmp / "pult" / "wake-state.json").write_text(
            json.dumps({"PultNote": True, "SizePushed": {SID: 700000}}), encoding="utf-8")
        self.handoff("save", "--file", FILE)
        log = self.run_watch(2)
        self.assertEqual(["11111111"], self.stops())
        self.assertEqual([f"start Only={LEAD} Handoff={FILE} Session={SID}"], self.starts())
        self.assertFalse(self.marker_left(), "the marker is cleared once the lead was moved")
        moved = [line for line in log if " HANDOFF" in line]
        self.assertEqual(1, len(moved), log)
        self.assertTrue(moved[0].endswith(f" HANDOFF-CLEAR {LEAD} {SID} {FILE}"), moved)
        state = json.loads((self.tmp / "pult" / "wake-state.json").read_text(encoding="utf-8"))
        self.assertLess(time.time() - state["LastWake"][LEAD], 120, "the moved lead counts as just woken")
        self.assertNotIn(SID, state["SizePushed"], "the old id's size push mark is dropped")

    # protects: Bug
    def test_moved_lead_never_gets_the_old_handoff_request_again(self):
        # A request sent but not seen yet would be sent again into the fresh context, which has no handoff to move.
        self.start_output = "Resumed lead: {name}"
        (self.tmp / "pult").mkdir(exist_ok=True)
        (self.tmp / "pult" / "wake-pending.json").write_text(json.dumps([{
            "Id": "1123000000-abcd", "Target": LEAD, "Kind": "lead", "Cause": "event", "Lines": [f"handoff requested: {FILE}"],
            "Kinds": ["handoff"], "EventKeys": [f"{LEAD}|handoff|-|{FILE}"],
            "Marks": [{"Project": str(self.project), "Kind": "handoff", "Id": "", "Key": FILE}], "Tries": 1,
            "Created": time.time(), "Sent": time.time(), "FirstSent": time.time(), "SessionId": SID}]), encoding="utf-8")
        self.handoff("save", "--file", FILE)
        log = self.run_watch(1)
        self.assertTrue(any(" HANDOFF-CLEAR " in line for line in log), log)
        pending = json.loads((self.tmp / "pult" / "wake-pending.json").read_text(encoding="utf-8"))
        self.assertEqual([], [i for i in (pending if isinstance(pending, list) else [pending]) if i], pending)

    # protects: Flow
    def test_fallback_fresh_start_is_logged_as_before(self):
        self.handoff("save", "--file", FILE)
        log = self.run_watch(2)
        self.assertEqual([f"start Only={LEAD} Handoff={FILE} Session={SID}"], self.starts())
        self.assertFalse(self.marker_left())
        moved = [line for line in log if " HANDOFF" in line]
        self.assertEqual(1, len(moved), log)
        self.assertTrue(moved[0].endswith(f" HANDOFF {LEAD} {SID} {FILE}"), moved)

    # protects: Rule
    def test_saved_handoff_of_a_lead_in_a_talk_asks_it_once_and_does_not_stop_it(self):
        # The owner wrote a minute ago: no silent move; the lead is asked (it warns the owner, then runs handoff go).
        self.owner_wrote(1)
        self.handoff("save", "--file", FILE)
        log = self.run_watch(3)
        self.assertEqual([], self.stops())
        self.assertEqual([], self.starts())
        asked = [line for line in log if " HANDOFF-ASKED " in line]
        self.assertEqual(1, len(asked), log)
        self.assertTrue(asked[0].endswith(f" HANDOFF-ASKED {LEAD} {FILE} (owner active)"), asked)
        self.assertEqual(1, len([line for line in log if " HANDOFF-WAIT " in line]), log)
        self.assertTrue(any(f"WAKE {LEAD} " in line and "kinds=handoff" in line for line in log), log)
        self.assertTrue(self.marker_left())

    # protects: Rule
    def test_go_handoff_moves_a_lead_in_a_talk_once_the_warning_time_passed(self):
        self.owner_wrote(1)
        self.handoff("save", "--file", FILE)
        self.handoff("go")
        started = time.time()
        log = self.run_watch(1, "-ReadyWarnSec", "3")
        self.assertGreaterEqual(time.time() - started, 3, "the rest of the warning time is waited out")
        self.assertEqual(["11111111"], self.stops())
        self.assertEqual([f"start Only={LEAD} Handoff={FILE} Session={SID}"], self.starts())
        self.assertTrue(any(line.endswith(f" HANDOFF {LEAD} {SID} {FILE}") for line in log), log)
        self.assertFalse([line for line in log if "HANDOFF-ASKED" in line], log)

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
    def test_lead_that_was_just_sent_a_message_is_not_stopped_or_asked(self):
        # A message sent a moment ago is not handled yet: stopping would lose it.
        (self.tmp / "pult").mkdir(exist_ok=True)
        (self.tmp / "pult" / "wake-state.json").write_text(
            json.dumps({"PultNote": True, "LastWake": {LEAD: time.time() - 30}}), encoding="utf-8")
        self.handoff("save", "--file", FILE)
        log = self.run_watch(2)
        self.assertEqual([], self.stops())
        self.assertFalse([line for line in log if "HANDOFF-ASKED" in line], log)

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
        self.assertEqual([f"start Only={LEAD} Handoff={FILE} Session={SID}"], self.starts())
        self.assertTrue(self.marker_left(), "the marker stays for the owner or the lead")

    # protects: Bug
    def test_hung_move_is_stopped_reported_once_and_the_old_lead_comes_back_by_heal(self):
        # Round 1: the move hangs and is cut; rounds 2-3: the stopped lead is down, HEAL resumes it (no -Handoff);
        # round 4: it is live with its marker, which is not tried again.
        self.start_output = "Resumed lead: {name}"
        self.handoff_sleep = 120
        self.handoff("save", "--file", FILE)
        t = time.monotonic()
        log = self.run_watch(4, "-HandoffMoveWaitSec", "3")
        self.assertLess(time.monotonic() - t, 100)
        timeouts = [line for line in log if " HANDOFF-TIMEOUT " in line]
        self.assertEqual(1, len(timeouts), log)
        self.assertIn(f" HANDOFF-TIMEOUT {LEAD} (no end in 3 s, stopped)", timeouts[0])
        self.assertFalse([line for line in log if " HANDOFF-FAILED " in line or " HANDOFF-CLEAR " in line], log)
        self.assertEqual(["11111111"], self.stops(), "one try per marker")
        self.assertEqual([f"start Only={LEAD} Handoff={FILE} Session={SID}", f"start Only={LEAD} Handoff= Session="],
                         self.starts())
        self.assertEqual(1, len([line for line in log if f" HEAL {LEAD} " in line]), log)
        self.assertFalse([line for line in log if "HEAL-FAILED" in line or "HEAL-TIMEOUT" in line], log)
        self.assertTrue(self.marker_left(), "the marker stays for the owner or the lead")
        hung = [line for line in self.restart_calls() if line.startswith("pid=")][0]
        for pid in (int(w.split("=")[1]) for w in hung.split()):  # the run and its child are stopped
            self.assertFalse(pid_alive(pid), pid)

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

    def clean_release(self, kind="routine", stale_since=None):
        """dev-kit 1.1.0 installed and marked clean; the lead started on 1.0.0 (stale since `stale_since`, default: a
        day ago); a restart-leads.ps1 stub that records a plain restart."""
        (self.scripts / "restart-leads.ps1").write_text(STUB_PLAIN_RESTART, encoding="ascii")
        self.set_version("dev-kit", "1.1.0", old=False)
        self.releases({"1.1.0": kind}, clean=("1.1.0",))
        self.lead_record("1.0.0", {"web-kit": "1.0.0"}, stale_since=stale_since or day(-1))

    def plain_restarts(self):
        return [line for line in self.restart_calls() if line.startswith("restart ")]

    # protects: Flow
    def test_clean_routine_release_asks_a_quiet_lead_on_a_later_day_and_the_handoff_moves_it(self):
        self.start_output = "Resumed lead: {name}"
        self.clean_release()
        log = self.run_watch(1)
        self.assertEqual([], self.plain_restarts(), "a clean release is never a direct restart")
        saved = self.restart_file()
        self.assertEqual(("1.1.0", True), (saved["version"], saved.get("clean")))
        asked = [line for line in log if " RESTART-ASKED " in line]
        self.assertEqual(1, len(asked), log)
        self.assertTrue(asked[0].endswith(f" RESTART-ASKED {LEAD} (dev-kit 1.0.0 -> 1.1.0, routine, clean, quiet)"), asked)
        self.assertTrue(any(line.endswith(f"RELEASE-KIND {LEAD} (dev-kit 1.0.0 -> 1.1.0): routine, clean") for line in log), log)
        self.assertTrue(any(f"WAKE {LEAD} " in line and "kinds=restart" in line for line in log), log)
        # The lead answers with a handoff: the restart check waits and the handoff move does the move.
        self.handoff("save", "--file", FILE, "--go")
        log = self.run_watch(2, "-ReadyWarnSec", "1")
        self.assertEqual([], self.plain_restarts())
        self.assertEqual(["11111111"], self.stops())
        self.assertEqual([f"start Only={LEAD} Handoff={FILE} Session={SID}"], self.starts())
        self.assertTrue(any(line.endswith(f" HANDOFF-CLEAR {LEAD} {SID} {FILE}") for line in log), log)
        self.assertFalse([line for line in log if "CLEAN-FALLBACK" in line or "RESTART-LEAD" in line], log)

    # protects: Rule
    def test_clean_routine_release_waits_for_a_later_day_like_a_plain_one(self):
        self.clean_release(stale_since=day(0))
        log = self.run_watch(2)
        self.assertEqual([], self.plain_restarts())
        self.assertIsNone(self.restart_file(), "not due on the day the lead turned stale: no request")
        self.assertEqual(1, len([line for line in log if " RESTART-DEFERRED " in line]), log)

    # protects: Rule
    def test_clean_request_with_no_answer_falls_back_to_the_plain_restart(self):
        # Fallback: no handoff marker and no ready mark within the wait: the lead is restarted as for a plain release.
        self.clean_release()
        log = self.run_watch(3, "-CleanWaitSec", "0")
        self.assertEqual(1, len([line for line in log if " RESTART-ASKED " in line]), log)
        fallback = [line for line in log if " CLEAN-FALLBACK " in line]
        self.assertEqual(1, len(fallback), log)
        self.assertTrue(fallback[0].endswith(f" CLEAN-FALLBACK {LEAD} (no handoff and no ready mark in 0 s)"), fallback)
        self.assertEqual([f"restart Name={LEAD} Ready="], self.plain_restarts())
        self.assertTrue(any(line.endswith(f"RESTART-LEAD {LEAD} (dev-kit 1.0.0 -> 1.1.0, quiet)") for line in log), log)

    # protects: Rule
    def test_failed_handoff_move_of_a_clean_request_falls_back_to_the_plain_restart(self):
        # Fallback: the move failed (HANDOFF-FAILED, the marker stays): the lead is never worse off than today.
        self.clean_release()
        self.run_watch(1)
        self.start_output = "Start failed, exit 1: {name}: boom"
        self.handoff("save", "--file", FILE, "--go")
        log = self.run_watch(3, "-ReadyWarnSec", "1")
        self.assertEqual(1, len([line for line in log if " HANDOFF-FAILED " in line]), log)
        fallback = [line for line in log if " CLEAN-FALLBACK " in line]
        self.assertEqual(1, len(fallback), log)
        self.assertTrue(fallback[0].endswith(f" CLEAN-FALLBACK {LEAD} (the handoff move failed)"), fallback)
        self.assertEqual([f"restart Name={LEAD} Ready="], self.plain_restarts())

    # protects: Rule
    def test_ready_mark_of_a_clean_request_is_honoured_as_a_plain_restart(self):
        # Fallback: an old skill answers the clean request the plain way.
        self.clean_release()
        self.run_watch(1)
        subprocess.run([sys.executable, str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                        str(self.project), "restart", "ready", "--version", "1.1.0"],
                       env=dict(os.environ, DEV_KIT_STATE_DIR=str(self.state)), check=True, capture_output=True, timeout=60)
        log = self.run_watch(2, "-ReadyWarnSec", "1")
        self.assertEqual([f"restart Name= Ready={LEAD}"], self.plain_restarts())
        self.assertTrue(any(f"RESTART-LEAD {LEAD} (dev-kit 1.0.0 -> 1.1.0, ready)" in line for line in log), log)
        self.assertFalse([line for line in log if "CLEAN-FALLBACK" in line], log)

    # protects: Bug
    def test_late_handoff_marker_beside_a_ready_mark_is_moved_not_restarted_too(self):
        # The lead marks itself ready and also saves a handoff (a late answer): the move takes the pending versions
        # with it, so the version check must not restart it plainly in the same round.
        self.agents("busy")  # the move waits for an idle lead; only the version check is looked at
        self.clean_release(kind="critical")  # a busy lead is asked at once
        self.run_watch(1)
        self.assertTrue(self.restart_file().get("clean"))
        subprocess.run([sys.executable, str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                        str(self.project), "restart", "ready", "--version", "1.1.0"],
                       env=dict(os.environ, DEV_KIT_STATE_DIR=str(self.state)), check=True, capture_output=True, timeout=60)
        self.handoff("save", "--file", FILE)
        log = self.run_watch(2, "-ReadyWarnSec", "1", "-CleanWaitSec", "0")
        self.assertEqual([], self.plain_restarts(), log)
        self.assertFalse([line for line in log if "RESTART-LEAD" in line or "CLEAN-FALLBACK" in line], log)

    # protects: Bug
    def test_plain_restart_after_a_clean_fallback_drops_the_undelivered_clean_request_line(self):
        # The resumed lead would otherwise get `restart requested: V clean` and start a handoff nobody needs.
        self.clean_release()
        (self.tmp / "pult").mkdir(exist_ok=True)
        (self.tmp / "pult" / "wake-pending.json").write_text(json.dumps([{
            "Id": "1123000000-abcd", "Target": LEAD, "Kind": "lead", "Cause": "event",
            "Lines": ["restart requested: 1.1.0 clean"], "Kinds": ["restart"], "EventKeys": [f"{LEAD}|restart|-|1.1.0"],
            "Marks": [{"Project": str(self.project), "Kind": "restart", "Id": "", "Key": "1.1.0"}], "Tries": 1,
            "Created": time.time(), "Sent": time.time(), "FirstSent": time.time(), "SessionId": SID}]), encoding="utf-8")
        log = self.run_watch(3, "-CleanWaitSec", "0")
        self.assertEqual([f"restart Name={LEAD} Ready="], self.plain_restarts(), log)
        pending = json.loads((self.tmp / "pult" / "wake-pending.json").read_text(encoding="utf-8"))
        lines = [line for item in (pending if isinstance(pending, list) else [pending]) if item for line in item["Lines"]]
        self.assertEqual([], [line for line in lines if line.startswith("restart requested: ")], pending)

    # protects: Rule
    def test_restart_check_waits_while_a_clean_lead_has_a_handoff_marker(self):
        # A critical release asks a busy lead plainly, and restarts it when it marks itself ready; with a clean one the
        # lead's own handoff marker is the answer, so neither happens meanwhile.
        self.agents("busy")
        self.clean_release(kind="critical")
        self.handoff("save", "--file", FILE)
        log = self.run_watch(2)
        self.assertEqual([], self.plain_restarts())
        self.assertIsNone(self.restart_file())
        self.assertFalse([line for line in log if "RESTART-ASKED" in line or "CLEAN-FALLBACK" in line], log)


if __name__ == "__main__":
    unittest.main()
