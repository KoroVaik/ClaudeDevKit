"""spend-kit waste signals: re-asks and their rework, a helper's model against its agent file, duplicated work, and the
spend by cause in `stats`. Synthetic transcripts in temp folders."""
import datetime
import json
import os
import re
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_spend import SpendFixture  # noqa: E402

import signals  # noqa: E402
import spend  # noqa: E402
import statusline  # noqa: E402

UTC = datetime.timezone.utc
BASE = datetime.datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0) - datetime.timedelta(days=2)
SHARE = re.compile(r"([\d.]+)% of the weekly limit")
NOW = datetime.datetime(2026, 11, 25, 12, tzinfo=UTC)
WEEK_END = datetime.datetime(2026, 11, 30, tzinfo=UTC)
PREVIOUS_END = datetime.datetime(2026, 11, 23, tzinfo=UTC)


def at(minutes):
    """A time `minutes` after BASE (noon two days ago), as a transcript stamp."""
    return (BASE + datetime.timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")


def owner(minutes, text):
    return {"type": "user", "timestamp": at(minutes), "origin": {"kind": "human"}, "message": {"content": text}}


def reply(mid, minutes, *blocks, tokens=1000, model="claude-sonnet-5-5", effort=None):
    """An assistant message of `tokens` output tokens (5 units each on Sonnet); a block is `("Agent", id, type,
    description)`, `("Read", id, path)` or `("Bash", id, command)`."""
    content = []
    for name, ident, *rest in blocks:
        given = ({"subagent_type": rest[0], "description": rest[1], "prompt": "p"} if name == "Agent"
                 else {"command": rest[0]} if name == "Bash" else {"file_path": rest[0]})
        content.append({"type": "tool_use", "id": ident, "name": name, "input": given})
    entry = {"type": "assistant", "timestamp": at(minutes),
             "message": {"id": mid, "model": model, "usage": {"output_tokens": tokens}, "content": content}}
    if effort:
        entry["effort"] = effort
    return entry


def result(minutes, tool_use_id, text="ok", error=False):
    block = {"type": "tool_result", "tool_use_id": tool_use_id, "content": text}
    if error:
        block["is_error"] = True
    return {"type": "user", "timestamp": at(minutes), "message": {"content": [block]}}


class SignalsFixture(SpendFixture):
    def helper(self, session, name, agent_type, tool_use_id, entries, description="task"):
        """A helper's transcript with its `meta.json` (the `toolUseId` links it to the session's `Agent` call)."""
        path = self.write(f"proj/{session}/subagents/{name}.jsonl", entries)
        path.with_suffix(".meta.json").write_text(json.dumps({"agentType": agent_type, "toolUseId": tool_use_id,
                                                              "description": description}), encoding="utf-8")

    def agent_file(self, plugin, name, **front):
        folder = self.plugins / plugin / "agents"
        folder.mkdir(parents=True, exist_ok=True)
        lines = "".join(f"{key}: {value}\n" for key, value in front.items())
        (folder / f"{name}.md").write_text(f"---\nname: {name}\n{lines}---\n\nBody\n", encoding="utf-8")

    def events(self, path, kind=None):
        return [event for event in spend.session_signals(path)["events"] if kind in (None, event["kind"])]

    def record(self, path):
        self.run_cmd("write-session", "--path", str(path))
        return json.loads((self.data / "sessions" / f"{path.stem}.json").read_text(encoding="utf-8"))


class ReaskTestCase(SignalsFixture):
    # protects: Flow
    def test_a_bare_question_mark_is_a_reask_and_its_rework_is_the_span_to_the_next_owner_message(self):
        main = self.write("proj/sess1.jsonl", [
            owner(0, "build the parser"), reply("m1", 1, effort="medium"),
            owner(10, "?"), reply("m2", 11, ("Agent", "tu1", "dev-kit:coder", "build parser"), effort="medium"),
            result(12, "tu1"), reply("m3", 13, effort="medium"),
            owner(30, "thanks"), reply("m4", 31, effort="medium")])
        self.helper("sess1", "agent-a", "dev-kit:coder", "tu1", [reply("h1", 11, tokens=2000)])
        events = self.events(main, "reask")
        self.assertEqual([(event["detail"], event["units"]) for event in events],
                         [("short", 5000 + 5000 + 10000)])  # m2, m3 and the whole helper file; not m4
        record = self.record(main)
        self.assertEqual((record["rework"]["units"], record["rework"]["reasks"]), (20000, 1))
        self.assertEqual((record["model"], record["effort"]), ("sonnet", "medium"))

    # protects: Rule
    def test_the_first_message_of_a_task_session_is_the_task_not_a_reask(self):
        entries = [owner(0, "?"), reply("m1", 1), owner(10, "?"), reply("m2", 11)]
        task = self.write("proj/task1.jsonl", [{"type": "custom-title", "customTitle": "M: build the parser"}] + entries)
        plain = self.write("proj/plain1.jsonl", entries)
        self.assertEqual(len(self.events(task, "reask")), 1)  # only the second «?»
        self.assertEqual(len(self.events(plain, "reask")), 2)

    # protects: Rule
    def test_a_question_asked_again_in_other_words_is_a_reask(self):
        main = self.write("proj/sess2.jsonl", [
            owner(0, "Чому не працює збірка проекту на сервері?"), reply("m1", 1),
            owner(10, "Скажи, чому не працює збірка проекту?"), reply("m2", 11),
            owner(20, "Додай ще кнопку в меню налаштувань?"), reply("m3", 21)])
        self.assertEqual([event["key"] for event in self.events(main, "reask")], ["reask|2"])  # the second message only

    # protects: Edge
    def test_only_the_owners_own_prose_is_checked_for_a_reask(self):
        for text, expected in (("?", "short"), ("що?", "short"), ("Ще раз, будь ласка", "short"), ("again please", "short"),
                               ("ти не так зрозумів", "strong"), ("I said no", "strong"), ("```\nне так\n```", None),
                               ("«не так» у файлі", None), ("> не так\nдобре", None), ("добре, дякую", None),
                               ("що це за помилка", None)):
            self.assertEqual(signals.reask_kind(text, []), expected, text)
        not_owner = [{"type": "user", "origin": {"kind": "task-notification"}, "message": {"content": "??"}},
                     {"type": "user", "origin": {"kind": "human"}, "message": {"content": "<command-name>/x</command-name>"}},
                     {"type": "user", "isMeta": True, "origin": {"kind": "human"}, "message": {"content": "?"}},
                     {"type": "user", "origin": {"kind": "human"},
                      "message": {"content": [{"type": "tool_result", "tool_use_id": "x", "content": "??"}]}}]
        self.assertEqual([signals.owner_text(entry) for entry in not_owner], [None] * 4)

    # protects: Edge
    def test_a_repeated_question_needs_enough_words_a_question_mark_and_a_recent_match(self):
        asked = "Чому не працює збірка проекту на сервері"
        self.assertTrue(signals.repeated_question("Чому не працює збірка проекту?", [asked]))
        self.assertFalse(signals.repeated_question("Чому не працює збірка проекту", [asked]))  # no question mark
        self.assertFalse(signals.repeated_question("Чому так?", ["Чому так"]))  # under 3 words
        self.assertFalse(signals.repeated_question("Чому не працює збірка?", ["збірка працює"]))  # earlier one too short
        old = [asked, "one thing here", "another thing here", "third thing here"]
        self.assertFalse(signals.repeated_question("Чому не працює збірка проекту?", old))  # only the last 3 count

    # protects: Bug
    # Broke: an earlier design counted a session again on every scan, so one re-ask grew with each rescan
    def test_a_reask_is_counted_once_when_the_session_grows_and_is_scanned_again(self):
        path = self.write("proj/sess3.jsonl", [owner(0, "do it"), reply("m1", 1), owner(10, "?"), reply("m2", 11)])
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100000):
            self.run_cmd("scan", "--force")
            with open(path, "a", encoding="utf-8") as handle:
                for entry in (owner(20, "next"), reply("m3", 21)):
                    handle.write(json.dumps(entry) + "\n")
            self.run_cmd("scan", "--force")
        day = BASE.astimezone().date().isoformat()
        row = self.state()["daily"][day]["proj/sess3"]
        self.assertEqual((row["reasks"], row["rework"]), (1, 5000))

    # protects: Flow
    def test_a_finished_day_gives_a_rework_finding_with_its_share_of_the_weekly_limit(self):
        self.write("proj/sess4.jsonl", [owner(0, "do it"), reply("m1", 1), owner(10, "?"), reply("m2", 11)])
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100000):
            lines, _ = self.findings()
        rework = [line for line in lines if "| rework |" in line]
        self.assertEqual(len(rework), 1)
        self.assertIn(f"| {BASE.astimezone().date().isoformat()}: 1 re-asks, rework 5.0% of the weekly limit "
                      f"(5.0k units)", rework[0])
        self.assertEqual(SHARE.findall(rework[0]), ["5.0"])

    # protects: Rule
    def test_every_reask_counts_in_the_rework_finding_whatever_its_share(self):
        self.write("proj/sess11.jsonl", [owner(0, "do it"), reply("m1", 1), owner(10, "?"), reply("m2", 11, tokens=1),
                                         owner(20, "?"), reply("m3", 21, tokens=1000)])
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100000):  # 5 units = 0.005%, under the 0.1% floor; 5000 = 5%
            lines, _ = self.findings()
        rework = [line for line in lines if "| rework |" in line]
        self.assertEqual(len(rework), 1)
        self.assertIn(": 2 re-asks, rework 5.0%", rework[0])

    # protects: Rule
    def test_a_lone_cheap_reask_is_still_a_finding_at_the_seed_limit(self):
        self.write("proj/sess12.jsonl", [owner(0, "do it"), reply("m1", 1), owner(10, "?"), reply("m2", 11, tokens=1)])
        rework = [line for line in self.findings()[0] if "| rework |" in line]  # 5 units of the 690M seed limit
        self.assertEqual(len(rework), 1)
        self.assertIn(": 1 re-asks, rework 0.00% of the weekly limit (5 units)", rework[0])


