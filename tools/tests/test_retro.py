import io
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
                                               retro.PROJECTS_ENV: str(self.projects)})
        patcher.start()
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


if __name__ == "__main__":
    unittest.main()
