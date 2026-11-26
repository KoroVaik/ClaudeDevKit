"""The Pult watcher (plugins/pult/scripts/watch-servers.ps1) takes its own new code (WATCH-RESTART) and restarts a lead
when an extension plugin it uses changed version. Runs a copy of the pult scripts in a temp folder with a fake `claude`
on PATH (it also changes files between rounds), a stub restart-leads.ps1 and a stub program for the new watcher copy,
so no real watcher, lead or Pult process is touched. The "lead" is this test process (its pid is alive)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS = ROOT / "plugins"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")
LEAD = "L: Lead"
LEAD_SID = "11111111-aaaa-bbbb-cccc-000000000001"
OLD_TIME = 946684800  # 2000-01-01: every plugin.json is older than the "lead" process


def day(offset):
    """The local date `offset` days from today, as the watcher writes staleSince."""
    return (datetime.now() + timedelta(days=offset)).strftime("%Y-%m-%d")


def owner_said(text, minutes_ago):
    stamp = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z")
    return {"type": "user", "timestamp": stamp, "origin": {"kind": "human"}, "message": {"role": "user", "content": text}}


def lead_said(text):
    return {"type": "assistant", "message": {"role": "assistant", "model": "m", "content": [{"type": "text", "text": text}]}}

FAKE_CLAUDE = '''import json, pathlib, sys
d = pathlib.Path(__file__).parent
if sys.argv[1:2] == ["stop"]:  # restart-leads.ps1 stops the lead: it is gone from the list
    (d / "agents.json").write_text("[]")
    print("stopped")
    raise SystemExit
n =int((d / "count").read_text()) + 1 if (d / "count").exists() else 1
(d / "count").write_text(str(n))
for a in json.loads((d / "plan.json").read_text()).get(str(n), []):
    p = pathlib.Path(a["path"])
    if "append" in a:
        with open(p, "ab") as f:
            f.write(a["append"].encode())
    else:
        p.write_text(a["write"])
print((d / "agents.json").read_text())
'''

STUB_RESTART = '''param($Name, $Ready, $ConfigFile, $StateDir)
$n = (Get-Content -Raw $env:TEST_COUNT_FILE).Trim()
Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "Name=$Name Ready=$Ready call=$n"
Write-Output "Resumed lead: $($Name -join ',')"
'''


# Stands in for start-servers.ps1 when the real restart-leads.ps1 runs: the real one would start a real watcher.
STUB_START = '''param([string[]]$Restarted, [string[]]$Only, [string]$ConfigFile, [string]$StateDir)
Add-Content -LiteralPath $env:TEST_STARTS_FILE -Value "Restarted=$($Restarted -join ',')"
'''


# A restart-leads.ps1 / start-servers.ps1 that finds no hard bans on main (the real lines: see resume-lib.ps1).
STUB_RESTART_NO_BANS = '''param($Name, $Ready, $ConfigFile, $StateDir)
Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "restart $Name"
Write-Output "NO-BANS $Name (no Bash and PowerShell hard-ban deny lines on main): not restarted, it keeps running."
'''
STUB_START_NO_BANS = '''param([string[]]$Restarted, [string[]]$Only, [string]$ConfigFile, [string]$StateDir)
Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "start $($Only -join ',')"
Write-Output "NO-BANS $($Only -join ',') (no .claude/settings.json committed on main): lead not started."
'''


def plugin_json(version):
    return json.dumps({"name": "x", "version": version})


class WatcherEnv:
    """The temp folder of a test: a copy of the pult scripts, fake plugins, a fake `claude`, one lead row."""
    REAL_RESTART_LEADS = False

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.plugins = self.tmp / "plugins"
        shutil.copytree(PLUGINS / "pult" / "scripts", self.plugins / "pult" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(PLUGINS / "dev-kit" / "scripts", self.plugins / "dev-kit" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        self.scripts = self.plugins / "pult" / "scripts"
        if self.REAL_RESTART_LEADS:
            (self.scripts / "start-servers.ps1").write_text(STUB_START, encoding="ascii")
        else:
            (self.scripts / "restart-leads.ps1").write_text(STUB_RESTART, encoding="ascii")
        self.set_version("pult", "1.0.0")
        self.set_version("dev-kit", "1.0.0")
        self.set_version("web-kit", "1.0.0")
        self.project = self.tmp / "project"
        (self.project / ".claude").mkdir(parents=True)
        self.enable("web-kit@korov-dev", "dev-kit@korov-dev", "pult@korov-dev")
        self.state = self.tmp / "devkit-state"
        self.state.mkdir()
        self.projects = self.tmp / "projects"
        self.projects.mkdir()
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="ascii")
        (self.bin / "claude.cmd").write_text(f'@"{sys.executable}" "%~dp0fake_claude.py" %*\r\n', encoding="ascii")
        # The new watcher copy: records its arguments and, like the real one, logs that it entered its loop.
        (self.bin / "stub.cmd").write_text(
            '@echo %* > "%~dp0started.txt"\r\n'
            '@echo 2026-01-01T00:00:00 WATCH started (pid 99999, every 0 s) >> "%TEST_LOG_FILE%"\r\n', encoding="ascii")
        (self.bin / "dead.cmd").write_text('@echo %* > "%~dp0started.txt"\r\n@exit /b 3\r\n', encoding="ascii")
        self.calls = self.tmp / "restart-calls.txt"
        self.config = self.tmp / "servers.psd1"
        self.config.write_text("@{ Servers = @( @{ Session = '%s'; Lead = $true; Path = '%s' } ) }\n"
                               % (LEAD, self.project), encoding="utf-8-sig")
        self.agents("idle")
        self.plan({})

    def set_version(self, name, version, old=True):
        f = self.plugins / name / ".claude-plugin" / "plugin.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(plugin_json(version), encoding="ascii")
        if old:
            os.utime(f, (OLD_TIME, OLD_TIME))
        return f

    def enable(self, *names):
        (self.project / ".claude" / "settings.json").write_text(
            json.dumps({"enabledPlugins": {n: True for n in names}}), encoding="utf-8")

    def agents(self, status):
        (self.bin / "agents.json").write_text(json.dumps([
            {"pid": os.getpid(), "kind": "background", "name": LEAD, "sessionId": LEAD_SID,
             "id": "11111111", "state": "blocked", "status": status}]), encoding="utf-8")

    def plan(self, plan):
        """plan: claude call number -> list of file changes the fake claude makes before it answers."""
        (self.bin / "plan.json").write_text(json.dumps({str(k): v for k, v in plan.items()}), encoding="utf-8")

    def start_time(self):
        out = subprocess.run([POWERSHELL, "-NoProfile", "-Command",
                              f"(Get-Process -Id {os.getpid()}).StartTime.ToUniversalTime().ToString('o', "
                              "[Globalization.CultureInfo]::InvariantCulture)"],
                             check=True, capture_output=True, text=True, timeout=60)
        return out.stdout.strip()

    def env(self):
        return dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
                    DEV_KIT_PROJECTS_DIR=str(self.projects), DEV_KIT_STATE_DIR=str(self.state),
                    DEV_KIT_JOBS_DIR=str(self.tmp / "jobs"), DEV_KIT_USAGE_LOG=str(self.tmp / "usage"),
                    TEST_COUNT_FILE=str(self.bin / "count"), TEST_CALLS_FILE=str(self.calls),
                    TEST_LOG_FILE=str(self.tmp / "pult" / "logs" / "servers.log"),
                    TEST_STARTS_FILE=str(self.tmp / "starts.txt"))

    def run_watch(self, rounds, *extra, restart_exe="stub.cmd"):
        env = self.env()
        subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(self.scripts / "watch-servers.ps1"),
                        "-Rounds", str(rounds), "-IntervalSec", "0", "-ConfigFile", str(self.config),
                        "-StateDir", str(self.tmp / "pult"), "-DevKitStateDir", str(self.state),
                        "-DaemonLog", str(self.tmp / "daemon.log"), "-DevKitDir", str(self.plugins / "dev-kit"),
                        "-RestartExe", str(self.bin / restart_exe), *extra],
                       env=env, check=True, capture_output=True, timeout=240)
        return (self.tmp / "pult" / "logs" / "servers.log").read_text(encoding="utf-8-sig").splitlines()

    def lead_record(self, version, ext=None, stale_since=None):
        """A lead-versions.json entry for the 'lead' (this process); ext None: an entry from before the extension check;
        stale_since: the day the watcher first saw it stale in dev-kit."""
        entry = {"pid": os.getpid(), "started": self.start_time(), "version": version}
        if ext is not None:
            entry["ext"] = ext
        if stale_since:
            entry["staleSince"] = stale_since
        (self.tmp / "pult").mkdir(exist_ok=True)
        (self.tmp / "pult" / "lead-versions.json").write_text(json.dumps({LEAD: entry}), encoding="utf-8")

    def run_ask(self):
        """restart-leads.ps1 -Ask (the real script; its start-servers.ps1 is a stub): its output lines."""
        out = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                              str(self.scripts / "restart-leads.ps1"), "-Ask", "-ConfigFile", str(self.config),
                              "-StateDir", str(self.tmp / "pult"), "-DevKitDir", str(self.plugins / "dev-kit"),
                              "-DevKitStateDir", str(self.state)],
                             env=self.env(), check=True, capture_output=True, text=True, timeout=240)
        return out.stdout.splitlines()

    def releases(self, marks, plugin="dev-kit", clean=()):
        """plugins/<plugin>/releases.json of the temp plugin: version -> kind (dated today); the versions in `clean`
        are marked "clean": true."""
        (self.plugins / plugin / "releases.json").write_text(json.dumps(
            {v: dict({"kind": k, "date": day(0), "reason": "test"}, **({"clean": True} if v in clean else {}))
             for v, k in marks.items()}), encoding="utf-8")

    def lead_chat(self, *entries):
        """The lead's transcript in the projects folder sessions.py reads (`quiet`)."""
        folder = self.projects / "p1"
        folder.mkdir(exist_ok=True)
        (folder / f"{LEAD_SID}.jsonl").write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")

    def lead_versions(self):
        return json.loads((self.tmp / "pult" / "lead-versions.json").read_text(encoding="utf-8-sig"))[LEAD]

    def restart_file(self):
        files = list(self.state.rglob("restart.json"))
        return json.loads(files[0].read_text(encoding="utf-8")) if files else None

    def starts(self):
        f = self.tmp / "starts.txt"
        return f.read_text(encoding="utf-8").splitlines() if f.exists() else []

    def claude_calls(self):
        return int((self.bin / "count").read_text())

    def restart_calls(self):
        return self.calls.read_text(encoding="utf-8").splitlines() if self.calls.exists() else []

    def started_args(self):
        f = self.bin / "started.txt"
        for _ in range(100):  # the stub runs detached
            if f.exists() and f.read_text().strip():
                return f.read_text()
            time.sleep(0.1)
        return None

    def append_to_watcher(self, text):
        return {"path": str(self.scripts / "watch-servers.ps1"), "append": text}


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult watcher runs on Windows PowerShell")
class WatchServersRestartTest(WatcherEnv, unittest.TestCase):

    # protects: Flow
    def test_new_watcher_code_restarts_the_watcher_with_the_same_parameters(self):
        self.plan({2: [self.append_to_watcher("\r\n# a merged change\r\n")]})
        log = self.run_watch(6)
        restart = [line for line in log if " WATCH-RESTART" in line]
        self.assertEqual(1, len(restart), log)
        self.assertRegex(restart[0], r"WATCH-RESTART 1\.0\.0\+[0-9a-f]{8} -> 1\.0\.0\+[0-9a-f]{8}$")
        self.assertEqual(3, self.claude_calls(), "the old watcher must exit right after the restart (round 3)")
        args = self.started_args()
        self.assertIsNotNone(args, "the new copy was not started")
        self.assertIn("-NoProfile -ExecutionPolicy Bypass -File", args)
        for part in ("watch-servers.ps1", "-Rounds 6", "-IntervalSec 0", "-ConfigFile", "-StateDir", "-DevKitDir",
                     "-RestartExe"):
            self.assertIn(part, args)

    # protects: Flow
    def test_restart_log_names_the_pult_version_when_it_changed(self):
        pult = self.plugins / "pult" / ".claude-plugin" / "plugin.json"
        self.plan({2: [self.append_to_watcher("\r\n# change\r\n"), {"path": str(pult), "write": plugin_json("1.0.1")}]})
        log = self.run_watch(6)
        self.assertTrue(any(line.endswith(" WATCH-RESTART 1.0.0 -> 1.0.1") for line in log), log)

    # protects: Rule
    def test_a_file_that_changes_every_round_is_not_restarted_on(self):
        self.plan({n: [self.append_to_watcher(f"\r\n# change {n}\r\n")] for n in range(2, 6)})
        log = self.run_watch(5)
        self.assertFalse([line for line in log if " WATCH-RESTART" in line], log)
        self.assertEqual(5, self.claude_calls())

    # protects: Rule
    def test_broken_new_code_is_skipped_once_and_the_watcher_keeps_running(self):
        self.plan({2: [self.append_to_watcher("\r\nfunction {{{ broken (\r\n")]})
        log = self.run_watch(6)
        skipped = [line for line in log if " WATCH-RESTART-SKIPPED" in line]
        self.assertEqual(1, len(skipped), log)
        self.assertIn("watch-servers.ps1 line", skipped[0])
        self.assertFalse([line for line in log if " WATCH-RESTART " in line], log)
        self.assertEqual(6, self.claude_calls(), "the watcher must keep running")
        self.assertFalse((self.bin / "started.txt").exists())

    # protects: Flow
    def test_idle_lead_is_restarted_when_an_extension_changed_version(self):
        self.releases({"1.1.0": "critical"}, "web-kit")
        self.lead_chat(owner_said("go", 60), lead_said("Done."))
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"),
                        "write": plugin_json("1.1.0")}]})
        log = self.run_watch(3)
        self.assertEqual([f"Name={LEAD} Ready= call=2"], self.restart_calls())
        self.assertTrue(any(f"RESTART-LEAD {LEAD} (web-kit 1.0.0 -> 1.1.0, critical, quiet)" in line for line in log), log)

    # protects: Rule
    def test_lead_without_hard_bans_is_not_restarted_again_and_again_and_is_reported_once(self):
        (self.scripts / "restart-leads.ps1").write_text(STUB_RESTART_NO_BANS, encoding="ascii")
        self.releases({"1.1.0": "critical"}, "web-kit")
        self.lead_chat(owner_said("go", 60), lead_said("Done."))
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"),
                        "write": plugin_json("1.1.0")}]})
        log = self.run_watch(6)
        self.assertEqual([f"restart {LEAD}"], self.restart_calls(), "asked again only after the retry time")
        notices = [line for line in log if " NO-BANS " in line]
        self.assertEqual(1, len(notices), log)
        self.assertIn(f"NO-BANS {LEAD} (no Bash and PowerShell hard-ban deny lines on main)", notices[0])
        self.assertFalse([line for line in log if "RESTART-LEAD-FAILED" in line], log)

    # protects: Bug
    def test_no_bans_line_of_another_lead_does_not_block_a_restarted_lead(self):
        (self.scripts / "restart-leads.ps1").write_text(
            STUB_RESTART + 'Write-Output "NO-BANS L: Other (no Bash and PowerShell hard-ban deny lines on main): not restarted"\n',
            encoding="ascii")
        self.releases({"1.1.0": "critical"}, "web-kit")
        self.lead_chat(owner_said("go", 60), lead_said("Done."))
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"),
                        "write": plugin_json("1.1.0")}]})
        log = self.run_watch(4)
        self.assertEqual([f"Name={LEAD} Ready= call=2"], self.restart_calls())
        self.assertFalse([line for line in log if " NO-BANS " in line], log)
        self.assertFalse([line for line in log if "RESTART-LEAD-FAILED" in line], log)

    # protects: Rule
    def test_down_lead_without_hard_bans_is_not_healed_in_a_loop(self):
        (self.scripts / "start-servers.ps1").write_text(STUB_START_NO_BANS, encoding="ascii")
        (self.bin / "agents.json").write_text("[]", encoding="utf-8")  # the lead is down
        log = self.run_watch(8)
        self.assertEqual([f"start {LEAD}"], self.restart_calls(), "one start try, then the retry time")
        self.assertEqual(1, len([line for line in log if " NO-BANS " in line]), log)
        self.assertFalse([line for line in log if "HEAL-FAILED" in line or "GIVEUP" in line], log)

    # protects: Rule
    def test_busy_lead_is_not_woken_for_a_routine_extension_release_and_waits(self):
        self.agents("busy")
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"),
                        "write": plugin_json("1.1.0")}]})  # no mark: routine
        self.run_watch(3)
        self.assertEqual([], self.restart_calls())
        self.assertEqual([], list(self.state.rglob("restart.json")), "a request would wake the lead (a paid turn)")

    # protects: Rule
    def test_busy_lead_is_asked_for_a_critical_extension_release_like_for_a_dev_kit_one_and_restarts_when_ready(self):
        self.agents("busy")
        self.releases({"1.1.0": "critical"}, "web-kit")
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"),
                        "write": plugin_json("1.1.0")}]})
        log = self.run_watch(3)
        self.assertEqual([], self.restart_calls())
        self.assertEqual("1.0.0", self.restart_file()["version"], "the request carries the installed dev-kit version")
        asked = [line for line in log if " RESTART-ASKED " in line]
        self.assertEqual(1, len(asked), log)
        self.assertTrue(asked[0].endswith(f"RESTART-ASKED {LEAD} (web-kit 1.0.0 -> 1.1.0, critical, busy)"))
        env = dict(os.environ, DEV_KIT_STATE_DIR=str(self.state))
        subprocess.run(["python", str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                        str(self.project), "restart", "ready", "--version", "1.0.0"],
                       env=env, check=True, capture_output=True, timeout=60)  # the lead's handshake
        (self.bin / "count").unlink()
        self.plan({})
        log = self.run_watch(2, "-ReadyWarnSec", "1")
        self.assertEqual([f"Name= Ready={LEAD} call=1"], self.restart_calls())
        self.assertTrue(any(f"RESTART-LEAD {LEAD} (web-kit 1.0.0 -> 1.1.0, ready)" in line for line in log), log)

    # protects: Rule
    def test_old_lead_versions_entry_without_extensions_causes_no_restart(self):
        self.set_version("web-kit", "2.0.0", old=False)
        (self.tmp / "pult").mkdir()
        (self.tmp / "pult" / "lead-versions.json").write_text(json.dumps(
            {LEAD: {"pid": os.getpid(), "started": self.start_time(), "version": "1.0.0"}}), encoding="utf-8")
        self.run_watch(3)
        self.assertEqual([], self.restart_calls())
        saved = json.loads((self.tmp / "pult" / "lead-versions.json").read_text(encoding="utf-8-sig"))
        self.assertEqual({"web-kit": "2.0.0"}, saved[LEAD]["ext"], "the entry adopts the installed extension versions")

    # protects: Rule
    def test_ready_lead_is_restarted_whatever_the_kind_after_its_warning_time(self):
        # The lead wrote «⚠ ЧЕРЕЗ 30 СЕК ...» into its chat, then marked itself ready: the restart waits out the rest.
        self.agents("busy")
        self.set_version("dev-kit", "1.1.0", old=False)  # no releases.json: routine, still restarted when ready
        self.lead_record("1.0.0", {"web-kit": "1.0.0"})
        env = dict(os.environ, DEV_KIT_STATE_DIR=str(self.state))
        subprocess.run(["python", str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                        str(self.project), "restart", "ready", "--version", "1.1.0"],
                       env=env, check=True, capture_output=True, timeout=60)
        marked = time.time()
        log = self.run_watch(2, "-ReadyWarnSec", "6")
        self.assertEqual([f"Name= Ready={LEAD} call=1"], self.restart_calls())
        self.assertTrue(any(f"RESTART-LEAD {LEAD} (dev-kit 1.0.0 -> 1.1.0, ready)" in line for line in log), log)
        self.assertGreaterEqual(self.calls.stat().st_mtime - marked, 5.8, "restarted before the warning time ran out")

    # protects: Rule
    def test_routine_release_is_deferred_on_its_day_even_for_a_quiet_lead(self):
        self.set_version("dev-kit", "1.1.0", old=False)
        self.releases({"1.1.0": "routine"})
        self.lead_record("1.0.0", {"web-kit": "1.0.0"})
        self.lead_chat(owner_said("go", 60), lead_said("Done."))
        log = self.run_watch(3)
        self.assertEqual([], self.restart_calls())
        self.assertIsNone(self.restart_file(), "a routine release never asks the lead")
        deferred = [line for line in log if " RESTART-DEFERRED " in line]
        self.assertEqual(1, len(deferred), log)
        self.assertTrue(deferred[0].endswith(f"RESTART-DEFERRED {LEAD} (dev-kit 1.0.0 -> 1.1.0, routine, until a later day)"))
        self.assertEqual(day(0), self.lead_versions()["staleSince"])

    # protects: Flow
    def test_routine_release_restarts_a_quiet_lead_on_a_later_day(self):
        self.set_version("dev-kit", "1.1.0", old=False)
        self.releases({"1.1.0": "routine"})
        self.lead_record("1.0.0", {"web-kit": "1.0.0"}, stale_since=day(-1))
        self.lead_chat(owner_said("go", 60), lead_said("Done."))
        log = self.run_watch(2)
        self.assertEqual([f"Name={LEAD} Ready= call=1"], self.restart_calls())
        self.assertTrue(any(line.endswith(f"RESTART-LEAD {LEAD} (dev-kit 1.0.0 -> 1.1.0, quiet)") for line in log), log)

    # protects: Rule
    def test_routine_release_waits_in_silence_while_the_owner_talks_to_the_lead(self):
        self.set_version("dev-kit", "1.1.0", old=False)
        self.lead_record("1.0.0", {"web-kit": "1.0.0"}, stale_since=day(-1))  # no releases.json: routine
        self.lead_chat(owner_said("а що з тестами?", 1), lead_said("Тести зелені."))
        log = self.run_watch(2)
        self.assertEqual([], self.restart_calls())
        self.assertIsNone(self.restart_file())
        self.assertFalse([line for line in log if "RESTART-" in line], log)

    # protects: Flow
    def test_critical_release_restarts_a_quiet_idle_lead_at_once(self):
        self.set_version("dev-kit", "1.1.0", old=False)
        self.releases({"1.0.0": "critical", "1.1.0": "critical"})
        self.lead_record("1.0.0", {"web-kit": "1.0.0"})
        self.lead_chat(owner_said("go", 60), lead_said("Done."))
        log = self.run_watch(2)
        self.assertEqual([f"Name={LEAD} Ready= call=1"], self.restart_calls())
        self.assertTrue(any(line.endswith(f"RELEASE-KIND {LEAD} (dev-kit 1.0.0 -> 1.1.0): critical 1.1.0: test")
                            for line in log), log)
        self.assertTrue(any(line.endswith(f"RESTART-LEAD {LEAD} (dev-kit 1.0.0 -> 1.1.0, critical, quiet)")
                            for line in log), log)

    # protects: Rule
    def test_critical_release_asks_an_idle_lead_with_an_open_question_instead_of_restarting(self):
        self.set_version("dev-kit", "1.1.0", old=False)
        self.releases({"1.1.0": "critical"})
        self.lead_record("1.0.0", {"web-kit": "1.0.0"})
        self.lead_chat(owner_said("go", 60), lead_said("Зливаємо гілку?\nРекомендую: так - тести зелені."))
        log = self.run_watch(2)
        self.assertEqual([], self.restart_calls())
        self.assertEqual("1.1.0", self.restart_file()["version"])
        asked = [line for line in log if " RESTART-ASKED " in line]
        self.assertEqual(1, len(asked), log)
        self.assertTrue(asked[0].endswith(f"RESTART-ASKED {LEAD} (dev-kit 1.0.0 -> 1.1.0, critical, open question)"))

    def user_scope_lead(self, plugin_versions, **record):
        """rules-kit and spend-kit installed at the given versions; the lead started on 1.0.0 of them (the project
        enables neither: they are user-scope plugins every lead loads)."""
        for name, version in plugin_versions.items():
            self.set_version(name, version, old=False)
        self.lead_record("1.0.0", {"web-kit": "1.0.0", "rules-kit": "1.0.0", "spend-kit": "1.0.0"}, **record)
        self.lead_chat(owner_said("go", 60), lead_said("Done."))

    # protects: Flow
    def test_routine_rules_kit_release_is_deferred_on_its_day_and_restarts_a_quiet_lead_later(self):
        self.user_scope_lead({"rules-kit": "1.1.0", "spend-kit": "1.0.0"})  # no releases.json: routine
        log = self.run_watch(3)
        self.assertEqual([], self.restart_calls())
        deferred = [line for line in log if " RESTART-DEFERRED " in line]
        self.assertEqual(1, len(deferred), log)
        self.assertTrue(deferred[0].endswith(f"RESTART-DEFERRED {LEAD} (rules-kit 1.0.0 -> 1.1.0, routine, until a later day)"))
        self.assertIsNone(self.restart_file(), "a plugin other than dev-kit is never asked of the lead")
        self.assertEqual(day(0), self.lead_versions()["staleSince"])
        (self.bin / "count").unlink()  # a new run on a later day
        self.user_scope_lead({"rules-kit": "1.1.0", "spend-kit": "1.0.0"}, stale_since=day(-1))
        log = self.run_watch(2)
        self.assertEqual([f"Name={LEAD} Ready= call=1"], self.restart_calls())
        self.assertTrue(any(line.endswith(f"RESTART-LEAD {LEAD} (rules-kit 1.0.0 -> 1.1.0, quiet)") for line in log), log)

    # protects: Rule
    def test_critical_mark_in_the_plugins_own_releases_file_restarts_a_quiet_lead_at_once(self):
        self.user_scope_lead({"rules-kit": "1.0.0", "spend-kit": "1.0.1"})
        self.releases({"1.0.1": "critical"}, "spend-kit")  # dev-kit's file says nothing about spend-kit
        log = self.run_watch(2)
        self.assertEqual([f"Name={LEAD} Ready= call=1"], self.restart_calls())
        self.assertTrue(any(line.endswith(f"RELEASE-KIND {LEAD} (spend-kit 1.0.0 -> 1.0.1): critical 1.0.1: test")
                            for line in log), log)
        self.assertTrue(any(line.endswith(f"RESTART-LEAD {LEAD} (spend-kit 1.0.0 -> 1.0.1, critical, quiet)")
                            for line in log), log)

    # protects: Rule
    def test_user_scope_plugins_are_stored_for_a_lead_whose_project_enables_none_of_them(self):
        self.set_version("rules-kit", "0.1.0")
        self.set_version("spend-kit", "0.1.0")
        self.run_watch(2)
        self.assertEqual({"web-kit": "1.0.0", "rules-kit": "0.1.0", "spend-kit": "0.1.0"}, self.lead_versions()["ext"])

    # protects: Bug
    def test_new_copy_that_dies_at_start_keeps_the_old_watcher_running(self):
        self.plan({2: [self.append_to_watcher("\r\n# a merged change\r\n")]})
        log = self.run_watch(6, restart_exe="dead.cmd")
        skipped = [line for line in log if " WATCH-RESTART-SKIPPED" in line]
        self.assertEqual(1, len(skipped), log)
        self.assertIn("did not confirm", skipped[0])
        self.assertIn("exited", skipped[0])
        self.assertFalse([line for line in log if " WATCH-RESTART " in line], log)
        self.assertEqual(6, self.claude_calls(), "the old watcher must keep running when the new copy is dead")

    # protects: Rule
    def test_extension_that_is_off_and_the_dev_kit_and_pult_keys_are_ignored(self):
        (self.project / ".claude" / "settings.json").write_text(json.dumps({"enabledPlugins": {
            "web-kit@korov-dev": False, "dev-kit@korov-dev": True, "pult@korov-dev": True,
            "other-kit@elsewhere": True}}), encoding="utf-8")
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"), "write": plugin_json("1.1.0")},
                       {"path": str(self.plugins / "pult" / ".claude-plugin" / "plugin.json"), "write": plugin_json("1.0.1")}]})
        self.run_watch(3)
        self.assertEqual([], self.restart_calls())
        saved = json.loads((self.tmp / "pult" / "lead-versions.json").read_text(encoding="utf-8-sig"))
        self.assertEqual({}, saved[LEAD]["ext"])

    # protects: Edge
    def test_enabled_extension_with_a_missing_plugin_folder_is_ignored(self):
        self.enable("web-kit@korov-dev", "unity-kit@korov-dev")  # there is no plugins/unity-kit
        log = self.run_watch(3)
        self.assertEqual([], self.restart_calls())
        self.assertFalse([line for line in log if " WARN" in line], log)
        saved = json.loads((self.tmp / "pult" / "lead-versions.json").read_text(encoding="utf-8-sig"))
        self.assertEqual({"web-kit": "1.0.0"}, saved[LEAD]["ext"])


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult watcher runs on Windows PowerShell")
class RestartLeadsAskTest(WatcherEnv, unittest.TestCase):
    """The real restart-leads.ps1 -Ask against lead-versions.json (its start-servers.ps1 is a stub)."""
    REAL_RESTART_LEADS = True

    def setUp(self):
        super().setUp()
        # The lead's project holds hard-ban lines on main and the user accepted the bypass disclaimer: the gate of
        # resume-lib.ps1 passes (a fake user folder, so the real settings of this machine are not read).
        self.user_home = self.tmp / "user"
        (self.user_home / ".claude").mkdir(parents=True)
        (self.user_home / ".claude" / "settings.json").write_text(
            json.dumps({"skipDangerousModePermissionPrompt": True}), encoding="utf-8")
        self.commit_bans()

    def commit_bans(self, deny=("Bash(rm -rf data*)", "PowerShell(Remove-Item*data*)")):
        settings = self.project / ".claude" / "settings.json"
        before = settings.read_text(encoding="utf-8")
        settings.write_text(json.dumps({"permissions": {"deny": list(deny)}}), encoding="utf-8")
        for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
                     ["add", ".claude/settings.json"], ["commit", "-q", "-m", "bans"]):
            subprocess.run(["git", "-C", str(self.project), *args], check=True, capture_output=True)
        settings.write_text(before, encoding="utf-8")  # the working copy keeps the enabledPlugins

    def env(self):
        return dict(super().env(), USERPROFILE=str(self.user_home))

    # protects: Rule
    def test_lead_without_hard_bans_on_main_is_not_stopped(self):
        subprocess.run(["git", "-C", str(self.project), "rm", "-q", "-r", "--cached", ".claude"], check=True,
                       capture_output=True)
        subprocess.run(["git", "-C", str(self.project), "commit", "-q", "-m", "drop"], check=True,
                       capture_output=True)
        self.lead_record("0.9.0", {"web-kit": "1.0.0"})
        lines = self.run_ask()
        self.assertTrue(any(line.startswith(f"NO-BANS {LEAD} (no .claude/settings.json committed on main)")
                            for line in lines), lines)
        self.assertEqual(1, len(json.loads((self.bin / "agents.json").read_text(encoding="utf-8"))),
                         "claude stop was not called: the lead is still listed")
        self.assertEqual(["Restarted="], self.starts())

    # protects: Rule
    def test_lead_on_the_installed_versions_is_left_alone(self):
        self.lead_record("1.0.0", {"web-kit": "1.0.0"})
        self.assertIn(f"Up to date: {LEAD}", self.run_ask())
        self.assertEqual(["Restarted="], self.starts())

    # protects: Rule
    def test_old_entry_without_extensions_counts_as_up_to_date(self):
        self.lead_record("1.0.0")
        self.assertIn(f"Up to date: {LEAD}", self.run_ask())
        self.assertEqual(["Restarted="], self.starts())

    # protects: Flow
    def test_idle_lead_stale_only_in_an_extension_is_restarted(self):
        self.lead_record("1.0.0", {"web-kit": "0.9.0"})
        lines = self.run_ask()
        self.assertNotIn(f"Up to date: {LEAD}", lines)
        self.assertEqual([f"Restarted={LEAD}"], self.starts())

    # protects: Rule
    def test_lead_stale_only_in_a_user_scope_plugin_counts_like_an_extension(self):
        self.set_version("rules-kit", "0.2.0")  # no project enables it; the lead started on 0.1.0
        self.lead_record("1.0.0", {"web-kit": "1.0.0", "rules-kit": "0.1.0"})
        self.agents("busy")
        self.assertIn(f"Not asked, busy and only an extension changed: {LEAD}", self.run_ask())
        self.agents("idle")
        lines = self.run_ask()
        self.assertNotIn(f"Up to date: {LEAD}", lines)
        self.assertEqual(["Restarted=", f"Restarted={LEAD}"], self.starts())

    # protects: Rule
    def test_busy_lead_stale_only_in_an_extension_is_not_asked(self):
        self.agents("busy")
        self.lead_record("1.0.0", {"web-kit": "0.9.0"})
        lines = self.run_ask()
        self.assertIn(f"Not asked, busy and only an extension changed: {LEAD}", lines)
        self.assertEqual([], list(self.state.rglob("restart.json")), "a request would wake the lead (a paid turn)")
        self.assertEqual(["Restarted="], self.starts())

    # protects: Rule
    def test_busy_lead_stale_in_dev_kit_is_asked_as_before(self):
        self.agents("busy")
        self.lead_record("0.9.0", {"web-kit": "0.9.0"})  # both changed: dev-kit decides
        lines = self.run_ask()
        self.assertIn(f"Asked: {LEAD}", lines)
        files = list(self.state.rglob("restart.json"))
        self.assertEqual(1, len(files))
        self.assertEqual("1.0.0", json.loads(files[0].read_text(encoding="utf-8"))["version"])
        self.assertEqual(["Restarted="], self.starts())

    # protects: Rule
    def test_idle_lead_stale_in_dev_kit_is_restarted_as_before(self):
        self.lead_record("0.9.0", {"web-kit": "1.0.0"})
        self.run_ask()
        self.assertEqual([f"Restarted={LEAD}"], self.starts())

    # protects: Rule
    def test_idle_lead_behind_a_clean_release_is_asked_with_clean_and_not_restarted(self):
        # A restart would resume the old conversation, which still holds the names the release changed.
        self.releases({"1.0.0": "routine"}, clean=("1.0.0",))
        self.lead_record("0.9.0", {"web-kit": "1.0.0"})
        lines = self.run_ask()
        self.assertIn(f"Asked: {LEAD}", lines)
        self.assertEqual({"version": "1.0.0", "clean": True},
                         {k: v for k, v in self.restart_file().items() if k in ("version", "clean")})
        self.assertEqual(["Restarted="], self.starts(), "nothing was stopped or restarted")
        self.assertEqual(1, len(json.loads((self.bin / "agents.json").read_text(encoding="utf-8"))))

    # protects: Rule
    def test_lead_that_cannot_get_event_messages_is_restarted_plainly_even_behind_a_clean_release(self):
        # A lead from before the wake messages never sees the clean request: it is handled as without the mark.
        self.releases({"1.0.0": "routine"}, clean=("1.0.0",))
        self.lead_record("0.1.50", {"web-kit": "1.0.0"})
        lines = self.run_ask()
        self.assertNotIn(f"Asked: {LEAD}", lines)
        self.assertEqual([f"Restarted={LEAD}"], self.starts())
        self.assertIsNone(self.restart_file())

    # protects: Rule
    def test_busy_lead_behind_a_clean_extension_release_is_asked_with_clean(self):
        # A busy lead behind a plain extension release is not asked (a paid turn); a clean one is, as the watcher does.
        self.agents("busy")
        self.releases({"1.1.0": "routine"}, "web-kit", clean=("1.1.0",))
        self.set_version("web-kit", "1.1.0")
        self.lead_record("1.0.0", {"web-kit": "1.0.0"})
        lines = self.run_ask()
        self.assertIn(f"Asked: {LEAD}", lines)
        self.assertEqual(("1.0.0", True), (self.restart_file()["version"], self.restart_file().get("clean")))
        self.assertEqual(["Restarted="], self.starts())


if __name__ == "__main__":
    unittest.main()
