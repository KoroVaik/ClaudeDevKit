import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PLUGINS = Path(__file__).resolve().parent.parent.parent / "plugins"
sys.path.insert(0, str(PLUGINS / "rules-kit" / "scripts"))
import subscriptions  # noqa: E402

VALID = """# Rules subscription: demo

Prose for readers.

| Setting | Value |
|---|---|
| set | demo |
| reviewed by | Owner |
| lands by | branch merged by P: Owner |
| special editor | facts.md: demo:keeper |

## Files

| Path (glob, relative to the set root) | Type | Part kinds | Section |
|---|---|---|---|
| skills/chat/SKILL.md | talk | skill demo:chat | Replies |
| skills/chat/SKILL.md | process | skill demo:chat | |
| agents/*.md | process | agent demo:helper, agent demo:other | |
| hooks/**/*.py | technical | hook demo | |
| docs/**/*.md | process | - | |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| owner corrects | talk | owner message matches «не так|я ж казав|\\?\\?\\?» |
| repeat | technical | the same call three times |

## May change itself

| Path | Changes |
|---|---|
| skills/** | word, sentence, new sign |
"""


def settings(set_name="demo"):
    return ("| Setting | Value |\n|---|---|\n" + (f"| set | {set_name} |\n" if set_name else "")
            + "| reviewed by | Owner |\n| lands by | merged |\n")


def with_files(*rows, header="| Path | Type | Part kinds |\n|---|---|---|\n", set_name="demo"):
    return settings(set_name) + "\n## Files\n\n" + header + "".join(row + "\n" for row in rows)


def parse(text, root="/sets/demo"):
    return subscriptions.parse(text, root)


