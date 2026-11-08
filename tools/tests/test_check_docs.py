import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "plugins" / "dev-kit" / "scripts"
SHIM = REPO / "plugins" / "dev-kit" / "bin" / "dev-kit-check-docs"
sys.path.insert(0, str(SCRIPTS))
import check_docs  # noqa: E402

HAS_GIT = shutil.which("git") is not None

PROFILE = """## documentation

| Setting | Value |
|---|---|
| scan | `src: .py` |
| code-root | `src 2` |
| area-alias | `pkg. -> src/pkg.` |
"""

FEATURE = """# Feature F

Epic: [E](../epics/e.md)

## Purpose

p

## Rules

r

## Acceptance criteria

a

## Built in

- `src/app.py`
"""

BASE = {
    "docs/product.md": "# Product\n\n## Epics\n\n- [E](epics/e.md)\n",
    "docs/epics/e.md": "# E\n\nPart of the [product](../product.md).\n\n## Features\n\n- [F](../features/f.md)\n",
    "docs/features/f.md": FEATURE,
    "docs/tech/map.md": "# Map\n\n- `src/` the code ([T](t.md)).\n",
    "docs/tech/t.md": "# T\n\nTech file for `src/app.py`.\n",
    "docs/standards/s.md": "# S\n\nStandard.\n",
    "docs/README.md": "# Index\n\n- [product](product.md)\n",
    "src/app.py": "x = 1\n",
    "src/sub/x.py": "y = 1\n",
    ".claude/dev-kit.md": PROFILE,
}


def feature(name="F", epic="[E](../epics/e.md)", sections=("Purpose", "Rules", "Acceptance criteria", "Built in"), built="- `src/app.py`", extra=""):
    lines = [f"# Feature {name}", ""]
    if epic is not None:
        lines += [f"Epic: {epic}", ""]
    for section in sections:
        lines += [f"## {section}", ""]
        lines += [built if section == "Built in" else "text", ""]
    return "\n".join(lines) + extra


class DocsTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "proj"
        for rel, text in BASE.items():
            self.write(rel, text)

    def write(self, rel, text, newline="\n", encoding="utf-8"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.replace("\n", newline).encode(encoding))

    def append(self, rel, text):
        with open(self.root / rel, "ab") as handle:
            handle.write(text.encode("utf-8"))

    def run_main(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stderr(err):
            code = check_docs.main(["--root", str(self.root), *args], out=out)
        return code, out.getvalue().splitlines(), err.getvalue()

    def check(self, *args):
        code, lines, _ = self.run_main(*args)
        return code, lines

    def errors(self, rule=None):
        """Error lines of the full check, optionally of one rule."""
        _, lines = self.check()
        found = [line for line in lines if ": error [" in line]
        return [line for line in found if f"[{rule}]" in line] if rule else found

    def assertHasError(self, rule, text, file=None):
        found = self.errors(rule)
        match = [line for line in found if text in line and (file is None or line.startswith(file + ":"))]
        self.assertTrue(match, f"no [{rule}] error with '{text}' in {found}")

    def assertNoErrors(self):
        self.assertEqual([], self.errors())

    def git(self, *args):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=self.root, check=True, capture_output=True,
        )

    def init_git(self):
        self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")


class CleanTests(DocsTestCase):
    def test_clean_fixture_has_no_errors_and_exits_zero(self):
        code, lines = self.check()
        self.assertEqual(0, code)
        self.assertEqual(["docs check: 0 errors, 0 warnings"], lines)

    def test_exit_code_is_one_when_there_is_an_error(self):
        self.append("docs/README.md", "[x](nope.md)\n")
        code, lines = self.check()
        self.assertEqual(1, code)
        self.assertEqual("docs check: 1 errors (link=1), 0 warnings", lines[-1])

    def test_summary_lists_rules_in_alphabetical_order_with_counts(self):
        self.append("docs/README.md", "[x](nope.md) [y](nope2.md) docs/ghost.md\n")
        _, lines = self.check()
        self.assertEqual("docs check: 3 errors (docs-path=1, link=2), 0 warnings", lines[-1])

    def test_missing_docs_folder_is_not_a_crash(self):
        shutil.rmtree(self.root / "docs")
        code, lines = self.check()
        self.assertEqual((0, ["docs check: 0 errors, 0 warnings"]), (code, lines))


