import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "pult" / "hooks" / "owner-scripts.py"


class OwnerScriptsTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.home = tmp / "home"
        self.folder = self.home / "Desktop" / "Claude"
        self.folder.mkdir(parents=True)
        self.ledger = self.home / ".claude" / "pult" / "owner-scripts.json"
        # The hook finds the desktop and its ledger under the user's home folder; point that at the temp folder.
        self.env = {**os.environ, "USERPROFILE": str(self.home), "HOME": str(self.home)}

    def run_hook(self, mode, payload):
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), mode], input=data, capture_output=True, env=self.env)
        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", "replace"))
        return result.stdout.decode("utf-8")

    def write(self, path, text="@echo off\r\npause\r\n"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.run_hook("post", {"tool_name": "Write", "tool_input": {"file_path": str(path)}, "cwd": "C:/proj"})

    def age(self, days):
        data = json.loads(self.ledger.read_text(encoding="utf-8"))
        for entry in data.values():
            entry["written"] = time.time() - days * 86400
        self.ledger.write_text(json.dumps(data), encoding="utf-8")

    def test_left_script_is_deleted_a_day_later(self):  # Flow
        script = self.folder / "allow push.cmd"
        self.write(script)
        self.run_hook("start", {})
        self.assertTrue(script.is_file(), "a fresh file stays")
        self.age(1.1)
        self.run_hook("start", {})
        self.assertFalse(script.is_file())
        self.assertEqual({}, json.loads(self.ledger.read_text(encoding="utf-8")))

    def test_owner_file_is_never_deleted(self):  # Flow
        own = self.folder / "mine.cmd"
        own.write_text("@echo mine", encoding="utf-8")
        script = self.folder / "agent.cmd"
        self.write(script)
        self.age(2)
        self.run_hook("start", {})
        self.assertTrue(own.is_file())
        self.assertFalse(script.is_file())

    def test_changed_script_counts_as_the_owners(self):  # Edge
        script = self.folder / "agent.cmd"
        self.write(script)
        self.age(2)
        script.write_text("@echo changed by the owner", encoding="utf-8")
        self.run_hook("start", {})
        self.assertTrue(script.is_file())

    def test_script_elsewhere_on_desktop_is_refused(self):  # Flow
        out = self.run_hook("pre", {"tool_name": "Write",
                                    "tool_input": {"file_path": str(self.home / "Desktop" / "x.cmd")}})
        decision = json.loads(out)["hookSpecificOutput"]
        self.assertEqual("deny", decision["permissionDecision"])
        self.assertIn("Claude", decision["permissionDecisionReason"])

    def test_script_in_folder_or_repo_passes(self):  # Edge
        for path in (self.folder / "x.cmd", self.home / "repos" / "p" / "build.cmd", self.home / "Desktop" / "notes.txt"):
            self.assertEqual("", self.run_hook("pre", {"tool_name": "Write", "tool_input": {"file_path": str(path)}}))

    def test_bad_input_is_silent(self):  # Edge
        for mode in ("pre", "post", "start"):
            self.assertEqual("", self.run_hook(mode, b"not json"))


if __name__ == "__main__":
    unittest.main()
