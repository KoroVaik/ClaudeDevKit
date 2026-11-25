"""spend-kit stats: where the weekly limit went (shares, attribution, the window, the detail views) and the never-cut
weekly archive. Synthetic transcripts and status line log in temp folders."""
import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_spend import SpendFixture  # noqa: E402

import spend  # noqa: E402
import statusline  # noqa: E402

UTC = datetime.timezone.utc
NOW = datetime.datetime(2026, 11, 25, 12, tzinfo=UTC)
WEEK_END = datetime.datetime(2026, 11, 30, tzinfo=UTC)  # the current window: 23.11 - 30.11
PREVIOUS_END = datetime.datetime(2026, 11, 23, tzinfo=UTC)  # the previous one: 16.11 - 23.11
ROW = re.compile(r"(.+?)\s{3,}(<1%|\d+%)\s*(.*)")
ALPHA = "C--Users-korov-MyRepositories-Alpha"
BETA_TREE = "C--Users-korov-MyRepositories-Beta--claude-worktrees-x"


def message(mid, tokens_m, stamp, *blocks, model="claude-sonnet-5-5"):
    """An assistant message of `tokens_m` million output tokens; a block is a skill name for a Skill tool call."""
    content = [{"type": "tool_use", "id": f"{mid}{n}", "name": "Skill", "input": {"skill": name}}
               for n, name in enumerate(blocks)]
    return {"type": "assistant", "timestamp": stamp,
            "message": {"id": mid, "model": model, "usage": {"output_tokens": tokens_m * 1_000_000}, "content": content}}


def owner(stamp, text="go"):
    return {"type": "user", "timestamp": stamp, "origin": {"kind": "human"}, "message": {"content": text}}


def tool_result(stamp):
    return {"type": "user", "timestamp": stamp,
            "message": {"content": [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]}}


def table(out):
    """`{heading: [(name, share cell, rest of the row)]}` of a stats output (the header line is `table(...)['']`)."""
    groups, name = {"": [out.splitlines()[0]]}, ""
    for line in out.splitlines()[1:]:
        if line.strip() and not line.startswith(" "):
            name = line
            groups[name] = []
        elif line.strip():
            groups[name].append(ROW.fullmatch(line.strip()).groups())
    return groups


