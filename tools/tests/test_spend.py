"""spend-kit: units, the per-session share of the weekly limit, the weekly limit fit, critical problems, the findings
a reader takes, the per-session spend file, the one-time move from dev-kit and the status line log."""
import datetime
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parent.parent.parent / "plugins" / "spend-kit"
sys.path.insert(0, str(PLUGIN / "scripts"))
import signals  # noqa: E402
import spend  # noqa: E402
import spend_dir  # noqa: E402
import statusline  # noqa: E402


def assistant(message_id, model, usage, stamp, **extra):
    return {"type": "assistant", "timestamp": stamp, **extra,
            "message": {"id": message_id, "model": model, "usage": usage, "content": []}}


def wake(stamp, summary="Background command finished"):
    return {"type": "user", "timestamp": stamp, "origin": {"kind": "task-notification"},
            "message": {"content": f"<task-notification><summary>{summary}</summary></task-notification>"}}


def reply(message_id, usage, stamp, *blocks):
    """A Sonnet message; a block is `("text", "words")` or `(tool name, run in background)`."""
    content = [{"type": "text", "text": arg} if name == "text" else
               {"type": "tool_use", "id": f"{message_id}{n}", "name": name,
                "input": {"command": "x", "run_in_background": True} if arg else {"command": "x"}}
               for n, (name, arg) in enumerate(blocks)]
    return {"type": "assistant", "timestamp": stamp,
            "message": {"id": message_id, "model": "claude-sonnet-5-5", "usage": usage, "content": content}}


