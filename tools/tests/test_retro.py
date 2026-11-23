import contextlib
import io
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit"
sys.path.insert(0, str(PLUGIN / "scripts"))
import dev_kit_state  # noqa: E402
import retro  # noqa: E402
import sessions  # noqa: E402
import statusline  # noqa: E402


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                   capture_output=True)


def make_repo(path, retro_project=True):
    """A git repository; a retro project has the `## project-lead` line in its dev-kit profile."""
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "commit", "-q", "--allow-empty", "-m", "i")
    if retro_project:
        (path / ".claude").mkdir()
        (path / ".claude" / "dev-kit.md").write_text("# dev-kit profile\n\n## project-lead\n\n| a | b |\n",
                                                     encoding="utf-8")
    return path


def call(tool_id, name, tool_input, stamp):
    return {"type": "assistant", "timestamp": stamp,
            "message": {"content": [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]}}


def result(tool_id, stamp, error=False):
    return {"type": "user", "timestamp": stamp,
            "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id, "is_error": error}]}}


def app_result(tool_id, stamp, content, error=None):
    """A tool result with content; `error` None leaves `is_error` out, as the host does for a failed SendMessage."""
    block = {"type": "tool_result", "tool_use_id": tool_id, "content": content}
    if error is not None:
        block["is_error"] = error
    return {"type": "user", "timestamp": stamp, "message": {"content": [block]}}


def send_result(tool_id, stamp, success, message):
    """The host's SendMessage result: a JSON text with `success`."""
    return app_result(tool_id, stamp, [{"type": "text", "text": json.dumps({"success": success, "message": message})}])


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


class RetroFixture(unittest.TestCase):
    """Temp retro, projects and usage folders, one retro project `repo`; helpers for the tests that follow."""

    def setUp(self):
        tmp = Path(os.path.realpath(tempfile.mkdtemp()))  # git and the script report real paths
        self.addCleanup(shutil.rmtree, tmp, True)
        self.tmp = tmp
        self.retro = tmp / "retro"
        self.projects = tmp / "projects"
        (self.projects / "proj").mkdir(parents=True)
        self.repo = make_repo(tmp / "repo")
        self.folder = self.retro / dev_kit_state.folder_name(self.repo)  # the item folder of the retro project
        patcher = mock.patch.dict(os.environ, {retro.RETRO_ENV: str(self.retro),
                                               retro.PROJECTS_ENV: str(self.projects),
                                               retro.NO_START_ENV: "1",
                                               statusline.USAGE_ENV: str(tmp / "usage")})
        patcher.start()
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)  # restored with the patch
        self.addCleanup(patcher.stop)

    def write(self, rel, entries, mode="w", cwd=None):
        """A transcript file; every line gets the `cwd` that maps it to a project (default: the retro project)."""
        path = self.projects / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, mode, encoding="utf-8") as handle:
            for entry in entries:
                handle.write(json.dumps({"cwd": str(cwd or self.repo), **entry}) + "\n")
        return path

    def run_cmd(self, *args):
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            retro.main(list(args))
        return out.getvalue()

    def project_cmd(self, *args, project=None):
        """A command of the retro project (never the current folder, which is the plugin's own repository)."""
        return self.run_cmd(*args, "--project", str(project or self.repo))

    def new_files(self, folder=None):
        new = (folder or self.folder) / "new"
        return sorted(new.glob("*.md")) if new.is_dir() else []

    def new_text(self, folder=None):
        return "".join(path.read_text(encoding="utf-8") for path in self.new_files(folder))

    def global_state(self):
        return json.loads((self.retro / "state.json").read_text(encoding="utf-8"))


