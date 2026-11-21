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
LEAD = "P: Lead"

FAKE_CLAUDE = '''import json, pathlib, sys
d = pathlib.Path(__file__).parent
if sys.argv[1:2] == ["agents"]:
    print((d / "agents.json").read_text())
    raise SystemExit
with open(d / "calls.txt", "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
print("started")
'''


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

    # protects: Rule
    def test_handoff_needs_exactly_one_only_name(self):
        for extra in (["-Handoff", "h.md"], ["-Only", f"{LEAD},P: Other", "-Handoff", "h.md"]):
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