class LinkTests(DocsTestCase):
    def test_missing_link_target(self):
        self.append("docs/README.md", "[x](nope.md)\n")
        self.assertHasError("link", "link target does not exist: nope.md", "docs/README.md")

    def test_error_line_number(self):
        self.append("docs/README.md", "\n\n[x](nope.md)\n")
        self.assertIn("docs/README.md:6: error [link] link target does not exist: nope.md", self.errors())

    def test_existing_targets_pass(self):
        self.append("docs/README.md", "[a](product.md) [b](features/) [c](/docs/product.md) [d](product.md#product)\n")
        self.assertNoErrors()

    def test_angle_brackets_title_and_reference_style(self):
        self.append("docs/README.md", '[a](<no such.md>) [b](nope.md "title")\n\n[ref]: nope2.md\n')
        found = self.errors("link")
        self.assertEqual(3, len(found), found)

    def test_external_and_scheme_links_are_ignored(self):
        self.append("docs/README.md", "[a](https://x.y/z) [b](mailto:a@b.c) [c](//host/x) [d](C:/nope) [e](#)\n")
        self.assertNoErrors()

    def test_query_is_cut_and_percent_escapes_are_decoded(self):
        self.write("docs/with space.md", "# W\n")
        self.append("docs/README.md", "[a](product.md?x=1) [b](with%20space.md) [c](gone%20x.md)\n")
        found = self.errors("link")
        self.assertEqual(1, len(found), found)
        self.assertIn("gone%20x.md", found[0])

    def test_inline_code_and_fenced_code_are_ignored(self):
        self.append("docs/README.md", "`[a](nope.md)`\n\n```\n[b](nope.md)\n```\n\n~~~\n[c](nope.md)\n~~~\n")
        self.assertNoErrors()

    def test_longer_fence_closes_only_with_a_fence_at_least_as_long(self):
        self.append("docs/README.md", "````\n```\n[a](nope.md)\n```\n[b](nope2.md)\n````\n[c](nope3.md)\n")
        found = self.errors("link")
        self.assertEqual(1, len(found), found)
        self.assertIn("nope3.md", found[0])

    def test_nested_brackets_and_images(self):
        self.append("docs/README.md", "[a [b] c](nope.md) [![i](x.png)](nope2.md) ![p](nope3.png)\n")
        self.assertEqual(3, len(self.errors("link")))

    def test_links_are_checked_in_root_md_and_claude_and_scan_folders(self):
        self.write("ROOT.md", "[a](nope.md)\n")
        self.write(".claude/x.md", "[b](nope.md)\n")
        self.write("src/doc.md", "[c](nope.md)\n")
        self.write("other/doc.md", "[d](nope.md)\n")
        files = sorted(line.split(":")[0] for line in self.errors("link"))
        self.assertEqual(["ROOT.md"], files)

    def test_scan_setting_adds_a_folder_and_extensions(self):
        self.write(".claude/dev-kit.md", PROFILE + "| scan | `.claude: .md` |\n| scan | `src: .py .md` |\n")
        self.write("ROOT.md", "[a](nope.md)\n")
        self.write(".claude/x.md", "[b](nope.md)\n")
        self.write("src/doc.md", "[c](nope.md)\n")
        files = sorted(line.split(":")[0] for line in self.errors("link"))
        self.assertEqual([".claude/x.md", "ROOT.md", "src/doc.md"], files)

    def test_skip_dirs_and_skills_lock(self):
        self.write(".claude/dev-kit.md", PROFILE + "| scan | `.claude: .md` |\n")
        self.write("docs/node_modules/a.md", "[a](nope.md)\n")
        self.write("docs/bin/a.md", "[a](nope.md)\n")
        self.write("docs/data/a.md", "[a](nope.md)\n")
        self.write(".claude/skills/third/SKILL.md", "[a](nope.md)\n")
        self.write(".claude/skills/own/SKILL.md", "[a](nope.md)\n")
        self.write("skills-lock.json", '{"skills": {"third": {}}}')
        files = sorted(line.split(":")[0] for line in self.errors("link"))
        self.assertEqual([".claude/skills/own/SKILL.md", "docs/data/a.md"], files)
        self.write(".claude/dev-kit.md", PROFILE + "| scan | `.claude: .md` |\n| skip-dirs | `data` |\n| skills-lock | `none` |\n")
        files = sorted(line.split(":")[0] for line in self.errors("link"))
        self.assertEqual([".claude/skills/own/SKILL.md", ".claude/skills/third/SKILL.md"], files)


class AnchorTests(DocsTestCase):
    def setUp(self):
        super().setUp()
        self.write("docs/target.md", "# Target\n\n## Тест Заголовок\n\n## Same\n\n## Same\n\n## Closed ##\n\n"
                   "## A `code` and *emph* and <b>html</b> [link](x.md)\n\n## What's (new)? - yes\n\n```\n## Fenced\n```\n")

    def anchor_errors(self, links):
        self.append("docs/README.md", links + "\n")
        return self.errors("anchor")

    def test_missing_anchor(self):
        found = self.anchor_errors("[a](target.md#nothing)")
        self.assertEqual(["docs/README.md:4: error [anchor] anchor #nothing not found in docs/target.md"], found)

    def test_unicode_slug_plain_upper_case_and_encoded(self):
        found = self.anchor_errors(
            "[a](target.md#тест-заголовок) [b](target.md#ТЕСТ-ЗАГОЛОВОК) "
            "[c](target.md#%D1%82%D0%B5%D1%81%D1%82-%D0%B7%D0%B0%D0%B3%D0%BE%D0%BB%D0%BE%D0%B2%D0%BE%D0%BA)"
        )
        self.assertEqual([], found)

    def test_duplicate_headings_get_numbered_slugs(self):
        found = self.anchor_errors("[a](target.md#same) [b](target.md#same-1) [c](target.md#same-2)")
        self.assertEqual(1, len(found))
        self.assertIn("#same-2", found[0])

    def test_closing_hashes_markup_and_punctuation_are_dropped(self):
        found = self.anchor_errors(
            "[a](target.md#closed) [b](target.md#a-code-and-emph-and-html-link) [c](target.md#whats-new---yes)"
        )
        self.assertEqual([], found)

    def test_heading_in_fenced_code_is_not_an_anchor(self):
        self.assertEqual(1, len(self.anchor_errors("[a](target.md#fenced)")))

    def test_self_anchor(self):
        found = self.anchor_errors("[a](#index) [b](#nothing)")
        self.assertEqual(1, len(found))
        self.assertIn("#nothing", found[0])

    def test_anchor_into_a_non_markdown_file_is_not_checked(self):
        self.assertEqual([], self.anchor_errors("[a](../src/app.py#L1)"))

    def test_missing_file_wins_over_anchor(self):
        before = len(self.errors("link"))
        self.append("docs/README.md", "[a](gone.md#x)\n")
        self.assertEqual(before + 1, len(self.errors("link")))
        self.assertEqual(0, len(self.errors("anchor")))

    def test_slug_function(self):
        self.assertEqual("пам'ять".replace("'", ""), check_docs.slug_of("Пам'ять"))
        self.assertEqual("under_score-dash", check_docs.slug_of("under_score dash"))
        self.assertEqual("-emoji-heading", check_docs.slug_of("😀 Emoji heading"))


