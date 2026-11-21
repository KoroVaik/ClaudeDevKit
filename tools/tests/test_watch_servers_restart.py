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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS = ROOT / "plugins"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")
LEAD = "P: Lead"
OLD_TIME = 946684800  # 2000-01-01: every plugin.json is older than the "lead" process

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
            {"pid": os.getpid(), "kind": "background", "name": LEAD, "sessionId": "11111111-aaaa-bbbb-cccc-000000000001",
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
                    TEST_COUNT_FILE=str(self.bin / "count"), TEST_CALLS_FILE=str(self.calls),
                    TEST_LOG_FILE=str(self.tmp / "pult" / "logs" / "servers.log"),
                    TEST_STARTS_FILE=str(self.tmp / "starts.txt"))

    def run_watch(self, rounds, restart_exe="stub.cmd"):
        env = self.env()
        subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(self.scripts / "watch-servers.ps1"),
                        "-Rounds", str(rounds), "-IntervalSec", "0", "-ConfigFile", str(self.config),
                        "-StateDir", str(self.tmp / "pult"), "-DevKitStateDir", str(self.state),
                        "-DaemonLog", str(self.tmp / "daemon.log"), "-DevKitDir", str(self.plugins / "dev-kit"),
                        "-RestartExe", str(self.bin / restart_exe)],
                       env=env, check=True, capture_output=True, timeout=240)
        return (self.tmp / "pult" / "logs" / "servers.log").read_text(encoding="utf-8-sig").splitlines()

    def lead_record(self, version, ext=None):
        """A lead-versions.json entry for the 'lead' (this process); ext None: an entry from before the extension check."""
        entry = {"pid": os.getpid(), "started": self.start_time(), "version": version}
        if ext is not None:
            entry["ext"] = ext
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
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"),
                        "write": plugin_json("1.1.0")}]})
        log = self.run_watch(3)
        self.assertEqual([f"Name={LEAD} Ready= call=2"], self.restart_calls())
        self.assertTrue(any(f"RESTART-LEAD {LEAD} (web-kit 1.0.0 -> 1.1.0, idle)" in line for line in log), log)

    # protects: Rule
    def test_lead_without_hard_bans_is_not_restarted_again_and_again_and_is_reported_once(self):
        (self.scripts / "restart-leads.ps1").write_text(STUB_RESTART_NO_BANS, encoding="ascii")
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
            STUB_RESTART + 'Write-Output "NO-BANS P: Other (no Bash and PowerShell hard-ban deny lines on main): not restarted"\n',
            encoding="ascii")
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
    def test_busy_lead_is_not_woken_for_an_extension_and_restarts_when_idle(self):
        self.agents("busy")
        self.plan({2: [{"path": str(self.plugins / "web-kit" / ".claude-plugin" / "plugin.json"),
                        "write": plugin_json("1.1.0")}]})
        self.run_watch(3)
        self.assertEqual([], self.restart_calls())
        self.assertEqual([], list(self.state.rglob("restart.json")), "a request would wake the lead (a paid turn)")
        (self.bin / "count").unlink()  # a new run: the lead goes idle in its round 3
        idle = (self.bin / "agents.json").read_text().replace("busy", "idle")
        self.plan({3: [{"path": str(self.bin / "agents.json"), "write": idle}]})
        self.run_watch(4)
        self.assertEqual([f"Name={LEAD} Ready= call=3"], self.restart_calls())

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
    def test_dev_kit_handshake_is_unchanged_for_a_busy_lead(self):
        self.agents("busy")
        self.set_version("dev-kit", "1.1.0", old=False)
        (self.tmp / "pult").mkdir()
        (self.tmp / "pult" / "lead-versions.json").write_text(json.dumps(
            {LEAD: {"pid": os.getpid(), "started": self.start_time(), "version": "1.0.0", "ext": {"web-kit": "1.0.0"}}}),
            encoding="utf-8")
        env = dict(os.environ, DEV_KIT_STATE_DIR=str(self.state))
        subprocess.run(["python", str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                        str(self.project), "restart", "ready", "--version", "1.1.0"],
                       env=env, check=True, capture_output=True, timeout=60)
        log = self.run_watch(2)
        self.assertEqual([f"Name= Ready={LEAD} call=1"], self.restart_calls())
        self.assertTrue(any(f"RESTART-LEAD {LEAD} (dev-kit 1.0.0 -> 1.1.0, ready)" in line for line in log), log)

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


if __name__ == "__main__":
    unittest.main()
