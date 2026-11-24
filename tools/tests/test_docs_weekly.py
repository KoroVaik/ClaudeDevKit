import datetime
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PLUGIN = Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit"
sys.path.insert(0, str(PLUGIN / "scripts"))
import dev_kit_state  # noqa: E402
import docs_weekly  # noqa: E402
import sessions  # noqa: E402


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                   capture_output=True)


def make_repo(path, lead=True):
    """A git repository; a project with a lead has the `## project-lead` line in its dev-kit profile."""
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "commit", "-q", "--allow-empty", "-m", "i")
    if lead:
        (path / ".claude").mkdir()
        (path / ".claude" / "dev-kit.md").write_text("# dev-kit profile\n\n## project-lead\n\n| a | b |\n",
                                                     encoding="utf-8")
    return path


def hours(value):
    """An ISO time `value` hours ago."""
    return (docs_weekly.now_utc() - datetime.timedelta(hours=value)).isoformat()


class DocsWeeklyTestCase(unittest.TestCase):
    """Temp state and rules-kit folders, one project `repo` with a lead; the retro's run file is written by hand."""

    def setUp(self):
        tmp = Path(os.path.realpath(tempfile.mkdtemp()))  # git reports real paths
        self.addCleanup(shutil.rmtree, tmp, True)
        self.tmp = tmp
        self.state = tmp / "state"
        self.rules = tmp / "rules-kit"
        self.repo = make_repo(tmp / "repo")
        self.name = dev_kit_state.folder_name(self.repo)
        self.docs = self.state / self.name  # the docs folder of the project
        patcher = mock.patch.dict(os.environ, {dev_kit_state.STATE_ENV: str(self.state),
                                               docs_weekly.RULES_KIT_ENV: str(self.rules),
                                               docs_weekly.NO_START_ENV: "1"})
        patcher.start()
        os.environ.pop(docs_weekly.OLD_RETRO_ENV, None)  # restored with the patch: never the real `~/.claude`
        self.addCleanup(patcher.stop)

    def stamps(self, **values):
        """Replace `docs.json` of the project."""
        docs_weekly.write_json(self.docs / "docs.json", values)

    def read_stamps(self):
        return json.loads((self.docs / "docs.json").read_text(encoding="utf-8"))

    def run_file(self, **values):
        """Replace the retro's run file of the project (what `plugins/rules-kit/scripts/retro.py` writes)."""
        docs_weekly.write_json(self.rules / "runs" / f"{self.name}.json", values)

    def start(self, title="C: task", cwd=None, claude="fake-claude"):
        """hook_start with the spawn recorded; returns the recorded commands."""
        spawned = []
        with mock.patch.object(docs_weekly, "spawn", lambda argv, cwd=None: spawned.append((argv, cwd))), \
                mock.patch.object(sessions, "find_claude", return_value=claude), mock.patch.dict(os.environ):
            os.environ.pop(docs_weekly.NO_START_ENV, None)
            docs_weekly.hook_start({"cwd": str(cwd or self.repo), "session_id": "s-1", "session_title": title})
        return spawned

    def command(self):
        return ["fake-claude", "--bg", "--name", "Документація: repo", "--settings",
                str(docs_weekly.NO_REMOTE_CONTROL), "--model", "opus", "--effort", "medium", "--permission-mode",
                "bypassPermissions", "--", "/dev-kit:maintain-project-docs weekly"]

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            code = docs_weekly.main(list(args))
        return code, out.getvalue(), err.getvalue()

    # protects: Flow
    def test_the_weekly_docs_session_starts_after_the_retro_or_on_its_own_once_a_week(self):
        started = [(self.command(), str(self.repo))]
        self.assertEqual(self.start(), started)  # never ran, no run file: on its own, in main
        self.assertIsNotNone(docs_weekly.parse_time(self.read_stamps()["docs_started"]))
        self.assertEqual(self.start(), [])  # started a moment ago
        self.assertEqual(self.cli("done", "--project", str(self.repo))[0], 0)
        self.assertEqual(self.start(), [])  # ran this week
        week = docs_weekly.DOCS_DAYS * 24
        self.stamps(docs_done=hours(week - 1))
        self.assertEqual(self.start(), [])  # a day short of a week
        self.stamps(docs_done=hours(week + 1))
        self.assertEqual(self.start(), started)  # a week with no retro
        self.stamps(docs_done=hours(week + 1))
        self.run_file(retro_started=hours(1), last_review=None, retro_branch=None, retro_due=False)
        self.assertEqual(self.start(), [])  # the retro session may still run
        self.run_file(retro_started=hours(docs_weekly.START_GUARD_HOURS + 1), last_review=None, retro_due=True)
        self.assertEqual(self.start(), [])  # findings wait: the retro session starts first
        self.run_file(retro_started=hours(2), last_review=hours(1), retro_branch=None, retro_due=False)
        self.assertEqual(self.start(title="Документація: repo"), [])  # the docs session starts nothing
        self.assertEqual(self.start(title="Ретро: repo"), [])  # nor the retro session
        self.assertEqual(self.start(), started)  # after the retro ended
        self.stamps(docs_started=hours(docs_weekly.DOCS_GUARD_HOURS - 1), docs_done=hours(week + 1))
        self.assertEqual(self.start(), [])  # a run with no `done` is retried once a day, not sooner
        self.stamps(docs_started=hours(docs_weekly.DOCS_GUARD_HOURS + 1), docs_done=hours(week + 1))
        self.assertEqual(self.start(), started)

    # protects: Rule
    def test_the_docs_session_waits_for_the_merge_of_the_retro_branch_at_most_two_days(self):
        git(self.repo, "branch", "retro-x")
        git(self.repo, "checkout", "-q", "retro-x")
        git(self.repo, "commit", "-q", "--allow-empty", "-m", "fix")
        git(self.repo, "checkout", "-q", "main")
        self.run_file(retro_started=hours(2), last_review=hours(1), retro_branch="retro-x", retro_due=False)
        self.assertEqual(self.start(), [])  # the retro's fixes are not on main yet
        self.run_file(retro_started=hours(docs_weekly.DOCS_MERGE_WAIT_HOURS + 2),
                      last_review=hours(docs_weekly.DOCS_MERGE_WAIT_HOURS + 1), retro_branch="retro-x", retro_due=False)
        self.assertEqual(len(self.start()), 1)  # waited long enough: runs anyway
        self.stamps()
        self.run_file(retro_started=hours(2), last_review=hours(1), retro_branch="retro-x", retro_due=False)
        git(self.repo, "merge", "-q", "--ff-only", "retro-x")
        self.assertEqual(len(self.start()), 1)  # merged
        self.stamps()
        git(self.repo, "branch", "-q", "-D", "retro-x")
        self.assertEqual(len(self.start()), 1)  # deleted after its merge
        self.stamps()
        self.run_file(retro_started=hours(2), last_review=hours(1), retro_branch=None, retro_due=False)
        self.assertEqual(len(self.start()), 1)  # nothing to merge

    # protects: Edge
    def test_a_broken_run_file_or_no_lead_or_no_claude_starts_nothing_and_stamps_nothing(self):
        plain = make_repo(self.tmp / "plain", lead=False)
        self.assertEqual(self.start(cwd=plain), [])
        self.assertFalse(self.state.exists())  # not even a folder for a project with no lead
        self.assertEqual(self.start(claude=None), [])  # no claude command: no stamp, a later session retries
        self.assertFalse((self.docs / "docs.json").exists())
        (self.rules / "runs").mkdir(parents=True)
        (self.rules / "runs" / f"{self.name}.json").write_text("{nope", encoding="utf-8")
        self.assertEqual(len(self.start()), 1)  # an unreadable file means no retro to wait for

    # protects: Rule
    def test_no_start_env_stamps_but_does_not_spawn(self):
        with mock.patch.object(docs_weekly, "spawn") as spawn, mock.patch.object(sessions, "find_claude",
                                                                                    return_value="c"):
            docs_weekly.hook_start({"cwd": str(self.repo), "session_id": "s", "session_title": "C: x"})  # env set by setUp
        spawn.assert_not_called()
        self.assertIn("docs_started", self.read_stamps())

    # protects: Flow
    def test_items_lists_the_docs_items_and_done_stamps_the_end(self):
        (self.docs / "docs-items").mkdir(parents=True)
        (self.docs / "docs-items" / "stale-epic.md").write_text("# stale epic\n- status: open\n", encoding="utf-8")
        (self.docs / "docs-items" / "product-rule.md").write_text("# product rule\n- status: owner\n", encoding="utf-8")
        (self.docs / "docs-items" / "no-status.md").write_text("# nothing\n", encoding="utf-8")
        code, out, _ = self.cli("items", "--project", str(self.repo))
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines()[0], str(self.docs))
        self.assertTrue(out.rstrip().endswith("## Docs items\nno-status | ?\nproduct-rule | owner\nstale-epic | open"))
        self.assertEqual(self.cli("done", "--project", str(self.repo))[:2], (0, "docs run stamped\n"))
        self.assertIsNotNone(docs_weekly.parse_time(self.read_stamps()["docs_done"]))
        plain = make_repo(self.tmp / "plain", lead=False)
        for command in ("items", "done"):
            self.assertEqual(self.cli(command, "--project", str(plain))[0], 2)  # not a project with a lead

    # protects: Flow
    def test_the_docs_stamps_and_items_of_the_old_retro_folder_are_copied_once_and_stay(self):
        old = self.tmp / "old-retro"
        (old / self.name / "docs-items").mkdir(parents=True)
        (old / self.name / "state.json").write_text(
            json.dumps({"docs_done": hours(3), "docs_started": hours(4), "lead_session": "x"}), encoding="utf-8")
        (old / self.name / "docs-items" / "k.md").write_text("- status: owner\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {docs_weekly.OLD_RETRO_ENV: str(old)}):
            self.assertEqual(self.start(), [])  # ran 3 hours ago, in the old folder: not due
            self.assertEqual(sorted(self.read_stamps()), ["docs_done", "docs_started"])  # no `lead_session`, no other key
            self.assertEqual((self.docs / "docs-items" / "k.md").read_text(encoding="utf-8"), "- status: owner\n")
            self.cli("done", "--project", str(self.repo))
            (old / self.name / "docs-items" / "k.md").write_text("- status: fixed\n", encoding="utf-8")
            self.cli("items", "--project", str(self.repo))
        self.assertEqual((self.docs / "docs-items" / "k.md").read_text(encoding="utf-8"), "- status: owner\n")  # not again
        self.assertIn("- status: fixed", (old / self.name / "docs-items" / "k.md").read_text(encoding="utf-8"))

    # protects: Edge
    def test_the_hook_script_exits_0_with_no_output_on_bad_input_and_starts_the_session_in_a_project_with_a_lead(self):
        fake = self.tmp / "bin"
        fake.mkdir()
        name = "claude.cmd" if os.name == "nt" else "claude"
        (fake / name).write_text("@exit 0\n" if os.name == "nt" else "#!/bin/sh\nexit 0\n", encoding="utf-8")
        (fake / name).chmod(0o755)
        env = {**os.environ, "PATH": str(fake) + os.pathsep + os.environ.get("PATH", "")}
        script = PLUGIN / "hooks" / "docs-start.py"
        payload = json.dumps({"cwd": str(self.repo), "session_id": "s-9", "session_title": "C: x"}).encode()
        for data in (b"not json", b"", b"[1]", b"\xff\xfe", b"{}", payload):
            result = subprocess.run([sys.executable, str(script)], input=data, env=env, capture_output=True)
            self.assertEqual((result.returncode, result.stdout), (0, b""), data)
        self.assertIn("docs_started", self.read_stamps())  # DEV_KIT_DOCS_NO_START=1: stamped, no session started


if __name__ == "__main__":
    unittest.main()
