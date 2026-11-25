"""The limit notices (plugins/spend-kit/scripts/limit_notices.py) the Pult watcher sends to the project leads."""
import datetime
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent.parent / "plugins" / "spend-kit"
sys.path.insert(0, str(PLUGIN / "scripts"))
import limit_notices  # noqa: E402

NOW = 1_800_000_000.0  # a fixed "now", epoch seconds
H = 3600


def stamp(epoch):
    return datetime.datetime.fromtimestamp(epoch, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LimitNoticesTest(unittest.TestCase):
    """`limit_notices.py notices`: the limit notices the Pult watcher sends to the project leads."""

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
        return limit_notices.notices(self.log, self.mark, now)

    # protects: Flow
    def test_weekly_notices_at_90_95_and_98_once_each_then_back_after_the_reset(self):
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
        self.add(98, week)
        self.assertTrue(self.run_at()[0].startswith(f"notice | week | 98 | 98 | {int(week)} | ЛІМІТ: тижневий 98%, оновиться "))
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

    # protects: Rule
    def test_a_jump_past_98_gives_one_reserve_notice_with_the_reset_time(self):
        week = NOW + 48 * H
        self.add(99, week)
        lines = self.run_at()
        self.assertEqual(len(lines), 1)
        self.assertRegex(lines[0], rf"^notice \| week \| 98 \| 99 \| {int(week)} \| ЛІМІТ: тижневий 98%, оновиться "
                                   r"(пн|вт|ср|чт|пт|сб|нд) \d\d:\d\d$")
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
            code = limit_notices.main(["notices", "--mark", str(self.mark), "--log", str(self.log), "--now", str(NOW)])
        self.assertEqual(code, 0)
        self.assertEqual([line.split(" | ")[1] for line in out.getvalue().splitlines()], ["week", "five"])


if __name__ == "__main__":
    unittest.main()