class SpendFixture(unittest.TestCase):
    """Temp spend-kit data, projects and usage log folders; no old dev-kit folder, so nothing reads the real `~/.claude`."""

    def setUp(self):
        tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, tmp, True)
        self.tmp = tmp
        self.data = tmp / "spend"
        self.projects = tmp / "projects"
        (self.projects / "proj").mkdir(parents=True)
        self.plugins = tmp / "plugins"  # the agent files of the signals: none, so no run is held against a real file
        patcher = mock.patch.dict(os.environ, {spend_dir.DIR_ENV: str(self.data), spend.PROJECTS_ENV: str(self.projects),
                                               statusline.USAGE_ENV: str(tmp / "usage"),
                                               signals.PLUGINS_ENV: str(self.plugins)})
        patcher.start()
        os.environ.pop(spend_dir.OLD_ENV, None)  # restored with the patch
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        self.addCleanup(patcher.stop)

    def write(self, rel, entries, mode="w"):
        """A transcript file; every line gets a `cwd`."""
        path = self.projects / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, mode, encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps({"cwd": str(self.tmp / "repo"), **entry}) + "\n")
        return path

    def run_cmd(self, *args):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            spend.main(list(args))
        return out.getvalue()

    def run_code(self, *args):
        """(exit code, stdout, stderr) of a command."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = spend.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def millions(self, mid, stamp, tokens_m=1):
        """A Sonnet message of `tokens_m` million output tokens = 5 * tokens_m million units."""
        return assistant(mid, "claude-sonnet-5-5", {"output_tokens": tokens_m * 1_000_000}, stamp)

    def state(self):
        return json.loads((self.data / "state.json").read_text(encoding="utf-8"))

    def findings(self, *args):
        """`(lines, table)` of one `findings` call."""
        data = json.loads(self.run_cmd("findings", *args))
        return [entry["line"] for entry in data["findings"]], data["table"]


class UnitsTestCase(SpendFixture):
    # protects: Rule
    def test_units_weigh_kinds_and_models_and_count_a_message_once(self):
        usage = {"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 100,
                 "cache_creation": {"ephemeral_5m_input_tokens": 4, "ephemeral_1h_input_tokens": 5}}
        self.assertAlmostEqual(spend.units_of(usage, "claude-sonnet-5-5"), 10 + 10 + 10 + 5 + 10)
        self.assertAlmostEqual(spend.units_of(usage, "claude-opus-5-5"), 45 * 1.5)
        self.assertAlmostEqual(spend.units_of({"cache_creation_input_tokens": 8}, "claude-haiku-5-5"), 10 / 3)
        line = assistant("m1", "claude-opus-5-5", {"output_tokens": 10}, "2026-11-19T10:00:00Z")
        old = assistant("m0", "claude-opus-5-5", {"output_tokens": 999}, "2026-11-18T10:00:00Z")
        seen = set()
        result = spend.analyse([json.dumps(e) for e in (old, line, line)], seen, spend.parse_time("2026-11-19T00:00:00Z"))
        self.assertEqual(result["units"], {"opus": 75})
        self.assertEqual(spend.analyse([json.dumps(line)], seen)["units"], {})  # the same id in another file

    def day_units(self, entries):
        """The per-day table of units of some transcript lines, all days summed."""
        days = spend.analyse([json.dumps(e) for e in entries])["days"]
        return {key: sum(row[key] for row in days.values()) for key in ("units", "idle", "cold", "bloat", "wakes")}

    # protects: Rule
    def test_idle_wake_is_a_notification_turn_that_only_re_arms_and_looks_up(self):
        quiet = [wake("2026-11-19T12:00:00Z"),
                 reply("m1", {"output_tokens": 1000}, "2026-11-19T12:00:05Z", ("text", "ok"), ("Bash", True))]
        busy = [wake("2026-11-19T13:00:00Z"),
                reply("m2", {"output_tokens": 1000}, "2026-11-19T13:00:05Z", ("Bash", True), ("SendMessage", False))]
        agent = [wake("2026-11-19T14:00:00Z", 'Agent "x" finished'),
                 reply("m3", {"output_tokens": 1000}, "2026-11-19T14:00:05Z", ("Bash", True))]
        owner = [{"type": "user", "timestamp": "2026-11-19T15:00:00Z", "origin": {"kind": "human"},
                  "message": {"content": "hi"}},
                 reply("m4", {"output_tokens": 1000}, "2026-11-19T15:00:05Z", ("Bash", True))]
        self.assertEqual(self.day_units(quiet + busy + agent + owner),
                         {"units": 20000, "idle": 5000, "cold": 0, "bloat": 0, "wakes": 1})

    # protects: Edge
    def test_cold_restart_is_the_cache_write_of_a_wake_after_a_gap_not_of_the_owner(self):
        write = {"cache_creation": {"ephemeral_1h_input_tokens": 1000, "ephemeral_5m_input_tokens": 0}}
        peer = {"type": "user", "timestamp": "2026-11-19T13:00:00Z", "origin": {"kind": "peer"},
                "message": {"content": "Manager report"}}
        soon = {**peer, "timestamp": "2026-11-19T13:10:00Z"}
        owner = {"type": "user", "timestamp": "2026-11-19T16:00:00Z", "origin": {"kind": "human"},
                 "message": {"content": "hi"}}
        entries = [owner, reply("m1", write, "2026-11-19T10:00:00Z"),
                   peer, reply("m2", write, "2026-11-19T13:00:05Z"),  # 3 h after m1: cold, 1000 * 2 units
                   soon, reply("m3", write, "2026-11-19T13:10:05Z"),  # 10 min after m2: warm
                   {**owner, "timestamp": "2026-11-19T16:30:00Z"}, reply("m4", write, "2026-11-19T16:30:05Z")]
        self.assertEqual(self.day_units(entries)["cold"], 2000)

    # protects: Rule
    def test_bloated_context_is_the_cache_read_above_the_limit(self):
        owner = {"type": "user", "timestamp": "2026-11-19T12:00:00Z", "message": {"content": "hi"}}
        entries = [owner, reply("m1", {"cache_read_input_tokens": spend.BLOAT_CONTEXT + 50000},
                                "2026-11-19T12:00:05Z"),
                   reply("m2", {"cache_read_input_tokens": spend.BLOAT_CONTEXT}, "2026-11-19T12:00:10Z")]
        self.assertAlmostEqual(self.day_units(entries)["bloat"], 5000)

    # protects: Rule
    def test_range_units_counts_main_chain_messages_in_the_byte_range_once(self):
        first = json.dumps(assistant("a", "claude-sonnet-5-5", {"output_tokens": 10}, "2026-11-19T10:00:00Z")) + "\n"
        rest = [assistant("b", "claude-sonnet-5-5", {"output_tokens": 20}, "2026-11-19T10:01:00Z"),
                assistant("b", "claude-sonnet-5-5", {"output_tokens": 20}, "2026-11-19T10:01:01Z"),
                assistant("c", "claude-sonnet-5-5", {"output_tokens": 999}, "2026-11-19T10:02:00Z", isSidechain=True)]
        path = self.projects / "proj" / "r.jsonl"
        path.write_bytes(first.encode("utf-8") + "".join(json.dumps(e) + "\n" for e in rest).encode("utf-8"))
        start, end = len(first.encode("utf-8")), path.stat().st_size
        self.assertEqual(spend.range_units(path, start, end), 100)  # b once; the side chain and a are out
        self.assertEqual(spend.range_units(path, 0, end), 150)
        self.assertEqual(self.run_cmd("units", "--path", str(path), "--from", str(start), "--to", str(end)), "100.000\n")


class FindingsTestCase(SpendFixture):
    def spending_session(self, stamp, output, mid):
        return [assistant(mid, "claude-sonnet-5-5", {"output_tokens": output}, stamp)]

    # protects: Flow
    def test_long_session_and_opus_coder_are_findings_and_spend_is_listed_apart(self):
        entries = [{"type": "custom-title", "customTitle": "C: Long"}]
        for n in range(60):
            entries.append({"type": "user", "timestamp": "2026-11-19T10:00:00Z", "message": {"content": "go"}})
            entries.append(assistant(f"L{n}", "claude-opus-5-5", {"output_tokens": 100}, "2026-11-19T10:00:01Z"))
        self.write("proj/long1234.jsonl", entries)
        self.write("proj/short123.jsonl", [{"type": "user", "timestamp": "2026-11-19T10:00:00Z",
                                            "message": {"content": "hi"}},
                                           assistant("S", "claude-opus-5-5", {"output_tokens": 50}, "2026-11-19T10:00:01Z")])
        for n, model in enumerate(("claude-opus-5-5", "claude-sonnet-5-5")):
            self.write(f"proj/long1234/subagents/agent-{n}.jsonl",
                       [assistant(f"A{n}", model, {"output_tokens": 1000}, "2026-11-19T10:00:00Z")])
            (self.projects / f"proj/long1234/subagents/agent-{n}.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        lines, table = self.findings()
        text = "\n".join(lines)
        self.assertNotIn("long session", text)  # 60 turns so far
        self.assertIn("- proj | C: Long (long1234) / subagent dev-kit:coder | opus coder | 7.5k units", lines)  # under 10 Sonnet runs: no ratio
        table = "\n".join(table)  # spend is evidence, not findings
        self.assertIn("| proj | C: Long (long1234) | opus 100% | 60 | 45k | 12k | 99% |", table)
        self.assertIn("| dev-kit:coder | opus | 1 | 7.5k |", table)
        with open(self.projects / "proj/long1234.jsonl", "a", encoding="utf-8") as handle:
            for n in range(40):
                handle.write(json.dumps({"type": "user", "timestamp": "2099-01-01T10:00:00Z",
                                         "message": {"content": "more"}}) + "\n")
                handle.write(json.dumps(assistant(f"M{n}", "claude-opus-5-5", {"output_tokens": 300},
                                                  "2099-01-01T10:00:01Z")) + "\n")
        for n in range(10):  # ten short sessions make a usual cost per turn
            self.write(f"proj/short{n}.jsonl", [{"type": "user", "timestamp": "2099-01-01T10:00:00Z",
                                                 "message": {"content": "x"}},
                                                assistant(f"S{n}x", "claude-opus-5-5", {"output_tokens": 50},
                                                          "2099-01-01T10:00:01Z")])
        with mock.patch.object(spend, "today", return_value="2099-01-01"):
            lines, _ = self.findings()
        long_lines = [line for line in lines if "long session" in line]
        self.assertEqual(len(long_lines), 1)
        self.assertIn("C: Long (long1234) | long session | 100 main turns so far; this scan 40 turns at 2.2k units per "
                      "turn, x6.0 of a session under 50 turns", long_lines[0])

    # protects: Bug
    # Broke: the retro scan summed the runs of one subagent type, so two coder runs read as one run
    def test_two_runs_of_one_subagent_type_and_model_are_two_runs_in_the_spend_table(self):
        self.write("proj/main1234.jsonl", [assistant("a", "claude-sonnet-5-5", {"output_tokens": 100},
                                                     "2026-11-19T10:00:00Z")])
        for n in range(2):
            self.write(f"proj/main1234/subagents/agent-{n}.jsonl",
                       [assistant(f"A{n}", "claude-sonnet-5-5", {"output_tokens": 200}, "2026-11-19T10:00:00Z")])
            (self.projects / f"proj/main1234/subagents/agent-{n}.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        _, table = self.findings()
        self.assertIn("| dev-kit:coder | sonnet | 2 | 2.0k | 1.0k |", "\n".join(table))  # two runs, 1.0k each

    # protects: Rule
    def test_findings_are_taken_once_and_name_the_folder_and_title_of_their_session(self):
        self.write("proj/big12345.jsonl", [{"type": "custom-title", "customTitle": "C: Big"}]
                   + [assistant("a", "claude-opus-5-5", {"output_tokens": 100}, "2026-11-19T10:00:00Z")])
        self.write("proj/big12345/subagents/agent-0.jsonl",
                   [assistant("c", "claude-opus-5-5", {"output_tokens": 100}, "2026-11-19T10:00:00Z")])
        (self.projects / "proj/big12345/subagents/agent-0.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        data = json.loads(self.run_cmd("findings"))
        self.assertEqual([(e["session"], e["title"], e["cwd"]) for e in data["findings"]],
                         [("proj/big12345", "C: Big", str(self.tmp / "repo"))])
        self.assertEqual(json.loads(self.run_cmd("findings")), {"findings": [], "table": []})  # taken, nothing new

    # protects: Flow
    def test_critical_shows_a_problem_once_and_again_when_it_grew(self):
        title = {"type": "custom-title", "customTitle": "C: Big"}
        path = self.write("proj/big12345.jsonl", [title] + self.spending_session("2099-01-01T12:00:00Z", 500, "a"))
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100000), mock.patch.object(spend, "today") as today:
            today.return_value = "2099-01-01"
            first = self.run_cmd("critical")
            self.assertEqual(first, "critical | proj | C: Big (big12345) | 2099-01-01 | "
                                    "spent 2.5% of the weekly limit (2.5k units)\n")
            self.assertEqual(self.run_cmd("critical"), "")  # shown, not grown
            today.return_value = "2099-01-02"
            with open(path, "a", encoding="utf-8") as handle:  # 500 units more: 3.0%, under 1.25 x 2.5%
                handle.write(json.dumps(self.spending_session("2099-01-01T13:00:00Z", 100, "b")[0]) + "\n")
            self.assertEqual(self.run_cmd("critical"), "")
            today.return_value = "2099-01-03"
            with open(path, "a", encoding="utf-8") as handle:  # 3000 units more: 6.0%
                handle.write(json.dumps(self.spending_session("2099-01-01T14:00:00Z", 600, "c")[0]) + "\n")
            self.assertIn("spent 6.0% of the weekly limit (6.0k units) (was 2.5% when last shown)", self.run_cmd("critical"))

    # protects: Rule
    def test_problems_below_critical_are_findings_once_their_day_is_over(self):
        title = {"type": "custom-title", "customTitle": "C: Mid"}
        self.write("proj/mid12345.jsonl", [title] + self.spending_session("2099-01-01T12:00:00Z", 150, "a"))
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100000), mock.patch.object(spend, "today") as today:
            today.return_value = "2099-01-01"
            self.assertNotIn("token spend", "\n".join(self.findings()[0]))  # the day is not over
            today.return_value = "2099-01-02"
            lines, _ = self.findings()
            self.assertEqual(self.run_cmd("critical"), "")  # 0.75% is under the critical 2%
            self.assertEqual(self.findings()[0], [])  # the day's line is written once
        self.assertEqual(lines, ["- proj | C: Mid (mid12345) | token spend | 2099-01-01: spent 0.75% of the weekly limit "
                                 "(750 units)"])

    # protects: Rule
    def test_every_session_counts_including_a_retro_titled_one(self):
        self.write("proj/abcdef1234.jsonl", [{"type": "custom-title", "customTitle": "Retro: repo"},
                                             assistant("a", "claude-sonnet-5-5", {"output_tokens": 500},
                                                       "2026-11-19T10:40:00Z")])
        self.run_cmd("scan")
        units = sum(day["proj/abcdef1234"]["units"] for day in self.state()["daily"].values()
                    if "proj/abcdef1234" in day)
        self.assertEqual(units, 2500)

    # protects: Rule
    def test_a_second_scan_reads_only_new_lines_and_a_transcript_scan_only_its_session(self):
        path = self.write("proj/aaaa1111.jsonl", self.spending_session("2026-11-19T10:00:00Z", 100, "a"))
        other = self.write("proj/bbbb2222.jsonl", self.spending_session("2026-11-19T10:00:00Z", 100, "b"))
        self.assertIn("scanned 2 transcript(s)", self.run_cmd("scan"))
        self.assertIn("already scanned today", self.run_cmd("scan"))
        self.write("proj/aaaa1111.jsonl", self.spending_session("2026-11-19T10:01:00Z", 100, "a2"), mode="a")
        self.write("proj/bbbb2222.jsonl", self.spending_session("2026-11-19T10:01:00Z", 100, "b2"), mode="a")
        self.assertIn("scanned 1 transcript(s)", self.run_cmd("scan", "--transcript", str(path)))
        offsets = self.state()["offsets"]
        self.assertEqual(offsets[str(path)], path.stat().st_size)
        self.assertLess(offsets[str(other)], other.stat().st_size)

    # protects: Rule
    def test_a_held_lock_stops_a_transcript_scan_and_a_stale_lock_is_taken(self):
        main = self.write("proj/abcdef1234.jsonl", self.spending_session("2026-11-19T10:00:00Z", 100, "a"))
        lock = self.data / spend.LOCK_NAME
        self.data.mkdir(parents=True)
        lock.write_text("1", encoding="ascii")
        with mock.patch.object(spend, "LOCK_WAIT_TRANSCRIPT_S", 0.2), mock.patch.object(spend, "LOCK_WAIT_FULL_S", 0.2):
            self.assertEqual(self.run_cmd("scan", "--transcript", str(main)), "")  # quiet, nothing changed
            self.assertIn("scan busy", self.run_cmd("scan"))
        self.assertFalse((self.data / "state.json").exists())
        old = time.time() - spend.LOCK_STALE_S - 5
        os.utime(lock, (old, old))
        self.run_cmd("scan", "--transcript", str(main))
        self.assertTrue((self.data / "state.json").exists())
        self.assertFalse(lock.exists())  # released


class SessionTestCase(SpendFixture):
    # protects: Flow
    def test_session_sums_main_and_subagents_once_per_message_id(self):
        stamp = "2026-11-19T10:00:00Z"
        self.write("proj/sess1.jsonl", [self.millions("m1", stamp), self.millions("m1", stamp),
                                        self.millions("m2", stamp)])
        self.write("proj/sess1/subagents/agent-a.jsonl", [self.millions("s1", stamp, 2), self.millions("m2", stamp)])
        self.write("proj/sess1/subagents/agent-b.jsonl", [self.millions("s2", stamp)])
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 200e6):
            code, out, _ = self.run_code("session", "--id", "sess1")
            _, main_only, _ = self.run_code("session", "--id", "sess1", "--no-subagents")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), [
            "~12.5% of the weekly limit, estimate",
            "main 5.0%, subagents 7.5% (2 runs); 25.0M units; limit 200M units (fit 2026-11-20)"])
        self.assertEqual(main_only.splitlines()[0], "~5.0% of the weekly limit, estimate")
        self.assertNotIn("subagents", main_only)

    # protects: Flow
    def test_session_defaults_to_the_env_id_and_counts_a_resumed_copy_once(self):
        stamp = "2026-11-19T10:00:00Z"
        self.write("proj/sess1.jsonl", [self.millions("m1", stamp)])
        self.write("other/sess1.jsonl", [self.millions("m1", stamp), self.millions("m3", stamp)])  # resumed copy
        self.write("proj/sess2.jsonl", [self.millions("x", stamp, 50)])
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": "sess1"}), \
                mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100e6):
            _, out, _ = self.run_code("session")
        self.assertEqual(out.splitlines()[0], "~10.0% of the weekly limit, estimate")

    # protects: Edge
    def test_session_without_id_or_file_is_an_error_and_a_tiny_share_is_not_zero(self):
        code, _, err = self.run_code("session")
        self.assertEqual(code, 2)
        self.assertIn("no session", err)
        code, _, err = self.run_code("session", "--id", "missing")
        self.assertEqual(code, 2)
        self.assertIn("no transcript found", err)
        path = self.write("proj/tiny.jsonl", [assistant("t", "claude-sonnet-5-5", {"output_tokens": 100},
                                                        "2026-11-19T10:00:00Z")])
        code, out, _ = self.run_code("session", "--path", str(path))
        self.assertEqual(out.splitlines()[0], "<0.1% of the weekly limit, estimate")

    # protects: Flow
    def test_write_session_writes_the_spend_file_other_plugins_read(self):
        stamp = "2026-11-19T10:00:00Z"
        entries = [{"type": "custom-title", "customTitle": "C: Spend"},
                   {"type": "user", "timestamp": stamp, "message": {"content": "go"}}, self.millions("m1", stamp),
                   wake(stamp), reply("m2", {"output_tokens": 1000}, stamp, ("text", "ok"), ("Bash", True))]
        self.write("proj/sess1.jsonl", entries)
        self.write("proj/sess1/subagents/agent-a.jsonl", [self.millions("s1", stamp, 2)])
        (self.projects / "proj/sess1/subagents/agent-a.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100e6):
            code, out, _ = self.run_code("write-session", "--id", "sess1")
        self.assertEqual(code, 0)
        written = json.loads((self.data / "sessions" / "sess1.json").read_text(encoding="utf-8"))
        self.assertIn("sess1.json", out)
        self.assertEqual((written["session"], written["title"], written["cwd"]), ("sess1", "C: Spend", str(self.tmp / "repo")))
        self.assertEqual((written["units"], written["limit_units"]), (15_005_000, 100_000_000))
        self.assertAlmostEqual(written["share_pct"], 15.005)
        self.assertEqual((written["main"]["units"], written["main"]["turns"]), (5_005_000, 2))
        self.assertEqual(written["subagents"]["runs"], [{"type": "dev-kit:coder", "model": "sonnet", "units": 10_000_000}])
        self.assertEqual(written["models"], {"sonnet": 15_005_000})
        self.assertEqual((written["waste"]["idle"], written["waste"]["wakes"]), (5000, 1))  # the quiet wake turn
        code, _, err = self.run_code("write-session", "--id", "missing")
        self.assertEqual(code, 2)
        self.assertIn("no transcript found", err)

    # protects: Edge
    def test_hook_end_starts_the_writing_only_for_an_existing_transcript_and_never_fails(self):
        transcript = self.projects / "proj" / "abcdef01.jsonl"
        spawned = []
        with mock.patch.object(spend, "spawn", lambda argv: spawned.append(argv)):
            for payload in ({"transcript_path": str(transcript)}, {}, {"transcript_path": 5}):  # missing, none, odd
                spend.hook_end(payload)
            self.assertEqual(spawned, [])
            transcript.write_text("{}\n", encoding="utf-8")
            spend.hook_end({"transcript_path": str(transcript)})
        self.assertEqual(spawned, [[sys.executable, "-X", "utf8", str(Path(spend.__file__).resolve()), "write-session",
                                    "--path", str(transcript), "--archive"]])
        for data in (b"not json", b"", b"[1]", b"\xff\xfe", b'{"transcript_path": 5}'):
            result = subprocess.run([sys.executable, str(PLUGIN / "hooks" / "session-end.py")], input=data,
                                    capture_output=True)
            self.assertEqual((result.returncode, result.stdout), (0, b""), data)


class FitTestCase(SpendFixture):
    def log(self, *readings):
        """Write the usage log: `(time, per cent, reset)` per reading."""
        folder = Path(os.environ[statusline.USAGE_ENV])
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / statusline.LOG_NAME, "w", encoding="utf-8") as handle:
            for stamp, pct, resets in readings:
                handle.write(json.dumps({"ts": stamp, "week_pct": pct, "week_resets": resets,
                                         "five_hour_pct": None}) + "\n")

    def week_clock(self, oldest="2026-11-01"):
        """Fix the clock at 2026-11-20 and add an empty transcript last written on `oldest`: the oldest transcript
        kept, so the log readings of 2026-11-10..19 lie inside the kept range."""
        now = datetime.datetime(2026, 11, 20, 12, tzinfo=datetime.timezone.utc)
        patcher = mock.patch.object(spend, "now_utc", return_value=now)
        patcher.start()
        self.addCleanup(patcher.stop)
        stamp = datetime.datetime.fromisoformat(oldest).replace(tzinfo=datetime.timezone.utc).timestamp()
        path = self.write("ancient/oldest.jsonl", [])
        os.utime(path, (stamp, stamp))

    def two_windows(self):
        """A log of two closed windows (4 and 6 points; a third has one reading) and their transcripts, 5M units a
        message: 25M units over 10 points = a limit of 250M."""
        week1, week2 = 7 * 86400, 14 * 86400
        self.log(("2026-11-10T00:00:00Z", 10, week1), ("2026-11-11T00:00:00Z", 12, week1),
                 ("2026-11-12T00:00:00Z", 14, week1),
                 ("2026-11-17T00:00:00Z", 20, week2), ("2026-11-18T00:00:00Z", 26, week2),
                 ("2026-11-19T00:00:00Z", 30, 21 * 86400))  # a lone reading of another window: no delta
        self.write("proj/a.jsonl", [self.millions("before", "2026-11-10T00:00:00Z"),  # at the first reading: excluded
                                    self.millions("w1a", "2026-11-11T10:00:00Z"),
                                    self.millions("w1b", "2026-11-12T00:00:00Z"),  # at the last reading: included
                                    self.millions("gap", "2026-11-14T00:00:00Z"),  # between windows: excluded
                                    self.millions("w2a", "2026-11-17T12:00:00Z")])
        self.write("other/b.jsonl", [self.millions("w2a", "2026-11-17T12:00:00Z"),  # a resumed copy: once
                                     self.millions("w2b", "2026-11-17T13:00:00Z")])
        self.write("other/b/subagents/agent-x.jsonl", [self.millions("w2c", "2026-11-18T00:00:00Z")])

    # protects: Flow
    def test_calibrate_fits_the_limit_from_log_windows_over_all_transcripts(self):
        self.two_windows()
        self.week_clock()
        code, out, _ = self.run_code("calibrate")
        self.assertEqual(out.strip(), "weekly limit fitted: 250.0M units from 10.0 points in 2 window(s)")
        state = self.state()
        self.assertEqual(state["fit"], {"units": 250_000_000, "date": spend.today(), "points": 10.0, "windows": 2})
        self.assertEqual(spend.weekly_limit(), (250_000_000, spend.today()))
        self.write("proj/s.jsonl", [self.millions("z", "2026-11-19T10:00:00Z", 10)])
        _, out, _ = self.run_code("session", "--id", "s")
        self.assertEqual(out.splitlines()[0], "~20.0% of the weekly limit, estimate")  # 50M of 250M

    # protects: Rule
    def test_a_closed_window_is_cached_and_not_read_again(self):
        self.two_windows()
        self.week_clock()
        self.run_cmd("calibrate")
        self.assertEqual(sorted(window["units"] for window in self.state()["fit_windows"].values()), [10e6, 15e6])
        shutil.rmtree(self.projects / "proj")  # the transcripts of both closed windows are gone
        shutil.rmtree(self.projects / "other")
        _, out, _ = self.run_code("calibrate")
        self.assertEqual(out.strip(), "weekly limit fitted: 250.0M units from 10.0 points in 2 window(s)")

    # protects: Edge
    def test_a_window_older_than_the_fit_days_is_ignored(self):
        self.log(("2026-10-01T00:00:00Z", 10, 100 * 86400), ("2026-10-02T00:00:00Z", 40, 100 * 86400),  # 30 points
                 ("2026-11-10T00:00:00Z", 10, 107 * 86400), ("2026-11-12T00:00:00Z", 14, 107 * 86400))  # 4 points
        self.write("proj/a.jsonl", [self.millions("old", "2026-10-01T10:00:00Z"),
                                    self.millions("new", "2026-11-11T10:00:00Z")])
        self.week_clock(oldest="2026-09-01")
        _, out, _ = self.run_code("calibrate")
        self.assertIn("kept 690.0M units", out)
        self.assertIn("4.0 per cent points in 1 usable window(s)", out)

    # protects: Rule
    def test_a_window_that_began_before_the_oldest_transcript_is_ignored(self):
        self.log(("2026-11-10T00:00:00Z", 10, 7 * 86400), ("2026-11-12T00:00:00Z", 30, 7 * 86400),  # 20 points
                 ("2026-11-17T00:00:00Z", 20, 14 * 86400), ("2026-11-18T00:00:00Z", 26, 14 * 86400))  # 6 points
        self.write("proj/a.jsonl", [self.millions("w1", "2026-11-11T10:00:00Z"),
                                    self.millions("w2", "2026-11-17T12:00:00Z")])
        self.week_clock(oldest="2026-11-11")  # transcripts older than this are deleted: window 1 is partly lost
        _, out, _ = self.run_code("calibrate")
        self.assertIn("6.0 per cent points in 1 usable window(s)", out)
        self.assertEqual(spend.weekly_limit()[0], spend.WEEKLY_LIMIT_UNITS)

    # protects: Edge
    def test_reset_times_seconds_apart_are_one_window(self):
        edge = 7 * 86400 + 1795  # round(x / 3600) would put these 10 s apart on two sides of a half hour
        self.log(("2026-11-10T00:00:00Z", 10, edge), ("2026-11-12T00:00:00Z", 20, edge + 10))
        self.write("proj/a.jsonl", [self.millions("w1", "2026-11-11T10:00:00Z")])
        self.week_clock()
        _, out, _ = self.run_code("calibrate")
        self.assertEqual(out.strip(), "weekly limit fitted: 50.0M units from 10.0 points in 1 window(s)")

    # protects: Rule
    def test_readings_without_a_numeric_reset_time_are_skipped_by_the_fit(self):
        self.log(("2026-11-10T00:00:00Z", 10, None), ("2026-11-12T00:00:00Z", 40, None),
                 ("2026-11-13T00:00:00Z", 10, "tomorrow"), ("2026-11-14T00:00:00Z", 40, "tomorrow"))
        self.write("proj/a.jsonl", [self.millions("w1", "2026-11-11T10:00:00Z")])
        self.week_clock()
        _, out, _ = self.run_code("calibrate")
        self.assertIn("0.0 per cent points in 0 usable window(s)", out)

    # protects: Rule
    def test_a_stored_fit_sets_the_share_that_critical_shows(self):
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / "state.json").write_text(
            json.dumps({"fit": {"units": 100000, "date": "2026-11-15", "points": 12.0, "windows": 1}}), encoding="utf-8")
        self.write("proj/big12345.jsonl", [assistant("a", "claude-sonnet-5-5", {"output_tokens": 500},
                                                     "2099-01-01T12:00:00Z")])
        with mock.patch.object(spend, "today", return_value="2099-01-01"):
            self.assertIn("spent 2.5% of the weekly limit (2.5k units)", self.run_cmd("critical"))  # seed: 0.0004%

    # protects: Rule
    def test_calibrate_keeps_the_old_limit_below_the_minimum_points(self):
        self.log(("2026-11-10T00:00:00Z", 10, 604800), ("2026-11-12T00:00:00Z", 19, 604800))
        self.write("proj/a.jsonl", [self.millions("w1", "2026-11-11T10:00:00Z")])
        self.week_clock()
        _, out, _ = self.run_code("calibrate")
        self.assertIn("kept 690.0M units (2026-11-20)", out)
        self.assertEqual(spend.weekly_limit(), (spend.WEEKLY_LIMIT_UNITS, spend.WEEKLY_LIMIT_DATE))
        state = {"fit": {"units": 123_000_000, "date": "2026-11-15", "points": 12.0, "windows": 1}}
        (self.data / "state.json").write_text(json.dumps(state), encoding="utf-8")
        _, out, _ = self.run_code("calibrate")
        self.assertIn("kept 123.0M units (2026-11-15): the log spans 9.0 per cent points", out)
        self.assertEqual(spend.weekly_limit(), (123_000_000, "2026-11-15"))

    # protects: Flow
    def test_scan_refits_only_when_the_log_has_readings_newer_than_the_last_check(self):
        self.log(("2026-11-10T00:00:00Z", 10, 604800), ("2026-11-12T00:00:00Z", 20, 604800))
        self.write("proj/a.jsonl", [self.millions("w1", "2026-11-11T10:00:00Z")])  # 5M units over 10 points
        self.week_clock()
        self.run_cmd("scan")
        state = self.state()
        self.assertEqual(state["fit"]["units"], 50_000_000)
        state["fit"]["units"] = 77_000_000  # a marker: a second scan with the same log must not touch the fit
        (self.data / "state.json").write_text(json.dumps(state), encoding="utf-8")
        self.run_cmd("scan", "--force")
        self.assertEqual(spend.weekly_limit()[0], 77_000_000)
        self.log(("2026-11-10T00:00:00Z", 10, 604800), ("2026-11-12T00:00:00Z", 20, 604800),
                 ("2026-11-13T00:00:00Z", 30, 604800))
        self.run_cmd("scan", "--force")
        self.assertEqual(spend.weekly_limit()[0], 25_000_000)  # 5M units over 20 points


class MoveTestCase(SpendFixture):
    """The one-time copy of what spend-kit took over from dev-kit's folder."""

    def old_folder(self):
        old = self.tmp / "old-dev-kit"
        os.environ[spend_dir.OLD_ENV] = str(old)  # restored by the fixture's patch
        return old

    # protects: Flow
    def test_the_token_part_of_the_old_retro_state_is_copied_once_and_never_over_a_new_one(self):
        old = self.old_folder()
        (old / "retro").mkdir(parents=True)
        (old / "retro" / "state.json").write_text(json.dumps(
            {"fit": {"units": 123_000_000, "date": "2026-11-15"}, "offsets": {"a": 5}, "claude_version": "2.1.1",
             "daily": {"2026-11-19": {"proj/s": {"units": 1, "idle": 0, "cold": 0, "bloat": 0, "wakes": 0}}}}),
            encoding="utf-8")
        self.assertEqual(spend.weekly_limit(), (spend.WEEKLY_LIMIT_UNITS, spend.WEEKLY_LIMIT_DATE))  # a plain read moves nothing
        self.run_cmd("calibrate")
        state = self.state()
        self.assertEqual((state["fit"]["units"], state["offsets"]), (123_000_000, {"a": 5}))
        self.assertNotIn("claude_version", state)  # the retro's own keys stay with the retro
        self.assertIn("daily", state)
        state["fit"]["units"] = 5
        (self.data / "state.json").write_text(json.dumps(state), encoding="utf-8")
        self.run_cmd("calibrate")
        self.assertEqual(self.state()["fit"]["units"], 5)  # not copied again

    # protects: Flow
    def test_the_usage_log_is_copied_once_when_the_new_one_is_missing(self):
        old = self.old_folder()
        old.mkdir()
        (old / statusline.LOG_NAME).write_text('{"ts": "2026-11-10T00:00:00Z", "week_pct": 10}\n', encoding="utf-8")
        os.environ.pop(statusline.USAGE_ENV)
        path = statusline.log_file()
        self.assertEqual(path, self.data / statusline.LOG_NAME)
        self.assertIn('"week_pct": 10', path.read_text(encoding="utf-8"))
        path.write_text("new\n", encoding="utf-8")
        statusline.log_file()
        self.assertEqual(path.read_text(encoding="utf-8"), "new\n")  # a present file is never replaced

    # protects: Rule
    def test_with_a_throwaway_folder_the_real_old_folder_is_never_read(self):
        self.assertIsNone(spend_dir.old_dir())  # SPEND_KIT_DIR is set and SPEND_KIT_OLD_DIR is not