class ParserTestCase(unittest.TestCase):
    # protects: Flow
    def test_a_valid_file_gives_the_settings_the_files_the_signs_and_the_permissions(self):
        sub = parse(VALID)
        self.assertEqual((sub.name, sub.reviewer, sub.lands_by), ("demo", "Owner", "branch merged by P: Owner"))
        self.assertEqual(sub.special_editor, "facts.md: demo:keeper")
        self.assertEqual([(rule.pattern, rule.type, rule.section) for rule in sub.files],
                         [("skills/chat/SKILL.md", "talk", "Replies"), ("skills/chat/SKILL.md", "process", None),
                          ("agents/*.md", "process", None), ("hooks/**/*.py", "technical", None),
                          ("docs/**/*.md", "process", None)])
        self.assertEqual(sub.files[2].kinds, (("agent", "demo:helper"), ("agent", "demo:other")))
        self.assertEqual([(sign.name, sign.kind) for sign in sub.signs], [("owner corrects", "talk"), ("repeat", "technical")])
        self.assertTrue(sub.signs[0].regex.search("ну я ж казав"))  # a `|` inside « » does not split the row
        self.assertIsNone(sub.signs[1].regex)
        self.assertEqual(sub.may_change_path("/sets/demo/skills/a/SKILL.md"), ["word, sentence, new sign"])
        self.assertEqual(sub.may_change_path("/sets/demo/hooks/x.py"), [])  # hooks and scripts: no row, no permission

    # protects: Rule
    def test_every_validation_error_names_the_problem(self):
        cases = {
            "unknown type '": with_files("| a.md | chatty | |"),
            "setting 'set' is missing (the set has no name)": with_files("| a.md | process | |", set_name=""),
            "set name 'a b'": with_files("| a.md | process | |", set_name="a b"),
            "set name 'a/b'": with_files("| a.md | process | |", set_name="a/b"),
            "setting 'reviewed by' is missing": "| Setting | Value |\n|---|---|\n| set | demo |\n| lands by | x |\n\n"
                                                "## Files\n\n| Path | Type | Part kinds |\n|---|---|---|\n| a.md | process | |\n",
            "setting 'lands by' is missing": "| Setting | Value |\n|---|---|\n| set | demo |\n| reviewed by | x |\n\n"
                                              "## Files\n\n| Path | Type | Part kinds |\n|---|---|---|\n| a.md | process | |\n",
            "unknown setting 'owner'": settings() + "| owner | me |\n\n## Files\n\n| Path | Type | Part kinds |\n|---|---|---|\n| a.md | process | |\n",
            "the Files table is missing": settings(),
            "has no row": with_files(),
            "bad path glob: '/etc/x.md': the path must be relative": with_files("| /etc/x.md | process | |"),
            "bad path glob: 'C:/x.md': the path must be relative": with_files("| C:/x.md | process | |"),
            "`..` leaves the set root": with_files("| ../x.md | process | |"),
            "`**` must be a whole path segment": with_files("| a**.md | process | |"),
            "`[` without `]`": with_files("| a[b.md | process | |"),
            "`]` without `[`": with_files("| ab].md | process | |"),
            "write the path with `/`": with_files("| skills\\a.md | process | |"),
            "empty path segment": with_files("| skills//a.md | process | |"),
            "is listed twice": with_files("| a.md | process | |", "| a.md | talk | |"),
            "part kind 'plugin x'": with_files("| a.md | process | plugin x |"),
            "a skill is named `<plugin>:<name>`": with_files("| a.md | process | skill nameonly |"),
            "a hook is named `<plugin>`": with_files("| a.md | process | hook a:b:c |"),
            "needs the columns Path, Type, Part kinds": with_files("| a.md | process |", header="| Path | Type |\n|---|---|\n"),
            "a Files row needs 4 cells": with_files("| a.md | process | |", header="| Path | Type | Part kinds | Section |\n|---|---|---|---|\n"),
            "a table needs a `|---|` separator": settings() + "\n## Files\n\n| Path | Type | Part kinds |\n| a.md | process | |\n",
            "the settings table needs the header": "| Name | Value |\n|---|---|\n| set | demo |\n",
            "a table under the heading 'Notes'": with_files("| a.md | process | |") + "\n## Notes\n\n| a | b |\n|---|---|\n| 1 | 2 |\n",
            "the Signs table needs the header": with_files("| a.md | process | |") + "\n## Signs\n\n| Name | Pattern |\n|---|---|\n| a | b |\n",
            "sign 'x': bad regular expression": with_files("| a.md | process | |")
                                               + "\n## Signs\n\n| Sign | Kind | Pattern |\n|---|---|---|\n| x | talk | «(» |\n",
            "unknown type 'loud'": with_files("| a.md | process | |")
                                   + "\n## Signs\n\n| Sign | Kind | Pattern |\n|---|---|---|\n| x | loud | y |\n",
            "sign 'x' is listed twice": with_files("| a.md | process | |")
                                        + "\n## Signs\n\n| Sign | Kind | Pattern |\n|---|---|---|\n| x | talk | y |\n| x | talk | z |\n",
            "a May change itself row needs": with_files("| a.md | process | |")
                                              + "\n## May change itself\n\n| Path | Changes |\n|---|---|\n| a.md | |\n",
            "bad path glob: '../x'": with_files("| a.md | process | |")
                                     + "\n## May change itself\n\n| Path | Changes |\n|---|---|\n| ../x | word |\n",
        }
        for expected, text in cases.items():
            with self.assertRaises(subscriptions.Problem, msg=expected) as caught:
                parse(text)
            self.assertIn(expected, str(caught.exception), expected)

    # protects: Rule
    def test_the_error_names_the_file_and_the_line_and_lists_every_error(self):
        text = with_files("| a.md | chatty | |", "| /b.md | process | |")
        with self.assertRaises(subscriptions.Problem) as caught:
            subscriptions.parse(text, "/sets/demo", source="/sets/demo/rules-subscription.md")
        message = str(caught.exception)
        self.assertIn("/sets/demo/rules-subscription.md: ", message)
        self.assertRegex(message, r"line \d+: unknown type 'chatty'")
        self.assertRegex(message, r"line \d+: bad path glob: '/b.md'")

    # protects: Rule
    def test_tables_in_code_fences_and_a_bom_and_backticks_are_handled(self):
        text = "\ufeff" + "```\n| Setting | Value |\n|---|---|\n| set | fake |\n```\n" + with_files("| `a.md` | `process` | `skill demo:a` |")
        sub = parse(text)
        self.assertEqual((sub.name, sub.files[0].pattern, sub.files[0].kinds), ("demo", "a.md", (("skill", "demo:a"),)))

    # protects: Rule
    def test_globs_keep_stars_inside_a_folder_and_double_stars_cross_folders(self):
        sub = parse(with_files("| skills/*/SKILL.md | process | |", "| .claude/**/*.md | process | |", "| tools/** | technical | |",
                               "| **/notes.md | process | |", "| data/[ab]?.json | technical | |"))
        listed = {path: bool(sub.lists("/sets/demo/" + path)) for path in (
            "skills/x/SKILL.md", "skills/x/y/SKILL.md", "skills/SKILL.md", ".claude/a.md", ".claude/x/y/a.md", ".claude/a.txt",
            "tools/a/b.py", "tools", "notes.md", "x/y/notes.md", "data/a1.json", "data/c1.json", "data/a12.json")}
        self.assertEqual([path for path, yes in listed.items() if yes],
                         ["skills/x/SKILL.md", ".claude/a.md", ".claude/x/y/a.md", "tools/a/b.py", "notes.md",
                          "x/y/notes.md", "data/a1.json"])

    # protects: Rule
    def test_a_section_row_types_its_heading_and_the_row_without_a_section_types_the_rest(self):
        sub = parse(VALID)
        path = "/sets/demo/skills/chat/SKILL.md"
        self.assertEqual((sub.type_of(path, "Replies"), sub.type_of(path, "Other part"), sub.type_of(path)), ("talk", "process", "process"))
        self.assertEqual(sub.sections(path), {"Replies": "talk"})
        self.assertIsNone(sub.type_of("/sets/demo/unlisted.md"))
        only_sections = parse(with_files("| a.md | talk | | Intro |", header="| Path | Type | Part kinds | Section |\n|---|---|---|---|\n"))
        self.assertEqual((only_sections.type_of("/sets/demo/a.md", "Intro"), only_sections.type_of("/sets/demo/a.md", "Else")),
                         ("talk", None))

    # protects: Rule
    def test_the_first_row_that_matches_wins(self):
        sub = parse(with_files("| docs/jargon.md | talk | |", "| docs/*.md | process | |"))
        self.assertEqual((sub.type_of("/sets/demo/docs/jargon.md"), sub.type_of("/sets/demo/docs/git.md")), ("talk", "process"))

    # protects: Rule
    def test_the_subscription_file_is_a_file_of_its_set_unless_a_row_already_matches_it(self):
        sub = subscriptions.parse(with_files("| a.md | talk | |"), "/sets/demo", source="/sets/demo/rules-subscription.md")
        self.assertEqual(sub.type_of("/sets/demo/rules-subscription.md"), "process")
        sub = subscriptions.parse(with_files("| rules-*.md | talk | |"), "/sets/demo", source="/sets/demo/rules-subscription.md")
        self.assertEqual(sub.type_of("/sets/demo/rules-subscription.md"), "talk")

    # protects: Rule
    def test_candidates_are_the_sets_that_name_the_part_kind_and_a_hook_matches_its_plugin(self):
        registry = subscriptions.Registry()
        registry.add(parse(VALID))
        registry.add(parse(with_files("| s.md | process | skill other:thing, hook other:guard |", set_name="other"), "/sets/other"))
        names = lambda kind, name: [sub.name for sub in registry.candidates(kind, name)]  # noqa: E731
        self.assertEqual(names("skill", "demo:chat"), ["demo"])
        self.assertEqual(names("agent", "demo:helper"), ["demo"])
        self.assertEqual(names("skill", "demo:helper"), [])  # a kind is not interchangeable with another
        self.assertEqual(names("hook", "demo:any-hook"), ["demo"])  # a row `hook demo` covers every hook of the plugin
        self.assertEqual(names("hook", "other:guard"), ["other"])
        self.assertEqual(names("hook", "other:else"), [])
        self.assertEqual(names("skill", "none:none"), [])