class DocsPathTests(DocsTestCase):
    def mention(self, text, rel="docs/README.md"):
        self.append(rel, text + "\n")
        return self.errors("docs-path")

    def test_missing_docs_path(self):
        found = self.mention("See docs/features/ghost.md for details.")
        self.assertEqual(["docs/README.md:4: error [docs-path] path does not exist: docs/features/ghost.md"], found)

    def test_existing_paths_globs_and_folders_pass(self):
        self.assertEqual([], self.mention("docs/features/f.md docs/standards/ docs/**/*.md docs/tech/map.md#map"))

    def test_glob_that_matches_nothing(self):
        found = self.mention("docs/nothing-*.md")
        self.assertIn("pattern matches nothing: docs/nothing-*.md", found[0])

    def test_anchor_in_path_mention(self):
        found = self.mention("docs/features/f.md#bad-anchor")
        self.assertIn("anchor #bad-anchor not found in docs/features/f.md", found[0])

    def test_trailing_punctuation_is_cut(self):
        found = self.mention("(docs/features/ghost.md), docs/features/ghost2.md.")
        self.assertEqual(2, len(found))
        self.assertTrue(any(line.endswith("docs/features/ghost.md") for line in found), found)
        self.assertTrue(any(line.endswith("docs/features/ghost2.md") for line in found), found)

    def test_date_placeholder_cuts_the_path(self):
        found = self.mention("docs/findings/YYYY-MM-DD.md")
        self.assertIn("path does not exist: docs/findings", found[0])

    def test_link_target_is_not_read_again_as_a_mention(self):
        self.append("docs/README.md", "[docs/features/ghost.md](product.md)\n[x](docs/ghost.md)\n")
        self.assertEqual(1, len(self.errors("link")))
        self.assertEqual(1, len(self.errors("docs-path")))

    def test_not_a_mention_when_part_of_a_longer_path_or_url(self):
        self.assertEqual([], self.mention("https://example.com/docs/ghost.md and mydocs/ghost.md and ./docs-ghost/x"))

    def test_code_files_are_scanned_and_are_not_fence_masked(self):
        self.write("src/note.py", "# docs/tech/ghost.md\n```\ndocs/tech/ghost2.md\n```\n")
        found = self.errors("docs-path")
        self.assertEqual(["src/note.py:1", "src/note.py:3"], sorted(line.split(": ")[0] for line in found))

    def test_fenced_code_and_inline_code_in_markdown(self):
        self.append("docs/README.md", "```\ndocs/ghost.md\n```\n")
        self.assertEqual(0, len(self.errors("docs-path")))
        self.append("docs/README.md", "`docs/ghost.md`\n")
        self.assertEqual(1, len(self.errors("docs-path")))

    def test_changelog_and_marker_files_skip_the_mention_rule_only(self):
        self.write("CHANGELOG.md", "docs/ghost.md [x](nope.md)\n")
        self.write("plans/p.md", "<!-- docs-check: no-path-mentions -->\ndocs/ghost.md [x](nope.md)\n")
        self.assertEqual(0, len(self.errors("docs-path")))
        self.assertEqual(1, len(self.errors("link")))

    def test_marker_does_not_apply_to_code_files(self):
        self.write("src/n.py", "# <!-- docs-check: no-path-mentions -->\n# docs/ghost.md\n")
        self.assertEqual(1, len(self.errors("docs-path")))

    def test_same_path_twice_in_one_line_counts_once(self):
        self.assertEqual(1, len(self.mention("docs/ghost.md and docs/ghost.md")))


class StructureTests(DocsTestCase):
    def test_epic_not_listed_in_product(self):
        self.write("docs/epics/orphan.md", "# Orphan\n")
        self.assertHasError("epic-listed", "epic is not linked from docs/product.md", "docs/epics/orphan.md")

    def test_feature_not_linked_from_any_epic(self):
        self.write("docs/features/g.md", feature("G"))
        self.assertHasError("feature-epic-link", "feature is not linked from any epic", "docs/features/g.md")

    def test_feature_linked_from_two_epics(self):
        self.write("docs/epics/e2.md", "# E2\n\n- [F](../features/f.md)\n")
        self.append("docs/product.md", "- [E2](epics/e2.md)\n")
        self.assertHasError(
            "feature-epic-link", "feature is linked from 2 epics, expected one: docs/epics/e.md, docs/epics/e2.md",
            "docs/features/f.md",
        )

    def test_feature_linked_twice_from_one_epic_is_fine(self):
        self.append("docs/epics/e.md", "- [F again](../features/f.md#purpose)\n")
        self.assertNoErrors()

    def test_missing_epic_line(self):
        self.write("docs/features/f.md", feature(epic=None))
        self.assertHasError("feature-epic-line", 'missing the "Epic:" line', "docs/features/f.md")

    def test_epic_line_without_link(self):
        self.write("docs/features/f.md", feature(epic="no link here"))
        self.assertHasError("feature-epic-line", 'the "Epic:" line has no link to an epic')

    def test_epic_line_pointing_outside_epics_folder(self):
        self.write("docs/features/f.md", feature(epic="[P](../product.md)"))
        self.assertHasError("feature-epic-line", 'the "Epic:" link does not point to a file in docs/epics')

    def test_epic_line_pointing_to_a_missing_epic(self):
        self.write("docs/features/f.md", feature(epic="[M](../epics/missing.md)"))
        self.assertHasError("feature-epic-line", "the \"Epic:\" link points to a missing epic: docs/epics/missing.md")

    def test_epic_line_inside_fenced_code_does_not_count(self):
        self.write("docs/features/f.md", feature(epic=None, extra="\n```\nEpic: [E](../epics/e.md)\n```\n"))
        self.assertHasError("feature-epic-line", 'missing the "Epic:" line')

    def test_missing_sections(self):
        self.write("docs/features/f.md", feature(sections=("Purpose",)))
        found = self.errors("feature-sections")
        self.assertEqual(
            ['docs/features/f.md:1: error [feature-sections] missing the section "## Rules"',
             'docs/features/f.md:1: error [feature-sections] missing the section "## Acceptance criteria"',
             'docs/features/f.md:1: error [feature-sections] missing the section "## Built in"'],
            sorted(found, key=lambda x: ("Rules" not in x, "Acceptance" not in x)),
        )

    def test_section_names_are_case_sensitive_h2_only_and_allow_closing_hashes(self):
        text = feature(sections=()).rstrip("\n") + (
            "\n\n## purpose\n\n### Rules\n\n## Acceptance criteria ##\n\n## Built in\n\n- `src/app.py`\n"
        )
        self.write("docs/features/f.md", text)
        found = sorted(line.split("missing the section ")[1] for line in self.errors("feature-sections"))
        self.assertEqual(['"## Purpose"', '"## Rules"'], found)

    def test_title_falls_back_to_file_name(self):
        self.write("docs/features/f.md", feature().replace("# Feature F", "No title"))
        _, lines = self.check("--who", "src/app.py")
        self.assertIn("docs/features/f.md  (f)  via src/app.py", lines)