class StatsFixture(SpendFixture):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(spend, "now_utc", return_value=NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    def log(self, *readings):
        """The status line log: `(time, per cent, reset time)` per reading."""
        folder = Path(os.environ[statusline.USAGE_ENV])
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / statusline.LOG_NAME, "w", encoding="utf-8") as handle:
            for stamp, pct, resets in readings:
                handle.write(json.dumps({"ts": stamp, "week_pct": pct, "week_resets": resets.timestamp(),
                                         "five_hour_pct": None}) + "\n")

    def this_week(self, pct=40):
        self.log(("2026-11-24T00:00:00Z", pct - 10, WEEK_END), ("2026-11-25T10:00:00Z", pct, WEEK_END))

    def agent(self, session, name, kind, *messages):
        path = self.write(f"{ALPHA}/{session}/subagents/{name}.jsonl", messages)
        path.with_suffix(".meta.json").write_text(json.dumps({"agentType": kind}), encoding="utf-8")

    def week(self):
        """Alpha: a main session (30M units, two skills) with three subagent runs (30M); Beta: 40M in a worktree. Two
        messages of Alpha's main file lie outside the window."""
        self.write(f"{ALPHA}/sess1.jsonl", [
            {"type": "custom-title", "customTitle": "T1"},
            message("old", 9, "2026-11-10T10:00:00Z"), message("future", 9, "2026-12-05T10:00:00Z"),
            owner("2026-11-24T09:00:00Z"), message("m1", 1, "2026-11-24T09:01:00Z"),
            owner("2026-11-24T10:00:00Z", "<command-message>dev-kit:fix-bug</command-message>\n"
                                          "<command-name>/dev-kit:fix-bug</command-name>"),
            message("m2", 1, "2026-11-24T10:01:00Z"), tool_result("2026-11-24T10:02:00Z"),
            message("m2b", 1, "2026-11-24T10:03:00Z"),
            owner("2026-11-24T11:00:00Z", "next"), message("m3", 1, "2026-11-24T11:01:00Z"),
            owner("2026-11-24T12:00:00Z", "more"),
            message("m4", 1, "2026-11-24T12:01:00Z", "dev-kit:new-feature"), tool_result("2026-11-24T12:02:00Z"),
            {"type": "user", "timestamp": "2026-11-24T12:02:01Z", "isMeta": True,
             "message": {"content": "skill text"}},
            message("m5", 1, "2026-11-24T12:03:00Z"), owner("2026-11-24T13:00:00Z", "stop")])
        self.agent("sess1", "agent-a", "dev-kit:coder", message("a1", 2, "2026-11-24T09:30:00Z"))
        self.agent("sess1", "agent-b", "dev-kit:coder",
                   message("b1", 2, "2026-11-24T09:40:00Z", model="claude-opus-5-5"))
        self.agent("sess1", "agent-c", "dev-kit:reviewer", message("c1", 1, "2026-11-24T09:50:00Z"))
        self.write(f"{BETA_TREE}/sess2.jsonl", [{"type": "custom-title", "customTitle": "T2"},
                                                owner("2026-11-24T14:00:00Z"), message("n1", 8, "2026-11-24T14:01:00Z")])

    # protects: Flow
    def test_stats_split_the_header_percent_over_projects_tasks_agents_and_skills(self):
        self.week()
        self.this_week(40)
        code, out, _ = self.run_code("stats")
        self.assertEqual(code, 0)
        shown = table(out)
        self.assertEqual(shown[""], [f"Тиждень ліміту: {(WEEK_END - spend.WEEK).astimezone():%d.%m} - "
                                     f"{WEEK_END.astimezone():%d.%m}, витрачено 40%"])
        projects = shown["Проєкти"]  # a worktree counts to its repository; 60M + 30M of 100M * 40
        self.assertEqual([(name, cell) for name, cell, _ in projects], [("Alpha", "24%"), ("Beta", "16%")])
        self.assertEqual(sum(int(cell[:-1]) for _, cell, _ in projects), 40)
        self.assertEqual([(name, cell) for name, cell, _ in shown["Задачі (топ-5)"]],
                         [("Alpha · T1", "24%"), ("Beta · T2", "16%")])  # a subagent counts to its parent session
        self.assertEqual(shown["Агенти"], [("coder · Opus", "6%", "(1 запуск)"), ("coder · Sonnet", "4%", "(1)"),
                                           ("reviewer · Sonnet", "2%", "(1)")])
        self.assertEqual([(name, cell) for name, cell, _ in shown["Скіли (приблизно)"]],
                         [("fix-bug", "4%"), ("new-feature", "2%")])  # a tool result does not end a skill

    # protects: Edge
    def test_messages_outside_the_window_are_not_counted(self):
        self.week()
        start, end = WEEK_END - spend.WEEK, WEEK_END
        self.assertEqual(spend.collect(start, end)["units"], 100_000_000)  # not the two 45M messages of 10.11 and 5.12

    # protects: Rule
    def test_without_a_status_line_reading_the_share_comes_from_units_over_the_limit(self):
        self.week()
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 400e6):
            _, out, _ = self.run_code("stats")
        shown = table(out)
        self.assertEqual(shown[""], [f"Тиждень ліміту: {(NOW - spend.WEEK).astimezone():%d.%m} - "
                                     f"{NOW.astimezone():%d.%m}, витрачено ~25% (обчислено з одиниць і ліміту)"])
        self.assertEqual([(name, cell) for name, cell, _ in shown["Проєкти"]], [("Alpha", "15%"), ("Beta", "10%")])

    # protects: Rule
    def test_tasks_and_skills_show_the_top_five_and_detail_shows_all(self):
        for number in range(1, 8):
            self.write(f"C--Users-korov-MyRepositories-P{number}/s.jsonl",
                       [{"type": "custom-title", "customTitle": f"task {number}"},
                        message(f"x{number}", number, "2026-11-24T14:00:00Z")])
        self.this_week(70)
        shown = table(self.run_code("stats")[1])
        self.assertEqual(len(shown["Проєкти"]), 7)
        self.assertEqual([name for name, _, _ in shown["Задачі (топ-5)"]], [f"P{n} · task {n}" for n in range(7, 2, -1)])
        _, out, _ = self.run_code("stats", "--detail", "tasks")
        self.assertEqual(list(table(out)), ["", "Задачі"])
        self.assertEqual(len(table(out)["Задачі"]), 7)

    # protects: Flow
    def test_detail_agents_lists_every_type_with_runs_and_usual_units_per_run(self):
        for number, tokens in enumerate((1, 2, 3), 1):  # coder runs of 5M, 10M, 15M: usual 10M
            self.agent("sess1", f"agent-{number}", "dev-kit:coder", message(f"c{number}", tokens, "2026-11-24T09:00:00Z"))
        self.agent("sess1", "agent-s", "dev-kit:reviewer", message("s1", 1, "2026-11-24T09:00:00Z"))
        self.agent("sess1", "agent-h", "dev-kit:reviewer",  # 6M Haiku tokens = 10M units
                   message("h1", 6, "2026-11-24T09:01:00Z", model="claude-haiku-5-5"))
        self.write(f"{ALPHA}/sess1.jsonl", [owner("2026-11-24T09:00:00Z")])
        self.this_week(45)  # 45M units in all: 1% per million
        _, out, _ = self.run_code("stats", "--detail", "agents")
        shown = table(out)
        self.assertEqual(list(shown), ["", "Агенти"])
        self.assertEqual(shown["Агенти"], [("coder · Sonnet", "30%", "(3 запуски, зазвичай 10.0M на запуск)"),
                                           ("reviewer · Haiku", "10%", "(1 запуск, зазвичай 10.0M на запуск)"),
                                           ("reviewer · Sonnet", "5%", "(1 запуск, зазвичай 5.0M на запуск)")])

    # protects: Flow
    def test_a_closed_window_is_archived_once_and_stays_readable_after_the_transcripts_are_gone(self):
        self.write(f"{ALPHA}/old.jsonl", [{"type": "custom-title", "customTitle": "Old work"},
                                          message("w1", 3, "2026-11-18T10:00:00Z"),
                                          message("w2", 1, "2026-11-22T23:00:00Z", model="claude-opus-5-5")])
        self.agent("old", "agent-a", "dev-kit:coder", message("w3", 2, "2026-11-19T10:00:00Z"))
        self.log(("2026-11-17T00:00:00Z", 5, PREVIOUS_END), ("2026-11-22T00:00:00Z", 90, PREVIOUS_END),
                 ("2026-11-24T00:00:00Z", 10, WEEK_END))
        self.run_code("stats")
        self.run_code("stats")  # the second run finds the window archived
        lines = (self.data / "weekly.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        record = json.loads(lines[0])
        self.assertEqual((record["v"], record["pct"], record["units"]), (1, 90, 15_000_000 + 7_500_000 + 10_000_000))
        self.assertEqual(record["projects"], {"Alpha": 32_500_000})
        self.assertEqual(record["tasks"], {"Alpha · Old work": 32_500_000})
        self.assertEqual(record["agents"], {"coder · Sonnet": {"units": 10_000_000, "runs": 1, "usual": 10_000_000}})
        shutil.rmtree(self.projects)
        code, out, _ = self.run_code("stats", "--week", "-1")
        self.assertEqual(code, 0)
        self.assertEqual([(name, cell) for name, cell, _ in table(out)["Проєкти"]], [("Alpha", "90%")])
        self.assertIn("витрачено 90%", out.splitlines()[0])
        self.assertEqual(len((self.data / "weekly.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    # protects: Edge
    def test_a_week_that_is_not_archived_gives_a_one_line_message_and_exit_code_2(self):
        self.this_week(40)
        code, out, err = self.run_code("stats", "--week", "-1")
        self.assertEqual((code, out), (2, ""))
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertIn("no archived week -1", err)