class StatuslineTestCase(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.folder = tmp / "dev-kit"
        patcher = mock.patch.dict(os.environ, {statusline.USAGE_ENV: str(self.folder)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_line(self, data):
        out = io.StringIO()
        code = statusline.main(io.BytesIO(data if isinstance(data, bytes) else json.dumps(data).encode("utf-8")), out)
        return code, out.getvalue()

    def payload(self, pct, resets, five=None):
        limits = {"seven_day": {"used_percentage": pct, "resets_at": resets}}
        if five is not None:
            limits["five_hour"] = {"used_percentage": five, "resets_at": resets - 100}
        return {"rate_limits": limits}

    def entries(self):
        path = self.folder / statusline.LOG_NAME
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    # protects: Flow
    def test_it_prints_the_week_and_logs_only_when_the_per_cent_rises_or_a_new_window_begins(self):
        week, next_week = 10_000_000, 10_000_000 + 604800
        self.assertEqual(self.run_line(self.payload(23.4, week, five=41)), (0, "тиждень: 23%\n"))
        self.run_line(self.payload(23.4, week, five=50))  # the same week reading: not logged again
        self.run_line(self.payload(24, week))
        self.run_line(self.payload(24, next_week))  # a new window with the same per cent
        rows = self.entries()
        self.assertEqual([(row["week_pct"], row["week_resets"], row["five_hour_pct"]) for row in rows],
                         [(23.4, week, 41), (24, week, None), (24, next_week, None)])
        self.assertRegex(rows[0]["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    # protects: Rule
    def test_a_lower_per_cent_in_the_same_window_and_an_older_window_are_not_logged(self):
        week = 10_000_000
        self.run_line(self.payload(30, week))
        self.assertEqual(self.run_line(self.payload(25, week + 20)), (0, "тиждень: 25%\n"))  # an idle session, stale
        self.run_line(self.payload(31, week + 20))  # a rise in the same window (reset time jitters): logged
        self.run_line(self.payload(90, week - 3600))  # an older window by an hour: stale
        self.run_line(self.payload(5, week + 604800))  # the next window starts low: logged
        self.assertEqual([(row["week_pct"], row["week_resets"]) for row in self.entries()],
                         [(30, week), (31, week + 20), (5, week + 604800)])

    # protects: Flow
    def test_a_high_five_hour_reading_is_logged_alone_once_per_rise_or_window(self):
        week = 10_000_000
        five = lambda pct, resets: {"rate_limits": {"seven_day": {"used_percentage": 40, "resets_at": week},  # noqa: E731
                                                    "five_hour": {"used_percentage": pct, "resets_at": resets}}}
        self.run_line(five(50, 5000))  # the first line of the log: a normal one
        self.run_line(five(79, 5000))  # below FIVE_LOG_FROM: not logged
        self.run_line(five(85, 5000))  # logged alone
        self.run_line(five(85, 5010))  # no rise in the same 5-hour window
        self.run_line(five(84, 5000 + 18000))  # a new 5-hour window, still high
        self.run_line(five(90, 5000 - 18000))  # an older window: a stale reading
        rows = self.entries()
        self.assertEqual([(row["five_hour_pct"], row["five_hour_resets"], row.get("five_only", False)) for row in rows],
                         [(50, 5000, False), (85, 5000, True), (84, 5000 + 18000, True)])

    # protects: Edge
    def test_the_last_line_is_found_in_a_log_longer_than_the_tail(self):
        self.folder.mkdir(parents=True)
        with open(self.folder / statusline.LOG_NAME, "w", encoding="utf-8") as handle:
            for n in range(200):
                handle.write(json.dumps({"ts": "2026-11-10T00:00:00Z", "week_pct": n % 50, "week_resets": 1000,
                                         "five_hour_pct": None}) + "\n")
        last = self.entries()[-1]["week_pct"]
        self.run_line(self.payload(last, 1000))
        self.assertEqual(len(self.entries()), 200)

    # protects: Rule
    def test_no_rate_limits_or_bad_input_prints_an_empty_line_and_writes_nothing(self):
        for data in ({"model": "x"}, {"rate_limits": {}}, {"rate_limits": {"seven_day": {"used_percentage": "7"}}},
                     b"not json", b"", b"[1, 2]"):
            self.assertEqual(self.run_line(data), (0, "\n"))
        self.assertFalse((self.folder / statusline.LOG_NAME).exists())

    # protects: Rule
    def test_a_log_that_cannot_be_written_does_not_raise(self):
        self.folder.write_text("a file where the folder should be", encoding="utf-8")
        self.assertEqual(self.run_line(self.payload(5, 1000)), (0, "\n"))


if __name__ == "__main__":
    unittest.main()
