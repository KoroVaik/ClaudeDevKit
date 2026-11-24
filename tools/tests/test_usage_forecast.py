"""The weekly limit forecast (plugins/spend-kit/scripts/usage_forecast.py) the Pult watcher runs for one phone push."""
import datetime
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent.parent / "plugins" / "spend-kit"
sys.path.insert(0, str(PLUGIN / "scripts"))
import usage_forecast  # noqa: E402

NOW = 1_800_000_000.0  # a fixed "now", epoch seconds
H = 3600


def stamp(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class UsageForecastTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = self.tmp / "usage-log.jsonl"
        self.mark = self.tmp / "state" / "limit-forecast.json"

    def write(self, rows):
        """rows: (hours before NOW, per cent, reset epoch)."""
        self.log.write_text("".join(json.dumps({"ts": stamp(NOW - h * H), "week_pct": p, "week_resets": r,
                                                "five_hour_pct": None}) + "\n" for h, p, r in rows), encoding="utf-8")

    def check(self, open_tasks=1):
        return usage_forecast.check(self.log, self.mark, open_tasks, NOW)

    def test_fast_pace_pushes_once_per_window(self):
        resets = NOW + 48 * H
        self.write([(3, 40, resets), (1, 50, resets)])  # 5 %/h: 50 % left runs out in 10 h, 37 h before the reset
        line = self.check()
        self.assertTrue(line.startswith("push | "), line)
        parts = line.split(" | ")
        self.assertEqual(int(parts[1]), int(NOW - H + 10 * H))
        self.assertEqual(int(parts[2]), int(resets))
        self.assertRegex(parts[5], r"^Тижневий ліміт: витрачено 50%, за темпом скінчиться (пн|вт|ср|чт|пт|сб|нд) \d\d:\d\d, "
                                   r"оновиться (пн|вт|ср|чт|пт|сб|нд) \d\d:\d\d$")  # the last reading's per cent
        self.assertEqual(self.check(), "none marked")  # never repeated in that window, even if it gets worse
        self.write([(3, 40, resets), (1, 50, resets), (0, 70, resets + 120)])  # same window, reset time jitter
        self.assertEqual(self.check(), "none marked")

    def test_slow_pace_gives_none(self):
        resets = NOW + 20 * H
        self.write([(5, 40, resets), (1, 44, resets)])  # 1 %/h: runs out in 56 h, after the reset
        self.assertEqual(self.check(), "none enough")

    def test_run_out_within_six_hours_of_reset_gives_none(self):
        resets = NOW + 20 * H
        self.write([(2, 80, resets), (0, 82, resets)])  # 1 %/h: runs out in 18 h, 2 h before the reset
        self.assertEqual(self.check(), "none enough")

    def test_limit_already_reached_gives_none(self):
        resets = NOW + 48 * H
        self.write([(3, 80, resets), (1, 100, resets)])  # sessions already stand: no forecast push
        self.assertEqual(self.check(), "none limit-reached")

    def test_too_few_readings(self):
        resets = NOW + 48 * H
        self.write([(1, 50, resets)])
        self.assertEqual(self.check(), "none few-readings")
        self.write([(9, 20, resets), (1, 50, resets)])  # the older one is out of the 6-hour span
        self.assertEqual(self.check(), "none few-readings")

    def test_readings_under_an_hour_apart(self):
        resets = NOW + 48 * H
        self.write([(0.5, 40, resets), (0, 50, resets)])
        self.assertEqual(self.check(), "none short-span")

    def test_new_window_drops_old_readings(self):
        old, new = NOW + 2 * H, NOW + 7 * 24 * H
        self.write([(4, 90, old), (3, 95, old), (2, 99, old), (0.5, 3, new)])  # a fresh window: one reading only
        self.assertEqual(self.check(), "none few-readings")
        self.write([(5, 30, NOW - H), (2, 60, NOW - H)])  # the window already reset
        self.assertEqual(self.check(), "none window-over")

    def test_mark_of_an_old_window_does_not_block(self):
        resets = NOW + 48 * H
        self.mark.parent.mkdir(parents=True)
        self.mark.write_text(json.dumps({"week_resets": resets - 7 * 24 * H}), encoding="utf-8")
        self.write([(3, 40, resets), (1, 50, resets)])
        self.assertTrue(self.check().startswith("push | "))

    def test_no_open_tasks_gives_none_and_no_mark(self):
        resets = NOW + 48 * H
        self.write([(3, 40, resets), (1, 50, resets)])
        self.assertEqual(self.check(open_tasks=0), "none no-open-tasks")
        self.assertFalse(self.mark.exists())
        self.assertTrue(self.check().startswith("push | "))  # tasks open later in the same window: still one push

    def test_no_log_and_bad_lines(self):
        self.assertEqual(self.check(), "none no-log")
        resets = NOW + 48 * H
        self.write([(3, 40, resets), (1, 50, resets)])
        with open(self.log, "a", encoding="utf-8") as f:
            f.write("not json\n{\"ts\": \"bad\", \"week_pct\": 99, \"week_resets\": 1}\n")
        self.assertTrue(self.check().startswith("push | "))

    def test_cli_prints_one_line(self):
        resets = NOW + 48 * H
        self.write([(3, 40, resets), (1, 50, resets)])
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = usage_forecast.main(["check", "--open", "2", "--mark", str(self.mark), "--log", str(self.log),
                                        "--now", str(NOW)])
        self.assertEqual(code, 0)
        self.assertTrue(out.getvalue().startswith("push | "))


if __name__ == "__main__":
    unittest.main()
