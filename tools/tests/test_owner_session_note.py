import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "dev-kit"
SCRIPT = PLUGIN / "hooks" / "owner-session-note.py"
sys.path.insert(0, str(PLUGIN / "scripts"))
import sessions  # noqa: E402

OWNER_ID = "11111111-aaaa-bbbb-cccc-000000000001"
LEAD_ID = "22222222-aaaa-bbbb-cccc-000000000002"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                   capture_output=True)


class OwnerSessionNoteTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.state = tmp / "state"
        self.repo = tmp / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "i")
        self.worktree = tmp / "wt"
        git(self.repo, "worktree", "add", "-q", str(self.worktree), "-b", "side")
        self.env = {**os.environ, "DEV_KIT_STATE_DIR": str(self.state)}
        self.register(OWNER_ID, "Own idea", owner=True)
        self.register(LEAD_ID, "C: task", owner=False)

    def register(self, session_id, name, owner):
        argv = ["--project", str(self.repo), "add", "--id", session_id, "--name", name, "--worktree", "wt",
                "--task", "t"] + (["--owner"] if owner else [])
        with mock.patch.dict(os.environ, self.env), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(0, sessions.main(argv))

    def run_hook(self, payload, cwd=None):
        data = payload if isinstance(payload, bytes) else json.dumps(
            {"session_id": payload, "cwd": str(cwd or self.repo)}).encode("utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT)], input=data, capture_output=True, env=self.env)
        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", "replace"))
        return result.stdout.decode("utf-8")

    def note(self, output):
        data = json.loads(output)["hookSpecificOutput"]
        self.assertEqual("UserPromptSubmit", data["hookEventName"])
        return data["additionalContext"]

    def test_registered_owner_session_gets_the_note(self):  # Flow
        text = self.note(self.run_hook(OWNER_ID))
        self.assertIn("«Роботу завершено»", text)
        self.assertIn("коміть у main", text)

    def test_owner_session_registered_by_short_id(self):  # Edge
        self.register("33333333", "Short", owner=True)
        self.assertIn("«Роботу завершено»", self.note(self.run_hook("33333333-aaaa-bbbb-cccc-000000000003")))
        self.assertEqual("", self.run_hook("3333333-aaaa"))

    def test_worktree_session_does_not_get_the_commit_sentence(self):  # Rule
        text = self.note(self.run_hook(OWNER_ID, cwd=self.worktree))
        self.assertIn("«Роботу завершено»", text)
        self.assertNotIn("коміть у main", text)

    def test_other_sessions_get_nothing(self):  # Rule
        self.assertEqual("", self.run_hook(LEAD_ID))  # registered, not an owner session
        self.assertEqual("", self.run_hook("99999999-aaaa-bbbb-cccc-000000000009"))  # not registered

    def test_ended_owner_record_gets_nothing(self):  # Rule
        argv = ["--project", str(self.repo), "end", "--id", OWNER_ID]
        with mock.patch.dict(os.environ, self.env), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            sessions.main(argv)
        self.assertEqual("", self.run_hook(OWNER_ID))

    def test_project_without_registry_creates_no_state_folder(self):  # Bug
        # The hook runs on every prompt of every project; it must not leave a folder in the user's state root.
        other = self.state.parent / "other"
        other.mkdir()
        git(other, "init", "-q", "-b", "main")
        before = sorted(p.name for p in self.state.iterdir())
        self.assertEqual("", self.run_hook("44444444-aaaa", cwd=other))
        self.assertEqual(before, sorted(p.name for p in self.state.iterdir()))

    def test_garbage_input_never_blocks(self):  # Edge
        for data in (b"not json", b"", b"[1, 2]", b'{"session_id": 5}', b'{"session_id": "x", "cwd": "/no/such"}',
                     b"\xff\xfe"):
            self.assertEqual("", self.run_hook(data), data)

    def test_unreadable_registry_never_blocks(self):  # Edge
        for registry in self.state.glob("*/sessions.json"):
            registry.write_text("{nope", encoding="utf-8")
        self.assertEqual("", self.run_hook(OWNER_ID))


if __name__ == "__main__":
    unittest.main()