class ModelTestCase(SignalsFixture):
    def two_runs(self):
        """A session with two Opus helpers of `x:coder`, whose file says Sonnet medium; the second is in the experiment log."""
        self.agent_file("x", "coder", model="sonnet", effort="medium")
        main = self.write("proj/sess5.jsonl", [
            owner(0, "start"),
            reply("m1", 1, ("Agent", "tu1", "x:coder", "alpha work"), ("Agent", "tu2", "x:coder", "beta thing")),
            owner(60, "thanks")])
        for name, call in (("agent-a", "tu1"), ("agent-b", "tu2")):
            self.helper("sess5", name, "x:coder", call, [reply(f"{name}-1", 5, model="claude-opus-5-5", effort="high")])
        return main

    # protects: Rule
    def test_a_helper_running_above_its_agent_files_model_or_effort_is_a_mismatch(self):
        main = self.two_runs()
        events = self.events(main, "mismatch")
        self.assertEqual([(event["key"], event["detail"]) for event in events],
                         [("mismatch|agent-a", "x:coder ran on Opus high, its file says Sonnet medium"),
                          ("mismatch|agent-b", "x:coder ran on Opus high, its file says Sonnet medium")])
        self.agent_file("x", "coder", model="opus", effort="high")
        self.assertEqual(self.events(main, "mismatch"), [])  # at the file's own level
        self.agent_file("x", "coder", model="inherit")
        self.assertEqual(self.events(main, "mismatch"), [])  # `inherit`: nothing to compare

    # protects: Rule
    def test_a_run_in_the_experiment_log_is_not_a_mismatch_and_the_rest_reach_the_findings(self):
        self.two_runs()
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / signals.EXPERIMENTS_NAME).write_text(json.dumps(
            {"tool_use_id": "tu2", "type": "x:coder", "variant": "opus-low", "model": "opus", "effort": "low",
             "time": at(1), "session": "sess5"}) + "\nnot json\n", encoding="utf-8")
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100000):
            lines, _ = self.findings()
        found = [line for line in lines if "| model mismatch |" in line]
        self.assertEqual(len(found), 1)  # tu1 only
        self.assertRegex(found[0], r"^- proj \| sess5 \| model mismatch \| x:coder ran on Opus high, its file says "
                                   r"Sonnet medium; [\d.]+% of the weekly limit$")

    # protects: Rule
    def test_a_cheap_step_followed_by_a_reask_or_the_same_launch_is_redone(self):
        main = self.write("proj/sess6.jsonl", [
            owner(0, "start"),
            reply("m1", 1, ("Agent", "tu1", "x:judge", "check the catalogue rows")), result(6, "tu1"),
            reply("m2", 8, ("Agent", "tu2", "x:judge", "check the catalogue rows again")), result(12, "tu2"),
            owner(30, "?"), reply("m3", 31)])
        self.helper("sess6", "agent-a", "x:judge", "tu1", [reply("a1", 5, effort="high")],
                    "check the catalogue rows")
        self.helper("sess6", "agent-b", "x:judge", "tu2", [reply("b1", 11, effort="high")],
                    "check the catalogue rows again")
        self.assertEqual(sorted(event["key"] for event in self.events(main, "redone")),
                         ["redone|agent-a", "redone|agent-b"])  # a: launched again, b: the next message is a re-ask
        calm = self.write("proj/sess7.jsonl", [
            owner(0, "start"), reply("m1", 1, ("Agent", "tu1", "x:judge", "check the catalogue rows")),
            result(6, "tu1"), owner(30, "good"), reply("m2", 31)])
        self.helper("sess7", "agent-a", "x:judge", "tu1", [reply("a1", 5, effort="high")])
        self.assertEqual(self.events(calm, "redone"), [])

    # protects: Rule
    def test_a_launch_that_starts_before_the_first_runs_tool_result_is_not_a_redo(self):
        main = self.write("proj/sess12.jsonl", [
            owner(0, "start"),
            reply("m1", 1, ("Agent", "tu1", "x:judge", "check the catalogue rows")),
            reply("m2", 7, ("Agent", "tu2", "x:judge", "check the catalogue rows again")),  # the helper ended at 5
            result(9, "tu1"), result(14, "tu2"), owner(30, "good"), reply("m3", 31)])
        self.helper("sess12", "agent-a", "x:judge", "tu1", [reply("a1", 5, effort="high")], "check the catalogue rows")
        self.helper("sess12", "agent-b", "x:judge", "tu2", [reply("b1", 13, effort="high")], "check the catalogue rows again")
        self.assertEqual(self.events(main, "redone"), [])

    # protects: Rule
    def test_a_plugin_agent_and_a_project_agent_are_found_by_their_type(self):
        self.agent_file("x", "coder", model="sonnet", effort="high")
        project = self.tmp / "repo" / ".claude" / "agents"
        project.mkdir(parents=True)
        (project / "judge.md").write_text("---\nname: judge\nmodel: haiku\n---\n", encoding="utf-8")
        self.assertEqual(signals.agent_settings("x:coder", None), {"model": "sonnet", "effort": "high"})
        self.assertEqual(signals.agent_settings("judge", str(self.tmp / "repo")), {"model": "haiku"})
        self.assertIsNone(signals.agent_settings("x:missing", None))