class BuiltInAndMapTests(DocsTestCase):
    def built(self, *tokens):
        self.write("docs/features/f.md", feature(built="\n".join(f"- `{t}`" for t in tokens)))
        return self.errors("built-in")

    def test_missing_path(self):
        found = self.built("src/ghost.py")
        self.assertEqual(["docs/features/f.md:19: error [built-in] Built in: path does not exist: src/ghost.py"], found)

    def test_existing_file_folder_and_dot_slash(self):
        self.assertEqual([], self.built("src/app.py", "src/sub/", "./src/sub"))

    def test_glob_matching_and_not_matching(self):
        self.assertEqual([], self.built("src/*.py", "src/**/x.py", "**/x.py", "src/s?b/x.py", "src/**"))
        found = self.built("src/*.rs", "src/**/nothing.py", "**/Nope9.py", "src/*/app.py")
        self.assertEqual(4, len(found), found)
        self.assertIn("pattern matches nothing: src/*.rs", found[0])

    def test_single_star_does_not_cross_folders(self):
        self.assertEqual(1, len(self.built("src/*.py?")))
        self.assertEqual(1, len(self.built("src/*/*/x.py")))
        self.assertEqual([], self.built("src/*/x.py"))

    def test_anchor_in_path(self):
        self.write("src/doc.md", "# Doc\n")
        found = self.built("src/doc.md#nothing", "src/doc.md#doc", "src/app.py#x")
        self.assertEqual(1, len(found))
        self.assertIn("Built in: anchor #nothing not found in src/doc.md", found[0])

    def test_docs_path_in_built_in_is_reported_once_by_the_scan(self):
        self.built("docs/tech/map.md#nothing", "docs/tech/ghost.md")
        found = self.errors()
        self.assertEqual(2, len(found), found)
        self.assertTrue(all("[docs-path]" in line for line in found))

    def test_tokens_without_slash_with_space_or_url_are_not_paths(self):
        self.assertEqual([], self.built("ghost.py", "a b/c", "http://x/y"))

    def test_token_in_fenced_code_is_ignored(self):
        text = feature(built="- `src/app.py`\n```\n- `src/ghost.py`\n```")
        self.write("docs/features/f.md", text)
        self.assertEqual([], self.errors("built-in"))

    def test_section_ends_at_next_h1_or_h2_only(self):
        text = feature(built="- `src/app.py`\n\n### Sub\n\n- `src/ghost.py`\n\n## After\n\n- `src/ghost2.py`")
        self.write("docs/features/f.md", text)
        found = self.errors("built-in")
        self.assertEqual(1, len(found), found)
        self.assertIn("src/ghost.py", found[0])

    def test_same_missing_token_twice_on_a_line_is_one_error(self):
        self.write("docs/features/f.md", feature(built="- `src/ghost.py` and `src/ghost.py.`"))
        self.assertEqual(1, len(self.errors("built-in")))

    def test_map_checks_every_backticked_path(self):
        self.append("docs/tech/map.md", "- `src/ghost/` and `src/*.rs` and `src/app.py`\n")
        found = self.errors("map")
        self.assertEqual(2, len(found), found)
        self.assertTrue(any("map: path does not exist: src/ghost" in line for line in found))
        self.assertTrue(any("map: pattern matches nothing: src/*.rs" in line for line in found))

    def test_map_ignores_fenced_code(self):
        self.append("docs/tech/map.md", "```\n`src/ghost/`\n```\n")
        self.assertEqual([], self.errors("map"))


class SizeTests(DocsTestCase):
    def long_feature(self, lines, marker=""):
        return feature(extra="\n" + "\n".join(f"- row {i}" for i in range(lines)) + "\n" + marker)

    def warnings(self):
        _, lines = self.check()
        return [line for line in lines if ": warning [" in line]

    def test_feature_over_limit_warns_and_exit_stays_zero(self):
        self.write("docs/features/f.md", self.long_feature(210))
        found = self.warnings()
        self.assertEqual(1, len(found))
        self.assertTrue(found[0].startswith("docs/features/f.md:1: warning [size] "))
        self.assertIn("(limit 200)", found[0])
        self.assertEqual(0, self.check()[0])

    def test_size_ok_marker_with_reason_silences_it(self):
        self.write("docs/features/f.md", self.long_feature(210, "<!-- size-ok: one feature -->\n"))
        self.assertEqual([], self.warnings())

    def test_size_ok_without_reason_does_not(self):
        self.write("docs/features/f.md", self.long_feature(210, "<!-- size-ok: -->\n"))
        self.assertEqual(1, len(self.warnings()))

    def test_tech_file_is_checked_too_but_standards_are_not(self):
        self.write("docs/tech/t.md", "# T\n\n" + "- x\n" * 210)
        self.write("docs/standards/s.md", "# S\n\n" + "- x\n" * 210)
        found = self.warnings()
        self.assertEqual(1, len(found))
        self.assertTrue(found[0].startswith("docs/tech/t.md:"))

    def test_trailing_newline_is_not_a_line(self):
        self.write("docs/tech/t.md", "x\n" * 200)
        self.assertEqual([], self.warnings())
        self.write("docs/tech/t.md", "x\n" * 200 + "last")
        self.assertEqual(1, len(self.warnings()))

    def test_limits_come_from_settings(self):
        self.write(".claude/dev-kit.md", PROFILE + "| size-limit | `30` |\n| map-limit | `5` |\n")
        self.write("docs/tech/t.md", "# T\n\n" + "- x\n" * 40)
        self.write("docs/tech/map.md", "# Map\n\n- `src/` ([T](t.md))\n" + "\n" * 5)
        found = self.warnings()
        self.assertEqual(2, len(found), found)
        self.assertIn("[map-size] map has 8 lines (limit 5)", "\n".join(found))
        self.assertIn("(limit 30)", "\n".join(found))


