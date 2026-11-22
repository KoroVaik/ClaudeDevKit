import io
import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit" / "scripts"))
import retro  # noqa: E402
import statusline  # noqa: E402


def call(tool_id, name, tool_input, stamp):
    return {"type": "assistant", "timestamp": stamp,
            "message": {"content": [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]}}


def result(tool_id, stamp, error=False):
    return {"type": "user", "timestamp": stamp,
            "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id, "is_error": error}]}}


def assistant(message_id, model, usage, stamp):
    return {"type": "assistant", "timestamp": stamp,
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


class RetroTestCase(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.retro = tmp / "retro"
        self.projects = tmp / "projects"
        (self.projects / "proj").mkdir(parents=True)
        patcher = mock.patch.dict(os.environ, {retro.RETRO_ENV: str(self.retro),
                                               retro.PROJECTS_ENV: str(self.projects),
                                               statusline.USAGE_ENV: str(tmp / "usage")})
        patcher.start()
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)  # restored with the patch
        self.addCleanup(patcher.stop)

    def write(self, rel, entries, mode="w"):
        path = self.projects / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, mode, encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps(entry) + "\n")
        return path

    def run_cmd(self, *args):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            retro.main(list(args))
        return out.getvalue()

    def session(self):
        entries = [{"type": "custom-title", "customTitle": "C: Task"}]
        for n in range(3):
            entries.append(call(f"r{n}", "Read", {"file_path": "a.py"}, f"2026-11-19T10:0{n}:00Z"))
            entries.append(result(f"r{n}", f"2026-11-19T10:0{n}:10Z", error=True))
        entries.append(call("s", "Bash", {"command": "make"}, "2026-11-19T10:10:00Z"))
        entries.append(result("s", "2026-11-19T10:25:00Z"))
        entries.append(call("w", "Bash", {"command": "watch", "run_in_background": True}, "2026-11-19T10:31:00Z"))
        entries.append(call("w2", "Bash", {"command": "watch", "run_in_background": True}, "2026-11-19T10:32:00Z"))
        entries.append(call("w3", "Bash", {"command": "watch", "run_in_background": True}, "2026-11-19T10:33:00Z"))
        return entries

    def test_scan_finds_repeats_errors_slow_calls_and_pauses(self):
        self.write("proj/abcdef1234.jsonl", self.session())
        self.assertIn("new findings: 4", self.run_cmd("check"))
        listing = self.run_cmd("list")
        self.assertIn("C: Task (abcdef12) | repeated call | Read x3", listing)
        self.assertIn("failed calls | 3 (Read x3)", listing)
        self.assertIn("slow call | Bash took 15 min", listing)
        self.assertIn("long pause | 2 pause(s)", listing)
        self.assertNotIn("watch", listing)  # background re-arms are by design

    def test_second_scan_reads_only_new_lines_and_once_a_day(self):
        path = self.write("proj/s1.jsonl", self.session())
        self.run_cmd("check")
        self.run_cmd("done")
        self.assertIn("no new findings", self.run_cmd("check"))
        self.write("proj/s1.jsonl", [call("x", "Grep", {"pattern": "a"}, "2026-11-19T11:00:00Z")], mode="a")
        self.assertIn("already scanned today", self.run_cmd("scan"))
        self.assertIn("scanned 1 transcript(s), 0 finding(s)", self.run_cmd("scan", "--force"))
        state = json.loads((self.retro / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["offsets"][str(path)], path.stat().st_size)

    def test_partial_last_line_waits(self):
        path = self.projects / "proj" / "s.jsonl"
        path.write_text(json.dumps(call("a", "Read", {}, "2026-11-19T10:00:00Z")) + "\n{\"type\": \"assi",
                        encoding="utf-8")
        self.run_cmd("scan")
        state = json.loads((self.retro / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["offsets"][str(path)], path.read_bytes().index(b"\n") + 1)

    def test_script_candidate_and_subagents_summed(self):
        for name in ("s1", "s2", "s3"):
            self.write(f"proj/{name}.jsonl", [call("b", "Bash", {"command": "npm  run build -- --mode production"}, "2026-11-19T10:00:00Z")])
        for n in range(2):
            self.write(f"proj/s1/subagents/agent-{n}.jsonl",
                       [call("c", "Glob", {"pattern": "*"}, "2026-11-19T10:00:00Z")] * 2)
            (self.projects / f"proj/s1/subagents/agent-{n}.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        self.run_cmd("scan")
        listing = self.run_cmd("list")
        self.assertIn("3 sessions | script candidate | npm run build -- --mode production", listing)
        self.assertIn("s1 / subagent dev-kit:coder | repeated call | Glob x4", listing)

    def test_notes_count_until_done(self):
        self.run_cmd("scan")
        (self.retro / "notes.md").write_text("- 2026-11-19 | p | C: X | correction | did Y\n", encoding="utf-8")
        self.assertIn("new findings: 1", self.run_cmd("check"))
        self.run_cmd("done")
        self.assertIn("no new findings", self.run_cmd("check"))

    def test_done_marks_only_what_was_shown(self):
        notes = self.retro / "notes.md"
        self.run_cmd("scan")
        notes.write_text("﻿- 2026-11-19 | p | C: X | correction | a\n", encoding="utf-8")
        self.assertIn("- 2026-11-19 | p | C: X", self.run_cmd("list"))
        with open(notes, "a", encoding="utf-8") as handle:
            handle.write("- 2026-11-19 | p | C: X | wrong order | b\n")
        self.run_cmd("done")
        self.assertIn("new findings: 1", self.run_cmd("check"))

    def test_units_weigh_kinds_and_models_and_count_a_message_once(self):
        usage = {"input_tokens": 10, "output_tokens": 2, "cache_read_input_tokens": 100,
                 "cache_creation": {"ephemeral_5m_input_tokens": 4, "ephemeral_1h_input_tokens": 5}}
        self.assertAlmostEqual(retro.units_of(usage, "claude-sonnet-5-5"), 10 + 10 + 10 + 5 + 10)
        self.assertAlmostEqual(retro.units_of(usage, "claude-opus-5-5"), 45 * 1.5)
        self.assertAlmostEqual(retro.units_of({"cache_creation_input_tokens": 8}, "claude-haiku-5-5"), 10 / 3)
        line = assistant("m1", "claude-opus-5-5", {"output_tokens": 10}, "2026-11-19T10:00:00Z")
        old = assistant("m0", "claude-opus-5-5", {"output_tokens": 999}, "2026-11-18T10:00:00Z")
        seen = set()
        result = retro.analyse([json.dumps(e) for e in (old, line, line)], seen,
                               retro.parse_time("2026-11-19T00:00:00Z"))
        self.assertEqual(result["units"], {"opus": 75})
        self.assertEqual(retro.analyse([json.dumps(line)], seen)["units"], {})  # the same id in another file

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
        self.run_cmd("scan")
        listing = self.run_cmd("list")
        self.assertNotIn("long session", listing)  # 60 turns so far
        self.assertIn("C: Long (long1234) / subagent dev-kit:coder | opus coder | 7.5k units\n", listing)  # under 10 Sonnet runs: no ratio
        self.assertIn("## Spend", listing)
        self.assertIn("| proj | C: Long (long1234) | opus 100% | 60 | 45k | 12k | 99% |", listing)
        self.assertIn("| dev-kit:coder | opus | 1 | 7.5k |", listing)
        self.run_cmd("done")
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
        with mock.patch.object(retro, "today", return_value="2099-01-01"):
            self.assertIn("new findings: 1", self.run_cmd("check"))
            listing = self.run_cmd("list")
        self.assertIn("C: Long (long1234) | long session | 100 main turns so far; this scan 40 turns at 2.2k units per turn, x6.0 of a session "
                      "under 50 turns", listing)

    def day_units(self, entries):
        """The per-day table of units of some transcript lines, all days summed."""
        days = retro.analyse([json.dumps(e) for e in entries])["days"]
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
                "message": {"content": "C report"}}
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
        entries = [owner, reply("m1", {"cache_read_input_tokens": retro.BLOAT_CONTEXT + 50000},
                                "2026-11-19T12:00:05Z"),
                   reply("m2", {"cache_read_input_tokens": retro.BLOAT_CONTEXT}, "2026-11-19T12:00:10Z")]
        self.assertAlmostEqual(self.day_units(entries)["bloat"], 5000)

    def spending_session(self, stamp, output, mid):
        return [assistant(mid, "claude-sonnet-5-5", {"output_tokens": output}, stamp)]

    # protects: Flow
    def test_critical_shows_a_problem_once_and_again_when_it_grew(self):
        title = {"type": "custom-title", "customTitle": "C: Big"}
        path = self.write("proj/big12345.jsonl", [title] + self.spending_session("2099-01-01T12:00:00Z", 500, "a"))
        with mock.patch.object(retro, "WEEKLY_LIMIT_UNITS", 100000), mock.patch.object(retro, "today") as today:
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
    def test_problems_below_critical_go_first_in_the_retro_list_once_their_day_is_over(self):
        title = {"type": "custom-title", "customTitle": "C: Mid"}
        other = [call("r", "Read", {"file_path": "a"}, "2099-01-01T12:00:00Z")] * 3
        self.write("proj/mid12345.jsonl", [title] + self.spending_session("2099-01-01T12:00:00Z", 150, "a") + other)
        with mock.patch.object(retro, "WEEKLY_LIMIT_UNITS", 100000), mock.patch.object(retro, "today") as today:
            today.return_value = "2099-01-01"
            self.run_cmd("scan")
            self.assertNotIn("token spend", self.run_cmd("list"))  # the day is not over
            today.return_value = "2099-01-02"
            self.run_cmd("scan")
            listing = self.run_cmd("list")
            self.assertEqual(self.run_cmd("critical"), "")  # 0.75% is under the critical 2%
        self.assertLess(listing.index("## Priority"), listing.index("token spend"))
        self.assertLess(listing.index("token spend"), listing.index("## Scan findings"))
        self.assertIn("| C: Mid (mid12345) | token spend | 2099-01-01: spent 0.75% of the weekly limit (750 units)", listing)
        self.assertLess(listing.index("## Scan findings"), listing.index("repeated call"))

    def test_first_scan_skips_old_files(self):
        path = self.write("proj/old.jsonl", self.session())
        os.utime(path, (0, 0))
        self.assertIn("scanned 0 transcript(s)", self.run_cmd("scan"))

    def run_code(self, *args):
        """(exit code, stdout, stderr) of a command."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = retro.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def millions(self, mid, stamp, tokens_m=1):
        """A Sonnet message of `tokens_m` million output tokens = 5 * tokens_m million units."""
        return assistant(mid, "claude-sonnet-5-5", {"output_tokens": tokens_m * 1_000_000}, stamp)

    # protects: Flow
    def test_session_sums_main_and_subagents_once_per_message_id(self):
        stamp = "2026-11-19T10:00:00Z"
        self.write("proj/sess1.jsonl", [self.millions("m1", stamp), self.millions("m1", stamp),
                                        self.millions("m2", stamp)])
        self.write("proj/sess1/subagents/agent-a.jsonl", [self.millions("s1", stamp, 2), self.millions("m2", stamp)])
        self.write("proj/sess1/subagents/agent-b.jsonl", [self.millions("s2", stamp)])
        with mock.patch.object(retro, "WEEKLY_LIMIT_UNITS", 200e6):
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
                mock.patch.object(retro, "WEEKLY_LIMIT_UNITS", 100e6):
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

    def log(self, *readings):
        """Write the usage log: `(time, per cent, reset)` per reading."""
        folder = Path(os.environ[retro.statusline.USAGE_ENV])
        folder.mkdir(parents=True, exist_ok=True)
        with open(folder / retro.statusline.LOG_NAME, "w", encoding="utf-8") as handle:
            for stamp, pct, resets in readings:
                handle.write(json.dumps({"ts": stamp, "week_pct": pct, "week_resets": resets,
                                         "five_hour_pct": None}) + "\n")

    def week_clock(self, oldest="2026-11-01"):
        """Fix the clock at 2026-11-20 and add an empty transcript last written on `oldest`: the oldest transcript
        kept, so the log readings of 2026-11-10..19 lie inside the kept range."""
        now = datetime.datetime(2026, 11, 20, 12, tzinfo=datetime.timezone.utc)
        patcher = mock.patch.object(retro, "now_utc", return_value=now)
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
        state = json.loads((self.retro / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["fit"], {"units": 250_000_000, "date": retro.today(), "points": 10.0, "windows": 2})
        self.assertEqual(retro.weekly_limit(), (250_000_000, retro.today()))
        self.write("proj/s.jsonl", [self.millions("z", "2026-11-19T10:00:00Z", 10)])
        _, out, _ = self.run_code("session", "--id", "s")
        self.assertEqual(out.splitlines()[0], "~20.0% of the weekly limit, estimate")  # 50M of 250M

    # protects: Rule
    def test_a_closed_window_is_cached_and_not_read_again(self):
        self.two_windows()
        self.week_clock()
        self.run_cmd("calibrate")
        state = json.loads((self.retro / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(sorted(window["units"] for window in state["fit_windows"].values()), [10e6, 15e6])
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
        self.assertEqual(retro.weekly_limit()[0], retro.WEEKLY_LIMIT_UNITS)

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
        self.retro.mkdir(parents=True, exist_ok=True)
        (self.retro / "state.json").write_text(
            json.dumps({"fit": {"units": 100000, "date": "2026-11-15", "points": 12.0, "windows": 1}}), encoding="utf-8")
        self.write("proj/big12345.jsonl", self.spending_session("2099-01-01T12:00:00Z", 500, "a"))
        with mock.patch.object(retro, "today", return_value="2099-01-01"):
            self.assertIn("spent 2.5% of the weekly limit (2.5k units)", self.run_cmd("critical"))  # seed: 0.0004%

    # protects: Rule
    def test_calibrate_keeps_the_old_limit_below_the_minimum_points(self):
        self.log(("2026-11-10T00:00:00Z", 10, 604800), ("2026-11-12T00:00:00Z", 19, 604800))
        self.write("proj/a.jsonl", [self.millions("w1", "2026-11-11T10:00:00Z")])
        self.week_clock()
        _, out, _ = self.run_code("calibrate")
        self.assertIn("kept 690.0M units (2026-11-20)", out)
        self.assertEqual(retro.weekly_limit(), (retro.WEEKLY_LIMIT_UNITS, retro.WEEKLY_LIMIT_DATE))
        state = {"fit": {"units": 123_000_000, "date": "2026-11-15", "points": 12.0, "windows": 1}}
        (self.retro / "state.json").write_text(json.dumps(state), encoding="utf-8")
        _, out, _ = self.run_code("calibrate")
        self.assertIn("kept 123.0M units (2026-11-15): the log spans 9.0 per cent points", out)
        self.assertEqual(retro.weekly_limit(), (123_000_000, "2026-11-15"))

    # protects: Flow
    def test_scan_refits_only_when_the_log_has_readings_newer_than_the_last_check(self):
        self.log(("2026-11-10T00:00:00Z", 10, 604800), ("2026-11-12T00:00:00Z", 20, 604800))
        self.write("proj/a.jsonl", [self.millions("w1", "2026-11-11T10:00:00Z")])  # 5M units over 10 points
        self.week_clock()
        self.run_cmd("scan")
        state = json.loads((self.retro / "state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["fit"]["units"], 50_000_000)
        state["fit"]["units"] = 77_000_000  # a marker: a second scan with the same log must not touch the fit
        (self.retro / "state.json").write_text(json.dumps(state), encoding="utf-8")
        self.run_cmd("scan", "--force")
        self.assertEqual(retro.weekly_limit()[0], 77_000_000)
        self.log(("2026-11-10T00:00:00Z", 10, 604800), ("2026-11-12T00:00:00Z", 20, 604800),
                 ("2026-11-13T00:00:00Z", 30, 604800))
        self.run_cmd("scan", "--force")
        self.assertEqual(retro.weekly_limit()[0], 25_000_000)  # 5M units over 20 points


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
