import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit" / "scripts"))
import migrations  # noqa: E402

ENTRY = """## {n}. {title}

- Added: dev-kit 0.1.{n}
- What: change {n}
- How: steps {n}
- Owner choice: none
- Done when: check {n}
"""
FILE = "# dev-kit migrations\n\nIntro.\n\n" + "\n".join(ENTRY.format(n=n, title=f"Title {n}") for n in (1, 2, 3))
ROW = "| migrations applied | {} |"
TABLE = "| Setting | Value |\n|---|---|\n" + ROW + "\n"


class MigrationsTestCase(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.project = tmp / "project"
        self.project.mkdir()
        self.profile = self.project / ".claude" / "dev-kit.md"
        self.file = tmp / "migrations.md"
        self.file.write_text(FILE, encoding="utf-8")
        patch = mock.patch.object(migrations, "MIGRATIONS", self.file)
        patch.start()
        self.addCleanup(patch.stop)

    def set_profile(self, text):
        self.profile.parent.mkdir(parents=True, exist_ok=True)
        self.profile.write_bytes(text.encode("utf-8"))

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = migrations.main([*args, "--project", str(self.project)])
        return code, out.getvalue(), err.getvalue()


class PendingTests(MigrationsTestCase):
    def test_no_profile_lists_every_entry_and_the_file(self):
        # Flow: a project that never applied anything sees all entries, titles only, and where to read them
        code, out, _ = self.run_cli("pending")
        self.assertEqual(0, code)
        self.assertEqual(["1. Title 1", "2. Title 2", "3. Title 3", f"file: {self.file.resolve()}"], out.splitlines())

    def test_applied_level_hides_done_entries(self):
        self.set_profile("## project-lead\n\n" + TABLE.format(2))
        _, out, _ = self.run_cli("pending")
        self.assertEqual(["3. Title 3", f"file: {self.file.resolve()}"], out.splitlines())

    def test_all_applied_prints_none(self):
        self.set_profile("## project-lead\n\n" + TABLE.format(3))
        self.assertEqual((0, "none\n", ""), self.run_cli("pending"))

    def test_profile_without_the_section_or_row_counts_as_zero(self):
        # Edge: a real profile that has other sections but no level yet; a row in another section is not the level
        self.set_profile("## coder\n\n" + TABLE.format(3) + "\n## project-lead\n\n| Path | How |\n|---|---|\n| a | link |\n")
        _, out, _ = self.run_cli("pending")
        self.assertEqual("1. Title 1", out.splitlines()[0])
        self.set_profile("## coder\n\n" + TABLE.format(3))
        self.assertEqual("1. Title 1", self.run_cli("pending")[1].splitlines()[0])

    def test_non_integer_level_fails(self):
        self.set_profile("## project-lead\n\n" + TABLE.format("two"))
        code, _, err = self.run_cli("pending")
        self.assertEqual(2, code)
        self.assertIn("not a whole number", err)

    def test_malformed_migrations_file_fails(self):
        self.file.write_text(FILE.replace("- How: steps 2\n", ""), encoding="utf-8")
        code, _, err = self.run_cli("pending")
        self.assertEqual(2, code)
        self.assertIn("entry 2: the field 'How' is missing", err)

    def test_entry_numbers_out_of_order_fail(self):
        self.file.write_text(FILE.replace("## 2.", "## 5."), encoding="utf-8")
        self.assertIn("entry 5 where 2 is expected", self.run_cli("pending")[2])

    def test_entry_without_a_title_fails(self):
        with self.assertRaisesRegex(migrations.Problem, "entry 1 has no title"):
            migrations.parse(FILE.replace("## 1. Title 1", "## 1."))

    def test_field_text_may_continue_on_the_next_lines(self):
        self.file.write_text(FILE.replace("- How: steps 1\n", "- How: steps 1\n  more steps\n"), encoding="utf-8")
        self.assertEqual("more steps", migrations.parse(self.file.read_text(encoding="utf-8"))[0][2]["How"].split("\n")[1])


class RecordTests(MigrationsTestCase):
    def test_creates_the_profile_with_section_and_table(self):
        # Flow: the first record in a project with no profile
        code, _, _ = self.run_cli("record", "2")
        self.assertEqual(0, code)
        self.assertEqual("# dev-kit profile\n\n## project-lead\n\n" + TABLE.format(2), self.profile.read_text(encoding="utf-8"))
        self.assertEqual("3. Title 3", self.run_cli("pending")[1].splitlines()[0])

    def test_appends_the_section_to_an_existing_profile(self):
        before = "## All agents\n\nRead the docs.\n"
        self.set_profile(before)
        self.run_cli("record", "1")
        self.assertEqual(before + "\n## project-lead\n\n" + TABLE.format(1), self.profile.read_text(encoding="utf-8"))

    def test_puts_the_table_before_an_existing_worktree_table(self):
        # Flow: a real project-lead section already holds the | Path | How | table
        head = "## All agents\n\nRules.\n\n## project-lead\n\n"
        tail = "| Path | How |\n|---|---|\n| `data/` | link |\n\n## coder\n\nCode.\n"
        self.set_profile(head + tail)
        self.run_cli("record", "1")
        self.assertEqual(head + TABLE.format(1) + "\n" + tail, self.profile.read_text(encoding="utf-8"))

    def test_updates_the_row_and_keeps_all_other_bytes(self):
        before = migrations.BOM + "## project-lead\r\n\r\nText.\r\n\r\n" + TABLE.format(1).replace("\n", "\r\n") + "\r\n## coder\r\n\r\nX"
        self.set_profile(before)
        self.run_cli("record", "3")
        self.assertEqual(before.replace(ROW.format(1), ROW.format(3)), self.profile.read_bytes().decode("utf-8"))

    def test_adds_the_row_to_a_settings_table_without_it(self):
        self.set_profile("## project-lead\n\n| Setting | Value |\n|---|---|\n| other | x |\n\nTail.\n")
        self.run_cli("record", "1")
        self.assertEqual("## project-lead\n\n| Setting | Value |\n|---|---|\n| other | x |\n" + ROW.format(1) + "\n\nTail.\n",
                         self.profile.read_text(encoding="utf-8"))

    def test_section_inside_a_code_fence_is_ignored(self):
        fenced = "```\n## project-lead\n\n" + TABLE.format(3) + "```\n"
        self.set_profile(fenced)
        self.run_cli("record", "1")
        self.assertEqual(fenced + "\n## project-lead\n\n" + TABLE.format(1), self.profile.read_text(encoding="utf-8"))

    def test_same_value_is_accepted_and_changes_nothing(self):
        text = "## project-lead\n\n" + TABLE.format(2)
        self.set_profile(text)
        self.assertEqual(0, self.run_cli("record", "2")[0])
        self.assertEqual(text, self.profile.read_text(encoding="utf-8"))

    def test_refuses_a_lower_value(self):
        # Rule: the level never goes back
        text = "## project-lead\n\n" + TABLE.format(2)
        self.set_profile(text)
        code, _, err = self.run_cli("record", "1")
        self.assertEqual(2, code)
        self.assertIn("below the applied level 2", err)
        self.assertEqual(text, self.profile.read_text(encoding="utf-8"))

    def test_refuses_a_value_above_the_last_entry(self):
        # Rule: a level can not claim entries that do not exist
        code, _, err = self.run_cli("record", "4")
        self.assertEqual(2, code)
        self.assertIn("above the last entry 3", err)
        self.assertFalse(self.profile.exists())


if __name__ == "__main__":
    unittest.main()