class ReverseIndexTests(DocsTestCase):
    def setUp(self):
        super().setUp()
        self.write("docs/features/f.md", feature(built="- `src/` and `src/sub/x.py`"))
        self.write("docs/features/g.md", feature("G", built="- `src/sub/`, `src/*.py`"))
        self.append("docs/epics/e.md", "- [G](../features/g.md)\n")

    def who(self, path):
        _, lines = self.check("--who", path)
        return lines

    def test_longest_prefix_first(self):
        self.assertEqual(
            ["docs/features/f.md  (Feature F)  via src/sub/x.py", "docs/features/g.md  (Feature G)  via src/sub/"],
            self.who("src/sub/x.py"),
        )

    def test_folder_entry_covers_everything_below(self):
        self.assertEqual(["docs/features/f.md  (Feature F)  via src/"], self.who("src/other/deep/file.cs"))

    def test_glob_entry(self):
        self.assertEqual(
            ["docs/features/g.md  (Feature G)  via src/*.py", "docs/features/f.md  (Feature F)  via src/"],
            self.who("src/app.py"),
        )

    def test_path_above_an_entry_matches_with_its_own_length(self):
        _, lines = self.check("--who", "src")
        self.assertEqual(2, len(lines))

    def test_no_match(self):
        self.assertEqual(["No feature lists nowhere/x.cs."], self.who("nowhere/x.cs"))

    def test_backslashes_dot_slash_trailing_slash_and_case(self):
        expected = self.who("src/sub/x.py")
        self.assertEqual(expected, self.who("src\\sub\\x.py"))
        self.assertEqual(expected, self.who("./src/sub/x.py"))
        self.assertEqual(expected, self.who("SRC/SUB/X.PY"))
        self.assertEqual(self.who("src/sub"), self.who("src/sub/"))

    def test_absolute_path_inside_the_root(self):
        self.assertEqual(self.who("src/sub/x.py"), self.who(str(self.root / "src" / "sub" / "x.py")))

    def test_who_wins_over_the_check_and_exits_zero(self):
        self.append("docs/README.md", "[x](nope.md)\n")
        code, _ = self.check("--who", "src/app.py")
        self.assertEqual(0, code)

    def test_open_wins_over_who(self):
        _, lines = self.check("--who", "src/app.py", "--open")
        self.assertEqual("Tasks (0)", lines[0])


class OpenItemsTests(DocsTestCase):
    def setUp(self):
        super().setUp()
        self.write("docs/features/f.md", feature(built="- `src/app.py`, `src/sub/x.py`", extra="""
## Open

- [ ] A plain task
  that wraps.
- [ ] Defect: a defect with a wrapped
  second line.
- [x] Done item.
- [ ] defect: lower case marker.
- [ ] Defect : space before the colon.
- [ ]
- [ ] Parent:
  - [ ] nested
  1. [ ] numbered is not an item
* [ ] star
+ [ ] plus

```
- [ ] fenced
```

### Open

- [ ] under h3

## Other

- [ ] under another heading

## open

- [ ] lower case heading
"""))
        self.write("docs/tech/t.md", "# T\n\nLead `pkg.core/Thing.cs` and `Dockerfile`.\n\nSecond `src/ignored.py`.\n\n"
                   "## Open\n\n- [ ] Defect: tech defect.\n- [ ] Tech task.\n")
        self.write("docs/standards/s.md", "# S\n\n## Open\n\n- [ ] Standard task.\n")
        self.write("docs/epics/e.md", BASE["docs/epics/e.md"] + "\n## Open\n\n- [ ] Epic task.\n")
        self.write("plans/p.md", "# P\n\n- [ ] Plan task\n  wrapped\n\n## Later\n\n* [ ] Plan star\n")

    def lines(self, *args):
        code, lines = self.check(*args)
        self.assertEqual(0, code)
        return lines

    def test_counts_and_groups(self):
        lines = self.lines("--open")
        self.assertEqual("Tasks (14)", lines[0])
        self.assertIn("Defects (3)", lines)
        self.assertEqual("open items: 17 (14 tasks, 3 defects)", lines[-1])

    def test_grouped_by_area_with_also_and_aliases(self):
        lines = self.lines("--open")
        joined = "\n".join(lines)
        self.assertIn("\nsrc  (", joined)
        self.assertIn("src/pkg.core  (1 item)", joined)
        self.assertIn("docs/features/f.md:23  [also: src/sub]  A plain task that wraps.", joined)

    def test_area_comes_from_lead_paragraph_of_a_tech_file(self):
        lines = self.lines("--open")
        index = lines.index("  docs/tech/t.md:10  Tech task.")
        header = [line for line in lines[:index] if not line.startswith(" ")][-1]
        self.assertEqual("src/pkg.core  (1 item)", header)

    def test_no_code_path_means_area_docs_and_plans_count_wholly(self):
        joined = "\n".join(self.lines("--open"))
        self.assertIn("docs  (", joined)
        self.assertIn("plans/p.md:3  Plan task wrapped", joined)
        self.assertIn("plans/p.md:8  Plan star", joined)

    def test_fence_other_headings_and_done_items_are_skipped(self):
        joined = "\n".join(self.lines("--open"))
        for skipped in ("fenced", "under another heading", "Done item"):
            self.assertNotIn(skipped, joined)
        for counted in ("under h3", "lower case heading"):
            self.assertIn(counted, joined)

    def test_defects_only(self):
        lines = self.lines("--defects")
        self.assertEqual("Defects (3)", lines[0])
        self.assertEqual("open defects: 3", lines[-1])
        self.assertNotIn("Tasks", "\n".join(lines))
        self.assertEqual(lines, self.lines("--open", "--defects"))

    def test_defect_marker_is_case_insensitive_but_needs_the_colon(self):
        lines = "\n".join(self.lines("--defects"))
        self.assertIn("lower case marker", lines)
        self.assertNotIn("space before the colon", lines)

    def test_by_file(self):
        lines = self.lines("--open", "--by-file")
        self.assertEqual("Tasks (14)", lines[0])
        self.assertIn("docs/features/f.md  (Feature F)", lines)
        self.assertIn("  23: A plain task that wraps.", lines)
        self.assertLess(lines.index("docs/epics/e.md  (E)"), lines.index("docs/features/f.md  (Feature F)"))
        self.assertLess(lines.index("docs/standards/s.md  (S)"), lines.index("docs/tech/t.md  (T)"))
        self.assertLess(lines.index("docs/tech/t.md  (T)"), lines.index("plans/p.md  (P)"))

    def test_without_code_roots_every_item_is_in_docs(self):
        self.write(".claude/dev-kit.md", "## documentation\n\n| Setting | Value |\n|---|---|\n| size-limit | `200` |\n")
        lines = self.lines("--open")
        areas = [line for line in lines if line and not line.startswith(" ") and "(" in line and "item" in line]
        self.assertEqual(["docs  (14 items)", "docs  (3 items)"], [a for a in areas if not a.startswith(("Tasks", "Defects", "open"))])