class DuplicateTestCase(SignalsFixture):
    # protects: Flow
    def test_two_helpers_reading_one_file_and_the_session_reading_it_again_are_duplicate_work(self):
        shared = str(self.tmp / "repo" / "docs" / "map.md")
        main = self.write("proj/sess8.jsonl", [
            owner(0, "start"),
            reply("m1", 1, ("Agent", "tuA", "x:reader", "map the docs"), ("Agent", "tuB", "x:counter", "count the tests")),
            result(7, "tuA"), result(8, "tuB"),
            reply("m2", 10, ("Read", "rm", shared)), result(11, "rm", "x" * 4000),
            owner(60, "thanks")])
        for name, call, start in (("agent-a", "tuA", 3), ("agent-b", "tuB", 4)):
            self.helper("sess8", name, "x:reader", call,
                        [reply(f"{name}-1", start, ("Read", f"r{name}", shared)), result(start + 1, f"r{name}", "x" * 4000),
                         reply(f"{name}-2", start + 2)])
        by_kind = {event["kind"]: event for event in self.events(main) if event["kind"].startswith("dup_")}
        self.assertEqual(sorted(by_kind), ["dup_reread", "dup_shared"])
        self.assertEqual((by_kind["dup_shared"]["units"], by_kind["dup_reread"]["units"]), (1250, 1250))  # 1000 tokens x 1.25
        self.assertEqual(by_kind["dup_shared"]["key"], f"shared|{signals.norm_path(shared)}|agent-b")
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100000):
            lines, _ = self.findings()
        found = [line for line in lines if "| duplicate work |" in line]
        self.assertEqual(len(found), 1)
        self.assertIn(": 1 files read by 2+ helpers, 1 read again by the session, 0 repeated launches; ~2.5% of the "
                      "weekly limit, estimate", found[0])

    # protects: Rule
    def test_files_every_agent_is_told_to_read_are_not_duplicate_work(self):
        names = ["CLAUDE.md", ".claude/dev-kit.md", "plugins/x/skills/y/SKILL.md", "plugins/x/agents/coder.md",
                 "plugins/x/rules-subscription.md", "claude-facts.md", "docs/messages.md"]
        paths = [str(self.tmp / "repo" / name) for name in names]
        reads = [("Read", f"r{n}", path) for n, path in enumerate(paths)]
        main = self.write("proj/sess13.jsonl", [
            owner(0, "start"), reply("m1", 1, ("Agent", "tuA", "x:reader", "map the docs"),
                                     ("Agent", "tuB", "x:counter", "count the tests")),
            result(7, "tuA"), result(8, "tuB"), reply("m2", 10, *reads), owner(60, "thanks")])
        for name, call, start in (("agent-a", "tuA", 3), ("agent-b", "tuB", 4)):
            self.helper("sess13", name, "x:reader", call,
                        [reply(f"{name}-1", start, *[(kind, f"{ident}{name}", path) for kind, ident, path in reads]),
                         reply(f"{name}-2", start + 2)])
        self.assertEqual([event for event in self.events(main) if event["kind"].startswith("dup_")], [])
        other = str(self.tmp / "repo" / "docs" / "map.md")  # any other file still counts
        self.assertTrue(signals.is_rule_file(signals.norm_path(paths[0])))
        self.assertFalse(signals.is_rule_file(signals.norm_path(other)))

    # protects: Rule
    def test_duplicate_work_under_the_note_share_of_its_session_day_is_no_finding(self):
        shared = str(self.tmp / "repo" / "docs" / "map.md")
        self.write("proj/sess14.jsonl", [
            owner(0, "start"),
            reply("m1", 1, ("Agent", "tuA", "x:reader", "map the docs"), ("Agent", "tuB", "x:counter", "count the tests")),
            result(7, "tuA"), result(8, "tuB"), owner(60, "thanks")])
        for name, call, start in (("agent-a", "tuA", 3), ("agent-b", "tuB", 4)):
            self.helper("sess14", name, "x:reader", call,
                        [reply(f"{name}-1", start, ("Read", f"r{name}", shared)), result(start + 1, f"r{name}", "x" * 4000),
                         reply(f"{name}-2", start + 2)])
        lines, _ = self.findings()  # 1250 units of the 690M seed limit: 0.0002%
        self.assertEqual([line for line in lines if "| duplicate work |" in line], [])

    # protects: Rule
    def test_a_read_by_the_session_before_the_helper_returned_is_not_duplicate_work(self):
        shared = str(self.tmp / "repo" / "docs" / "map.md")
        main = self.write("proj/sess9.jsonl", [
            owner(0, "start"), reply("m1", 1, ("Read", "rm", shared)), result(2, "rm", "x" * 4000),
            reply("m2", 3, ("Agent", "tuA", "x:reader", "map the docs")), result(9, "tuA"), owner(60, "thanks")])
        self.helper("sess9", "agent-a", "x:reader", "tuA",
                    [reply("a1", 4, ("Read", "ra", shared)), result(5, "ra", "x" * 4000), reply("a2", 6)])
        self.assertEqual([event for event in self.events(main) if event["kind"].startswith("dup_")], [])

    # protects: Rule
    def test_the_same_launch_again_is_duplicate_work_priced_as_the_whole_repeated_run(self):
        main = self.write("proj/sess10.jsonl", [
            owner(0, "start"), reply("m1", 1, ("Agent", "tu1", "x:reader", "map the docs folder")), result(6, "tu1"),
            reply("m2", 8, ("Agent", "tu2", "x:reader", "map the docs folder again")), result(14, "tu2"),
            owner(60, "thanks")])
        self.helper("sess10", "agent-a", "x:reader", "tu1", [reply("a1", 5)])
        self.helper("sess10", "agent-b", "x:reader", "tu2", [reply("b1", 13, tokens=3000)])
        launches = self.events(main, "dup_launch")
        self.assertEqual([(event["key"], event["units"]) for event in launches], [("launch|tu2", 15000)])