class OwnershipTestCase(unittest.TestCase):
    def registry(self):
        registry = subscriptions.Registry()
        registry.add(parse(with_files("| skills/**/*.md | process | |", "| notes.md | talk | |", set_name="plug"), "/repo/plugins/plug"))
        registry.add(parse(with_files("| CLAUDE.md | process | |", "| plugins/**/*.md | process | |", "| .claude/**/*.md | process | |",
                                      set_name="proj"), "/repo"))
        registry.add(parse(with_files("| CLAUDE.md | talk | |", set_name="global"), "/home/me/.claude"))
        return registry

    # protects: Rule
    def test_a_file_belongs_to_the_set_of_the_deepest_root_that_lists_it(self):
        registry = self.registry()
        owner = lambda path: (registry.owner(path).set.name if registry.owner(path) else None)  # noqa: E731
        self.assertEqual(owner("/repo/plugins/plug/skills/a/SKILL.md"), "plug")  # not the project, though its glob matches too
        self.assertEqual(owner("/repo/plugins/plug/notes.md"), "plug")
        self.assertEqual(owner("/repo/CLAUDE.md"), "proj")
        self.assertEqual(owner("/home/me/.claude/CLAUDE.md"), "global")
        self.assertIsNone(owner("/repo/plugins/plug/README.md"))  # the plugin does not list it: no set, not the project
        self.assertIsNone(owner("/repo/src/main.py"))
        self.assertIsNone(owner("/elsewhere/CLAUDE.md"))
        self.assertIsNone(owner("/repo/plugins/plug"))  # a root itself is no file

    # protects: Rule
    def test_a_path_in_a_worktree_is_the_same_path_in_its_project(self):
        registry = self.registry()
        for path in ("/repo/.claude/worktrees/c1/CLAUDE.md", "\\repo\\.claude\\worktrees\\c1\\CLAUDE.md"):
            self.assertEqual(registry.owner(path).set.name, "proj", path)
        self.assertEqual(registry.owner("/repo/.claude/worktrees/c1/plugins/plug/skills/a/SKILL.md").set.name, "plug")
        self.assertEqual(registry.owner("/repo/.claude/dev.md").set.name, "proj")  # a project's own .claude file
        inside = subscriptions.Registry()
        inside.add(parse(with_files("| x.md | process | |", set_name="wt"), "/repo/.claude/worktrees/c1/plugins/wt"))
        self.assertEqual(inside.owner("/repo/plugins/wt/x.md").set.name, "wt")  # a set found through a worktree

    # protects: Rule
    def test_the_type_of_a_file_comes_from_its_owner_and_its_section(self):
        registry = subscriptions.Registry()
        registry.add(parse(VALID, "/sets/demo"))
        self.assertEqual(registry.type_of("/sets/demo/skills/chat/SKILL.md", "Replies"), "talk")
        self.assertEqual(registry.type_of("/sets/demo/hooks/a/b.py"), "technical")
        self.assertIsNone(registry.type_of("/sets/demo/nothing.md"))

    # protects: Rule
    def test_a_set_is_reviewed_by_the_project_it_names_ignoring_case(self):
        registry = self.registry()
        self.assertEqual([sub.name for sub in registry.reviewed_by("OWNER")], ["plug", "proj", "global"])  # all name "Owner"
        self.assertEqual(registry.reviewed_by("Somebody else"), [])
        self.assertEqual(registry.reviewed_by(" owner ")[0].name, "plug")

    # protects: Rule
    def test_the_default_project_set_lists_claude_md_and_the_claude_folder_as_process(self):
        sub = subscriptions.default_project("/work/My App")
        self.assertEqual((sub.name, sub.reviewer, sub.lands_by), ("My-App", "My App", "the project's lead merge"))
        for path in ("CLAUDE.md", ".claude/dev-kit.md", ".claude/agents/a/b.md"):
            self.assertEqual(sub.type_of("/work/My App/" + path), "process", path)
        self.assertIsNone(sub.type_of("/work/My App/src/a.md"))
        self.assertIsNone(sub.type_of("/work/My App/.claude/settings.json"))


class DiscoveryTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, rel, text):
        path = self.tmp / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def subscription(self, name, reviewer="Owner"):
        return (f"# Rules subscription: {name}\n\n| Setting | Value |\n|---|---|\n| set | {name} |\n| reviewed by | {reviewer} |\n"
                "| lands by | merged |\n\n## Files\n\n| Path | Type | Part kinds |\n|---|---|---|\n| a.md | process | |\n")

    # protects: Flow
    def test_sets_come_from_plugin_folders_the_global_folder_and_projects_with_or_without_a_file(self):
        self.write("plugins/alpha/rules-subscription.md", self.subscription("alpha"))
        self.write("plugins/beta/rules-subscription.md", self.subscription("beta"))
        (self.tmp / "plugins" / "gamma").mkdir()  # no file: not a set
        self.write("global/rules-subscription.md", self.subscription("global"))
        self.write("proj-a/.claude/rules-subscription.md", self.subscription("proj-a-set", reviewer="proj-a"))
        (self.tmp / "proj-b" / ".claude").mkdir(parents=True)  # no file: the default project set
        registry = subscriptions.discover(self.tmp / "plugins", self.tmp / "global", [self.tmp / "proj-a", self.tmp / "proj-b"])
        self.assertEqual(list(registry.sets), ["alpha", "beta", "global", "proj-a-set", "proj-b"])
        self.assertEqual(registry.errors, [])
        self.assertEqual(registry.sets["proj-a-set"].root, self.tmp / "proj-a")  # a project's root is its repository
        self.assertEqual(registry.sets["alpha"].root, self.tmp / "plugins" / "alpha")
        self.assertEqual(registry.set_at(self.tmp / "proj-b").name, "proj-b")
        self.assertEqual(registry.owner(self.tmp / "proj-a" / "a.md").set.name, "proj-a-set")
        self.assertEqual(registry.owner(self.tmp / "proj-b" / "CLAUDE.md").set.name, "proj-b")

    # protects: Edge
    def test_a_file_that_does_not_parse_is_skipped_and_reported_and_a_duplicate_name_keeps_the_first(self):
        self.write("plugins/alpha/rules-subscription.md", self.subscription("alpha"))
        self.write("plugins/bad/rules-subscription.md", "# nothing here\n")
        self.write("plugins/copy/rules-subscription.md", self.subscription("alpha"))
        registry = subscriptions.discover(self.tmp / "plugins", self.tmp / "no-global", [])
        self.assertEqual(list(registry.sets), ["alpha"])
        self.assertEqual(registry.sets["alpha"].root, self.tmp / "plugins" / "alpha")
        self.assertEqual(len(registry.errors), 2)
        self.assertTrue(any("bad" in message and "Files table is missing" in message for message in registry.errors))
        self.assertTrue(any("set 'alpha' is already defined" in message for message in registry.errors))

    # protects: Edge
    def test_a_missing_plugins_folder_gives_no_plugin_sets(self):
        self.assertEqual(subscriptions.discover(self.tmp / "none", self.tmp / "none", []).sets, {})

    # protects: Bug
    def test_no_sign_of_the_plugins_fires_on_a_bare_session_title(self):
        # Step 4 left «P: » and «Ретро: » in prose rows; read as expressions they marked unrelated packets.
        registry = subscriptions.discover(PLUGINS, self.tmp / "none", [])
        for found in registry.sets.values():
            for sign in found.signs:
                if sign.regex is not None:
                    for text in ("P: ClaudeDevKit", "Ретро: Zhratva", "C: build the page"):
                        self.assertIsNone(sign.regex.search(text), (found.name, sign.name, text))

    # protects: Flow
    def test_environment_variables_replace_the_plugins_and_global_folders(self):
        with mock.patch.dict(os.environ, {subscriptions.PLUGINS_ENV: str(self.tmp / "p"), subscriptions.GLOBAL_ENV: str(self.tmp / "g")}):
            self.assertEqual((subscriptions.plugins_dir(), subscriptions.global_dir()), (self.tmp / "p", self.tmp / "g"))
        with mock.patch.dict(os.environ):
            os.environ.pop(subscriptions.PLUGINS_ENV, None)
            os.environ.pop(subscriptions.GLOBAL_ENV, None)
            self.assertEqual(subscriptions.plugins_dir(), PLUGINS)
            self.assertEqual(subscriptions.global_dir(), Path.home() / ".claude")


class GlobalFileTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(os.path.realpath(tempfile.mkdtemp()))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.git_env = mock.patch.dict(os.environ, {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                                                    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})
        self.git_env.start()
        self.addCleanup(self.git_env.stop)

    def git(self, folder, *args):
        return subprocess.run(["git", "-C", str(folder), *args], capture_output=True, text=True, check=True).stdout

    # protects: Flow
    def test_the_global_file_is_written_from_the_template_and_committed_in_a_git_folder(self):
        folder = self.tmp / "global"
        folder.mkdir()
        self.git(folder, "init", "-q", "-b", "main")
        self.git(folder, "commit", "-q", "--allow-empty", "-m", "start")
        self.assertTrue(subscriptions.ensure_global(folder))
        text = (folder / subscriptions.FILE_NAME).read_text(encoding="utf-8")
        self.assertEqual(text, subscriptions.TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual(self.git(folder, "status", "--porcelain").strip(), "")  # committed
        self.assertIn("Rules subscription: the owner's global set", self.git(folder, "log", "-1", "--format=%s"))
        self.assertFalse(subscriptions.ensure_global(folder))  # not again: an edited file stays
        (folder / subscriptions.FILE_NAME).write_text(text + "\nedited\n", encoding="utf-8")
        subscriptions.ensure_global(folder)
        self.assertTrue((folder / subscriptions.FILE_NAME).read_text(encoding="utf-8").endswith("edited\n"))

    # protects: Edge
    def test_a_global_folder_that_is_not_a_repository_top_gets_the_file_and_no_commit(self):
        outer = self.tmp / "outer"
        inner = outer / "global"
        inner.mkdir(parents=True)
        self.git(outer, "init", "-q", "-b", "main")
        self.git(outer, "commit", "-q", "--allow-empty", "-m", "start")
        self.assertTrue(subscriptions.ensure_global(inner))  # the folder lies inside another repository: not its own
        self.assertEqual(self.git(outer, "log", "--oneline").count("\n"), 1)
        folder = self.tmp / "plain"  # no git at all, and the folder does not exist yet
        self.assertTrue(subscriptions.ensure_global(folder))
        self.assertTrue((folder / subscriptions.FILE_NAME).is_file())

    # protects: Rule
    def test_the_template_is_a_valid_global_set(self):
        sub = subscriptions.parse(subscriptions.TEMPLATE.read_text(encoding="utf-8"), "/home/me/.claude")
        self.assertEqual((sub.name, sub.reviewer), ("global", "ClaudeDevKit"))
        claude = "/home/me/.claude/CLAUDE.md"
        self.assertEqual((sub.type_of(claude, "Chat replies"), sub.type_of(claude, "Reply language"), sub.type_of(claude, "Git")),
                         ("talk", "talk", "process"))
        self.assertEqual((sub.type_of("/home/me/.claude/docs/jargon.md"), sub.type_of("/home/me/.claude/docs/git.md")),
                         ("talk", "process"))


class RealFilesTestCase(unittest.TestCase):
    # protects: Rule
    def test_every_plugin_has_a_subscription_that_parses_and_is_reviewed_by_claudedevkit(self):
        folders = sorted(path for path in PLUGINS.iterdir() if path.is_dir())
        self.assertGreaterEqual(len(folders), 6)
        for folder in folders:
            sub = subscriptions.load(folder / subscriptions.FILE_NAME, folder)
            self.assertEqual((sub.name, sub.reviewer), (folder.name, "ClaudeDevKit"), folder.name)
            self.assertIn(f"plugins/{folder.name}", sub.lands_by, folder.name)
            self.assertTrue(sub.files, folder.name)

    # protects: Rule
    def test_the_real_plugins_are_found_together_and_own_their_files(self):
        registry = subscriptions.discover(PLUGINS, PLUGINS / "none", [])
        self.assertEqual(registry.errors, [])
        self.assertEqual(sorted(registry.sets), ["dev-kit", "pult", "rules-kit", "spend-kit", "unity-kit", "web-kit"])
        skill = registry.owner(PLUGINS / "dev-kit" / "skills" / "manager" / "SKILL.md")
        self.assertEqual((skill.set.name, skill.set.type_of(PLUGINS / "dev-kit" / "skills" / "manager" / "SKILL.md")), ("dev-kit", "process"))
        self.assertEqual(registry.type_of(PLUGINS / "dev-kit" / "skills" / "manager" / "SKILL.md", "Stating the cost of work"), "talk")
        self.assertEqual(registry.type_of(PLUGINS / "dev-kit" / "hooks" / "windows-traps.py"), "technical")
        self.assertEqual(registry.type_of(PLUGINS / "rules-kit" / "rules-subscription.md"), "process")
        self.assertEqual([sub.name for sub in registry.candidates("skill", "web-kit:e2e-check")], ["web-kit"])
        self.assertEqual([sub.name for sub in registry.candidates("hook", "pult:hub-rules")], ["pult"])
        self.assertEqual([sub.name for sub in registry.candidates("agent", "dev-kit:question-reader")], ["dev-kit"])
        self.assertEqual(registry.type_of(PLUGINS / "dev-kit" / "agents" / "question-reader.md"), "talk")

    # protects: Rule
    def test_the_retro_gates_are_not_among_the_files_the_retro_may_change_itself(self):
        folder = PLUGINS / "rules-kit"
        sub = subscriptions.load(folder / subscriptions.FILE_NAME, folder)
        for gate in ("agents/approver.md", "agents/replayer.md", "skills/retro/SKILL.md"):
            self.assertEqual(sub.may_change_path(folder / gate), [], gate)  # a fix there goes to P as a task
        for free in ("agents/rule-reviewer.md", "agents/part-reader.md", "skills/edit-rules/SKILL.md"):
            self.assertTrue(sub.may_change_path(folder / free), free)


if __name__ == "__main__":
    unittest.main()
