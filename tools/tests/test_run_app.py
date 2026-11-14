import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit" / "scripts"))
import run_app  # noqa: E402

PYTHON = sys.executable
SCRIPT = Path(run_app.__file__)


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


def shared_step(logfile, name, code=0):
    """Like step, but appends to one absolute log file shared by several worktrees."""
    return f"`\"{PYTHON}\" -c \"open(r'{logfile}', 'a').write('{name} '); raise SystemExit({code})\"`"


class QueueTestCase(unittest.TestCase):
    """Two git worktrees of one repository share one lock in the state folder."""

    def setUp(self):
        tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, tmp, True)
        self.state = tmp / "state"
        patcher = mock.patch.dict(os.environ, {"DEV_KIT_STATE_DIR": str(self.state), "DEV_KIT_LOCK_POLL": "0.1",
                                               "DEV_KIT_QUEUE_WAIT": "0.5", "DEV_KIT_LOCK_TTL": "3600"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.main = tmp / "main"
        self.other = tmp / "other"
        self.main.mkdir()
        self.git(self.main, "init", "-q")
        self.git(self.main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "x")
        self.git(self.main, "worktree", "add", "-q", "--detach", str(self.other))
        self.logfile = tmp / "log.txt"
        self.lock = None

    @staticmethod
    def git(folder, *args):
        subprocess.run(["git", *args], cwd=folder, check=True, capture_output=True)

    def profile(self, folder, rows):
        (folder / ".claude").mkdir(exist_ok=True)
        lines = ["## Slots", "", "| Slot | Skill or command |", "|---|---|"]
        lines += [f"| {slot} | {value} |" for slot, value in rows]
        (folder / ".claude" / "dev-kit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def both(self, rows):
        self.profile(self.main, rows)
        self.profile(self.other, rows)

    def run_main(self, folder, action):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run_app.main([action, "--project", str(folder)])
        return code, out.getvalue() + err.getvalue()

    def lock_file(self):
        return next(self.state.glob("*/app.lock"), None)

    def holder(self):
        return json.loads(self.lock_file().read_text(encoding="utf-8"))["worktree"]

    def log(self):
        return self.logfile.read_text().split() if self.logfile.exists() else []

    def rows(self):
        return [("run-app", shared_step(self.logfile, "run")), ("stop-app", shared_step(self.logfile, "stop"))]

    def test_start_takes_the_lock_and_stop_releases_it(self):
        self.both(self.rows())
        self.assertEqual(0, self.run_main(self.main, "start")[0])
        data = json.loads(self.lock_file().read_text(encoding="utf-8"))
        self.assertEqual(run_app.norm(self.main), data["worktree"])
        self.assertIn("started", data)
        self.assertIn("pid", data)
        self.assertEqual(0, self.run_main(self.main, "stop")[0])
        self.assertIsNone(self.lock_file())
        self.assertEqual(["run", "stop"], self.log())

    def test_same_worktree_restarts(self):
        self.both(self.rows())
        self.run_main(self.main, "start")
        self.assertEqual(0, self.run_main(self.main, "start")[0])
        self.assertEqual(["run", "run"], self.log())

    def test_other_worktree_waits_then_times_out(self):
        self.both(self.rows())
        self.run_main(self.main, "start")
        code, output = self.run_main(self.other, "start")
        self.assertEqual(3, code)
        self.assertIn("waiting for the app, held by " + run_app.norm(self.main), output)
        self.assertEqual(1, output.count("waiting for the app"))
        self.assertIn(run_app.norm(self.main), output.splitlines()[-1])
        self.assertEqual(["run"], self.log())
        self.assertEqual(run_app.norm(self.main), self.holder())

    def test_expired_lock_is_taken_over(self):
        self.both(self.rows())
        self.run_main(self.main, "start")
        old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(timespec="seconds")
        self.lock_file().write_text(json.dumps({"worktree": run_app.norm(self.main), "started": old, "pid": 1}))
        code, output = self.run_main(self.other, "start")
        self.assertEqual(0, code)
        self.assertIn("taking it over", output)
        self.assertEqual(run_app.norm(self.other), self.holder())

    def test_fresh_empty_lock_counts_as_held(self):
        self.both(self.rows())
        run_app.lock_path(self.main).write_text("", encoding="utf-8")
        code, output = self.run_main(self.other, "start")
        self.assertEqual(3, code)
        self.assertIn("an unknown worktree", output)
        self.assertEqual([], self.log())
        self.assertEqual("", self.lock_file().read_text(encoding="utf-8"))

    def test_old_broken_lock_expires(self):
        self.both(self.rows())
        path = run_app.lock_path(self.main)
        path.write_text("{broken", encoding="utf-8")
        old = time.time() - 4 * 3600
        os.utime(path, (old, old))
        self.assertEqual(0, self.run_main(self.other, "start")[0])
        self.assertEqual(run_app.norm(self.other), self.holder())

    def test_two_concurrent_takeovers_leave_one_holder(self):
        self.both(self.rows())
        self.run_main(self.main, "start")
        old = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(timespec="seconds")
        self.lock_file().write_text(json.dumps({"worktree": "gone", "started": old, "pid": 1}))
        scripts = str(SCRIPT.parent)
        code = chr(10).join([
            "import sys, time",
            "sys.path.insert(0, sys.argv[1])",
            "import run_app",
            "while time.time() < float(sys.argv[3]): pass",
            "try:",
            "    run_app.acquire(sys.argv[2]); print('RESULT ok')",
            "except run_app.Queued:",
            "    print('RESULT queued')"])
        env = dict(os.environ, DEV_KIT_QUEUE_WAIT="1.5")
        at = str(time.time() + 1.5)
        procs = [subprocess.Popen([PYTHON, "-c", code, scripts, str(folder), at], env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True) for folder in (self.main, self.other)]
        results = sorted(p.communicate(timeout=30)[0].strip().splitlines()[-1] for p in procs)
        self.assertEqual(["RESULT ok", "RESULT queued"], results)
        self.assertFalse(run_app.lock_path(self.main).with_name("app.lock.takeover").exists())


    def test_stop_from_another_worktree_does_nothing(self):
        self.both(self.rows())
        self.run_main(self.main, "start")
        code, output = self.run_main(self.other, "stop")
        self.assertEqual(0, code)
        self.assertIn(f"the app is held by {run_app.norm(self.main)}, not stopped", output)
        self.assertEqual(["run"], self.log())
        self.assertEqual(run_app.norm(self.main), self.holder())

    def test_failed_stop_still_releases(self):
        self.both([("run-app", shared_step(self.logfile, "run")), ("stop-app", shared_step(self.logfile, "stop", 1))])
        self.run_main(self.main, "start")
        self.assertEqual(1, self.run_main(self.main, "stop")[0])
        self.assertIsNone(self.lock_file())

    def test_failed_start_releases_the_lock(self):
        self.both([("run-app", shared_step(self.logfile, "run", 4))])
        code, output = self.run_main(self.main, "start")
        self.assertEqual(1, code)
        self.assertIn("queue lock is released", output)
        self.assertIsNone(self.lock_file())

    def test_project_without_run_app_does_not_use_the_lock(self):
        self.both([("stop-app", shared_step(self.logfile, "stop"))])
        self.assertEqual(0, self.run_main(self.main, "stop")[0])
        self.assertIsNone(self.lock_file())

    def test_concurrent_starts_run_one_after_another(self):
        self.both(self.rows())
        env = dict(os.environ, DEV_KIT_QUEUE_WAIT="60")

        def cli(folder, action):
            return subprocess.Popen([PYTHON, str(SCRIPT), action, "--project", str(folder)], env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        first = cli(self.main, "start")
        first.communicate(timeout=30)
        second = cli(self.other, "start")
        self.addCleanup(second.kill)
        time.sleep(1.5)
        self.assertIsNone(second.poll())
        self.assertEqual(["run"], self.log())
        cli(self.main, "stop").communicate(timeout=30)
        output = second.communicate(timeout=30)[0]
        self.assertEqual(0, second.returncode)
        self.assertIn("waiting for the app", output)
        self.assertEqual(["run", "stop", "run"], self.log())
        self.assertEqual(run_app.norm(self.other), self.holder())


if __name__ == "__main__":
    unittest.main()
