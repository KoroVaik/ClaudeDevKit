import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit" / "scripts"))
import run_app  # noqa: E402

PYTHON = sys.executable


def step(name, code=0):
    """A command that appends its name to log.txt in the project root and exits with code."""
    return f'`"{PYTHON}" -c "open(\'log.txt\', \'a\').write(\'{name} \'); raise SystemExit({code})"`'


class RunAppTestCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        self.root = Path(tmp)
        (self.root / ".claude").mkdir()

    def profile(self, rows):
        lines = ["## Slots", "", "| Slot | Skill or command |", "|---|---|"]
        lines += [f"| {slot} | {value} |" for slot, value in rows]
        (self.root / ".claude" / "dev-kit.md").write_text("\n".join(lines + ["", "## coder", "", "Rules."]) + "\n", encoding="utf-8")

    def run_main(self, action):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_app.main([action, "--project", str(self.root)])
        return code, out.getvalue() + err.getvalue()

    def log(self):
        path = self.root / "log.txt"
        return path.read_text().split() if path.exists() else []

    def test_start_runs_in_order(self):
        self.profile([("run-app", step("a")), ("run-tests", "`x`"), ("run-app", step("b"))])
        self.assertEqual(0, self.run_main("start")[0])
        self.assertEqual(["a", "b"], self.log())

    def test_stop_runs_in_reverse(self):
        self.profile([("run-app", step("a")), ("stop-app", step("x")), ("stop-app", step("y"))])
        self.assertEqual(0, self.run_main("stop")[0])
        self.assertEqual(["y", "x"], self.log())

    def test_start_stops_at_first_failure(self):
        self.profile([("run-app", step("a", 3)), ("run-app", step("b"))])
        code, output = self.run_main("start")
        self.assertEqual(1, code)
        self.assertEqual(["a"], self.log())
        self.assertIn("exit code 3", output)

    def test_stop_goes_on_after_failure(self):
        self.profile([("stop-app", step("x")), ("stop-app", step("y", 1))])
        self.assertEqual(1, self.run_main("stop")[0])
        self.assertEqual(["y", "x"], self.log())

    def test_prose_row_refuses_before_running(self):
        self.profile([("run-app", step("a")), ("run-app", "the commands in CLAUDE.md")])
        code, output = self.run_main("start")
        self.assertEqual(2, code)
        self.assertEqual([], self.log())
        self.assertIn("not one command in backticks", output)

    def test_start_without_run_app_is_not_run(self):
        self.profile([("run-tests", "`x`")])
        self.assertEqual(2, self.run_main("start")[0])

    def test_stop_without_stop_app_does_nothing(self):
        self.profile([("run-app", step("a"))])
        code, output = self.run_main("stop")
        self.assertEqual(0, code)
        self.assertIn("fills no stop-app", output)
        self.assertEqual([], self.log())

    def test_list_shows_both_lists(self):
        self.profile([("run-app", "`one`"), ("run-app", "a skill"), ("stop-app", "`two`")])
        code, output = self.run_main("list")
        self.assertEqual(0, code)
        self.assertIn("  one", output)
        self.assertIn("followed by hand: a skill", output)
        self.assertIn("stop-app (in reverse of this order):\n  two", output)

    def test_project_found_from_a_subfolder(self):
        self.profile([("run-app", step("a"))])
        (self.root / "sub").mkdir()
        self.assertEqual(self.root.resolve(), Path(run_app.find_root(str(self.root / "sub"))).resolve())

    def test_no_profile_is_not_run(self):
        (self.root / ".claude").rmdir()
        self.assertEqual(2, self.run_main("start")[0])

    def test_escaped_pipe_and_fenced_table_are_handled(self):
        text = "```\n## Slots\n| Slot | Skill or command |\n|---|---|\n| run-app | `fake` |\n```\n" \
               "## Slots\n\n| Slot | Skill or command |\n|---|---|\n| run-app | `a \\| b` |\n"
        self.assertEqual(["a | b"], run_app.commands(text, "run-app"))


if __name__ == "__main__":
    unittest.main()