class RetroTestCase(RetroFixture):
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
        self.run_cmd("scan")
        self.assertEqual(sum(len(retro.read_lines(path)) for path in self.new_files()), 4)
        self.assertRegex(self.new_files()[0].name, rf"^scan-{retro.today()}-\d{{6}}\.md$")
        listing = self.project_cmd("items")
        self.assertIn("C: Task (abcdef12) | repeated call | Read x3", listing)
        self.assertIn("failed calls | 3 (Read x3)", listing)
        self.assertIn("slow call | Bash took 15 min", listing)
        self.assertIn("long pause | 2 pause(s)", listing)
        self.assertNotIn("watch", listing)  # background re-arms are by design

    def test_second_scan_reads_only_new_lines_and_once_a_day(self):
        path = self.write("proj/s1.jsonl", self.session())
        retro.write_json(self.retro / "state.json", {"facts_recheck": retro.today()})  # the weekly line is not this test's
        self.run_cmd("scan")
        self.project_cmd("items")
        self.project_cmd("done")
        self.assertEqual(self.new_files(), [])
        self.write("proj/s1.jsonl", [call("x", "Grep", {"pattern": "a"}, "2026-11-19T11:00:00Z")], mode="a")
        self.assertIn("already scanned today", self.run_cmd("scan"))
        self.assertIn("scanned 1 transcript(s), 0 finding(s)", self.run_cmd("scan", "--force"))
        self.assertEqual(self.new_files(), [])
        self.assertEqual(self.global_state()["offsets"][str(path)], path.stat().st_size)

    def test_partial_last_line_waits(self):
        path = self.projects / "proj" / "s.jsonl"
        path.write_text(json.dumps({"cwd": str(self.repo), **call("a", "Read", {}, "2026-11-19T10:00:00Z")})
                        + "\n{\"type\": \"assi", encoding="utf-8")
        self.run_cmd("scan")
        self.assertEqual(self.global_state()["offsets"][str(path)], path.read_bytes().index(b"\n") + 1)

    def test_script_candidate_and_subagents_summed(self):
        for name in ("s1", "s2", "s3"):
            self.write(f"proj/{name}.jsonl", [call("b", "Bash", {"command": "npm  run build -- --mode production"}, "2026-11-19T10:00:00Z")])
        for n in range(2):
            self.write(f"proj/s1/subagents/agent-{n}.jsonl",
                       [call("c", "Glob", {"pattern": "*"}, "2026-11-19T10:00:00Z")] * 2)
            (self.projects / f"proj/s1/subagents/agent-{n}.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        self.run_cmd("scan")
        listing = self.project_cmd("items")
        self.assertIn("3 sessions | script candidate | npm run build -- --mode production", listing)
        self.assertIn("s1 / subagent dev-kit:coder | repeated call | Glob x4", listing)

    # protects: Rule
    def test_a_script_candidate_over_several_projects_goes_to_the_plugins_own_project(self):
        other = make_repo(self.tmp / "other")
        command = {"command": "npm  run build -- --mode production"}
        self.write("proj/s1.jsonl", [call("b", "Bash", command, "2026-11-19T10:00:00Z")])
        self.write("proj2/s2.jsonl", [call("b", "Bash", command, "2026-11-19T10:00:00Z")], cwd=other)
        self.write("proj2/s3.jsonl", [call("b", "Bash", command, "2026-11-19T10:00:00Z")], cwd=other)
        self.run_cmd("scan")
        plugin = self.retro / dev_kit_state.folder_name(Path(retro.__file__).resolve().parents[3])
        self.assertIn("2 project(s) | 3 sessions | script candidate", self.new_text(plugin))
        self.assertNotIn("script candidate", self.new_text())
        self.assertNotIn("script candidate", self.new_text(self.retro / dev_kit_state.folder_name(other)))

    # protects: Rule
    def test_owner_notes_are_sorted_by_their_project_field_once(self):
        other = make_repo(self.tmp / "Other")
        self.write("proj/s1.jsonl", [call("a", "Read", {}, "2026-11-19T10:00:00Z")])
        self.write("proj/s2.jsonl", [call("a", "Read", {}, "2026-11-19T10:00:00Z")], cwd=other)
        notes = self.retro / "notes.md"
        self.retro.mkdir(parents=True, exist_ok=True)
        notes.write_text("﻿- 2026-11-19 | repo | C: X | correction | for repo\n"
                         "- 2026-11-19 | OTHER | C: Y | wrong order | for other, case ignored\n"
                         "- 2026-11-19 | stranger | C: Z | correction | no such project: dropped\n", encoding="utf-8")
        self.run_cmd("scan")
        self.assertIn("for repo", self.new_text())
        self.assertNotIn("for other", self.new_text())
        self.assertIn("for other, case ignored", self.new_text(self.retro / dev_kit_state.folder_name(other)))
        self.assertNotIn("no such project", self.new_text() + self.new_text(self.retro / dev_kit_state.folder_name(other)))
        with open(notes, "a", encoding="utf-8") as handle:
            handle.write("- 2026-11-20 | repo | C: X | correction | later line\n")
        self.run_cmd("scan", "--force")
        text = self.new_text()
        self.assertEqual(text.count("for repo"), 1)  # the first line is not sorted again
        self.assertIn("later line", text)

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
        listing = self.project_cmd("items")
        self.assertNotIn("long session", listing)  # 60 turns so far
        self.assertIn("C: Long (long1234) / subagent dev-kit:coder | opus coder | 7.5k units\n", listing)  # under 10 Sonnet runs: no ratio
        table = (self.retro / f"scan-{retro.today()}.md").read_text(encoding="utf-8")  # spend is evidence, not findings
        self.assertIn("## Spend", table)
        self.assertNotIn("## Spend", listing)
        self.assertIn("| proj | C: Long (long1234) | opus 100% | 60 | 45k | 12k | 99% |", table)
        self.assertIn("| dev-kit:coder | opus | 1 | 7.5k |", table)
        self.project_cmd("done")
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
            self.run_cmd("scan")
            listing = self.project_cmd("items")
        self.assertEqual(listing.count("long session"), 1)
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
            self.assertNotIn("token spend", self.project_cmd("items"))  # the day is not over
            today.return_value = "2099-01-02"
            self.run_cmd("scan")
            listing = self.project_cmd("items")
            self.assertEqual(self.run_cmd("critical"), "")  # 0.75% is under the critical 2%
        self.assertLess(listing.index("## Priority"), listing.index("token spend"))
        self.assertLess(listing.index("token spend"), listing.index("## New findings"))
        self.assertIn("| C: Mid (mid12345) | token spend | 2099-01-01: spent 0.75% of the weekly limit (750 units)", listing)
        self.assertLess(listing.index("## New findings"), listing.index("repeated call"))

    def test_first_scan_skips_old_files(self):
        path = self.write("proj/old.jsonl", self.session())
        os.utime(path, (0, 0))
        self.assertIn("scanned 0 transcript(s)", self.run_cmd("scan"))

    # protects: Rule
    def test_a_folder_belongs_to_the_retro_project_of_its_checkout_even_when_its_worktree_is_gone(self):
        worktree = self.tmp / "wt"
        git(self.repo, "worktree", "add", "-q", str(worktree), "-b", "side")
        plain = make_repo(self.tmp / "plain", retro_project=False)
        mapper = retro.Mapper()
        project = mapper.project_of_cwd(str(self.repo))
        self.assertEqual((project.name, project.folder), ("repo", dev_kit_state.folder_name(self.repo)))
        gone = str(self.repo / ".claude" / "worktrees" / "gone")
        for cwd in (str(worktree), str(self.repo / ".claude"), gone, gone + "\\sub", gone.replace("\\", "/"),
                    str(self.repo) + "\\.CLAUDE\\worktrees\\gone"):
            self.assertEqual(mapper.project_of_cwd(cwd), project, cwd)
        folder = self.tmp / "no-git"
        folder.mkdir()
        for cwd in (str(plain), str(plain / ".claude" / "worktrees" / "gone"), str(folder), str(self.tmp / "missing"),
                    "", None):
            self.assertIsNone(mapper.project_of_cwd(cwd), cwd)

    # protects: Rule
    def test_findings_of_other_projects_are_not_routed_but_their_tokens_still_count(self):
        plain = make_repo(self.tmp / "plain", retro_project=False)
        other = self.write("proj/abcdef01.jsonl", self.session(), cwd=plain)
        self.write("proj/12345678.jsonl", self.session())
        self.run_cmd("scan")
        text = self.new_text()
        self.assertIn("(12345678)", text)
        self.assertNotIn("(abcdef01)", text)
        log = (self.retro / f"scan-{retro.today()}.md").read_text(encoding="utf-8")
        self.assertIn("(abcdef01)", log)  # the human log keeps it
        state = self.global_state()
        self.assertEqual(state["offsets"][str(other)], other.stat().st_size)
        self.assertFalse(any(key.startswith("proj/abcdef01") for key in state.get("home", {})))
        self.write("proj/abcdef01.jsonl", self.session(), mode="a", cwd=plain)
        self.run_cmd("scan", "--force")
        self.assertEqual(self.new_text(), text)

    def devkit_project(self):
        """The retro project named ClaudeDevKit, with its item folder `state.json` (what makes it a known project)."""
        path = make_repo(self.tmp / "ClaudeDevKit")
        folder = self.retro / dev_kit_state.folder_name(path)
        retro.write_json(folder / "state.json", {"root": str(path)})
        return path, folder

    # protects: Flow
    def test_claude_app_failures_of_any_transcript_go_to_claudedevkit_not_to_their_own_project(self):
        _, devkit = self.devkit_project()
        plain = make_repo(self.tmp / "plain", retro_project=False)
        stamp = "2026-11-19T10:00:00Z"
        failure = [call("s", "SendMessage", {"to": "x"}, stamp),
                   send_result("s", stamp, False, "No agent named 'x' is reachable. Use ListAgents")]
        self.write("proj/lead1234.jsonl", failure)  # a project with a lead
        self.write("proj/home1234.jsonl", self.session() + failure, cwd=plain)  # a folder with no lead
        self.run_cmd("scan")
        text = self.new_text(devkit)
        self.assertIn("- proj | lead1234 | claude app | SendMessage: No agent named 'x' is reachable.", text)
        self.assertIn("- proj | C: Task (home1234) | claude app | SendMessage: No agent named 'x' is reachable.", text)
        self.assertNotIn("failed calls", text)  # the other findings of a no-lead project keep their routing
        self.assertNotIn("claude app", self.new_text())  # not the lead project that the transcript belongs to
        log = (self.retro / f"scan-{retro.today()}.md").read_text(encoding="utf-8")
        self.assertEqual(log.count("claude app | SendMessage"), 2)
        self.assertIn("C: Task (home1234) | failed calls", log)

    # protects: Rule
    def test_claude_app_failures_are_found_by_the_tool_not_by_the_words(self):
        stamp = "2026-11-19T10:00:00Z"
        entries = []
        for n in range(3):  # the same failure with another session id each time is one line
            entries += [call(f"s{n}", "SendMessage", {}, stamp),
                        send_result(f"s{n}", stamp, False, f"Failed to send to cse_0{n}ab: HTTP 409 - not active")]
        entries += [call("a", "Agent", {}, stamp),
                    app_result("a", stamp, "<tool_use_error>Concurrent subagent limit reached.</tool_use_error>", True)]
        not_found = [
            call("ok", "SendMessage", {}, stamp), send_result("ok", stamp, True, "Sent"),
            call("b", "Bash", {}, stamp), app_result("b", stamp, '{"success": false, "message": "No agent named"}'),
            call("h", "Agent", {}, stamp),
            app_result("h", stamp, "PreToolUse:Agent hook error: subagent type 'x' is not a narrow agent", True),
            call("r", "SendMessage", {}, stamp), send_result("r", stamp, False, "2 agents are named 'x'. Re-send with the ref"),
            call("p", "Agent", {}, stamp), app_result("p", stamp, "Concurrent subagent limit reached.")]  # no is_error
        found = [f for f in retro.findings_of(retro.analyse([json.dumps(e) for e in entries + not_found]))
                 if f[0] == "claude app"]
        self.assertEqual(found, [("claude app", "SendMessage x3: Failed to send to cse_<id>: HTTP 409 - not active"),
                                 ("claude app", "Agent: Concurrent subagent limit reached.")])

    # protects: Edge
    def test_claude_app_failures_stay_in_the_log_when_claudedevkit_is_not_a_known_project(self):
        stamp = "2026-11-19T10:00:00Z"
        self.write("proj/lead1234.jsonl", [call("s", "SendMessage", {}, stamp), send_result("s", stamp, False, "gone")])
        self.run_cmd("scan")
        self.assertEqual(self.new_files(), [])
        self.assertIn("| claude app | SendMessage: gone", (self.retro / f"scan-{retro.today()}.md").read_text(encoding="utf-8"))

    # protects: Flow
    def test_a_higher_claude_code_version_makes_one_line_and_the_first_run_none(self):
        path, devkit = self.devkit_project()

        def scan_with(version):
            self.write("proj/s1.jsonl", [{"type": "system", "version": version}], mode="a")
            self.run_cmd("scan", "--force")
            return self.new_text(devkit).count("claude app | updated")

        self.assertEqual(scan_with("2.1.330"), 0)  # the first run stores it silently
        self.assertEqual(self.global_state()["claude_version"], "2.1.330")
        self.assertEqual(scan_with("2.1.331"), 1)
        self.assertIn("- ClaudeDevKit | - | claude app | updated 2.1.330 -> 2.1.331", self.new_text(devkit))
        self.assertEqual(scan_with("2.1.331"), 1)  # not again
        self.assertEqual(scan_with("2.1.99"), 1)  # a resumed old session lowers nothing
        self.assertEqual(self.global_state()["claude_version"], "2.1.331")
        self.assertIn("claude code: 2.1.331\n", self.project_cmd("items", project=path))

    # protects: Flow
    def test_the_weekly_recheck_line_goes_to_claudedevkit_once_in_seven_days(self):
        _, devkit = self.devkit_project()
        self.write("proj/s1.jsonl", [{"type": "system", "version": "2.1.330"}])

        def scan_on(day):
            with mock.patch.object(retro, "today", return_value=day):
                self.run_cmd("scan", "--force")
            return self.new_text(devkit).count("- ClaudeDevKit | - | claude app | weekly re-check due")

        self.assertEqual(scan_on("2099-01-01"), 1)  # the first full scan asks for the re-check
        self.assertEqual(scan_on("2099-01-01"), 1)  # not again on the same day
        self.assertEqual(scan_on("2099-01-07"), 1)  # nor on day 6
        self.assertEqual(self.global_state()["facts_recheck"], "2099-01-01")
        self.assertEqual(scan_on("2099-01-08"), 2)  # day 7: due again
        self.assertEqual(self.global_state()["facts_recheck"], "2099-01-08")

    # protects: Rule
    def test_critical_still_sees_the_tokens_of_a_project_that_is_not_a_retro_project(self):
        plain = make_repo(self.tmp / "plain", retro_project=False)
        title = {"type": "custom-title", "customTitle": "C: Big"}
        self.write("proj/big12345.jsonl", [title] + [assistant("a", "claude-sonnet-5-5", {"output_tokens": 500},
                                                               "2099-01-01T12:00:00Z")], cwd=plain)
        with mock.patch.object(retro, "WEEKLY_LIMIT_UNITS", 100000), mock.patch.object(retro, "today",
                                                                                        return_value="2099-01-01"):
            out = self.run_cmd("critical")
        self.assertEqual(out, "critical | proj | C: Big (big12345) | 2099-01-01 | "
                              "spent 2.5% of the weekly limit (2.5k units)\n")
        self.assertEqual(self.new_files(), [])

    # protects: Bug
    def retro_session(self):
        """The transcript of a retro session with findings of its own and of a subagent, and 2500 units."""
        entries = [{"type": "custom-title", "customTitle": "Ретро: repo"}] + self.session()[1:]  # [0] is another title
        entries.append(assistant("a", "claude-sonnet-5-5", {"output_tokens": 500}, "2026-11-19T10:40:00Z"))
        self.write("proj/abcdef1234/subagents/agent-0.jsonl", [call("c", "Glob", {"pattern": "*"},
                                                                    "2026-11-19T10:00:00Z")] * 3)
        return self.write("proj/abcdef1234.jsonl", entries)

    def retro_session_units(self):
        return sum(day["proj/abcdef1234"]["units"] for day in self.global_state()["daily"].values()
                   if "proj/abcdef1234" in day)

    # protects: Bug
    def test_the_findings_of_a_retro_session_and_its_subagents_are_dropped_by_the_full_scan(self):
        self.retro_session()
        self.write("proj/12345678.jsonl", [{"type": "custom-title", "customTitle": "C: Task"}] + self.session())
        self.run_cmd("scan")
        text = self.new_text()
        self.assertIn("(12345678)", text)  # an ordinary session still counts
        self.assertNotIn("abcdef12", text)
        log = (self.retro / f"scan-{retro.today()}.md").read_text(encoding="utf-8")
        self.assertEqual([line for line in log.splitlines() if line.startswith("- ") and "abcdef12" in line], [])
        self.assertIn("| Ретро: repo (abcdef12) |", log)  # the spend table is not a finding
        self.assertEqual(self.retro_session_units(), 2500)  # its tokens still count

    # protects: Bug
    def test_the_findings_of_a_retro_session_are_dropped_by_the_transcript_scan_too(self):
        main = self.retro_session()
        self.run_cmd("scan", "--transcript", str(main))
        self.assertEqual(self.new_files(), [])
        self.assertEqual(self.retro_session_units(), 2500)

    # protects: Edge
    def test_a_transcript_with_no_cwd_yet_is_read_unrouted_and_its_later_lines_are_routed(self):
        path = self.projects / "proj" / "abcdef01.jsonl"
        path.write_text(json.dumps({"type": "custom-title", "customTitle": "C: Task"}) + "\n", encoding="utf-8")
        self.run_cmd("scan")
        self.assertEqual(self.new_files(), [])
        self.write("proj/abcdef01.jsonl", self.session(), mode="a")
        self.run_cmd("scan", "--force")
        self.assertIn("failed calls | 3 (Read x3)", self.new_text())

    # protects: Flow
    def test_a_full_scan_writes_one_new_file_per_project_with_only_its_own_findings(self):
        other = make_repo(self.tmp / "other")
        self.write("proj/abcdef01.jsonl", self.session())
        self.write("proj2/12345678.jsonl", self.session(), cwd=other)
        self.run_cmd("scan")
        mine, theirs = self.new_files(), self.new_files(self.retro / dev_kit_state.folder_name(other))
        self.assertEqual((len(mine), len(theirs)), (1, 1))
        self.assertIn("(abcdef01)", mine[0].read_text(encoding="utf-8"))
        self.assertNotIn("(12345678)", mine[0].read_text(encoding="utf-8"))
        self.assertIn("(12345678)", theirs[0].read_text(encoding="utf-8"))
        everything = (self.retro / f"scan-{retro.today()}.md").read_text(encoding="utf-8")
        self.assertIn("(abcdef01)", everything)  # the human log keeps all lines
        self.assertIn("(12345678)", everything)
        self.assertEqual(json.loads((self.folder / "state.json").read_text(encoding="utf-8"))["root"], str(self.repo))

    # protects: Flow
    def test_a_transcript_scan_reads_only_that_session_into_its_own_file(self):
        stamp = "2026-11-19T10:00:00Z"
        main = self.write("proj/abcdef1234.jsonl", self.session())
        agent = self.write("proj/abcdef1234/subagents/agent-0.jsonl", [call("c", "Glob", {"pattern": "*"}, stamp)] * 3)
        (self.projects / "proj/abcdef1234/subagents/agent-0.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        other = self.write("proj/99999999.jsonl", self.session())
        self.run_cmd("scan", "--transcript", str(main))
        files = self.new_files()
        self.assertEqual(len(files), 1)
        self.assertRegex(files[0].name, rf"^{retro.today()}-abcdef12-\d{{6}}\.md$")
        text = files[0].read_text(encoding="utf-8")
        self.assertIn("C: Task (abcdef12) | repeated call | Read x3", text)
        self.assertIn("(abcdef12) / subagent dev-kit:coder | repeated call | Glob x3", text)
        state = self.global_state()
        self.assertEqual((state["offsets"][str(main)], state["offsets"][str(agent)]),
                         (main.stat().st_size, agent.stat().st_size))
        self.assertNotIn(str(other), state["offsets"])  # another session is the full scan's
        self.assertEqual(state["last_scan"], "")  # and the day's full scan is still to come
        self.run_cmd("scan", "--transcript", str(main))
        self.assertEqual(len(self.new_files()), 1)  # nothing new: no file
        self.run_cmd("scan")
        self.assertEqual(len(self.new_files()), 2)
        self.assertEqual(self.new_text().count("(abcdef12)"), 4 + 1)  # the main findings once, plus the subagent's

    # protects: Edge
    def test_a_transcript_scan_with_nothing_found_writes_no_file(self):
        path = self.write("proj/abcdef1234.jsonl", [call("a", "Read", {}, "2026-11-19T10:00:00Z")])
        self.run_cmd("scan", "--transcript", str(path))
        self.assertEqual(self.new_files(), [])
        self.assertEqual(self.global_state()["offsets"][str(path)], path.stat().st_size)

    # protects: Rule
    def test_a_held_lock_stops_a_transcript_scan_and_a_stale_lock_is_taken(self):
        main = self.write("proj/abcdef1234.jsonl", self.session())
        lock = self.retro / retro.LOCK_NAME
        self.retro.mkdir(parents=True)
        lock.write_text("1", encoding="ascii")
        with mock.patch.object(retro, "LOCK_WAIT_TRANSCRIPT_S", 0.2), mock.patch.object(retro, "LOCK_WAIT_FULL_S", 0.2):
            self.assertEqual(self.run_cmd("scan", "--transcript", str(main)), "")  # quiet, nothing changed
            self.assertIn("scan busy", self.run_cmd("scan"))
        self.assertEqual(self.new_files(), [])
        self.assertFalse((self.retro / "state.json").exists())
        self.assertTrue(lock.exists())
        old = time.time() - retro.LOCK_STALE_S - 5
        os.utime(lock, (old, old))
        self.run_cmd("scan", "--transcript", str(main))
        self.assertEqual(len(self.new_files()), 1)
        self.assertFalse(lock.exists())  # released

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


class RetroCommandsTestCase(RetroFixture):
    """`items`, `done`, `add`, `due`, `asked` and the two hooks, on item folders written by hand."""

    def put(self, rel, text):
        path = self.folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def project_state(self):
        return json.loads((self.folder / "state.json").read_text(encoding="utf-8"))

    def exit_code(self, *args):
        err = io.StringIO()
        with mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", err):
            return retro.main(list(args)), err.getvalue()

    # protects: Flow
    def test_items_shows_the_folder_new_findings_priority_first_items_and_the_trivial_fix_count(self):
        day = datetime.date.today()
        self.put("new/scan-a.md", "- repo | S (12345678) | repeated call | Read x3\n"
                                  "- repo | S (12345678) | token spend | 2026-11-19: spent 1%\n")
        self.put("items/stale-doc.md", "# stale doc\n- status: disputed\n- kind: rule gap\n"
                                       "- seen: 2026-11-19 | s1\n- seen: 2026-11-20 | s2\n"
                                       f"- fix: {day} | reworded one word | trivial\n"
                                       f"- fix: {day - datetime.timedelta(days=6)} | older | trivial\n"
                                       f"- fix: {day - datetime.timedelta(days=7)} | too old | trivial\n"
                                       f"- fix: {day} | big change | high-impact\n")
        self.put("items/other.md", "- status: open\n")
        out = self.project_cmd("items")
        self.assertEqual(out.splitlines()[:2], [str(self.folder), "last review: never"])
        self.assertLess(out.index("token spend"), out.index("## New findings"))
        self.assertLess(out.index("## New findings"), out.index("repeated call"))
        self.assertIn("\nstale-doc | disputed | rule gap | sightings 2\n", out)
        self.assertIn("\nother | open | ? | sightings 0\n", out)
        self.assertIn(f"trivial fixes in the last 7 days: 2 of {retro.FIXES_PER_WEEK}" + chr(10) * 2
                      + "## Docs items" + chr(10) + "(none)", out)
        self.assertEqual(self.project_state()["shown"], ["scan-a.md"])

    # protects: Rule
    def test_a_folder_of_another_project_gets_exit_code_2(self):
        plain = make_repo(self.tmp / "plain", retro_project=False)
        for command in (("items",), ("done",), ("add", "--text", "x"), ("asked", "--answer", "yes")):
            code, err = self.exit_code(*command, "--project", str(plain))
            self.assertEqual(code, 2, command)
            self.assertIn("no retro project", err)
        self.assertEqual(self.project_cmd("due", project=plain), "")  # silent: a hook may ask anywhere

    # protects: Flow
    def test_done_moves_what_items_showed_and_leaves_later_findings_and_prunes_old_seen_files(self):
        self.put("new/a.md", "- one\n")
        self.put("seen/a.md", "- earlier file of the same name\n")
        old = self.put("seen/old.md", "- old\n")
        long_ago = time.time() - (retro.SEEN_DAYS + 1) * 86400
        os.utime(old, (long_ago, long_ago))
        self.put("seen/recent.md", "- recent\n")
        self.project_cmd("items")
        self.put("new/b.md", "- came after items\n")
        self.assertIn("1 file(s)", self.project_cmd("done"))
        self.assertEqual([path.name for path in self.new_files()], ["b.md"])
        seen = sorted(path.name for path in (self.folder / "seen").iterdir())
        self.assertEqual(len(seen), 3)  # the earlier a.md kept, the moved one beside it, recent.md; old.md deleted
        self.assertIn("recent.md", seen)
        self.assertNotIn("old.md", seen)
        state = self.project_state()
        self.assertNotIn("shown", state)
        self.assertIsNotNone(retro.parse_time(state["last_review"]))
        self.assertIn("0 file(s)", self.project_cmd("done"))  # nothing shown since: b.md stays new
        self.assertEqual([path.name for path in self.new_files()], ["b.md"])
        self.assertRegex(self.project_cmd("items").splitlines()[1], r"^last review: \d{4}-\d\d-\d\d \d\d:\d\d$")

    # protects: Flow
    def test_add_writes_a_file_of_its_own_marked_with_the_sender(self):
        self.project_cmd("add", "--text", "agents open the\nwrong file", "--from", "Zhratva")
        self.project_cmd("add", "--text", "second", "--from", "Zhratva")
        files = self.new_files()
        self.assertEqual(len(files), 2)  # two adds in one second do not share a file
        for path in files:
            self.assertRegex(path.name, r"^add-\d{4}-\d\d-\d\d-\d{6}-[0-9a-f]{6}\.md$")
        self.assertIn(f"- {datetime.date.today()} | from Zhratva | agents open the wrong file\n", self.new_text())
        start = Path.cwd()
        self.addCleanup(os.chdir, start)
        os.chdir(make_repo(self.tmp / "Prishch", retro_project=False))
        self.project_cmd("add", "--text", "from cwd")
        self.assertIn(" | from Prishch | from cwd\n", self.new_text())

    # protects: Flow
    def test_project_accepts_the_repository_folder_name_of_a_known_project_in_any_case(self):
        retro.save_project(self.folder, {"root": str(self.repo)})  # recorded by the scan or a session start
        start = Path.cwd()
        self.addCleanup(os.chdir, start)
        os.chdir(make_repo(self.tmp / "Prishch", retro_project=False))  # another project's session
        self.run_cmd("add", "--text", "agents open the wrong file", "--project", "REPO", "--from", "Prishch")
        self.assertIn("from Prishch | agents open the wrong file", self.new_text())
        self.assertEqual(self.run_cmd("items", "--project", "Repo").splitlines()[0], str(self.folder))
        code, err = self.exit_code("add", "--text", "x", "--project", "stranger")  # no such name: a folder, not a project
        self.assertEqual(code, 2)
        self.assertIn("no retro project", err)

    # protects: Rule
    def test_a_locked_project_state_is_not_changed_by_commands_and_a_stale_lock_is_taken(self):
        self.scanned_today()
        self.put("new/a.md", "- finding\n")
        lock = self.put("state.lock", "1")
        with mock.patch.object(retro, "PROJECT_LOCK_WAIT_S", 0.2):
            for command in (("items",), ("done",), ("asked", "--answer", "yes")):
                code, err = self.exit_code(*command, "--project", str(self.repo))
                self.assertEqual(code, 1, command)
                self.assertIn("locked", err)
            self.assertEqual(self.start(), [])  # hook-start cannot stamp: it starts nothing
        self.assertFalse((self.folder / "state.json").exists())
        old = time.time() - retro.PROJECT_LOCK_STALE_S - 5
        os.utime(lock, (old, old))
        self.assertEqual(len(self.start()), 1)  # a stale lock is taken: the retro session starts
        self.assertFalse(lock.exists())  # released
        self.assertIn("retro_started", self.project_state())

    # protects: Flow
    def test_the_detached_start_on_windows_hides_the_window_and_retries_without_breakaway(self):
        calls = []

        def popen(argv, **options):
            calls.append(options.get("creationflags"))
            if len(calls) == 1:
                raise PermissionError("the job forbids breakaway")

        flags = retro.CREATE_NO_WINDOW | retro.CREATE_NEW_PROCESS_GROUP
        with mock.patch.object(retro, "WINDOWS", True), mock.patch.object(retro.subprocess, "Popen", popen):
            retro.spawn(["x"])
        self.assertEqual(calls, [flags | retro.CREATE_BREAKAWAY_FROM_JOB, flags])
        self.assertEqual(flags & 0x00000008, 0)  # no DETACHED_PROCESS: it would cancel CREATE_NO_WINDOW
        calls.clear()
        with mock.patch.object(retro, "WINDOWS", False), mock.patch.object(retro.subprocess, "Popen") as other:
            retro.spawn(["x"], cwd="somewhere")
        self.assertTrue(other.call_args.kwargs["start_new_session"])
        self.assertEqual(other.call_args.kwargs["cwd"], "somewhere")

    def lead(self, **state):
        self.put("state.json", json.dumps({"lead_session": "lead-1", **state}))

    # protects: Rule
    def test_due_is_silent_for_other_sessions_and_speaks_for_urgent_or_weekly_items(self):
        self.lead()
        self.put("items/open.md", "- status: open\n")
        self.assertEqual(self.project_cmd("due", "--session", "lead-1"), "")
        self.put("items/disp.md", "- status: Disputed\n")
        self.put("items/fixed.md", "- status: trivial-fixed\n")
        self.assertEqual(self.project_cmd("due", "--session", "lead-1"), "retro: 2 items due (0 urgent)\n")
        self.assertEqual(self.project_cmd("due"), "retro: 2 items due (0 urgent)\n")  # no session given: the project's
        self.assertEqual(self.project_cmd("due", "--session", "someone-else"), "")
        self.assertEqual(self.project_cmd("due", "--session", ""), "")
        self.put("items/hot.md", "- status: urgent\n")
        self.assertEqual(self.project_cmd("due", "--session", "lead-1"), "retro: 3 items due (1 urgent)\n")

    # protects: Rule
    def test_the_weekly_ask_waits_a_week_after_yes_and_a_day_after_no_but_urgent_ignores_it(self):
        self.lead()
        self.put("items/disp.md", "- status: disputed\n")
        base = datetime.datetime(2026, 11, 22, 12, tzinfo=datetime.timezone.utc)

        def at(**delta):
            return mock.patch.object(retro, "now_utc", return_value=base + datetime.timedelta(**delta))

        def due(**delta):
            with at(**delta):
                return self.project_cmd("due", "--session", "lead-1")

        with at():
            self.assertIn("stamped: yes", self.project_cmd("asked", "--answer", "yes"))
        self.assertEqual((due(days=6, hours=23), due(days=7)), ("", "retro: 1 items due (0 urgent)\n"))
        with at():
            self.project_cmd("asked", "--answer", "no")
        self.assertEqual((due(hours=23), due(days=1)), ("", "retro: 1 items due (0 urgent)\n"))
        self.put("items/hot.md", "- status: urgent\n")
        self.assertEqual(due(hours=1), "retro: 1 items due (1 urgent)\n")  # urgent: asked at once, the others wait

    def retro_state(self, **values):
        retro.save_project(self.folder, {"root": str(self.repo), **values})

    def start(self, title="C: task", cwd=None, session_id="s-1", claude="fake-claude", docs=False):
        """hook_start with the spawn recorded; returns the recorded commands. The weekly docs session is left out
        unless `docs` is set."""
        spawned = []
        no_docs = mock.patch.object(retro, "docs_start_command", lambda *args: None) if not docs \
            else contextlib.nullcontext()
        with mock.patch.object(retro, "spawn", lambda argv, cwd=None: spawned.append((argv, cwd))), \
                mock.patch.object(sessions, "find_claude", return_value=claude), \
                mock.patch.dict(os.environ), no_docs:
            os.environ.pop(retro.NO_START_ENV, None)
            retro.hook_start({"cwd": str(cwd or self.repo), "session_id": session_id, "session_title": title})
        return spawned

    def scanned_today(self):
        self.retro.mkdir(parents=True, exist_ok=True)
        (self.retro / "state.json").write_text(json.dumps({"offsets": {}, "last_scan": retro.today()}), encoding="utf-8")

    # protects: Rule
    def test_a_retro_session_start_does_nothing_so_the_retro_never_starts_itself(self):
        self.put("new/a.md", "- finding\n")
        self.assertEqual(self.start(title="Ретро: repo", session_id="retro-1"), [])
        self.assertFalse((self.folder / "state.json").exists())  # not even a lead record

    # protects: Rule
    def test_only_a_lead_title_records_the_lead_session(self):
        self.scanned_today()
        self.start(title="P: repo", session_id="lead-1")
        self.assertEqual(self.project_state()["lead_session"], "lead-1")
        self.start(title="C: repo task", session_id="builder-1")
        self.start(title="", session_id="untitled-1")
        self.assertEqual(self.project_state()["lead_session"], "lead-1")
        self.start(title="P: repo", session_id="lead-2")  # a restarted lead replaces it
        self.assertEqual(self.project_state()["lead_session"], "lead-2")

    # protects: Rule
    def test_a_session_of_another_project_starts_nothing_and_leaves_no_folder(self):
        plain = make_repo(self.tmp / "plain", retro_project=False)
        self.assertEqual(self.start(cwd=plain), [])
        self.assertFalse(self.retro.exists())

    # protects: Flow
    def test_the_daily_full_scan_starts_once_when_the_lock_is_free(self):
        scan = [retro.sys.executable, "-X", "utf8", str(Path(retro.__file__).resolve()), "scan"]
        self.assertEqual([argv for argv, _ in self.start()], [scan])
        self.scanned_today()
        self.assertEqual(self.start(), [])
        (self.retro / "state.json").write_text(json.dumps({"offsets": {}, "last_scan": "2000-01-01"}), encoding="utf-8")
        lock = self.retro / retro.LOCK_NAME
        lock.write_text("1", encoding="ascii")
        self.assertEqual(self.start(), [])  # a scan is running
        old = time.time() - retro.LOCK_STALE_S - 5
        os.utime(lock, (old, old))
        self.assertEqual([argv for argv, _ in self.start()], [scan])  # a stale lock does not hold it

    # protects: Flow
    def test_the_retro_session_starts_when_findings_wait_the_review_is_old_and_no_start_is_recent(self):
        self.scanned_today()
        command = ["fake-claude", "--bg", "--name", "Ретро: repo", "--settings", str(retro.NO_REMOTE_CONTROL), "--model", "opus", "--effort", "medium",
                   "--permission-mode", "bypassPermissions", "--", "/dev-kit:retro"]
        self.assertEqual(self.start(), [])  # no findings
        self.put("new/a.md", "- finding\n")
        self.assertEqual(self.start(claude=None), [])  # no claude command: no stamp, a later session retries
        self.assertNotIn("retro_started", self.project_state())
        self.assertEqual(self.start(), [(command, str(self.repo))])  # in the main checkout
        self.assertIsNotNone(retro.parse_time(self.project_state()["retro_started"]))
        self.assertEqual(self.start(), [])  # started a moment ago
        hours = lambda value: (retro.now_utc() - datetime.timedelta(hours=value)).isoformat()  # noqa: E731
        self.retro_state(retro_started=hours(retro.START_GUARD_HOURS + 1), last_review=hours(retro.REVIEW_HOURS - 1))
        self.assertEqual(self.start(), [])  # reviewed lately
        self.retro_state(retro_started=hours(retro.START_GUARD_HOURS - 1), last_review=hours(retro.REVIEW_HOURS + 1))
        self.assertEqual(self.start(), [])  # the last start may still run
        self.retro_state(retro_started=hours(retro.START_GUARD_HOURS + 1), last_review=hours(retro.REVIEW_HOURS + 1))
        self.assertEqual(self.start(), [(command, str(self.repo))])

    # protects: Flow
    def test_the_weekly_docs_session_starts_after_the_retro_or_on_its_own_once_a_week(self):
        self.scanned_today()
        command = ["fake-claude", "--bg", "--name", "Документація: repo", "--settings", str(retro.NO_REMOTE_CONTROL), "--model", "opus", "--effort", "medium",
                   "--permission-mode", "bypassPermissions", "--", "/dev-kit:maintain-project-docs weekly"]
        hours = lambda value: (retro.now_utc() - datetime.timedelta(hours=value)).isoformat()  # noqa: E731
        self.assertEqual(self.start(docs=True), [(command, str(self.repo))])  # never ran: on its own, in main
        self.assertIsNotNone(retro.parse_time(self.project_state()["docs_started"]))
        self.assertEqual(self.start(docs=True), [])  # started a moment ago
        self.project_cmd("docs-done")
        self.retro_state(docs_done=self.project_state()["docs_done"])
        self.assertEqual(self.start(docs=True), [])  # ran this week
        week = retro.DOCS_DAYS * 24
        self.retro_state(docs_done=hours(week + 1))
        self.assertEqual(self.start(docs=True), [(command, str(self.repo))])  # a week with no retro
        self.retro_state(docs_done=hours(week + 1), retro_started=hours(1))
        self.assertEqual(self.start(docs=True), [])  # the retro session may still run
        self.put("new/a.md", "- finding\n")
        self.retro_state(docs_done=hours(week + 1), retro_started=hours(retro.START_GUARD_HOURS + 1))
        names = [argv[3] for argv, _ in self.start(docs=True)]
        self.assertEqual(names, ["Ретро: repo"])  # findings wait: the retro session first, never both at once
        (self.folder / "new" / "a.md").unlink()
        self.retro_state(retro_started=hours(2), last_review=hours(1), docs_done=hours(week + 1))
        self.assertEqual(self.start(title="Документація: repo", docs=True), [])  # the docs session starts nothing
        self.assertEqual(self.start(docs=True), [(command, str(self.repo))])  # after the retro ended
        self.put("new/b.md", "- finding\n")
        self.retro_state(docs_started=hours(1), docs_done=hours(week + 1))
        self.assertEqual(self.start(), [])  # the docs session may still run: the retro waits
        self.retro_state(docs_started=hours(retro.DOCS_GUARD_HOURS - 1), docs_done=hours(week + 1))
        self.assertEqual([argv[3] for argv, _ in self.start(docs=True)], ["Ретро: repo"])  # docs did not end
        (self.folder / "new" / "b.md").unlink()
        self.retro_state(docs_started=hours(retro.DOCS_GUARD_HOURS - 1), docs_done=hours(week + 1))
        self.assertEqual(self.start(docs=True), [])  # a run with no docs-done is retried once a day, not sooner
        self.retro_state(docs_started=hours(retro.DOCS_GUARD_HOURS + 1), docs_done=hours(week + 1))
        self.assertEqual(self.start(docs=True), [(command, str(self.repo))])

    # protects: Rule
    def test_the_docs_session_waits_for_the_merge_of_the_retro_branch_at_most_two_days(self):
        self.scanned_today()
        git(self.repo, "branch", "retro-x")
        git(self.repo, "checkout", "-q", "retro-x")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "fix")
        git(self.repo, "checkout", "-q", "main")
        hours = lambda value: (retro.now_utc() - datetime.timedelta(hours=value)).isoformat()  # noqa: E731
        self.retro_state(retro_started=hours(2), last_review=hours(1))
        self.project_cmd("done", "--branch", "retro-x")
        self.assertEqual(self.project_state()["retro_branch"], "retro-x")
        self.assertEqual(self.start(docs=True), [])  # the retro's fixes are not on main yet
        state = self.project_state()
        state["last_review"] = hours(retro.DOCS_MERGE_WAIT_HOURS + 1)
        state["retro_started"] = hours(retro.DOCS_MERGE_WAIT_HOURS + 2)
        retro.save_project(self.folder, state)
        self.assertEqual(len(self.start(docs=True)), 1)  # waited long enough: runs anyway
        self.retro_state(retro_started=hours(2), last_review=hours(1), retro_branch="retro-x")
        git(self.repo, "merge", "-q", "--ff-only", "retro-x")
        self.assertEqual(len(self.start(docs=True)), 1)  # merged
        git(self.repo, "branch", "-q", "-D", "retro-x")
        self.retro_state(retro_started=hours(2), last_review=hours(1), retro_branch="retro-x")
        self.assertEqual(len(self.start(docs=True)), 1)  # deleted after its merge
        self.project_cmd("done")
        self.assertNotIn("retro_branch", self.project_state())  # nothing left to merge

    # protects: Rule
    def test_docs_items_for_the_owner_join_the_weekly_ask_and_items_lists_them(self):
        self.lead()
        self.put("docs-items/stale-epic.md", "# stale epic\n- status: open\n")
        self.assertEqual(self.project_cmd("due", "--session", "lead-1"), "")  # P has it fixed with no owner
        self.put("docs-items/product-rule.md", "# product rule\n- status: owner\n")
        self.put("items/disp.md", "- status: disputed\n")
        self.assertEqual(self.project_cmd("due", "--session", "lead-1"), "retro: 2 items due (0 urgent)\n")
        out = self.project_cmd("items")
        self.assertTrue(out.rstrip().endswith("## Docs items\nproduct-rule | owner\nstale-epic | open"))

    # protects: Rule
    def test_no_start_env_stamps_but_does_not_spawn(self):
        self.scanned_today()
        self.put("new/a.md", "- finding\n")
        with mock.patch.object(retro, "spawn") as spawn, mock.patch.object(sessions, "find_claude", return_value="c"):
            retro.hook_start({"cwd": str(self.repo), "session_id": "s", "session_title": "C: x"})  # env set by setUp
        spawn.assert_not_called()
        self.assertIn("retro_started", self.project_state())

    # protects: Flow
    def test_session_end_scans_the_transcript_of_a_retro_project_only_when_it_exists(self):
        transcript = self.projects / "proj" / "abcdef01.jsonl"
        plain = make_repo(self.tmp / "plain", retro_project=False)
        spawned = []
        with mock.patch.object(retro, "spawn", lambda argv, cwd=None: spawned.append(argv)):
            retro.hook_end({"cwd": str(self.repo), "transcript_path": str(transcript)})  # missing file
            retro.hook_end({"cwd": str(self.repo)})
            retro.hook_end({"cwd": str(self.repo), "transcript_path": 5})
            self.assertEqual(spawned, [])
            transcript.write_text("{}\n", encoding="utf-8")
            retro.hook_end({"cwd": str(plain), "transcript_path": str(transcript)})  # not a retro project
            self.assertEqual(spawned, [])
            retro.hook_end({"cwd": str(self.repo), "transcript_path": str(transcript)})
        self.assertEqual(spawned, [[retro.sys.executable, "-X", "utf8", str(Path(retro.__file__).resolve()),
                                    "scan", "--transcript", str(transcript)]])

    # protects: Edge
    def test_hook_scripts_exit_0_with_no_output_on_bad_input_and_record_the_lead(self):
        self.scanned_today()
        fake = self.tmp / "bin"
        fake.mkdir()
        name = "claude.cmd" if os.name == "nt" else "claude"
        (fake / name).write_text("@exit 0\n" if os.name == "nt" else "#!/bin/sh\nexit 0\n", encoding="utf-8")
        (fake / name).chmod(0o755)
        env = {**os.environ, "PATH": str(fake) + os.pathsep + os.environ.get("PATH", "")}
        self.put("new/a.md", "- finding\n")
        payload = json.dumps({"cwd": str(self.repo), "session_id": "lead-9", "session_title": "P: repo"}).encode()
        for script in ("retro-start.py", "retro-end.py"):
            for data in (b"not json", b"", b"[1]", b"\xff\xfe", payload if script == "retro-end.py" else b"{}"):
                result = subprocess.run([sys.executable, str(PLUGIN / "hooks" / script)], input=data, env=env,
                                        capture_output=True)
                self.assertEqual((result.returncode, result.stdout), (0, b""), (script, data))
        result = subprocess.run([sys.executable, str(PLUGIN / "hooks" / "retro-start.py")], input=payload, env=env,
                                capture_output=True)
        self.assertEqual((result.returncode, result.stdout), (0, b""))
        state = self.project_state()
        self.assertEqual(state["lead_session"], "lead-9")
        self.assertIn("retro_started", state)  # DEV_KIT_RETRO_NO_START=1: stamped, no session started


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
