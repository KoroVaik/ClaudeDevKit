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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit" / "scripts"))
import hard_bans  # noqa: E402

BASH = "Bash(git push*)"
PWSH = "PowerShell(git push*)"
SETTINGS = ".claude/settings.json"


def git(cwd, *args):
    result = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)
    return result.stdout.decode("utf-8").rstrip()


class HardBansTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())  # a temporary repo: the script never runs on a real one
        self.addCleanup(shutil.rmtree, self.repo, True)
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@example.com")
        git(self.repo, "config", "user.name", "T")
        git(self.repo, "config", "commit.gpgsign", "false")
        git(self.repo, "config", "core.autocrlf", "false")
        (self.repo / "readme.md").write_text("hi\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "init")
        self.settings = self.repo / ".claude" / "settings.json"

    def run_cmd(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = hard_bans.main([argv[0], str(self.repo), *argv[1:]])
        return code, out.getvalue() + err.getvalue()

    def commits(self):
        return int(git(self.repo, "rev-list", "--count", "HEAD"))

    def deny(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))["permissions"]["deny"]

    def commit_settings(self, data, message="settings"):
        self.settings.parent.mkdir(exist_ok=True)
        self.settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        git(self.repo, "add", SETTINGS)
        git(self.repo, "commit", "-q", "-m", message)

    # protects: Flow - the first run creates the file and commits it alone
    def test_add_to_absent_file(self):
        code, out = self.run_cmd("add", BASH, PWSH)
        self.assertEqual((code, self.deny()), (0, [BASH, PWSH]))
        self.assertEqual(out.strip(), git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s"), "hard bans: add 2 deny lines")
        self.assertEqual(git(self.repo, "log", "-1", "--format=%(trailers:key=Hard-Bans,valueonly)").strip(), "add")
        self.assertIn(f"- {BASH}", git(self.repo, "log", "-1", "--format=%b"))
        self.assertEqual(git(self.repo, "show", "--name-only", "--format=", "HEAD"), SETTINGS)
        self.assertTrue(self.settings.read_text(encoding="utf-8").endswith("}\n"))

    # protects: Rule - add only appends, order and other keys stay
    def test_add_keeps_other_keys_and_lines(self):
        before = {"model": "x", "permissions": {"allow": ["Read(*)"], "deny": ["Bash(old*)"]}, "env": {"A": "1"}}
        self.commit_settings(before)
        code, _ = self.run_cmd("add", BASH)
        self.assertEqual(code, 0)
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(list(data), ["model", "permissions", "env"])
        self.assertEqual(data["permissions"], {"allow": ["Read(*)"], "deny": ["Bash(old*)", BASH]})
        self.assertEqual(data["env"], {"A": "1"})

    # protects: Edge - a Windows file stays CRLF, so the commit diff is only the new lines
    def test_add_keeps_crlf(self):
        self.settings.parent.mkdir()
        self.settings.write_bytes(b'{\r\n  "permissions": {\r\n    "deny": []\r\n  }\r\n}\r\n')
        git(self.repo, "add", SETTINGS)
        git(self.repo, "commit", "-q", "-m", "s")
        self.assertEqual(self.run_cmd("add", BASH)[0], 0)
        raw = self.settings.read_bytes()
        self.assertEqual(raw.count(b"\n"), raw.count(b"\r\n"))

    # protects: Rule - a line already there, or given twice, is added once
    def test_duplicates_skipped(self):
        self.commit_settings({"permissions": {"deny": [BASH]}})
        code, _ = self.run_cmd("add", BASH, PWSH, PWSH)
        self.assertEqual((code, self.deny()), (0, [BASH, PWSH]))
        self.assertEqual(git(self.repo, "log", "-1", "--format=%s"), "hard bans: add 1 deny lines")

    # protects: Rule - no new line means no commit
    def test_nothing_to_add_makes_no_commit(self):
        self.commit_settings({"permissions": {"deny": [BASH]}})
        count = self.commits()
        code, out = self.run_cmd("add", BASH)
        self.assertEqual((code, out.strip(), self.commits()), (0, "nothing to add", count))

    # protects: Rule - only main gets bans
    def test_refuses_off_main(self):
        git(self.repo, "checkout", "-q", "-b", "other")
        count = self.commits()
        code, out = self.run_cmd("add", BASH)
        self.assertEqual((code, self.commits(), self.settings.exists()), (1, count, False))
        self.assertIn("not on branch main", out)

    # protects: Rule - an uncommitted edit of the file is never swept into a commit
    def test_refuses_dirty_settings(self):
        self.commit_settings({"permissions": {"deny": [BASH]}})
        self.settings.write_text('{"permissions": {"deny": []}, "mine": 1}\n', encoding="utf-8")
        count = self.commits()
        code, out = self.run_cmd("add", PWSH)
        self.assertEqual((code, self.commits()), (1, count))
        self.assertIn("uncommitted", out)
        self.assertIn('"mine"', self.settings.read_text(encoding="utf-8"))

    # protects: Rule - other staged and unstaged work stays out of the commit
    def test_other_dirty_files_untouched(self):
        (self.repo / "readme.md").write_text("edited\n", encoding="utf-8")
        (self.repo / "staged.txt").write_text("s\n", encoding="utf-8")
        git(self.repo, "add", "staged.txt")
        (self.repo / "new.txt").write_text("n\n", encoding="utf-8")
        self.assertEqual(self.run_cmd("add", BASH)[0], 0)
        self.assertEqual(git(self.repo, "show", "--name-only", "--format=", "HEAD"), SETTINGS)
        status = git(self.repo, "status", "--porcelain").splitlines()
        self.assertEqual(sorted(status), sorted([" M readme.md", "A  staged.txt", "?? new.txt"]))
        self.assertEqual((self.repo / "readme.md").read_text(encoding="utf-8"), "edited\n")

    # protects: Edge - a typo must not land in the deny list; nothing is committed
    def test_invalid_line_refused(self):
        count = self.commits()
        for bad in ("git push", "Bash()", "Bash(x", "(x)", "Bash (x)"):
            code, _ = self.run_cmd("add", BASH, bad)
            self.assertEqual(code, 1, bad)
        self.assertEqual((self.commits(), self.settings.exists()), (count, False))

    # protects: Flow - one step back removes exactly the lines of the latest add
    def test_undo_reverts_latest_add(self):
        self.commit_settings({"model": "x", "permissions": {"deny": ["Bash(old*)"]}})
        self.run_cmd("add", BASH)
        added = git(self.repo, "rev-parse", "HEAD")
        code, out = self.run_cmd("undo")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(json.loads(self.settings.read_text(encoding="utf-8")),
                         {"model": "x", "permissions": {"deny": ["Bash(old*)"]}})
        trailer = git(self.repo, "log", "-1", "--format=%(trailers:key=Hard-Bans,valueonly)").strip()
        self.assertEqual(trailer, f"undo {added}")

    # protects: Edge - undoing the add that created the file removes the file
    def test_undo_of_file_creating_add(self):
        self.run_cmd("add", BASH)
        code, _ = self.run_cmd("undo")
        self.assertEqual((code, self.settings.exists()), (0, False))

    # protects: Rule - only one step back
    def test_second_undo_refused(self):
        self.run_cmd("add", BASH)
        self.run_cmd("add", PWSH)
        self.assertEqual(self.run_cmd("undo")[0], 0)
        count = self.commits()
        code, out = self.run_cmd("undo")
        self.assertEqual((code, self.commits()), (1, count))
        self.assertIn("one step back", out)
        self.assertEqual(self.deny(), [BASH])

    # protects: Rule - a later change of the file is not ours to undo
    def test_undo_refused_after_other_change(self):
        self.run_cmd("add", BASH)
        self.commit_settings({"permissions": {"deny": [BASH, "Bash(mine*)"]}}, "owner edit")
        count = self.commits()
        code, out = self.run_cmd("undo")
        self.assertEqual((code, self.commits()), (1, count))
        self.assertIn("after the hard-bans commit", out)
        self.assertEqual(self.deny(), [BASH, "Bash(mine*)"])

    # protects: Edge - a file the script never wrote is left alone
    def test_undo_refused_without_hard_bans_commit(self):
        self.commit_settings({"permissions": {"deny": [BASH]}})
        self.assertEqual(self.run_cmd("undo")[0], 1)

    # protects: Rule - undo does not sweep in other work either
    def test_undo_keeps_other_dirty_files(self):
        self.run_cmd("add", BASH)
        (self.repo / "readme.md").write_text("edited\n", encoding="utf-8")
        self.assertEqual(self.run_cmd("undo")[0], 0)
        self.assertEqual(git(self.repo, "show", "--name-only", "--format=", "HEAD"), SETTINGS)
        self.assertEqual(git(self.repo, "status", "--porcelain"), " M readme.md")

    def write_bans(self, text):
        path = self.repo / ".claude" / "hard-bans.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(text if isinstance(text, str) else json.dumps(text), encoding="utf-8")

    # protects: Flow - the owner's one short command adds the approved set, both files in one commit
    def test_add_approved_one_commit_with_both_files(self):
        self.commit_settings({"permissions": {"deny": ["Bash(old*)"]}})
        self.write_bans({"deny": ["Bash(old*)", BASH, PWSH]})
        code, out = self.run_cmd("add-approved")
        self.assertEqual((code, self.deny()), (0, ["Bash(old*)", BASH, PWSH]))
        self.assertIn(f"added: {BASH}", out)
        self.assertNotIn("added: Bash(old*)", out)
        self.assertEqual(out.strip().splitlines()[-1], git(self.repo, "rev-parse", "HEAD"))
        self.assertEqual(sorted(git(self.repo, "show", "--name-only", "--format=", "HEAD").split()),
                         [".claude/hard-bans.json", SETTINGS])
        self.assertEqual(git(self.repo, "log", "-1", "--format=%(trailers:key=Hard-Bans,valueonly)").strip(), "add")
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    # protects: Flow - with no repo argument the command works on the git top folder of the current directory
    def test_add_approved_default_repo_from_cwd(self):
        self.write_bans({"deny": [BASH]})
        sub = self.repo / "sub"
        sub.mkdir()
        old = Path.cwd()
        self.addCleanup(os.chdir, old)
        os.chdir(sub)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = hard_bans.main(["add-approved"])
        self.assertEqual((code, self.deny()), (0, [BASH]))

    # protects: Rule - without the approved file, or with a broken one, nothing is added
    def test_add_approved_refuses_absent_or_invalid_file(self):
        count = self.commits()
        code, out = self.run_cmd("add-approved")
        self.assertEqual(code, 1)
        self.assertIn("absent", out)
        for bad in ("{not json", "[]", '{"deny": "Bash(x)"}', '{"deny": []}', '{"deny": ["git push"]}', '{"deny": [1]}'):
            self.write_bans(bad)
            self.assertEqual(self.run_cmd("add-approved")[0], 1, bad)
        self.assertEqual((self.commits(), self.settings.exists()), (count, False))

    # protects: Rule - add-approved keeps the checks of add (main only, settings file clean)
    def test_add_approved_keeps_add_checks(self):
        self.write_bans({"deny": [BASH]})
        self.commit_settings({"permissions": {"deny": []}})
        self.settings.write_text('{"mine": 1}\n', encoding="utf-8")
        self.assertEqual(self.run_cmd("add-approved")[0], 1)
        git(self.repo, "checkout", "--", SETTINGS)
        git(self.repo, "checkout", "-q", "-b", "other")
        self.assertEqual(self.run_cmd("add-approved")[0], 1)
        self.assertEqual(self.deny(), [])

    # protects: Rule - nothing new and an unchanged file mean no commit; a new file alone is still recorded
    def test_add_approved_nothing_to_add(self):
        self.write_bans({"deny": [BASH]})
        self.assertEqual(self.run_cmd("add-approved")[0], 0)
        count = self.commits()
        code, out = self.run_cmd("add-approved")
        self.assertEqual((code, out.strip(), self.commits()), (0, "nothing to add", count))
        self.write_bans({"deny": [BASH, BASH]})
        self.assertEqual(self.run_cmd("add-approved")[0], 0)
        self.assertEqual((self.commits(), git(self.repo, "show", "--name-only", "--format=", "HEAD")),
                         (count + 1, ".claude/hard-bans.json"))

    # protects: Flow - the owner can take back the latest add-approved commit, both files
    def test_undo_of_add_approved_commit(self):
        self.commit_settings({"model": "x", "permissions": {"deny": ["Bash(old*)"]}})
        self.write_bans({"deny": [BASH]})
        self.run_cmd("add-approved")
        added = git(self.repo, "rev-parse", "HEAD")
        code, _ = self.run_cmd("undo")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(self.settings.read_text(encoding="utf-8")),
                         {"model": "x", "permissions": {"deny": ["Bash(old*)"]}})
        self.assertFalse((self.repo / ".claude" / "hard-bans.json").exists())
        self.assertEqual(sorted(git(self.repo, "show", "--name-only", "--format=", "HEAD").split()),
                         [".claude/hard-bans.json", SETTINGS])
        self.assertEqual(git(self.repo, "log", "-1", "--format=%(trailers:key=Hard-Bans,valueonly)").strip(),
                         f"undo {added}")

    # protects: Rule - a hard-bans.json edited after the add is not ours to revert
    def test_undo_refused_when_bans_file_changed_since(self):
        self.write_bans({"deny": [BASH]})
        self.run_cmd("add-approved")
        self.write_bans({"deny": [BASH, PWSH]})
        count = self.commits()
        code, out = self.run_cmd("undo")
        self.assertEqual((code, self.commits()), (1, count))
        self.assertIn("changed after", out)

    # protects: Bug - a staged file of other work must not stop an undo or enter its commit
    def test_undo_with_other_file_staged(self):
        self.write_bans({"deny": [BASH]})
        self.run_cmd("add-approved")
        (self.repo / "staged.txt").write_text("s\n", encoding="utf-8")
        git(self.repo, "add", "staged.txt")
        code, _ = self.run_cmd("undo")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(git(self.repo, "show", "--name-only", "--format=", "HEAD").split()),
                         [".claude/hard-bans.json", SETTINGS])
        self.assertEqual(git(self.repo, "status", "--porcelain"), "A  staged.txt")

    # protects: Flow - the gate needs a Bash and a PowerShell line, same as Pult
    def test_check_pass_and_fail(self):
        self.assertEqual(self.run_cmd("check")[0], 1)  # no file
        self.commit_settings({"permissions": {"deny": [BASH, "Bash(rm -rf*)"]}})
        code, out = self.run_cmd("check")
        self.assertEqual(code, 1)
        self.assertIn("PowerShell", out)
        self.run_cmd("add", "PowerShell(docker*)")
        self.assertEqual(self.run_cmd("check")[0], 0)

    # protects: Rule - an uncommitted file does not pass the gate
    def test_check_reads_committed_main_only(self):
        self.commit_settings({"permissions": {"deny": []}})
        self.settings.write_text(json.dumps({"permissions": {"deny": [BASH, PWSH]}}), encoding="utf-8")
        self.assertEqual(self.run_cmd("check")[0], 1)

    # protects: Edge - a wrong path exits 2, not a traceback
    def test_not_a_repo_is_an_error(self):
        out, err = io.StringIO(), io.StringIO()
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder, True)
        with redirect_stdout(out), redirect_stderr(err):
            self.assertEqual(hard_bans.main(["check", str(folder)]), 2)


if __name__ == "__main__":
    unittest.main()
