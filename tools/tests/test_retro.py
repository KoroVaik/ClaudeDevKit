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

PLUGIN = Path(__file__).resolve().parent.parent.parent / "plugins" / "rules-kit"
sys.path.insert(0, str(PLUGIN / "scripts"))
import claude_path  # noqa: E402
import folder_naming  # noqa: E402
import retro  # noqa: E402
import rules_dir  # noqa: E402
import subscriptions  # noqa: E402

SPEND_DIR_ENV = "SPEND_KIT_DIR"  # spend-kit's data folder: the retro runs its command, so the tests point it at a temp folder


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
        self.pfolder = self.retro / folder_naming.folder_name(self.repo)  # the state folder of the retro project
        self.folder = self.set_folder("repo")  # the own set of the retro project: its findings and items
        patcher = mock.patch.dict(os.environ, {retro.RETRO_ENV: str(self.retro),
                                               retro.PROJECTS_ENV: str(self.projects),
                                               subscriptions.PLUGINS_ENV: str(tmp / "plugins"),  # no plugin sets
                                               subscriptions.GLOBAL_ENV: str(tmp / "global"),  # never the real `~/.claude`
                                               retro.NO_START_ENV: "1",
                                               SPEND_DIR_ENV: str(tmp / "spend"),
                                               "DEV_KIT_USAGE_LOG": str(tmp / "usage")})
        patcher.start()
        os.environ.pop("SPEND_KIT_OLD_DIR", None)  # restored with the patch: never the real `~/.claude/dev-kit`
        os.environ.pop(rules_dir.OLD_ENV, None)  # the same for the retro folder of dev-kit
        os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
        self.addCleanup(patcher.stop)

    def set_folder(self, name):
        """The folder of the rule set `name` (a project's own set is named by its repository folder)."""
        return self.retro / retro.SETS_FOLDER / name

    def devkit_project(self):
        """The retro project named ClaudeDevKit, with its state folder `state.json` (what makes it a known project);
        returns it and its own set's folder."""
        path = make_repo(self.tmp / "ClaudeDevKit")
        retro.write_json(self.retro / folder_naming.folder_name(path) / "state.json", {"root": str(path)})
        return path, self.set_folder("ClaudeDevKit")

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

    # protects: Flow
    def test_a_script_candidate_counts_the_sessions_of_one_command(self):
        for name in ("s1", "s2", "s3"):
            self.write(f"proj/{name}.jsonl", [call("b", "Bash", {"command": "npm  run build -- --mode production"}, "2026-11-19T10:00:00Z")])
        self.run_cmd("scan")
        self.assertIn("3 sessions | script candidate | npm run build -- --mode production", self.project_cmd("items"))

    # protects: Bug
    # Broke: the scan summed all runs of one subagent type, so short runs read as one repeated call or one huge run
    def test_two_runs_of_one_subagent_type_count_as_two_not_as_one_summed_run(self):
        # Each coder run below stays under the thresholds (2 repeats, 2 errors, 80 calls); summed they would read as
        # "Glob x4", "4 failed calls" and "160 tool calls". One run over a threshold still gets its own line.
        stamp = "2026-11-19T10:00:00Z"
        entries = [call(f"g{n}", "Glob", {"pattern": "*"}, stamp) for n in range(2)]
        entries += [result(f"g{n}", stamp, error=True) for n in range(2)]
        entries += [call(f"w{n}", "Write", {"n": n}, stamp) for n in range(78)]
        for n in range(2):
            self.write(f"proj/s1/subagents/agent-{n}.jsonl", entries)
            (self.projects / f"proj/s1/subagents/agent-{n}.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        self.write("proj/s1/subagents/agent-2.jsonl", [call("c", "Glob", {"pattern": "*"}, stamp)] * 3)
        (self.projects / "proj/s1/subagents/agent-2.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        self.assertIn("scanned 3 transcript(s)", self.run_cmd("scan"))  # one window per run
        listing = self.project_cmd("items")
        self.assertEqual(listing.count("s1 / subagent dev-kit:coder |"), 1, listing)
        self.assertIn("s1 / subagent dev-kit:coder | repeated call | Glob x3", listing)
        self.assertNotIn("failed calls", listing)
        self.assertNotIn("many calls", listing)

    # protects: Rule
    def test_a_script_candidate_over_several_projects_goes_to_the_plugins_own_project(self):
        other = make_repo(self.tmp / "other")
        command = {"command": "npm  run build -- --mode production"}
        self.write("proj/s1.jsonl", [call("b", "Bash", command, "2026-11-19T10:00:00Z")])
        self.write("proj2/s2.jsonl", [call("b", "Bash", command, "2026-11-19T10:00:00Z")], cwd=other)
        self.write("proj2/s3.jsonl", [call("b", "Bash", command, "2026-11-19T10:00:00Z")], cwd=other)
        self.run_cmd("scan")
        root = folder_naming.main_checkout(Path(retro.__file__).resolve().parents[3])
        plugin = self.set_folder(subscriptions.default_project(root).name)
        self.assertIn("2 project(s) | 3 sessions | script candidate", self.new_text(plugin))
        self.assertNotIn("script candidate", self.new_text())
        self.assertNotIn("script candidate", self.new_text(self.set_folder("other")))

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
        self.assertIn("for other, case ignored", self.new_text(self.set_folder("Other")))
        self.assertNotIn("no such project", self.new_text() + self.new_text(self.set_folder("Other")))
        with open(notes, "a", encoding="utf-8") as handle:
            handle.write("- 2026-11-20 | repo | C: X | correction | later line\n")
        self.run_cmd("scan", "--force")
        text = self.new_text()
        self.assertEqual(text.count("for repo"), 1)  # the first line is not sorted again
        self.assertIn("later line", text)

    # protects: Bug
    def test_notes_written_to_the_old_dev_kit_path_are_read_too_and_the_copied_ones_once(self):
        # The owner's global docs still tell agents to write ~/.claude/dev-kit/retro/notes.md.
        old = self.tmp / "old-retro"
        old.mkdir()
        self.write("proj/s1.jsonl", [call("a", "Read", {}, "2026-11-19T10:00:00Z")])
        first = "- 2026-11-19 | repo | C: X | correction | before the copy\n"
        (old / "notes.md").write_text(first, encoding="utf-8")
        with mock.patch.dict(os.environ, {rules_dir.OLD_ENV: str(old)}):
            self.run_cmd("scan")  # the first run copies the old folder: the line is in both files
            self.assertEqual(self.new_text().count("before the copy"), 1, "a copied line is read once")
            with open(old / "notes.md", "a", encoding="utf-8") as handle:
                handle.write("- 2026-11-20 | repo | C: X | correction | from the old path\n")
            with open(self.retro / "notes.md", "a", encoding="utf-8") as handle:
                handle.write("- 2026-11-20 | repo | C: Y | correction | from the new path\n")
            self.run_cmd("scan", "--force")
            text = self.new_text()
            self.assertEqual(text.count("from the old path"), 1)
            self.assertEqual(text.count("from the new path"), 1)
            self.assertLess(text.index("from the new path"), text.index("from the old path"), "the new file is read first")
            self.assertEqual(text.count("before the copy"), 1)
            self.run_cmd("scan", "--force")
            self.assertEqual(self.new_text().count("from the old path"), 1, "the old line is not read again")

    # protects: Flow
    def test_token_findings_come_from_spend_kit_and_go_to_the_project_of_their_cwd(self):
        plain = make_repo(self.tmp / "plain", retro_project=False)
        coder = {"type": "custom-title", "customTitle": "C: Long"}
        for session, cwd in (("long1234", self.repo), ("other567", plain)):
            self.write(f"proj/{session}.jsonl", [coder, assistant(f"{session}m", "claude-sonnet-5-5", {"output_tokens": 10},
                                                                 "2026-11-19T10:00:00Z")], cwd=cwd)
            self.write(f"proj/{session}/subagents/agent-0.jsonl",
                       [assistant(f"{session}a", "claude-opus-5-5", {"output_tokens": 1000}, "2026-11-19T10:00:00Z")], cwd=cwd)
            (self.projects / f"proj/{session}/subagents/agent-0.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        self.write("proj/retro123.jsonl", [{"type": "custom-title", "customTitle": "Ретро: repo"},
                                           assistant("rm", "claude-sonnet-5-5", {"output_tokens": 10}, "2026-11-19T10:00:00Z")])
        self.write("proj/retro123/subagents/agent-0.jsonl",
                   [assistant("ra", "claude-opus-5-5", {"output_tokens": 1000}, "2026-11-19T10:00:00Z")])
        (self.projects / "proj/retro123/subagents/agent-0.meta.json").write_text('{"agentType": "dev-kit:coder"}')
        self.run_cmd("scan")
        listing = self.project_cmd("items")
        self.assertIn("C: Long (long1234) / subagent dev-kit:coder | opus coder | 7.5k units\n", listing)  # under 10 Sonnet runs: no ratio
        self.assertNotIn("other567", listing)  # a project with no lead: the log only
        self.assertNotIn("retro123", listing)  # a retro session's own findings are dropped
        log = (self.retro / f"scan-{retro.today()}.md").read_text(encoding="utf-8")
        self.assertIn("(other567) / subagent dev-kit:coder | opus coder", log)
        self.assertNotIn("(retro123) / subagent", log)
        self.assertIn("## Spend", log)  # the table is evidence, not a finding
        self.assertNotIn("## Spend", listing)
        self.assertIn("| dev-kit:coder | opus | 3 | ", log)  # the retro session's run counts in the spend table
        self.assertLess(listing.index("## Priority"), listing.index("## New findings"))

    # protects: Edge
    def test_a_scan_without_spend_kit_still_finds_the_rest(self):
        self.write("proj/abcdef1234.jsonl", self.session())
        with mock.patch.dict(os.environ, {"SPEND_KIT_BIN": str(self.tmp / "none")}):  # a path that is no file
            self.assertIsNone(retro.spend_client.command())
            self.assertIn("scanned 1 transcript(s)", self.run_cmd("scan"))
        self.assertEqual(sum(len(retro.read_lines(path)) for path in self.new_files()), 4)

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
        self.assertEqual((project.name, project.folder), ("repo", folder_naming.folder_name(self.repo)))
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
    def test_findings_of_other_projects_are_not_routed_but_stay_in_the_log(self):
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
        self.write("proj/abcdef01.jsonl", self.session(), mode="a", cwd=plain)
        self.run_cmd("scan", "--force")
        self.assertEqual(self.new_text(), text)

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

    # protects: Bug
    def retro_session(self):
        """The transcript of a retro session with findings of its own and of a subagent."""
        entries = [{"type": "custom-title", "customTitle": "Ретро: repo"}] + self.session()[1:]  # [0] is another title
        entries.append(assistant("a", "claude-sonnet-5-5", {"output_tokens": 500}, "2026-11-19T10:40:00Z"))
        self.write("proj/abcdef1234/subagents/agent-0.jsonl", [call("c", "Glob", {"pattern": "*"},
                                                                    "2026-11-19T10:00:00Z")] * 3)
        return self.write("proj/abcdef1234.jsonl", entries)

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
        self.assertIn("| Ретро: repo (abcdef12) |", log)  # the spend table is not a finding; its tokens still count

    # protects: Bug
    def test_the_findings_of_a_retro_session_are_dropped_by_the_transcript_scan_too(self):
        main = self.retro_session()
        self.run_cmd("scan", "--transcript", str(main))
        self.assertEqual(self.new_files(), [])

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
        mine, theirs = self.new_files(), self.new_files(self.set_folder("other"))
        self.assertEqual((len(mine), len(theirs)), (1, 1))
        self.assertIn("(abcdef01)", mine[0].read_text(encoding="utf-8"))
        self.assertNotIn("(12345678)", mine[0].read_text(encoding="utf-8"))
        self.assertIn("(12345678)", theirs[0].read_text(encoding="utf-8"))
        everything = (self.retro / f"scan-{retro.today()}.md").read_text(encoding="utf-8")
        self.assertIn("(abcdef01)", everything)  # the human log keeps all lines
        self.assertIn("(12345678)", everything)
        self.assertEqual(json.loads((self.pfolder / "state.json").read_text(encoding="utf-8"))["root"], str(self.repo))

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

class RetroCommandsTestCase(RetroFixture):
    """`items`, `done`, `add` and the two hooks, on item folders written by hand."""

    def put(self, rel, text):
        """A file of the project's own set (`new/...`, `items/...`), or of its state folder (`state.*`)."""
        path = (self.pfolder if rel.startswith("state.") else self.folder) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def project_state(self):
        return json.loads((self.pfolder / "state.json").read_text(encoding="utf-8"))

    def exit_code(self, *args):
        err = io.StringIO()
        with mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", err):
            return retro.main(list(args)), err.getvalue()

    # protects: Flow
    def test_items_shows_the_folder_new_findings_priority_first_items_and_the_landed_fix_count(self):
        day = datetime.date.today()
        self.put("new/scan-a.md", "- repo | S (12345678) | repeated call | Read x3\n"
                                  "- repo | S (12345678) | token spend | 2026-11-19: spent 1%\n")
        self.put("items/stale-doc.md", "# stale doc\n- status: fixed\n- kind: rule gap\n"
                                       "- seen: 2026-11-19 | s1\n- seen: 2026-11-20 | s2\n"
                                       f"- fix: {day} | repo | abc1234 | CLAUDE.md | -\n"
                                       f"- fix: {day - datetime.timedelta(days=6)} | older | trivial\n"
                                       f"- fix: {day - datetime.timedelta(days=7)} | too old | trivial\n")
        self.put("items/other.md", "- status: open\n")
        out = self.project_cmd("items")
        self.assertEqual(out.splitlines()[:3], [str(self.retro / retro.SETS_FOLDER), "sets: repo", "last review: never"])
        self.assertLess(out.index("token spend"), out.index("## New findings"))
        self.assertLess(out.index("## New findings"), out.index("repeated call"))
        self.assertIn("\nstale-doc | fixed | rule gap | sightings 2\n", out)
        self.assertIn("\nother | open | ? | sightings 0\n", out)
        self.assertTrue(out.rstrip().endswith(f"landed fixes in the last 7 days (repo): 2 of {retro.FIXES_PER_WEEK}"), out)
        self.assertIn(f"### repo ({self.folder / 'items'})\n", out)
        self.assertEqual(self.project_state()["shown"], ["repo/scan-a.md"])

    # protects: Rule
    def test_a_folder_of_another_project_gets_exit_code_2(self):
        plain = make_repo(self.tmp / "plain", retro_project=False)
        for command in (("items",), ("done",), ("add", "--text", "x"), ("check",)):
            code, err = self.exit_code(*command, "--project", str(plain))
            self.assertEqual(code, 2, command)
            self.assertIn("no retro project", err)

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
        self.assertRegex(self.project_cmd("items").splitlines()[2], r"^last review: \d{4}-\d\d-\d\d \d\d:\d\d$")

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
        retro.save_project(self.pfolder, {"root": str(self.repo)})  # recorded by the scan or a session start
        start = Path.cwd()
        self.addCleanup(os.chdir, start)
        os.chdir(make_repo(self.tmp / "Prishch", retro_project=False))  # another project's session
        self.run_cmd("add", "--text", "agents open the wrong file", "--project", "REPO", "--from", "Prishch")
        self.assertIn("from Prishch | agents open the wrong file", self.new_text())
        self.assertEqual(self.run_cmd("items", "--project", "Repo").splitlines()[1], "sets: repo")
        code, err = self.exit_code("add", "--text", "x", "--project", "stranger")  # no such name: a folder, not a project
        self.assertEqual(code, 2)
        self.assertIn("no retro project", err)

    # protects: Rule
    def test_a_locked_project_state_is_not_changed_by_commands_and_a_stale_lock_is_taken(self):
        self.scanned_today()
        self.put("new/a.md", "- finding\n")
        lock = self.put("state.lock", "1")
        with mock.patch.object(retro, "PROJECT_LOCK_WAIT_S", 0.2):
            for command in (("items",), ("done",)):
                code, err = self.exit_code(*command, "--project", str(self.repo))
                self.assertEqual(code, 1, command)
                self.assertIn("locked", err)
            self.assertEqual(self.start(), [])  # hook-start cannot stamp: it starts nothing
        self.assertFalse((self.pfolder / "state.json").exists())
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

    def retro_state(self, **values):
        retro.save_project(self.pfolder, {"root": str(self.repo), **values})

    def start(self, title="C: task", cwd=None, session_id="s-1", claude="fake-claude"):
        """hook_start with the spawn recorded; returns the recorded commands."""
        spawned = []
        with mock.patch.object(retro, "spawn", lambda argv, cwd=None: spawned.append((argv, cwd))), \
                mock.patch.object(claude_path, "find_claude", return_value=claude), \
                mock.patch.dict(os.environ):
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
        self.assertFalse((self.pfolder / "state.json").exists())  # not even a root record

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
                   "--permission-mode", "bypassPermissions", "--", "/rules-kit:retro"]
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
    def test_the_run_file_tells_the_docs_session_what_the_retro_did(self):
        self.scanned_today()
        hours = lambda value: (retro.now_utc() - datetime.timedelta(hours=value)).isoformat()  # noqa: E731
        run_file = self.retro / retro.RUNS_FOLDER / f"{folder_naming.folder_name(self.repo)}.json"
        self.start()  # nothing waits: the file still says so
        self.assertEqual(json.loads(run_file.read_text(encoding="utf-8")),
                         {"root": str(self.repo), "retro_started": None, "last_review": None, "retro_branch": None,
                          "retro_due": False})
        self.put("new/a.md", "- finding\n")
        self.start()
        run = json.loads(run_file.read_text(encoding="utf-8"))
        self.assertTrue(run["retro_due"])
        self.assertEqual(retro.parse_time(run["retro_started"]), retro.parse_time(self.project_state()["retro_started"]))
        self.project_cmd("items")
        self.project_cmd("done", "--branch", "retro-x")
        run = json.loads(run_file.read_text(encoding="utf-8"))
        self.assertEqual((run["retro_branch"], run["retro_due"]), ("retro-x", False))  # reviewed: nothing is due
        self.assertIsNotNone(retro.parse_time(run["last_review"]))
        self.project_cmd("done")
        self.assertIsNone(json.loads(run_file.read_text(encoding="utf-8"))["retro_branch"])  # nothing left to merge
        self.put("new/b.md", "- finding\n")
        self.retro_state(last_review=hours(retro.REVIEW_HOURS - 1))
        self.start()
        self.assertFalse(json.loads(run_file.read_text(encoding="utf-8"))["retro_due"])  # reviewed lately

    # protects: Rule
    def test_no_retro_session_starts_while_the_docs_session_may_still_run(self):
        self.scanned_today()
        self.put("new/a.md", "- finding\n")
        hours = lambda value: (retro.now_utc() - datetime.timedelta(hours=value)).isoformat()  # noqa: E731
        state_root = self.tmp / "dev-kit-state"
        docs = state_root / folder_naming.folder_name(self.repo) / "docs.json"
        docs.parent.mkdir(parents=True)
        with mock.patch.dict(os.environ, {retro.STATE_ENV: str(state_root)}):
            docs.write_text(json.dumps({"docs_started": hours(1)}), encoding="utf-8")
            self.assertEqual(self.start(), [])  # started an hour ago, not ended
            docs.write_text(json.dumps({"docs_started": hours(2), "docs_done": hours(1)}), encoding="utf-8")
            self.assertEqual(len(self.start()), 1)  # ended
            self.retro_state()
            docs.write_text(json.dumps({"docs_started": hours(retro.START_GUARD_HOURS + 1)}), encoding="utf-8")
            self.assertEqual(len(self.start()), 1)  # ended with no stamp long ago: it does not hold the retro
            self.retro_state()
            docs.write_text("{nope", encoding="utf-8")
            self.assertEqual(len(self.start()), 1)  # an unreadable file holds nothing

    # protects: Flow
    def test_the_old_retro_folder_of_dev_kit_is_copied_once_on_the_first_run_and_stays(self):
        old = self.tmp / "old-retro"
        (old / "repo-x" / "items").mkdir(parents=True)
        (old / "repo-x" / "items" / "k.md").write_text("- status: waiting\n", encoding="utf-8")
        (old / "repo-x" / "state.lock").write_text("1", encoding="ascii")
        (old / "notes.md").write_text("- one\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {rules_dir.OLD_ENV: str(old)}):
            self.assertEqual(self.run_cmd("scan"), "scanned 0 transcript(s), 0 finding(s)\n")
            self.assertEqual((self.retro / "repo-x" / "items" / "k.md").read_text(encoding="utf-8"), "- status: waiting\n")
            self.assertEqual((self.retro / "notes.md").read_text(encoding="utf-8"), "- one\n")
            self.assertFalse((self.retro / "repo-x" / "state.lock").exists())  # a lock is not state
            (self.retro / "repo-x" / "items" / "k.md").write_text("- status: fixed\n", encoding="utf-8")
            (old / "notes.md").write_text("- two\n", encoding="utf-8")
            self.run_cmd("scan", "--force")
        self.assertEqual((self.retro / "repo-x" / "items" / "k.md").read_text(encoding="utf-8"), "- status: fixed\n")
        self.assertEqual((self.retro / "notes.md").read_text(encoding="utf-8"), "- one\n")  # copied once, not again
        self.assertEqual((old / "notes.md").read_text(encoding="utf-8"), "- two\n")  # the old folder stays as it was

    # protects: Rule
    def test_no_start_env_stamps_but_does_not_spawn(self):
        self.scanned_today()
        self.put("new/a.md", "- finding\n")
        with mock.patch.object(retro, "spawn") as spawn, mock.patch.object(claude_path, "find_claude", return_value="c"):
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
    def test_hook_scripts_exit_0_with_no_output_on_bad_input_and_record_the_root(self):
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
        self.assertEqual(state["root"], str(self.repo))
        self.assertIn("retro_started", state)  # RULES_KIT_NO_START=1: stamped, no session started


SUBSCRIPTION = """# Rules subscription: {name}

| Setting | Value |
|---|---|
| set | {name} |
| reviewed by | {reviewer} |
| lands by | merged |

## Files

| Path | Type | Part kinds |
|---|---|---|
| skills/*/SKILL.md | process | skill {name}:x |
"""


class RetroSetsTestCase(RetroFixture):
    """Rule sets: findings and items per set, the sets a project's retro handles, the first-run work."""

    def plugin_set(self, name, reviewer="repo"):
        path = self.tmp / "plugins" / name / subscriptions.FILE_NAME
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(SUBSCRIPTION.format(name=name, reviewer=reviewer), encoding="utf-8")

    def put(self, folder, rel, text):
        path = folder / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def files(self, folder, kind):
        return sorted(path.name for path in (folder / kind).glob("*.md")) if (folder / kind).is_dir() else []

    # protects: Rule
    def test_a_project_retro_handles_only_the_sets_that_name_it_as_reviewer(self):
        self.plugin_set("alpha", reviewer="REPO")
        self.plugin_set("beta", reviewer="somebody")
        mine, theirs = self.set_folder("alpha"), self.set_folder("beta")
        self.put(mine, "new/a.md", "- in alpha\n")
        self.put(theirs, "new/b.md", "- in beta\n")
        self.put(self.folder, "new/c.md", "- in the project\n")
        self.put(mine, "items/key.md", "- status: waiting\n")
        self.put(theirs, "items/other.md", "- status: urgent\n")
        listing = self.project_cmd("items")
        self.assertIn("sets: alpha, repo\n", listing)
        self.assertIn("### alpha\n- in alpha", listing)
        self.assertIn("- in the project", listing)
        self.assertNotIn("in beta", listing)
        self.assertIn("key | waiting |", listing)
        self.assertNotIn("other | urgent", listing)
        self.assertEqual(sorted(retro.load_project(self.pfolder)["shown"]), ["alpha/a.md", "repo/c.md"])
        self.project_cmd("done")
        self.assertEqual((self.files(mine, "new"), self.files(mine, "seen"), self.files(theirs, "new")), ([], ["a.md"], ["b.md"]))

    # protects: Rule
    def test_findings_in_a_set_of_another_project_do_not_start_this_retro_nor_make_it_due(self):
        self.plugin_set("beta", reviewer="somebody")
        self.put(self.set_folder("beta"), "new/b.md", "- in beta\n")
        self.retro.mkdir(parents=True, exist_ok=True)
        (self.retro / "state.json").write_text(json.dumps({"offsets": {}, "last_scan": retro.today()}), encoding="utf-8")
        with mock.patch.object(retro, "spawn") as spawn, mock.patch.object(claude_path, "find_claude", return_value="c"):
            retro.hook_start({"cwd": str(self.repo), "session_id": "s", "session_title": "C: x"})
        spawn.assert_not_called()
        run = json.loads((self.retro / retro.RUNS_FOLDER / f"{folder_naming.folder_name(self.repo)}.json").read_text(encoding="utf-8"))
        self.assertFalse(run["retro_due"])
        self.put(self.folder, "new/a.md", "- in the project\n")
        retro.hook_start({"cwd": str(self.repo), "session_id": "s", "session_title": "C: x"})
        run = json.loads((self.retro / retro.RUNS_FOLDER / f"{folder_naming.folder_name(self.repo)}.json").read_text(encoding="utf-8"))
        self.assertTrue(run["retro_due"])

    # protects: Flow
    def test_add_with_a_project_goes_to_the_sets_it_reviews_that_the_text_names_else_to_its_own_set(self):
        self.plugin_set("alpha")
        self.plugin_set("gamma", reviewer="somebody")
        mine = self.set_folder("alpha")
        self.project_cmd("add", "--text", "plugins/alpha/skills/x/SKILL.md:12 is unclear", "--from", "Zhratva")
        self.project_cmd("add", "--text", "the skill alpha:x sends agents to a missing file", "--from", "Zhratva")
        self.project_cmd("add", "--text", "agents do something odd", "--from", "Zhratva")
        self.project_cmd("add", "--text", "plugins/gamma/skills/x/SKILL.md names a gone file", "--from", "Zhratva")  # not reviewed here
        self.assertEqual(len(self.files(mine, "new")), 2)
        self.assertIn("SKILL.md:12 is unclear", "".join(path.read_text(encoding="utf-8") for path in (mine / "new").glob("*.md")))
        self.assertEqual(len(self.files(self.folder, "new")), 2)  # the plain one and the one for a set it does not review
        self.assertEqual(self.files(self.set_folder("gamma"), "new"), [])

    # protects: Rule
    def test_an_added_line_about_a_claude_app_fact_goes_to_the_facts_set_when_the_project_reviews_it(self):
        self.plugin_set("dev-kit")
        self.project_cmd("add", "--text", "claude app: SendMessage fails to a background session", "--from", "Zhratva")
        self.project_cmd("add", "--text", "Owner check 2026-11-24: does the push show", "--from", "Zhratva")
        self.assertEqual(len(self.files(self.set_folder("dev-kit"), "new")), 2)
        self.assertEqual(self.files(self.folder, "new"), [])

    # protects: Flow
    def test_add_with_a_set_name_goes_to_that_set_and_an_unknown_set_is_refused(self):
        self.plugin_set("alpha", reviewer="somebody")
        self.run_cmd("add", "--set", "alpha", "--text", "finding", "--from", "Zhratva")
        self.assertEqual(len(self.files(self.set_folder("alpha"), "new")), 1)
        err = io.StringIO()
        with mock.patch("sys.stdout", io.StringIO()), mock.patch("sys.stderr", err):
            self.assertEqual(retro.main(["add", "--set", "nope", "--text", "x"]), 2)
        self.assertIn("no rule set named nope (known: alpha", err.getvalue())

    # protects: Rule
    def test_claude_app_findings_go_to_the_facts_set_when_it_is_known(self):
        self.plugin_set("dev-kit", reviewer="ClaudeDevKit")
        _, own = self.devkit_project()
        stamp = "2026-11-19T10:00:00Z"
        self.write("proj/lead1234.jsonl", [call("s", "SendMessage", {"to": "x"}, stamp), send_result("s", stamp, False, "gone")])
        self.run_cmd("scan")
        self.assertIn("claude app | SendMessage: gone", self.new_text(self.set_folder("dev-kit")))
        self.assertEqual(self.new_files(own), [])

    # protects: Flow
    def test_the_first_run_writes_the_global_subscription_from_the_template(self):
        global_file = self.tmp / "global" / subscriptions.FILE_NAME
        self.assertFalse(global_file.exists())
        self.assertIn("global | reviewed by ClaudeDevKit | ", self.run_cmd("sets"))
        self.assertEqual(global_file.read_text(encoding="utf-8"), subscriptions.TEMPLATE.read_text(encoding="utf-8"))
        global_file.write_text(global_file.read_text(encoding="utf-8") + "\n<!-- edited -->\n", encoding="utf-8")
        self.run_cmd("sets")
        self.assertIn("<!-- edited -->", global_file.read_text(encoding="utf-8"))  # never written over

    # protects: Flow
    def test_a_project_with_its_own_subscription_file_and_no_dev_kit_profile_is_a_retro_project(self):
        plain = make_repo(self.tmp / "plain", retro_project=False)
        self.assertFalse(retro.is_retro_project(plain))
        (plain / ".claude").mkdir()
        (plain / ".claude" / subscriptions.FILE_NAME).write_text(SUBSCRIPTION.format(name="plain-rules", reviewer="plain"),
                                                                 encoding="utf-8")
        self.assertTrue(retro.is_retro_project(plain))
        self.assertIn("sets: plain-rules\n", self.project_cmd("items", project=plain))

    # protects: Rule
    def test_the_sets_command_lists_every_set_and_the_files_that_fail(self):
        self.plugin_set("alpha")
        bad = self.tmp / "plugins" / "bad" / subscriptions.FILE_NAME
        bad.parent.mkdir(parents=True)
        bad.write_text("# nope\n", encoding="utf-8")
        retro.write_json(self.pfolder / "state.json", {"root": str(self.repo)})
        listing = self.run_cmd("sets")
        self.assertIn("alpha | reviewed by repo | ", listing)
        self.assertIn("repo | reviewed by repo | ", listing)
        self.assertIn("error: ", listing)
        self.assertIn("Files table is missing", listing)

    # protects: Rule
    def test_the_sets_a_text_names_come_from_its_files_first_then_from_its_skills_and_agents(self):
        self.plugin_set("alpha")
        self.plugin_set("beta")
        registry = retro.prepare(out=io.StringIO())
        roots = retro.text_roots(self.repo)
        alpha = "plugins/alpha/skills/x/SKILL.md"
        beta = str(self.tmp / "plugins" / "beta" / "skills" / "x" / "SKILL.md").replace("\\", "/")
        self.assertEqual(retro.sets_of_text(f"{alpha}:12 and {alpha}, also {beta}", registry, roots), ["alpha", "beta"])
        self.assertEqual(retro.sets_of_text(f"{alpha} then {beta}, {beta}.", registry, roots), ["beta", "alpha"])
        self.assertEqual(retro.sets_of_text("see beta:x and alpha:x", registry, roots), ["beta", "alpha"])
        self.assertEqual(retro.sets_of_text("a file plugins/alpha/skills/x/SKILL.md and the skill beta:x", registry, roots), ["alpha"])
        self.assertEqual(retro.sets_of_text("nothing here, 12:30 or src/main.py", registry, roots), [])

    def old_item(self, folder, key, text):
        return self.put(folder, f"items/{key}.md", text)

    # protects: Flow
    def test_old_items_move_once_to_the_set_of_the_files_they_name_else_to_the_project_set_and_the_old_files_stay(self):
        self.plugin_set("alpha", reviewer="ClaudeDevKit")
        other = make_repo(self.tmp / "other")
        old, old_other = self.pfolder, self.retro / folder_naming.folder_name(other)
        retro.write_json(old / "state.json", {"root": str(self.repo)})
        retro.write_json(old_other / "state.json", {"root": str(other)})
        gdoc = str(self.tmp / "global" / "docs" / "a.md")
        self.old_item(old, "by-fix", "# t\n- status: waiting\n- seen: 2026-11-20 | s | plugins/beta/skills/x/SKILL.md\n"
                                     "- fix: 2026-11-21 | plugins/alpha/skills/x/SKILL.md | trivial\n")
        self.old_item(old, "by-text", "# t\n- status: waiting\n- seen: 2026-11-20 | s | agents ignore alpha:x\n")
        self.old_item(old, "by-global", f"# t\n- status: fixed\n- fix: 2026-11-21 | {gdoc} | trivial\n")
        self.old_item(old, "plain", "# t\n- status: waiting\n- seen: 2026-11-20 | s | nothing named\n")
        self.old_item(old_other, "plain", "# other project\n- status: waiting\n")
        self.old_item(old_other, "by-fix", "# t\n- fix: 2026-11-21 | plugins/alpha/skills/x/SKILL.md | trivial\n")
        self.put(old, "new/f.md", "- a finding nobody reviewed\n")
        self.put(old, "seen/s.md", "- reviewed already\n")
        out = io.StringIO()
        retro.prepare(out=out)
        sets = lambda name: self.set_folder(name)  # noqa: E731
        self.assertEqual(self.files(sets("alpha"), "items"), ["by-fix-repo.md", "by-fix.md", "by-text.md"])  # a name clash keeps both
        self.assertEqual(self.files(sets("global"), "items"), ["by-global.md"])
        self.assertEqual(self.files(sets("repo"), "items"), ["plain.md"])
        self.assertEqual(self.files(sets("other"), "items"), ["plain.md"])
        self.assertEqual(self.files(sets("repo"), "new"), ["f.md"])
        self.assertEqual(self.files(sets("repo"), "seen"), [])  # a reviewed finding is not carried over
        self.assertEqual(sorted(self.files(old, "items")), ["by-fix.md", "by-global.md", "by-text.md", "plain.md"])  # old files stay
        self.assertEqual(self.files(old, "seen"), ["s.md"])
        for line in (f"moved {old.name}/items/by-fix.md -> sets/alpha/items/", f"moved {old.name}/items/by-global.md -> sets/global/items/",
                     f"moved {old.name}/new/f.md -> sets/repo/new/"):
            self.assertIn(line, out.getvalue())
        marker = json.loads((self.retro / retro.SETS_FOLDER / retro.MIGRATED_FILE).read_text(encoding="utf-8"))
        self.assertEqual(sorted(marker["folders"]), sorted([old.name, old_other.name]))
        again = io.StringIO()
        (sets("alpha") / "items" / "by-text.md").write_text("# edited since\n", encoding="utf-8")
        retro.prepare(out=again)
        self.assertEqual(again.getvalue(), "")  # once
        self.assertEqual((sets("alpha") / "items" / "by-text.md").read_text(encoding="utf-8"), "# edited since\n")

    # protects: Edge
    def test_an_old_folder_with_no_recorded_root_waits_and_a_copy_that_already_exists_is_not_repeated(self):
        old = self.pfolder
        self.old_item(old, "k", "# t\n- status: waiting\n")
        retro.prepare(out=io.StringIO())
        self.assertEqual(self.files(self.folder, "items"), [])  # no `root` in its state yet: no way to tell its project
        retro.write_json(old / "state.json", {"root": str(self.repo)})
        out = io.StringIO()
        retro.prepare(out=out)
        self.assertEqual(self.files(self.folder, "items"), ["k.md"])
        marker = self.retro / retro.SETS_FOLDER / retro.MIGRATED_FILE
        marker.unlink()  # a lost marker: the same files are found again and not copied twice
        again = io.StringIO()
        retro.prepare(out=again)
        self.assertEqual((self.files(self.folder, "items"), again.getvalue()), (["k.md"], ""))

    # protects: Flow
    def test_a_scan_takes_over_the_old_items_and_routes_its_findings_to_the_set(self):
        retro.write_json(self.pfolder / "state.json", {"root": str(self.repo)})
        self.old_item(self.pfolder, "old-key", "# t\n- status: waiting\n")
        failures = [{"type": "custom-title", "customTitle": "C: Task"}]
        for n in range(3):
            failures += [call(f"r{n}", "Read", {"file_path": "a.py"}, f"2026-11-19T10:0{n}:00Z"),
                         result(f"r{n}", f"2026-11-19T10:0{n}:10Z", error=True)]
        self.write("proj/abcdef1234.jsonl", failures)
        out = self.run_cmd("scan")
        self.assertIn("moved " + self.pfolder.name + "/items/old-key.md -> sets/repo/items/", out)
        self.assertEqual(self.files(self.folder, "items"), ["old-key.md"])
        self.assertEqual(len(self.new_files()), 1)
        self.assertEqual(self.new_files()[0].parent.parent, self.folder)
        self.assertIn("old-key | waiting |", self.project_cmd("items"))


if __name__ == "__main__":
    unittest.main()
