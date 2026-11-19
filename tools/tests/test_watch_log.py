"""The Pult log watcher (plugins/pult/scripts/watch-log.py) exits with the first new problem line of servers.log,
keeps its place between runs and runs once at a time."""
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "plugins" / "pult" / "scripts" / "watch-log.py"
SPEC = importlib.util.spec_from_file_location("watch_log", SCRIPT)
watch_log = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(watch_log)


class WatchLogTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = self.tmp / "servers.log"
        self.state = self.tmp / "state"

    def write(self, *lines):
        with open(self.log, "a", encoding="utf-8") as handle:
            for line in lines:
                handle.write(line + "\n")

    def run_watch(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = watch_log.main(["--log", str(self.log), "--state-dir", str(self.state),
                                   "--interval", "0", "--max-minutes", "0"])
        return code, out.getvalue().strip()

    def test_first_run_starts_at_the_end(self):  # Edge
        self.write("2026-11-19T10:00:00 GIVEUP P: Old (old problem)")
        self.assertEqual(self.run_watch(), (4, "time limit"))

    def test_new_problem_line_wakes_once_and_routine_lines_do_not(self):  # Flow
        self.write("2026-11-19T10:00:00 UP P: Lead")
        self.run_watch()
        self.write("2026-11-19T10:01:00 HEAL P: Lead", "2026-11-19T10:01:05 UP P: Lead",
                   "2026-11-19T10:02:00 LIMIT C: task resets 12:00",
                   "2026-11-19T10:03:00 GIVEUP-TASK C: task abc (3 respawns did not keep it up)",
                   "2026-11-19T10:03:30 HEAL-FAILED P: Lead (no start)",
                   "2026-11-19T10:04:00 GIVEUP P: Lead (3 restarts)")
        self.assertEqual(self.run_watch(), (0, "problem: 2026-11-19T10:03:00 GIVEUP-TASK C: task abc "
                                               "(3 respawns did not keep it up)"))
        # Lines written between two runs are not lost; a reported line is not reported again.
        self.assertEqual(self.run_watch(), (0, "problem: 2026-11-19T10:04:00 GIVEUP P: Lead (3 restarts)"))
        self.assertEqual(self.run_watch(), (4, "time limit"))

    def test_partial_line_waits_for_its_end(self):  # Edge
        self.run_watch()
        with open(self.log, "a", encoding="utf-8") as handle:
            handle.write("2026-11-19T10:00:00 GIVEUP P: Lead")
        self.assertEqual(self.run_watch()[0], 4)
        self.write(" (3 restarts)")
        self.assertEqual(self.run_watch(), (0, "problem: 2026-11-19T10:00:00 GIVEUP P: Lead (3 restarts)"))

    def test_a_cut_log_is_read_from_the_start(self):  # Edge
        self.write("2026-11-19T10:00:00 UP P: Lead " + "x" * 200)
        self.run_watch()
        self.log.write_text("2026-11-19T11:00:00 RESTART-LEAD-FAILED P: Lead\n", encoding="utf-8")
        self.assertEqual(self.run_watch(), (0, "problem: 2026-11-19T11:00:00 RESTART-LEAD-FAILED P: Lead"))

    def test_old_position_starts_at_the_end(self):  # Edge
        self.run_watch()
        self.write("2026-11-19T10:00:00 GIVEUP P: Lead (3 restarts)")
        old = os.path.getmtime(self.state / watch_log.POSITION) - watch_log.FRESH - 60
        os.utime(self.state / watch_log.POSITION, (old, old))
        self.assertEqual(self.run_watch(), (4, "time limit"))

    def test_cyrillic_line_prints_on_a_cp1252_console(self):  # Bug
        self.run_watch()
        self.write("2026-11-19T10:00:00 GIVEUP P: Жратва (3 restarts)")
        env = dict(os.environ, PYTHONIOENCODING="cp1252")
        out = subprocess.run([sys.executable, str(SCRIPT), "--log", str(self.log), "--state-dir", str(self.state),
                              "--interval", "0", "--max-minutes", "0"], env=env, capture_output=True)
        self.assertEqual(out.returncode, 0, out.stderr.decode("utf-8", "replace"))
        self.assertEqual(out.stdout.decode("utf-8").strip(), "problem: 2026-11-19T10:00:00 GIVEUP P: Жратва (3 restarts)")

    def test_second_watcher_leaves(self):  # Rule
        self.state.mkdir()
        (self.state / watch_log.LOCK).write_text(str(os.getppid()), encoding="ascii")
        code, out = self.run_watch()
        self.assertEqual((code, out), (6, f"already watching: pid {os.getppid()}"))
        self.assertTrue((self.state / watch_log.LOCK).exists())

    def test_stale_lock_is_taken_and_released(self):  # Rule
        self.state.mkdir()
        (self.state / watch_log.LOCK).write_text("999999", encoding="ascii")
        self.assertEqual(self.run_watch()[0], 4)
        self.assertFalse((self.state / watch_log.LOCK).exists())


if __name__ == "__main__":
    unittest.main()
