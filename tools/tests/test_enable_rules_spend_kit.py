"""tools/enable-rules-spend-kit.py: the one-time edit of the user's settings.json, on a temp file only."""
import datetime
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "enable-rules-spend-kit.py"
spec = importlib.util.spec_from_file_location("enable_rules_spend_kit", SCRIPT)
enable = importlib.util.module_from_spec(spec)
spec.loader.exec_module(enable)

START = {"enabledPlugins": {"dev-kit@korov-dev": True, "pult@korov-dev": False, "other@else": True},
         "statusLine": {"type": "command", "command": "dev-kit-statusline", "padding": 1},
         "permissions": {"allow": ["Bash(git status)"]}, "model": "opus"}


class EnableTest(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.settings = tmp / "settings.json"
        self.settings.write_text(json.dumps(START, indent=2), encoding="utf-8")

    def run_script(self, *args):
        out = io.StringIO()
        code = enable.run(self.settings, dry_run="--dry-run" in args, out=out, now=datetime.datetime(2026, 11, 24, 15, 30, 5))
        return code, out.getvalue()

    def data(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def backups(self):
        return sorted(path.name for path in self.settings.parent.glob("settings.json.bak-*"))

    # protects: Flow
    def test_it_adds_the_two_plugins_and_points_the_status_line_and_changes_nothing_else(self):
        before = self.settings.read_text(encoding="utf-8")
        code, out = self.run_script()
        data = self.data()
        self.assertEqual(code, 0)
        self.assertEqual(data["enabledPlugins"], {**START["enabledPlugins"], "spend-kit@korov-dev": True,
                                                  "rules-kit@korov-dev": True})  # nothing removed, pult stays false
        expected = f"python -X utf8 {enable.REPO.as_posix()}/plugins/spend-kit/scripts/statusline.py"
        self.assertEqual(data["statusLine"], {"type": "command", "command": expected, "padding": 1})
        self.assertEqual({key: data[key] for key in ("permissions", "model")},
                         {key: START[key] for key in ("permissions", "model")})
        self.assertIn('"spend-kit@korov-dev" set to true', out)
        self.assertIn("statusLine.command", out)
        self.assertEqual(self.backups(), ["settings.json.bak-20261124-153005"])
        self.assertEqual((self.settings.parent / self.backups()[0]).read_text(encoding="utf-8"), before)

    # protects: Rule
    def test_a_second_run_changes_nothing_and_makes_no_backup(self):
        self.run_script()
        written = self.settings.read_text(encoding="utf-8")
        code, out = self.run_script()
        self.assertEqual((code, out), (0, "nothing to change\n"))
        self.assertEqual(self.settings.read_text(encoding="utf-8"), written)
        self.assertEqual(len(self.backups()), 1)

    # protects: Rule
    def test_dry_run_prints_the_changes_and_writes_nothing(self):
        before = self.settings.read_text(encoding="utf-8")
        code, out = self.run_script("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("rules-kit@korov-dev", out)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), before)
        self.assertEqual(self.backups(), [])

    # protects: Edge
    def test_missing_sections_are_created_and_a_disabled_entry_is_enabled(self):
        self.settings.write_text(json.dumps({"enabledPlugins": {"spend-kit@korov-dev": False}}), encoding="utf-8")
        self.run_script()
        data = self.data()
        self.assertEqual(data["enabledPlugins"], {"spend-kit@korov-dev": True, "rules-kit@korov-dev": True})
        self.assertEqual(data["statusLine"]["type"], "command")
        self.settings.unlink()
        self.run_script()
        self.assertTrue(self.data()["enabledPlugins"]["rules-kit@korov-dev"])  # no file yet: created, nothing to back up
        self.assertEqual(len(self.backups()), 1)

    # protects: Rule
    def test_a_settings_file_that_is_not_json_is_left_alone(self):
        self.settings.write_text("{not json", encoding="utf-8")
        code, _ = self.run_script()
        self.assertEqual(code, 1)
        self.assertEqual(self.settings.read_text(encoding="utf-8"), "{not json")
        self.assertEqual(self.backups(), [])


if __name__ == "__main__":
    unittest.main()