@unittest.skipUnless(HAS_GIT, "git is not installed")
class PreCommitTests(DocsTestCase):
    def test_without_staged_code_and_with_full_coverage_there_is_only_the_summary(self):
        self.init_git()
        code, lines = self.check("--pre-commit")
        self.assertEqual((0, ["docs check: 0 errors, 0 warnings"]), (code, lines))

    def test_staged_code_listed_by_a_feature(self):
        self.init_git()
        self.write("src/app.py", "x = 2\n")
        self.write("docs/README.md", "# Index\n")
        self.git("add", "-A")
        _, lines = self.check("--pre-commit")
        self.assertEqual(
            ["Advisory: staged code listed by features",
             "  src/app.py - feature docs/features/f.md lists this path: did its rules change?"],
            lines[1:],
        )

    def test_deleted_and_unstaged_files_are_not_listed(self):
        self.init_git()
        self.write("src/sub/x.py", "y = 2\n")
        self.git("rm", "-q", "src/app.py")
        _, lines = self.check("--pre-commit")
        self.assertEqual([], [line for line in lines if line.startswith("Advisory")])

    def test_staged_files_outside_code_roots_are_not_listed(self):
        self.init_git()
        self.write("other/a.txt", "a")
        self.git("add", "-A")
        _, lines = self.check("--pre-commit")
        self.assertEqual(1, len(lines))

    def test_uncovered_code_folders(self):
        self.write("docs/tech/map.md", "# Map\n\n- `src/sub` ([T](t.md)).\n")
        self.write("docs/features/f.md", feature(built="- `src/sub/x.py`"))
        self.write("src/new/deep/a.py", "a")
        self.write("src/other/b.py", "b")
        self.init_git()
        _, lines = self.check("--pre-commit")
        self.assertEqual(
            ["Advisory: 3 code folders that no feature 'Built in' and no map line mentions",
             "  src/new", "  src/new/deep", "  src/other"],
            lines[1:],
        )

    def test_a_map_line_naming_the_bare_root_covers_everything(self):
        self.write("src/new/a.py", "a")
        self.init_git()
        self.assertEqual(1, len(self.check("--pre-commit")[1]))

    def test_lists_are_capped_at_thirty(self):
        self.write("docs/tech/map.md", "# Map\n\n- `src/sub`\n")
        for i in range(35):
            self.write(f"src/f{i:02d}.py", "a")
            self.write(f"src/d{i:02d}/a.py", "a")
        self.write("docs/features/f.md", feature(built="- `src/*.py`"))
        self.init_git()
        for i in range(35):
            self.write(f"src/f{i:02d}.py", "b")
        self.git("add", "-A")
        _, lines = self.check("--pre-commit")
        self.assertEqual("Advisory: staged code listed by features", lines[1])
        self.assertEqual("  ... and 5 more", lines[32])
        self.assertTrue(lines[33].startswith("Advisory: 35 code folders"))
        self.assertEqual("  ... and 5 more", lines[-1])
        self.assertEqual(30, len([line for line in lines[2:32] if "lists this path" in line]))
        self.assertEqual(30, len([line for line in lines[34:-1] if line.startswith("  src/d")]))

    def test_no_code_roots_means_no_advisory(self):
        self.write(".claude/dev-kit.md", "## documentation\n\n| Setting | Value |\n|---|---|\n| size-limit | `200` |\n")
        self.init_git()
        self.write("src/app.py", "x = 2\n")
        self.git("add", "-A")
        self.assertEqual(["docs check: 0 errors, 0 warnings"], self.check("--pre-commit")[1])

    def test_advisory_does_not_change_the_exit_code_but_errors_do(self):
        self.init_git()
        self.append("docs/README.md", "[x](nope.md)\n")
        self.assertEqual(1, self.check("--pre-commit")[0])

    def test_not_a_git_repo_gives_no_staged_list(self):
        self.assertEqual(["docs check: 0 errors, 0 warnings"], self.check("--pre-commit")[1])


