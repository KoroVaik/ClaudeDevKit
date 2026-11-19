"""A project lead starts in the permission mode its C sessions get (plugins/pult/scripts/resume-lib.ps1):
bypassPermissions only when the settings committed on main hold Bash and PowerShell hard-ban deny lines
and the bypass disclaimer is accepted; the mode goes into a fresh start and into the saved options of a
resumed lead. Dot-sources resume-lib.ps1 in Windows PowerShell; uses temp git repos, starts no session."""
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

    def mode(self):
        return ps(f"(Get-LeadPermissionMode '{self.repo}' '{self.user}').Mode")

    def test_bypass_with_hard_bans_on_main(self):
        self.commit_settings(HARD_BANS)
        self.assertEqual(self.mode(), "bypassPermissions")

    def test_auto_without_shell_deny_lines(self):
        self.commit_settings(EDIT_ONLY)
        self.assertEqual(self.mode(), "auto")

    def test_auto_with_other_shell_deny_lines(self):
        self.commit_settings({"permissions": {"deny": ["Bash(npm publish*)", "PowerShell(npm publish*)"]}})
        self.assertEqual(self.mode(), "auto")

    def test_bypass_with_data_bans_only(self):
        self.commit_settings({"permissions": {"deny": ["Bash(rm -rf data*)", "PowerShell(Remove-Item*data*)"]}})
        self.assertEqual(self.mode(), "bypassPermissions")

    def test_auto_when_hard_bans_only_uncommitted(self):
        self.commit_settings(EDIT_ONLY)
        (self.repo / ".claude" / "settings.json").write_text(json.dumps(HARD_BANS))
        self.assertEqual(self.mode(), "auto")

    def test_auto_without_settings(self):
        (self.repo / "a.txt").write_text("a")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "a")
        self.assertEqual(self.mode(), "auto")

    def test_auto_without_disclaimer(self):
        self.commit_settings(HARD_BANS)
        self.user.write_text("{}")
        self.assertEqual(self.mode(), "auto")

    def test_fresh_start_passes_mode(self):
        out = ps("(Get-LeadStartArgs 'P: X' $null -Mode bypassPermissions) -join ' '")
        self.assertIn("--permission-mode bypassPermissions", out)

    def test_resume_rewrites_saved_mode(self):
        job = self.tmp / "jobs" / "abc"
        job.mkdir(parents=True)
        state = job / "state.json"
        state.write_text(json.dumps({"name": "P: X", "sessionId": "s1", "respawnFlags": [
            "--remote-control", "P: X", "--permission-mode", "auto", "--model", "sonnet"]}))
        ps(f"Set-LeadRespawnModel 'P: X' 's1' '{self.tmp / 'jobs'}' -Mode bypassPermissions | Out-Null")
        flags = json.loads(state.read_text())["respawnFlags"]
        self.assertEqual(flags, ["--remote-control", "P: X", "--model", "opus", "--effort", "medium",
                                 "--permission-mode", "bypassPermissions"])


if __name__ == "__main__":
    unittest.main()
