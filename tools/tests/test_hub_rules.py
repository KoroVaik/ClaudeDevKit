import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "pult"
SCRIPT = PLUGIN / "hooks" / "hub-rules.py"


class HubRulesTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.home = tmp / "home"
        self.project = self.home / "repos" / "Proj"
        self.project.mkdir(parents=True)
        self.elsewhere = tmp / "elsewhere"
        self.elsewhere.mkdir()
        # The hook compares the cwd with the user's home folder; point that at the temp folder.
        self.env = {**os.environ, "USERPROFILE": str(self.home), "HOME": str(self.home)}

    def run_hook(self, payload):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT)], input=data, capture_output=True, env=self.env,
                                cwd=self.elsewhere)
        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", "replace"))
        return result.stdout.decode("utf-8")

    def test_home_session_gets_the_rules_with_real_paths(self):  # Flow
        data = json.loads(self.run_hook({"cwd": str(self.home)}))["hookSpecificOutput"]
        self.assertEqual("SessionStart", data["hookEventName"])
        text = data["additionalContext"]
        self.assertNotIn("{PLUGIN}", text)
        self.assertNotIn("{DEVKIT}", text)
        self.assertNotIn("{SPENDKIT}", text)
        self.assertIn(PLUGIN.resolve().as_posix() + "/scripts/servers.psd1", text)
        self.assertIn(PLUGIN.resolve().parent.as_posix() + "/dev-kit/bin/dev-kit-sessions", text)
        self.assertIn(PLUGIN.resolve().parent.as_posix() + "/spend-kit/bin/spend-kit critical", text)

    def test_rules_carry_the_plugin_version_for_the_update_check(self):  # Rule
        text = json.loads(self.run_hook({"cwd": str(self.home)}))["hookSpecificOutput"]["additionalContext"]
        version = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
        self.assertNotIn("{VERSION}", text)
        self.assertIn(f"pult {version}", text)

    def test_home_cwd_matches_ignoring_case_and_slashes(self):  # Edge
        # Windows reports the folder in any case and slash form.
        for spelled in (str(self.home).upper(), str(self.home).replace("\\", "/") + "/"):
            self.assertIn("SessionStart", self.run_hook({"cwd": spelled}), spelled)

    def test_project_folder_under_home_gets_nothing(self):  # Rule
        # Home is a prefix of every project; only the home folder itself is the hub.
        self.assertEqual("", self.run_hook({"cwd": str(self.project)}))
        self.assertEqual("", self.run_hook({"cwd": str(self.elsewhere)}))

    def test_missing_cwd_falls_back_to_the_process_folder(self):  # Edge
        self.assertEqual("", self.run_hook({"session_id": "x"}))  # the process runs in `elsewhere`

    def test_garbage_input_never_blocks(self):  # Edge
        for data in (b"not json", b"", b"[1, 2]", b'{"cwd": 5}', b"\xff\xfe"):
            self.assertEqual("", self.run_hook(data), data)


if __name__ == "__main__":
    unittest.main()