class OrderingTests(unittest.TestCase):
    def test_all_equal_keys_come_out_in_the_powershell_order(self):
        expected = {
            2: [1, 0], 3: [2, 1, 0], 4: [2, 3, 0, 1], 5: [3, 4, 2, 0, 1], 7: [4, 5, 6, 3, 0, 1, 2],
            8: [5, 4, 7, 6, 1, 0, 3, 2],
        }
        for size, order in expected.items():
            self.assertEqual(order, check_docs.ps_sort(range(size), lambda a, b: 0), size)

    def test_ps_sort_sorts(self):
        data = [5, 3, 9, 1, 1, 7, 2, 8, 0, 6, 4, 4, 3, 2, 10, 12, 11, 15, 14, 13, 20, 19, 18, 17, 16]
        self.assertEqual(sorted(data), check_docs.ps_sort(data, lambda a, b: (a > b) - (a < b)))

    def test_culture_key_ordering(self):
        shuffled = ["docs/f.md", "docs/B.md", "docs/_x.md", "docs/é.md", "docs/a.md", "docs/ab.md", "docs/b-a.md", "docs/a-b.md"]
        self.assertEqual(
            ["docs/_x.md", "docs/a.md", "docs/ab.md", "docs/a-b.md", "docs/B.md", "docs/b-a.md", "docs/é.md", "docs/f.md"],
            sorted(shuffled, key=check_docs.culture_key),
        )

    def test_punctuation_sorts_before_digits_before_letters(self):
        keys = sorted(["b", "1", ".", "a", "_", "/"], key=check_docs.culture_key)
        self.assertEqual([".", "/", "_", "1", "a", "b"], keys)

    def test_same_file_and_line_problems_keep_the_powershell_order(self):
        problems = [check_docs.Problem("r", "f.md", 1, str(i)) for i in range(4)]
        ordered = check_docs.ps_sort(problems, check_docs.compare_problems)
        self.assertEqual(["2", "3", "0", "1"], [p.message for p in ordered])


class SettingsTests(unittest.TestCase):
    def parse(self, *rows):
        return check_docs.parse_settings(list(rows))

    def test_defaults_suit_a_project_without_code_roots(self):
        settings, errors = self.parse()
        self.assertEqual([], errors)
        self.assertEqual([], settings.code_roots)
        self.assertEqual([], settings.scan)
        self.assertEqual((200, 60), (settings.size_limit, settings.map_limit))
        self.assertIn("node_modules", settings.skip_dirs)
        self.assertEqual("skills-lock.json", settings.skills_lock)
        self.assertIn(".py", settings.known_file_ext())

    def test_every_setting(self):
        settings, errors = self.parse(
            ("scan", "backend: .cs"), ("scan", "web/src: .TS, .tsx"), ("code-root", "backend 3"), ("code-root", "web/src/ 2"),
            ("skip-dirs", "data, logs"), ("skip-dirs", ".run"), ("area-alias", "src/ -> web/src/"),
            ("file-ext", ".cs .ts"), ("file-ext", ".md"), ("skills-lock", "none"), ("size-limit", "100"), ("map-limit", "20"),
        )
        self.assertEqual([], errors)
        self.assertEqual([("backend", [".cs"]), ("web/src", [".ts", ".tsx"])], settings.scan)
        self.assertEqual([("backend", 3), ("web/src", 2)], settings.code_roots)
        self.assertTrue({"data", "logs", ".run", ".git"} <= settings.skip_dirs)
        self.assertEqual([("src/", "web/src/")], settings.area_aliases)
        self.assertEqual([".cs", ".ts", ".md"], settings.file_ext)
        self.assertEqual(("none", 100, 20), (settings.skills_lock, settings.size_limit, settings.map_limit))

    def test_bad_values_are_reported(self):
        cases = {
            ("scan", "backend"): "setting 'scan': expected",
            ("scan", "backend: cs"): "is not an extension",
            ("scan", "../x: .cs"): "relative to the project root",
            ("code-root", "backend"): "setting 'code-root': expected",
            ("code-root", "backend 0"): "depth of 1 or more",
            ("skip-dirs", "a/b"): "must be a folder name",
            ("area-alias", "src/"): "expected '<prefix> -> <replacement>'",
            ("file-ext", "cs"): "is not an extension",
            ("skills-lock", "a b"): "project-relative file path or 'none'",
            ("size-limit", "many"): "whole number",
            ("map-limit", "0"): "whole number",
            ("ghost", "x"): "unknown setting 'ghost'",
        }
        for row, message in cases.items():
            errors = self.parse(row)[1]
            self.assertTrue(any(message in e for e in errors), f"{row}: {errors}")

    def test_single_settings_cannot_be_set_twice(self):
        errors = self.parse(("size-limit", "1"), ("size-limit", "2"))[1]
        self.assertEqual(["setting 'size-limit' is set twice"], errors)


class ProfileTests(unittest.TestCase):
    def test_profile_without_the_section_has_no_errors(self):
        self.assertEqual([], check_docs.profile_errors("## coder\n\nx\n"))
        self.assertIsNone(check_docs.profile_table("## coder\n\nx\n"))

    def test_clean_table(self):
        self.assertEqual([], check_docs.profile_errors(PROFILE))

    def test_section_without_table_or_with_wrong_header(self):
        self.assertEqual(1, len(check_docs.profile_errors("## documentation\n\nNothing.\n")))
        self.assertEqual(1, len(check_docs.profile_errors("## documentation\n\n| Name | Value |\n|---|---|\n| a | b |\n")))

    def test_row_problems_are_reported(self):
        text = "## documentation\n\n| Setting | Value |\n|---|---|\n| ghost | x |\n| scan | |\n| code-root | `a 0` |\n"
        errors = check_docs.profile_errors(text)
        self.assertEqual(3, len(errors), errors)

    def test_extra_columns_are_allowed_and_fences_are_ignored(self):
        text = "```\n## documentation\n```\n\n## documentation\n\n| Setting | Value | Note |\n|---|---|---|\n| size-limit | `5` | why |\n"
        self.assertEqual([], check_docs.profile_errors(text))

    def test_bad_settings_stop_the_run_with_exit_two(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".claude").mkdir()
            (root / ".claude" / "dev-kit.md").write_text("## documentation\n\n| Setting | Value |\n|---|---|\n| ghost | x |\n", encoding="utf-8")
            err = io.StringIO()
            out = io.StringIO()
            with redirect_stderr(err):
                code = check_docs.main(["--root", str(root)], out=out)
            self.assertEqual(2, code)
            self.assertEqual("", out.getvalue())
            self.assertIn("unknown setting 'ghost'", err.getvalue())

    def test_default_root_outside_git_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = os.getcwd()
            os.chdir(tmp)
            try:
                err = io.StringIO()
                with mock.patch.dict(os.environ, {"GIT_CEILING_DIRECTORIES": str(Path(tmp).parent)}):
                    with redirect_stderr(err):
                        code = check_docs.main([], out=io.StringIO())
            finally:
                os.chdir(previous)
            self.assertEqual(2, code)
            self.assertIn("not inside a git repository", err.getvalue())


