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
    def assistant(i, c, r, model="claude-opus-5-5"):
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
        self.transcript("a1", [self.assistant(0, 0, 300000, model="claude-opus-5-5[1m]")])
        self.assertIn("window 1000000 | 30%", self.run_main("fill")[1])

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
                self.assertEqual((5, "claude-opus-5-5"), sessions.last_usage(path), chunk)
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


if __name__ == "__main__":
    unittest.main()
