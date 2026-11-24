import datetime
import io
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
from test_parts import command, owner, plugins_with_demo, said  # noqa: E402
from test_retro import RetroFixture, git  # noqa: E402

PLUGIN = TESTS.parent.parent / "plugins" / "rules-kit"
sys.path.insert(0, str(PLUGIN / "scripts"))
import fixes  # noqa: E402
import retro  # noqa: E402

TODAY = datetime.date.today()


def days_ago(count):
    return (TODAY - datetime.timedelta(days=count)).isoformat()


class FixLoopTestCase(RetroFixture):
    """The fix loop's commands on the project's own set `repo` (its root is the temp git repository)."""

    def setUp(self):
        super().setUp()
        start = Path.cwd()
        self.addCleanup(os.chdir, start)
        os.chdir(self.repo)  # `fixed` and `revert` work in the current folder, the retro's worktree
        patcher = mock.patch.dict(os.environ, {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                                               "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
        patcher.start()  # `git revert` commits: a machine with no git identity must not fail
        self.addCleanup(patcher.stop)

    def item(self, key, text, set_name="repo"):
        path = self.set_folder(set_name) / "items" / f"{key}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def commit(self, rel, text, message="retro-fix", repo=None):
        repo = repo or self.repo
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        git(repo, "add", rel)
        git(repo, "commit", "-q", "-m", message)
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

    def enter_worktree(self):
        """The retro's worktree of the project (a revert runs only there): made from main, and the current folder."""
        work = self.tmp / "retro-worktree"
        git(self.repo, "worktree", "add", "-q", "-b", "retro-wt", str(work))
        os.chdir(work)
        return work

    def done_list(self):
        path = self.retro / fixes.DONE_FILE
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []

    def status(self, key, set_name="repo"):
        return fixes.Item(self.set_folder(set_name) / "items" / f"{key}.md", set_name).status

    # protects: Rule
    def test_a_one_off_unseen_for_14_days_expires_and_others_stay(self):
        self.item("old-one", f"# Старе\n- status: waiting\n- seen: {days_ago(14)} | S (abcdef12) | x\n")
        self.item("young-one", f"# Нове\n- status: waiting\n- seen: {days_ago(13)} | S (abcdef12) | x\n")
        self.item("twice", f"# Двічі\n- status: waiting\n- seen: {days_ago(20)} | a\n- seen: {days_ago(19)} | b\n")
        self.item("fixed-one", f"# Виправлене\n- status: fixed\n- seen: {days_ago(30)} | a\n")
        out = self.project_cmd("items")
        self.assertIn("expired: repo/old-one", out)
        self.assertEqual([self.status(key) for key in ("old-one", "young-one", "twice", "fixed-one")],
                         ["expired", "waiting", "waiting", "fixed"])
        self.assertEqual([(entry["key"], entry["action"]) for entry in self.done_list()], [("old-one", "expired")])
        self.assertIn("Старе", self.done_list()[0]["text"])

    # protects: Flow
    def test_a_fix_is_recorded_reverted_once_then_parked_on_the_second_failed_try(self):
        self.item("vague-step", "# Нечіткий крок\n- status: waiting\n- kind: no rule\n- seen: 2026-11-20 | S (abcdef12) | x\n"
                                "\nБуло: ...\n")
        work = self.enter_worktree()
        first = self.commit("CLAUDE.md", "rule v1\n", repo=work)
        out = self.run_cmd("fixed", "--item", "vague-step", "--commit", first, "--what", "merged two lines")
        self.assertIn("landed in the last 7 days: 1 of 5", out)
        text = (self.set_folder("repo") / "items" / "vague-step.md").read_text(encoding="utf-8")
        self.assertIn(f"- fix: {TODAY} | repo | {first} | CLAUDE.md | merged two lines\n\nБуло:", text)
        self.assertEqual(self.status("vague-step"), "fixed")
        self.assertIn("reverted", self.run_cmd("revert", "--item", "vague-step"))
        self.assertFalse((work / "CLAUDE.md").exists())  # the revert commit undid the fix
        self.assertEqual(self.status("vague-step"), "reverted")
        second = self.commit("CLAUDE.md", "rule v2\n", repo=work)
        self.run_cmd("fixed", "--item", "vague-step", "--commit", second)
        self.run_cmd("revert", "--item", "vague-step")
        self.assertEqual(self.status("vague-step"), "parked")
        self.assertEqual([entry["action"] for entry in self.done_list()],
                         ["fixed", "reverted", "fixed", "reverted", "parked"])
        listing = self.run_cmd("list", "--days", "7")
        self.assertEqual(len(listing.splitlines()), 5)
        self.assertTrue(listing.startswith(f"{TODAY} | repo | Виправлено правило (CLAUDE.md): Нечіткий крок (vague-step, fixed)"))

    # protects: Flow
    def test_a_revert_request_shows_in_items_and_the_revert_clears_it(self):
        self.item("bad-fix", "# Погана зміна\n- status: fixed\n")
        work = self.enter_worktree()
        commit = self.commit("CLAUDE.md", "rule\n", repo=work)
        self.run_cmd("fixed", "--item", "bad-fix", "--commit", commit)
        self.assertIn("revert requested: repo/bad-fix", self.run_cmd("revert-request", "bad-fix"))
        self.assertIn("## Revert requests\nrepo | bad-fix\n", self.project_cmd("items"))
        self.run_cmd("revert", "--item", "bad-fix")
        self.assertIn("## Revert requests\n(none)\n", self.project_cmd("items"))
        with mock.patch("sys.stderr", io.StringIO()) as err:
            self.assertEqual(retro.main(["revert-request", "no-such-key"]), 2)
        self.assertIn("no item no-such-key", err.getvalue())

    # protects: Flow
    def test_the_check_waits_for_main_then_lists_only_sessions_started_after_the_fix_reached_it(self):
        self.item("late", "# Пізно\n- status: fixed\n")
        git(self.repo, "checkout", "-q", "-b", "retro-x")
        commit = self.commit("CLAUDE.md", "rule\n")
        self.run_cmd("fixed", "--item", "late", "--commit", commit)
        self.assertIn("not in main yet", self.project_cmd("check"))
        git(self.repo, "checkout", "-q", "main")
        git(self.repo, "merge", "-q", "--ff-only", "retro-x")
        after = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).isoformat()
        self.write("proj/aaaa1111-0.jsonl", [{"type": "user", "timestamp": "2020-01-01T00:00:00Z", "message": {"content": "x"}}])
        self.write("proj/bbbb2222-0.jsonl", [{"type": "user", "timestamp": after, "message": {"content": "y"}}])
        out = self.project_cmd("check")
        self.assertIn("in main since", out)
        self.assertIn("sessions after: 1", out)
        self.assertIn("(bbbb2222)", out)
        self.assertNotIn("aaaa1111", out)

    # protects: Edge
    def test_a_new_finding_in_a_file_of_a_recent_fix_is_linked_to_it(self):
        self.item("recent", f"# Свіже\n- status: fixed\n- fix: {days_ago(3)} | repo | abc1234 | .claude/rules.md | -\n")
        self.item("old", f"# Давнє\n- status: fixed\n- fix: {days_ago(30)} | repo | abc5678 | CLAUDE.md | -\n")
        new = self.set_folder("repo") / "new" / "scan.md"
        new.parent.mkdir(parents=True)
        new.write_text("- repo | S (abcdef12) | part reader: .claude/rules.md:4 | wrong order\n"
                       "- repo | S (abcdef12) | part reader: CLAUDE.md:2 | other\n", encoding="utf-8")
        out = self.project_cmd("items")
        self.assertIn(".claude/rules.md:4 | wrong order | possible breakage: recent\n", out)
        self.assertIn("CLAUDE.md:2 | other\n", out)  # the fix of that file is older than 14 days

    # protects: Rule
    def test_the_spend_cap_is_two_percent_of_the_weekly_limit(self):
        def run(stdout, code=0):
            return mock.patch.object(fixes.spend_client, "run", return_value=None if stdout is None else
                                     subprocess.CompletedProcess([], code, stdout, ""))
        for stdout, word in (("~2.3% of the weekly limit, estimate\nmain 1%", "over"),
                             ("~1.9% of the weekly limit, estimate", "under"), (None, "unknown")):
            with run(stdout):
                self.assertTrue(self.run_cmd("budget", "--session-id", "s1").startswith(word + ":"), stdout)


    def code(self, *args):
        """`(exit code, stdout, stderr)` of a retro command."""
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
            return retro.main(list(args)), out.getvalue(), err.getvalue()

    # protects: Rule
    def test_a_revert_runs_only_in_a_worktree_never_in_a_main_checkout_and_in_place_in_the_global_folder(self):
        self.item("risky", "# Ризик\n- status: fixed\n")
        commit = self.commit("CLAUDE.md", "rule\n")  # on main, in the main checkout (the current folder)
        self.run_cmd("fixed", "--item", "risky", "--commit", commit)
        code, _, err = self.code("revert", "--item", "risky")
        self.assertEqual(code, 1)
        self.assertIn("main checkout", err)
        self.assertTrue((self.repo / "CLAUDE.md").exists())  # nothing was reverted on main
        self.assertEqual(self.status("risky"), "fixed")
        self.assertEqual(len(subprocess.run(["git", "log", "--oneline"], cwd=self.repo, capture_output=True,
                                            text=True).stdout.splitlines()), 2, "no revert commit on main")
        self.assertIsNone(fixes.revert_refusal(self.repo, self.repo), "the global folder reverts in place")
        work = self.enter_worktree()
        self.assertIsNone(fixes.revert_refusal(work, self.tmp / "global"))

    # protects: Rule
    def test_the_old_retros_fix_lines_give_their_commit_or_a_date_only_fix_that_cannot_be_reverted(self):
        self.item("old-a", f"# Старе\n- status: trivial-fixed\n- fix: {days_ago(3)} | CLAUDE.md:3, docs/a.md (commit abc1234) | nothing removed | owner\n")
        self.item("old-b", f"# Інше\n- status: fixed\n- fix: {days_ago(3)} | CLAUDE.md (6e087bd, e5902ba) | plugin commit | owner\n")
        self.item("old-c", f"# Без коміту\n- status: fixed\n- fix: {days_ago(3)} | plugins/x/SKILL.md:11 | merged | trivial\n")
        item = lambda key: fixes.Item(self.set_folder("repo") / "items" / f"{key}.md", "repo")  # noqa: E731
        self.assertEqual(item("old-a").status, "fixed")
        self.assertEqual(item("old-a").fixes()[0][2:], ("abc1234", ["CLAUDE.md:3", "docs/a.md"]))
        self.assertEqual(item("old-b").fixes()[0][2], "e5902ba")  # the last hash of the list
        self.assertIsNone(item("old-c").fixes()[0][2])
        self.assertEqual(item("old-c").fixes()[0][3], ["plugins/x/SKILL.md:11"])
        text, sessions = fixes.check(item("old-c"), None, self.projects)
        self.assertIn("date-only fix", text)
        self.assertEqual(sessions, [])
        self.write("proj/dddd4444-0.jsonl", [{"type": "user", "timestamp": retro.now_utc().isoformat(),
                                                "message": {"content": "z"}}])
        self.assertEqual(len(fixes.check(item("old-c"), None, self.projects)[1]), 1)  # sessions after its date
        code, _, err = self.code("revert", "--item", "old-c")
        self.assertEqual(code, 1)
        self.assertIn("nothing to revert", err)
        self.assertEqual(self.status("old-c"), "fixed")

    # protects: Rule
    def test_the_global_folder_is_edited_only_when_clean_and_only_its_own_files_are_committed_or_restored(self):
        folder = self.tmp / "global"
        folder.mkdir(parents=True, exist_ok=True)
        for args in (["init", "-q", "-b", "main"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
            subprocess.run(["git", "-C", str(folder), *args], check=True, capture_output=True)
        (folder / "docs").mkdir()
        for name in ("a.md", "b.md"):
            (folder / "docs" / name).write_text("v1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(folder), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(folder), "commit", "-q", "-m", "i"], check=True, capture_output=True)
        self.assertEqual(self.code("global", "check", "--file", "docs/a.md")[:2], (0, "clean\n"))
        (folder / "docs" / "b.md").write_text("the owner is editing\n", encoding="utf-8")  # another file: not our business
        self.assertEqual(self.code("global", "check", "--file", "docs/a.md")[0], 0)
        (folder / "docs" / "a.md").write_text("the owner is editing this too\n", encoding="utf-8")
        code, _, err = self.code("global", "check", "--file", "docs/a.md")
        self.assertEqual(code, 1)
        self.assertIn("docs/a.md", err)
        (folder / "docs" / "a.md").write_text("v1\n", encoding="utf-8")  # clean again; now the retro's own edit
        subprocess.run(["git", "-C", str(folder), "checkout", "--", "docs/a.md"], check=True, capture_output=True)
        (folder / "docs" / "a.md").write_text("v2 by the retro\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(folder), "add", "docs/b.md"], check=True, capture_output=True)  # staged by the owner
        code, out, _ = self.code("global", "commit", "--file", "docs/a.md", "--message", "retro-fix: global k")
        self.assertEqual(code, 0)
        files = subprocess.run(["git", "-C", str(folder), "show", "--name-only", "--format=", out.strip()],
                               capture_output=True, text=True).stdout.split()
        self.assertEqual(files, ["docs/a.md"], "the owner's staged b.md stays out of the fix commit")
        self.assertEqual((folder / "docs" / "b.md").read_text(encoding="utf-8"), "the owner is editing\n")
        (folder / "docs" / "a.md").write_text("v3 rejected\n", encoding="utf-8")
        self.assertEqual(self.code("global", "restore", "--file", "docs/a.md")[0], 0)
        self.assertEqual((folder / "docs" / "a.md").read_text(encoding="utf-8"), "v2 by the retro\n")
        self.assertEqual((folder / "docs" / "b.md").read_text(encoding="utf-8"), "the owner is editing\n")

    # protects: Rule
    def test_an_unknown_spend_stops_the_run_like_an_over_one(self):
        def run(stdout):
            return mock.patch.object(fixes.spend_client, "run", return_value=None if stdout is None else
                                     subprocess.CompletedProcess([], 0, stdout, ""))
        for stdout, code in (("~1.9% of the weekly limit, estimate", 0), ("~2.3% of the weekly limit, estimate", 1),
                             (None, 1)):
            with run(stdout):
                self.assertEqual(self.code("budget", "--session-id", "s1")[0], code, stdout)

    # protects: Rule
    def test_a_parked_item_shows_its_own_reason_in_the_done_list(self):
        self.item("owner-only", "# Питання власнику\n- status: waiting\n")
        self.run_cmd("mark", "--item", "owner-only", "--status", "parked", "--note", "owner-only questions of the facts keeper")
        entry = self.done_list()[-1]
        self.assertEqual(entry["action"], "parked")
        self.assertIn("owner-only questions of the facts keeper", entry["text"])
        self.assertNotIn("двох невдалих", entry["text"])


class ReplayTestCase(RetroFixture):
    """`replay`: the item's problem parts from its sightings, and good parts of the same skill with no sign."""

    def setUp(self):
        super().setUp()
        plugins_with_demo(self.tmp / "plugins")

    # protects: Flow
    def test_replay_writes_the_problem_part_and_good_parts_of_the_same_skill_without_a_sign(self):
        title = {"type": "custom-title", "customTitle": "S"}
        self.write("proj/abcdef12-0000.jsonl", [command("demo:lead"), owner("я ж казав не так"), said("Виправляю."), title])
        self.write("proj/11112222-0000.jsonl", [command("demo:lead"), owner("Збери."), said("Зібрав."), title])
        self.write("proj/33334444-0000.jsonl", [command("demo:lead"), owner("не так!"), said("Ок."), title])  # a sign
        self.write("proj/55556666-0000.jsonl", [command("demo:build"), owner("Збери."), said("Ок."), title])  # other skill
        item = self.set_folder("demo") / "items" / "lead-order.md"
        item.parent.mkdir(parents=True)
        item.write_text("# Порядок\n- status: waiting\n"
                        "- seen: 2026-11-20 | S (abcdef12) | part reader: skills/lead/SKILL.md:5 | x | skill demo:lead "
                        "lines 1-3\n", encoding="utf-8")
        out = self.run_cmd("replay", "--item", "lead-order")
        self.assertIn("problem parts 1, good parts 1", out)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("problem | ") and "(abcdef12) | skill demo:lead lines 1-" in lines[0], out)
        self.assertTrue(lines[1].startswith("good | ") and "(11112222)" in lines[1], out)
        packet = Path(lines[0].split(" | ")[1])
        self.assertEqual(packet.parent.name, "replay-lead-order")
        self.assertIn("я ж казав не так", packet.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
