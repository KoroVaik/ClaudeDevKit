import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit" / "scripts"))
import dev_kit_state  # noqa: E402
import sessions  # noqa: E402


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class SessionsTestCase(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.tmp = tmp
        self.state = tmp / "state"
        self.projects = tmp / "projects"
        (self.projects / "p1").mkdir(parents=True)
        self.project = tmp / "work"
        self.project.mkdir()
        env = mock.patch.dict(os.environ, {"DEV_KIT_STATE_DIR": str(self.state), "DEV_KIT_PROJECTS_DIR": str(self.projects)})
        env.start()
        self.addCleanup(env.stop)

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sessions.main(["--project", str(self.project), *argv])
        return code, out.getvalue() + err.getvalue()

    def add(self, session_id, name="C: x", **extra):
        argv = ["add", "--id", session_id, "--name", name, "--worktree", "wt", "--task", "t.md"]
        for key, value in extra.items():
            argv += [f"--{key}", value]
        return self.run_main(*argv)

    def records(self):
        return json.loads((dev_kit_state.project_state_dir(self.project) / "sessions.json").read_text())

    def transcript(self, session_id, entries):
        lines = [json.dumps(entry) for entry in entries]
        (self.projects / "p1" / f"{session_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def assistant(i, c, r, model="claude-haiku-4-5-20251001"):  # a 200K model unless a test says otherwise
        usage = {"input_tokens": i, "cache_creation_input_tokens": c, "cache_read_input_tokens": r, "output_tokens": 5}
        return {"type": "assistant", "message": {"role": "assistant", "model": model, "usage": usage}}

    def test_add_list_end(self):
        self.assertEqual(0, self.add("a1")[0])
        code, output = self.run_main("list")
        self.assertEqual(0, code)
        self.assertIn("C: x | a1 | wt | t.md |", output)
        self.assertEqual(0, self.run_main("end", "--id", "a1")[0])
        self.assertIn("no active sessions", self.run_main("list")[1])
        record = self.records()[0]
        self.assertEqual("done", record["status"])
        self.assertTrue(record["ended"])

    def test_duplicate_and_unknown_id(self):
        self.add("a1")
        self.assertEqual(1, self.add("a1")[0])
        self.assertEqual(1, self.run_main("end", "--id", "zz")[0])

    def test_end_by_short_id(self):
        self.add("abcd1234-0000")
        self.add("abcd9999-0000")
        self.assertEqual(1, self.run_main("end", "--id", "abcd")[0])  # too short
        self.assertEqual(1, self.run_main("end", "--id", "")[0])
        self.assertEqual(0, self.run_main("end", "--id", "abcd1234")[0])
        self.assertEqual("done", self.records()[0]["status"])
        self.assertEqual("active", self.records()[1]["status"])
        self.assertEqual(0, self.add("abcd5555-0000", predecessor="abcd9999")[0])
        self.assertEqual("replaced", self.records()[1]["status"])
        self.assertEqual("abcd9999-0000", self.records()[2]["predecessor"])

    def test_predecessor_marked_replaced(self):
        self.add("a1")
        self.assertEqual(0, self.add("a2", name="C: y", predecessor="a1", parent="p0")[0])
        records = self.records()
        self.assertEqual("replaced", records[0]["status"])
        self.assertEqual("a1", records[1]["predecessor"])
        self.assertEqual("p0", records[1]["parent"])
        self.assertEqual(1, self.add("a3", predecessor="nope")[0])

    def test_fill_sums_last_assistant_message(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(1, 1, 1), {"type": "user"}, self.assistant(10, 200, 99790), {"type": "user"}])
        code, output = self.run_main("fill")
        self.assertEqual(0, code)
        self.assertIn("100000 tokens | window 200000 | 50% OVER", output)

    def test_fill_under_limit_and_window(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(0, 0, 50000)])
        self.assertNotIn("OVER", self.run_main("fill")[1])
        self.assertIn("window 1000000 | 5%", self.run_main("fill", "--window", "1000000")[1])
        self.assertIn("OVER", self.run_main("fill", "--limit", "0.2")[1])

    def test_fill_one_million_model(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(0, 0, 300000, model="claude-opus-4-6[1m]")])
        self.assertIn("window 1000000 | 30%", self.run_main("fill")[1])

    def test_fill_native_one_million_model_without_suffix(self):
        # Seen live: a fresh Sonnet 5.5 C at 80k tokens showed 40% against an assumed 200K window.
        self.add("a1")
        self.transcript("a1", [self.assistant(0, 0, 80000, model="claude-sonnet-5-5")])
        self.assertIn("window 1000000 | 8%", self.run_main("fill")[1])

    def test_window_for_models(self):
        one_m, two_k = sessions.NATIVE_1M_WINDOW, sessions.DEFAULT_WINDOW
        cases = {"claude-opus-5-5": one_m, "claude-sonnet-5-5": one_m, "claude-haiku-5-5": one_m,
                 "claude-fable-5-2": one_m, "claude-opus-4-7": one_m, "sonnet": one_m,
                 "claude-haiku-4-5-20251001": two_k, "claude-sonnet-4-6": two_k, "claude-opus-4-6": two_k,
                 "claude-sonnet-4-6[1m]": one_m, "": two_k}
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_DISABLE_1M_CONTEXT": ""}):
            for model, window in cases.items():
                self.assertEqual(window, sessions.window_for(model), model)
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_DISABLE_1M_CONTEXT": "1"}):
            self.assertEqual(two_k, sessions.window_for("claude-opus-5-5"))

    def test_fill_large_transcript_reads_from_end(self):
        self.add("a1")
        filler = [{"type": "user", "text": "x" * 1000}] * 2000
        self.transcript("a1", [self.assistant(7, 0, 0)] + filler)
        self.assertIn("7 tokens", self.run_main("fill")[1])

    def test_fill_skips_zero_usage_messages(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(3, 0, 40), self.assistant(0, 0, 0)])
        self.assertIn("43 tokens", self.run_main("fill")[1])

    def test_fill_non_ascii_and_chunk_boundary(self):
        self.add("a1")
        entries = [self.assistant(5, 0, 0)] + [{"type": "user", "text": "Привіт, світе " * 20}] * 30
        self.transcript("a1", entries)
        path = self.projects / "p1" / "a1.jsonl"
        for chunk in (7, 64, 1000, 4097):
            with mock.patch.object(sessions, "CHUNK", chunk):
                self.assertEqual((5, "claude-haiku-4-5-20251001"), sessions.last_usage(path), chunk)
        # a usage line cut in the middle by the first read must still be found whole
        self.transcript("a1", [self.assistant(9, 0, 0, model="модель")] + [{"type": "user", "text": "й" * 50}] * 3)
        lines = path.read_bytes().split(b"\n")
        with mock.patch.object(sessions, "CHUNK", len(lines[-2]) + len(lines[-3]) + 10):
            self.assertEqual((9, "модель"), sessions.last_usage(path))

    def test_fill_missing_transcript(self):
        self.add("a1")
        code, output = self.run_main("fill")
        self.assertEqual(0, code)
        self.assertIn("a1 | no transcript", output)

    def test_unreadable_registry(self):
        (dev_kit_state.project_state_dir(self.project) / "sessions.json").write_text("{nope", encoding="utf-8")
        self.assertEqual(2, self.run_main("list")[0])

    def test_state_dir_same_for_worktrees(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
        git(repo, "worktree", "add", "-q", str(self.tmp / "wt"), "-b", "side")
        first = dev_kit_state.project_state_dir(repo)
        self.assertEqual(first, dev_kit_state.project_state_dir(self.tmp / "wt"))
        self.assertTrue(first.name.startswith("repo-"))
        self.assertNotEqual(first, dev_kit_state.project_state_dir(self.project))

    def others_setup(self):
        """A repo on main with a worktree on branch `side` (one committed, one untracked file), and a session list."""
        repo, wt = self.tmp / "repo", self.tmp / "repo" / ".claude" / "worktrees" / "side"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
        git(repo, "worktree", "add", "-q", str(wt), "-b", "side")
        (wt / "a.md").write_text("a", encoding="utf-8")
        git(wt, "add", "a.md")
        git(wt, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "a")
        (wt / "b.py").write_text("b", encoding="utf-8")
        self.project = repo
        agents = [
            {"sessionId": "me", "name": "C: me", "cwd": str(repo), "kind": "background", "status": "busy"},
            {"sessionId": "lead", "name": "P: repo", "cwd": str(repo), "kind": "background", "status": "idle"},
            {"sessionId": "c1", "name": "C: side", "cwd": str(wt), "kind": "background", "status": "busy",
             "state": "working"},
            {"sessionId": "o1", "name": "Own idea", "cwd": str(repo), "kind": "interactive", "status": "idle"},
            {"sessionId": "x1", "name": "Elsewhere", "cwd": str(self.tmp), "kind": "interactive", "status": "idle"},
        ]
        listing = self.tmp / "agents.json"
        listing.write_text(json.dumps(agents), encoding="utf-8")
        env = mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(listing), "CLAUDE_CODE_SESSION_ID": "me"})
        env.start()
        self.addCleanup(env.stop)
        self.add("c1", name="C: side")
        return repo, wt

    def test_others_lists_sessions_of_this_repo(self):
        self.others_setup()
        self.transcript("c1", [
            {"type": "user", "isMeta": True, "message": {"content": "<local-command-caveat>x</local-command-caveat>"}},
            {"type": "user", "origin": {"kind": "human"}, "message": {"content": "<command-name>/x</command-name>"
                                                                               "<command-args>Fix login</command-args>"}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "noise"}]}},
            {"type": "user", "isMeta": True, "origin": {"kind": "peer", "body": "Full task:  login bug"},
             "message": {"content": "wrapper"}},
            {"type": "user", "origin": {"kind": "human"}, "message": {"content": "third, not shown"}},
        ])
        code, output = self.run_main("others", "--json")
        self.assertEqual(0, code)
        rows = {row["sessionId"]: row for row in json.loads(output)}
        self.assertEqual({"c1", "o1"}, set(rows))  # not the caller, the lead or another repo's session
        self.assertEqual("lead", rows["c1"]["startedBy"])
        self.assertEqual("owner", rows["o1"]["startedBy"])
        self.assertEqual("side", rows["c1"]["branch"])
        self.assertEqual("working", rows["c1"]["status"])
        self.assertEqual(["a.md", "b.py"], rows["c1"]["files"])
        self.assertEqual("Fix login // Full task: login bug", rows["c1"]["task"])
        self.assertEqual("main", rows["o1"]["branch"])
        self.assertEqual([], rows["o1"]["files"])
        text = self.run_main("others")[1]
        self.assertIn("C: side | background working | started by lead | branch side |", text)
        self.assertIn("  files: a.md, b.py", text)
        self.assertIn("  task: (no transcript)", text)  # o1 has none

    def test_others_none_self_flag_and_unreadable_list(self):
        self.others_setup()
        with mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(self.tmp / "agents.json")}):
            (self.tmp / "agents.json").write_text(json.dumps([{"sessionId": "me", "cwd": str(self.project)}]))
            self.assertIn("no other sessions", self.run_main("others")[1])
            self.assertIn("(no name)", self.run_main("others", "--self", "other")[1])
            (self.tmp / "agents.json").write_text("{not json")
            self.assertEqual(3, self.run_main("others")[0])

    def test_others_task_text_is_cut(self):
        self.others_setup()
        self.transcript("c1", [{"type": "user", "message": {"content": "w " * 1000}}])
        rows = {row["sessionId"]: row for row in json.loads(self.run_main("others", "--json")[1])}
        self.assertEqual(sessions.TASK_CHARS + 3, len(rows["c1"]["task"]))


if __name__ == "__main__":
    unittest.main()
