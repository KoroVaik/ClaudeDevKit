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

    # protects: Rule
    def test_five_only_lines_are_not_forecast_readings(self):
        resets = NOW + 48 * H
        self.write([(3, 40, resets), (1, 50, resets)])
        with open(self.log, "a", encoding="utf-8") as f:  # a later 5-hour line would slow the pace if it counted
            f.write(json.dumps({"ts": stamp(NOW), "week_pct": 50, "week_resets": resets, "five_hour_pct": 91,
                                "five_hour_resets": NOW + H, "five_only": True}) + "\n")
        parts = self.check().split(" | ")
        self.assertEqual(int(parts[1]), int(NOW - H + 10 * H))


class LimitNoticesTest(unittest.TestCase):
    """`usage_forecast.py notices`: the limit notices the Pult watcher sends to the project leads."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.log = self.tmp / "usage-log.jsonl"
        self.mark = self.tmp / "state" / "limit-notices.json"

    def add(self, week, week_resets, five=None, five_resets=None, five_only=False):
        row = {"ts": stamp(NOW), "week_pct": week, "week_resets": week_resets, "five_hour_pct": five,
               "five_hour_resets": five_resets}
        if five_only:
            row["five_only"] = True
        with open(self.log, "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")

    def run_at(self, now=NOW):
        return usage_forecast.notices(self.log, self.mark, now)

    # protects: Flow
    def test_weekly_notices_at_90_and_95_once_each_then_back_after_the_reset(self):
        week = NOW + 48 * H
        self.add(85, week)
        self.assertEqual(self.run_at(), [])
        self.add(90, week)
        lines = self.run_at()
        self.assertEqual(len(lines), 1)
        self.assertRegex(lines[0], r"^notice \| week \| 90 \| 90 \| \d+ \| ЛІМІТ: тижневий 90%, оновиться "
                                   r"(пн|вт|ср|чт|пт|сб|нд) \d\d:\d\d$")
        self.add(93, week + 60)  # the same window, the reset time jitters
        self.assertEqual(self.run_at(), [])
        self.add(95, week + 30)
        self.assertTrue(self.run_at()[0].startswith(f"notice | week | 95 | 95 | {int(week)} | "))  # the window's first reset time
        self.add(99, week)
        self.assertEqual(self.run_at(), [])
        self.assertEqual(self.run_at(week + 10), [f"back | week | {int(week)} | ЛІМІТ: тижневий ліміт оновився, "
                                                  "можна будити призупинені сесії"])
        self.assertEqual(self.run_at(week + 20), [])  # back once per window

    # protects: Rule
    def test_a_jump_past_both_thresholds_gives_one_notice_for_the_higher(self):
        week = NOW + 48 * H
        self.add(96, week)
        lines = self.run_at()
        self.assertEqual([line.split(" | ")[:3] for line in lines], [["notice", "week", "95"]])
        self.assertEqual(self.run_at(), [])

    # protects: Flow
    def test_five_hour_notice_at_90_once_per_window_from_a_five_only_line(self):
        week, five = NOW + 48 * H, NOW + 2 * H
        self.add(40, week, 85, five)
        self.assertEqual(self.run_at(), [])
        self.add(40, week, 91, five, five_only=True)
        lines = self.run_at()
        self.assertEqual([line.split(" | ")[:4] for line in lines], [["notice", "five", "90", "91"]])
        self.assertIn("ЛІМІТ: 5-годинний 90%", lines[0])
        self.add(40, week, 97, five, five_only=True)
        self.assertEqual(self.run_at(), [])
        self.assertEqual([line.split(" | ")[:2] for line in self.run_at(five + 1)], [["back", "five"]])
        self.add(41, week, 92, five + 5 * H)  # the next 5-hour window reaches 90 again
        self.assertEqual([line.split(" | ")[:3] for line in self.run_at(five + 2)], [["notice", "five", "90"]])

    # protects: Edge
    def test_a_window_already_over_gives_no_notice_and_no_back_without_a_notice(self):
        self.add(97, NOW - H, 95, NOW - 2 * H)  # stale readings of windows that reset before now
        self.assertEqual(self.run_at(), [])
        self.assertFalse(self.mark.exists())

    # protects: Edge
    def test_back_comes_first_when_a_new_window_is_already_high(self):
        five = NOW + H
        self.add(40, NOW + 48 * H, 90, five)
        self.run_at()
        later = five + 60
        self.add(40, NOW + 48 * H, 95, later + 5 * H)
        self.assertEqual([line.split(" | ")[0] for line in self.run_at(later)], ["back", "notice"])

    # protects: Edge
    def test_no_log_and_bad_mark(self):
        self.assertEqual(self.run_at(), [])
        self.mark.parent.mkdir(parents=True)
        self.mark.write_text("not json", encoding="utf-8")
        self.add(91, NOW + 48 * H)
        self.assertEqual(len(self.run_at()), 1)

    # protects: Flow
    def test_cli_prints_each_line(self):
        self.add(96, NOW + 48 * H, 92, NOW + H)
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = usage_forecast.main(["notices", "--mark", str(self.mark), "--log", str(self.log), "--now", str(NOW)])
        self.assertEqual(code, 0)
        self.assertEqual([line.split(" | ")[1] for line in out.getvalue().splitlines()], ["week", "five"])


if __name__ == "__main__":
    unittest.main()
