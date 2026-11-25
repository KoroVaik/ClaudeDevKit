"""Every session the plugin starts runs in bypassPermissions, with no fallback (plugins/pult/scripts/resume-lib.ps1):
a lead starts only when the settings committed on main hold Bash and PowerShell hard-ban deny lines and the bypass
disclaimer is accepted; otherwise the gate says "do not start" with a reason, never `auto`. The mode goes into a
fresh start and into the saved options of a resumed lead. Dot-sources resume-lib.ps1 in Windows PowerShell; uses
temp git repos, starts no session."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LIB = ROOT / "plugins" / "pult" / "scripts" / "resume-lib.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")

HARD_BANS = {"permissions": {"deny": [
    "Bash(git push*main*)", "PowerShell(git push*main*)", "Edit(.claude/settings.json)"]}}
EDIT_ONLY = {"permissions": {"deny": ["Edit(.claude/settings.json)"]}}


def ps(script):
    out = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                          f". '{LIB}'; {script}"], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise AssertionError(out.stderr)
    return out.stdout.strip()


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True)


@unittest.skipUnless(POWERSHELL, "Windows PowerShell needed")
class LeadPermissionModeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "t")
        self.user = self.tmp / "user-settings.json"
        self.user.write_text(json.dumps({"skipDangerousModePermissionPrompt": True}))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit_settings(self, data):
        (self.repo / ".claude").mkdir(exist_ok=True)
        (self.repo / ".claude" / "settings.json").write_text(json.dumps(data))
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "s")

    def gate(self):
        """'<Start>|<Mode>|<Reason>' of the gate."""
        r = f"(Get-LeadPermissionMode '{self.repo}' '{self.user}')"
        return ps(f"$r = {r}; \"$($r.Start)|$($r.Mode)|$($r.Reason)\"")

    def assert_no_start(self, reason):
        start, mode, why = self.gate().split("|", 2)
        self.assertEqual(("False", ""), (start, mode), "no fallback mode: the lead is not started")
        self.assertIn(reason, why)

    # protects: Flow
    def test_bypass_with_hard_bans_on_main(self):
        self.commit_settings(HARD_BANS)
        self.assertEqual(self.gate(), "True|bypassPermissions|hard bans on main")

    # protects: Rule
    def test_no_start_without_shell_deny_lines(self):
        self.commit_settings(EDIT_ONLY)
        self.assert_no_start("no Bash and PowerShell hard-ban deny lines")

    # protects: Rule
    def test_no_start_with_other_shell_deny_lines(self):
        self.commit_settings({"permissions": {"deny": ["Bash(npm publish*)", "PowerShell(npm publish*)"]}})
        self.assert_no_start("no Bash and PowerShell hard-ban deny lines")

    # protects: Rule
    def test_bypass_with_data_bans_only(self):
        self.commit_settings({"permissions": {"deny": ["Bash(rm -rf data*)", "PowerShell(Remove-Item*data*)"]}})
        self.assertEqual(self.gate().split("|")[1], "bypassPermissions")

    # protects: Rule
    def test_no_start_when_hard_bans_only_uncommitted(self):
        self.commit_settings(EDIT_ONLY)
        (self.repo / ".claude" / "settings.json").write_text(json.dumps(HARD_BANS))
        self.assert_no_start("no Bash and PowerShell hard-ban deny lines")

    # protects: Rule
    def test_no_start_without_settings(self):
        (self.repo / "a.txt").write_text("a")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "a")
        self.assert_no_start("no .claude/settings.json committed on main")

    # protects: Rule
    def test_no_start_without_disclaimer(self):
        self.commit_settings(HARD_BANS)
        self.user.write_text("{}")
        self.assert_no_start("bypass disclaimer not accepted")

    # protects: Flow
    def test_fresh_start_is_always_bypass(self):
        out = ps("(Get-LeadStartArgs 'L: X' $null) -join ' '")
        self.assertIn("--permission-mode bypassPermissions", out)
        self.assertNotIn("auto", out)

    # protects: Rule
    def test_handoff_start_is_fresh_even_with_a_session_id_and_names_the_file(self):
        # A resume would bring back the full conversation: the handoff lead must start empty and read the file.
        out = ps("(Get-LeadStartArgs 'L: X' 'old-session-id' -Handoff 'handoff-2.md') -join ' '")
        self.assertNotIn("--resume", out)
        self.assertIn("--remote-control L: X --name L: X --permission-mode bypassPermissions", out)
        self.assertTrue(out.endswith("-- /dev-kit:project-lead handoff: handoff-2.md"), out)
        self.assertNotIn('"', out)
        plain = ps("(Get-LeadStartArgs 'L: X' 'old-session-id') -join ' '")
        self.assertIn("--resume old-session-id", plain)  # without -Handoff nothing changes

    # protects: Rule
    def test_handoff_name_with_a_path_or_a_quote_is_refused(self):
        # The name goes into a command line (no double quote survives Windows PowerShell 5.1).
        for bad in ("..\\x.md", "a b.md", 'a"b.md', "x.txt", "a;b.md"):
            got = ps(f"try {{ Get-LeadStartArgs 'L: X' $null -Handoff '{bad.replace(chr(39), chr(39) * 2)}' | Out-Null; 'ok' }} "
                     "catch { 'threw' }")
            self.assertEqual("threw", got, bad)

    # protects: Flow
    def test_resume_rewrites_saved_mode(self):
        job = self.tmp / "jobs" / "abc"
        job.mkdir(parents=True)
        state = job / "state.json"
        state.write_text(json.dumps({"name": "L: X", "sessionId": "s1", "respawnFlags": [
            "--remote-control", "L: X", "--permission-mode", "auto", "--model", "sonnet"]}))
        ps(f"Set-LeadRespawnModel 'L: X' 's1' '{self.tmp / 'jobs'}' | Out-Null")
        flags = json.loads(state.read_text())["respawnFlags"]
        self.assertEqual(flags, ["--remote-control", "L: X", "--model", "opus", "--effort", "medium",
                                 "--permission-mode", "bypassPermissions"])


if __name__ == "__main__":
    unittest.main()