class CausesTestCase(SignalsFixture):
    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(spend, "now_utc", return_value=NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    def log(self, *readings):
        folder = Path(os.environ[statusline.USAGE_ENV])
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / statusline.LOG_NAME, "w", encoding="utf-8") as handle:
            for stamp, pct, resets in readings:
                handle.write(json.dumps({"ts": stamp, "week_pct": pct, "week_resets": resets.timestamp(),
                                         "five_hour_pct": None}) + "\n")

    def session(self, name, day, main_tokens_m, helper_tokens_m):
        """A session of one Sonnet main message and one Opus helper run, both on `day` (a date text)."""
        stamp = f"{day}T10:00:00Z"
        main = {"type": "assistant", "timestamp": stamp,
                "message": {"id": f"{name}-m", "model": "claude-sonnet-5-5", "content": [],
                            "usage": {"output_tokens": main_tokens_m * 1_000_000}}}
        owner_line = {"type": "user", "timestamp": stamp, "origin": {"kind": "human"}, "message": {"content": "go"}}
        self.write(f"proj/{name}.jsonl", [owner_line, main])
        self.helper(name, "agent-a", "x:coder", "tu1",
                    [{**main, "message": {**main["message"], "id": f"{name}-h", "model": "claude-opus-5-5",
                                          "usage": {"output_tokens": helper_tokens_m * 1_000_000}}}])

    def cause(self, out, name):
        found = re.search(rf"^  {name}\s+(<1%|\d+%)\s+\((.+)\)$", out, re.MULTILINE)
        return found.groups() if found else None

    # protects: Flow
    def test_stats_show_the_spend_by_cause_with_last_weeks_share_from_the_archived_line(self):
        self.session("last", "2026-11-19", 1, 1)  # last week: Opus helper 7.5M of 12.5M units = 60%
        self.session("now", "2026-11-24", 3, 1)  # this week: Opus helper 7.5M of 22.5M units = 33%
        self.log(("2026-11-17T00:00:00Z", 5, PREVIOUS_END), ("2026-11-22T00:00:00Z", 90, PREVIOUS_END),
                 ("2026-11-24T00:00:00Z", 10, WEEK_END), ("2026-11-25T10:00:00Z", 40, WEEK_END))
        code, out, _ = self.run_code("stats")
        self.assertEqual(code, 0)
        self.assertIn("Куди пішли токени", out.splitlines())
        self.assertEqual(self.cause(out, "Дорогі моделі"), ("33%", "минулого тижня 60%"))
        self.assertEqual(self.cause(out, "Переробка"), ("0%", "минулого тижня 0%"))
        self.assertRegex(out, r"  Перепитування 0, модель вище за файл \d+, повтори кроку \d+, дубльована робота \d+\n")
        self.assertLess(out.index("Куди пішли токени"), out.index("Проєкти"))
        record = json.loads((self.data / "weekly.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual((record["v"], record["causes"]["expensive models"]), (1, 7_500_000))
        self.assertEqual(set(record["counts"]), set(spend.COUNTS))

    # protects: Rule
    def test_the_counts_line_counts_every_reask_but_skips_other_events_under_the_note_share(self):
        def line(kind, stamp, text="go"):
            return {"type": kind, "timestamp": f"2026-11-24T{stamp}Z", "origin": {"kind": "human"},
                    "message": {"content": text}}

        def message(mid, stamp, tokens):
            return {"type": "assistant", "timestamp": f"2026-11-24T{stamp}Z",
                    "message": {"id": mid, "model": "claude-sonnet-5-5", "content": [],
                                "usage": {"output_tokens": tokens}}}

        self.write("proj/sess1.jsonl", [line("user", "10:00:00"), message("a", "10:01:00", 1000),
                                        line("user", "11:00:00", "?"), message("b", "11:01:00", 1_000_000),  # 5M units
                                        line("user", "12:00:00", "?"), message("c", "12:01:00", 1)])  # 5 units
        self.log(("2026-11-24T00:00:00Z", 10, WEEK_END), ("2026-11-25T10:00:00Z", 40, WEEK_END))
        _, out, _ = self.run_code("stats")
        self.assertIn("  Перепитування 2, ", out)  # the 5-unit re-ask counts too
        self.assertEqual(self.cause(out, "Переробка")[0], "100%")  # 5M + 5 of ~5M units: both are summed

    # protects: Rule
    def test_large_context_is_the_whole_units_of_a_message_over_200k_prompt_and_cold_is_a_late_turns_cache_write(self):
        def turn(stamp, mid, usage):
            return [{"type": "user", "timestamp": f"2026-11-24T{stamp}Z", "origin": {"kind": "human"},
                     "message": {"content": "go"}},
                    {"type": "assistant", "timestamp": f"2026-11-24T{stamp}Z",
                     "message": {"id": mid, "model": "claude-sonnet-5-5", "content": [], "usage": usage}}]

        hour = {"ephemeral_1h_input_tokens": 1000, "ephemeral_5m_input_tokens": 0}
        self.write("proj/sess1.jsonl",
                   turn("10:00:00", "a1", {"cache_read_input_tokens": 250000, "output_tokens": 1000})  # large: 30000
                   + turn("10:05:00", "a2", {"cache_creation": hour, "output_tokens": 10})  # 1h write: lifetime 60 min
                   + turn("11:30:00", "a3", {"cache_creation": {"ephemeral_5m_input_tokens": 2000}})  # 85 min: cold, 2500
                   + turn("11:34:00", "a4", {"cache_creation": {"ephemeral_5m_input_tokens": 100}})  # 4 min: warm
                   + turn("11:50:00", "a5", {"cache_creation": {"ephemeral_5m_input_tokens": 400}})  # 16 min > 5: cold, 500
                   + turn("11:51:00", "a6", {"cache_read_input_tokens": 200000}))  # not above 200k
        self.write("proj/sess1/subagents/agent-a.jsonl",
                   turn("12:00:00", "h1", {"input_tokens": 300000}))  # a helper's message over 200k: 300000
        causes = spend.collect(NOW - spend.WEEK, WEEK_END)["causes"]
        self.assertEqual((causes["large context"], causes["cold restarts"]), (330000, 3000))
        self.assertEqual(spend.collect(NOW - spend.WEEK, WEEK_END)["causes"]["large context"], 330000)  # a repeat is stable

    # protects: Edge
    def test_a_week_archived_before_the_causes_existed_gives_no_data_for_last_week(self):
        self.session("now", "2026-11-24", 3, 1)
        self.log(("2026-11-24T00:00:00Z", 10, WEEK_END), ("2026-11-25T10:00:00Z", 40, WEEK_END))
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "weekly.jsonl").write_text(json.dumps(
            {"v": 1, "start": "2026-11-09T00:00:00Z", "end": "2026-11-16T00:00:00Z", "pct": 50, "units": 1000,
             "limit_units": 2000, "projects": {}, "tasks": {}, "agents": {}, "skills": {}}) + "\n", encoding="utf-8")
        _, out, _ = self.run_code("stats")
        self.assertEqual(self.cause(out, "Дорогі моделі"), ("33%", "минулого тижня немає даних"))
        _, detail, _ = self.run_code("stats", "--detail", "agents")
        self.assertNotIn("Куди пішли токени", detail)  # a detail view shows one group
