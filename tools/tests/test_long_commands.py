import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "dev-kit" / "hooks" / "long-commands.py"
SPEC = importlib.util.spec_from_file_location("long_commands", SCRIPT)
lc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lc)

PROFILE = """# dev-kit profile

## long commands

| Pattern | Why |
|---|---|
| `court\\.py\\s+(repair|check)-all` | the whole-store court runs for minutes |
| `npm run e2e` | |
| `([bad` | broken regex, skipped |

## documentation

| `sleep` | not in the section |
"""


class WaitTests(unittest.TestCase):
    def assertLong(self, command):
        self.assertIsNotNone(lc.reason(command, []), command)

    def assertShort(self, command):
        self.assertIsNone(lc.reason(command, []), command)

    def test_long_waits_are_refused(self):
        self.assertLong("sleep 120")
        self.assertLong("sleep 2m")
        self.assertLong("cd x && sleep 60 && cat log")
        self.assertLong("sleep 30; sleep 30")
        self.assertLong("sleep 1m 30s")
        self.assertLong("Start-Sleep 90")
        self.assertLong("Start-Sleep -Seconds 120")
        self.assertLong("Start-Sleep -s 75; Get-Content x")
        self.assertLong("Start-Sleep -Milliseconds 90000")
        self.assertLong("timeout /t 120 /nobreak")
        self.assertLong("if true; then sleep 300; fi")

    def test_short_or_unrelated_commands_pass(self):
        self.assertShort("sleep 5")
        self.assertShort("sleep 59")
        self.assertShort("Start-Sleep -Milliseconds 500")
        self.assertShort("timeout 900 python -X utf8 run.py")
        self.assertShort('echo "sleep 120"')
        self.assertShort("grep -r 'sleep 300' src")
        self.assertShort("git commit -F - <<'EOF'\nsleep 120\nEOF")
        self.assertShort("ls sleep-120.log")


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        (Path(self.dir.name) / ".claude").mkdir()
        (Path(self.dir.name) / ".claude" / "dev-kit.md").write_text(PROFILE, encoding="utf-8")
        self.patterns = lc.profile_patterns(self.dir.name)

    def tearDown(self):
        self.dir.cleanup()

    def test_section_rows_are_read_and_bad_ones_skipped(self):
        self.assertEqual(2, len(self.patterns))

    def test_listed_pattern_is_refused_with_its_reason(self):
        self.assertEqual("the whole-store court runs for minutes",
                         lc.reason("python -X utf8 tools/court.py repair-all", self.patterns))
        self.assertIn("npm run e2e", lc.reason("npm run e2e -- --headed", self.patterns))
        self.assertIsNone(lc.reason("python -X utf8 tools/court.py repair one", self.patterns))

    def test_no_profile_means_no_patterns(self):
        self.assertEqual([], lc.profile_patterns(Path(self.dir.name) / "missing"))

    def run_hook(self, tool_input):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.dir.name)
        call = {"tool_name": "Bash", "tool_input": tool_input, "cwd": self.dir.name}
        out = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT)], input=json.dumps(call).encode("utf-8"),
                             capture_output=True, env=env, check=True).stdout.decode("utf-8")
        return json.loads(out)["hookSpecificOutput"] if out else None

    def test_hook_denies_foreground_and_passes_background(self):
        denied = self.run_hook({"command": "sleep 120"})
        self.assertEqual("deny", denied["permissionDecision"])
        self.assertIn("run_in_background", denied["permissionDecisionReason"])
        self.assertIsNone(self.run_hook({"command": "sleep 120", "run_in_background": True}))
        self.assertIsNotNone(self.run_hook({"command": "python -X utf8 court.py check-all"}))
        self.assertIsNone(self.run_hook({"command": "ls"}))


if __name__ == "__main__":
    unittest.main()