class ShimTests(DocsTestCase):
    def test_shim_runs_the_script_and_prints_utf8_without_bom(self):
        self.write("docs/features/f.md", feature("Страва"))
        result = subprocess.run(
            [sys.executable, str(SHIM), "--root", str(self.root), "--who", "src/app.py"], capture_output=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(result.stdout.startswith(b"\xef\xbb\xbf"))
        self.assertIn("(Feature Страва)", result.stdout.decode("utf-8"))

    def test_shim_exit_code_follows_the_check(self):
        self.append("docs/README.md", "[x](nope.md)\n")
        result = subprocess.run([sys.executable, str(SHIM), "--root", str(self.root)], capture_output=True, check=False)
        self.assertEqual(1, result.returncode)
        self.assertIn("docs check: 1 errors (link=1), 0 warnings", result.stdout.decode("utf-8"))

    def test_shim_file_has_lf_endings_and_a_shebang(self):
        data = SHIM.read_bytes()
        self.assertTrue(data.startswith(b"#!/usr/bin/env python\n"))
        self.assertNotIn(b"\r", data)


BAD_PROFILES = {
    "empty value cell": ("## documentation\n\n| Setting | Value |\n|---|---|\n| size-limit | |\n", "needs a setting and a value"),
    "missing value cell": ("## documentation\n\n| Setting | Value |\n|---|---|\n| code-root |\n", "needs a setting and a value"),
    "empty setting cell": ("## documentation\n\n| Setting | Value |\n|---|---|\n| | `5` |\n", "needs a setting and a value"),
    "wrong-case heading": ("## Documentation\n\n| Setting | Value |\n|---|---|\n| size-limit | `5` |\n",
                           "heading '## Documentation' must be written '## documentation'"),
    "upper-case heading": ("## DOCUMENTATION\n", "must be written '## documentation'"),
    "no table": ("## documentation\n\nNothing.\n", "documentation table with header"),
    "unknown setting": ("## documentation\n\n| Setting | Value |\n|---|---|\n| ghost | x |\n", "unknown setting 'ghost'"),
}


class StrictSettingsTests(DocsTestCase):
    """A problem in the documentation table stops the run; it never falls back to defaults silently."""

    def run_shim(self, link=None):
        return subprocess.run([sys.executable, str(link or SHIM), "--root", str(self.root)], capture_output=True, check=False)

    def test_main_exits_two_for_every_problem(self):
        for name, (profile, message) in BAD_PROFILES.items():
            with self.subTest(name):
                self.write(".claude/dev-kit.md", profile)
                code, lines, err = self.run_main()
                self.assertEqual((2, []), (code, lines))
                self.assertIn(message, err)
                self.assertIn(".claude/dev-kit.md", err)

    def test_every_mode_stops(self):
        self.write(".claude/dev-kit.md", BAD_PROFILES["wrong-case heading"][0])
        for args in (["--pre-commit"], ["--who", "src/app.py"], ["--open"], ["--defects"], ["--open", "--by-file"]):
            with self.subTest(args):
                code, lines, _ = self.run_main(*args)
                self.assertEqual((2, []), (code, lines))

    def test_shim_exits_two_for_every_problem(self):
        for name, (profile, message) in BAD_PROFILES.items():
            with self.subTest(name):
                self.write(".claude/dev-kit.md", profile)
                result = self.run_shim()
                self.assertEqual(2, result.returncode)
                self.assertEqual(b"", result.stdout)
                self.assertIn(message, result.stderr.decode("utf-8", errors="replace"))

    def test_every_problem_is_reported_not_only_the_first(self):
        self.write(".claude/dev-kit.md", "## Documentation\n\n| Setting | Value |\n|---|---|\n| size-limit | |\n| ghost | x |\n")
        _, _, err = self.run_main()
        self.assertEqual(3, len(err.strip().splitlines()), err)

    def test_other_headings_and_a_missing_section_are_still_fine(self):
        self.write(".claude/dev-kit.md", "## coder\n\nText.\n\n## documentation notes\n\nText.\n")
        self.assertEqual(0, self.run_main()[0])
        (self.root / ".claude" / "dev-kit.md").unlink()
        self.assertEqual(0, self.run_main()[0])

    def test_wrong_case_heading_in_a_fence_is_ignored(self):
        self.write(".claude/dev-kit.md", "```\n## Documentation\n```\n")
        self.assertEqual(0, self.run_main()[0])

    def test_shim_runs_through_a_symlink(self):
        link = Path(self.tmp.name) / "linked-check-docs"
        try:
            link.symlink_to(SHIM)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not allowed here")
        result = self.run_shim(link)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("docs check: 0 errors, 0 warnings", result.stdout.decode("utf-8").strip())


class EncodingTests(DocsTestCase):
    def test_bom_utf16_crlf_and_bad_bytes(self):
        self.write("docs/a.md", "# A\n\n[x](nope.md)\n", newline="\r\n", encoding="utf-8-sig")
        self.write("docs/b.md", "# B\n\n[x](nope.md)\n", encoding="utf-16")
        (self.root / "docs" / "c.md").write_bytes(b"# C\n\n\xff\xfe bad\n[x](nope.md)\n")
        found = sorted(line.split(": ")[0] for line in self.errors("link"))
        self.assertEqual(["docs/a.md:3", "docs/b.md:3", "docs/c.md:4"], found)


if __name__ == "__main__":
    unittest.main()
