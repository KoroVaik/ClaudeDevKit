import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "web-kit" / "scripts" / "build-mockups.mjs"

SPEC = {
    "title": "Pick an item",
    "group": "Choice",
    "source": "docs/features/pick.md",
    "phones": {
        "start": {"caption": "Opens the app", "user": "A", "step": 1, "blocks": [
            {"type": "topbar", "title": "Today"},
            {"type": "dish", "name": "Item <one>", "photo": "photo"},
            {"type": "buttons", "items": [{"text": "Pick", "kind": "approve"}]},
        ]},
        "done": {"caption": "Item picked", "blocks": [{"type": "text", "text": "Done"}]},
    },
    "layout": [
        [{"branch": "Main path", "given": "**Precondition:** none"}],
        [{"phone": "start"}, {"link": "tap on the button «Pick»"}, {"phone": "done"}],
    ],
}


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class BuildMockupsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.project, check=True)
        self.mockups = self.project / "docs" / "mockups"
        (self.mockups / "src").mkdir(parents=True)
        self.write_spec("pick-item", SPEC)

    def write_spec(self, name, spec):
        (self.mockups / "src" / f"{name}.json").write_text(json.dumps(spec), encoding="utf-8")

    def run_build(self, *args, cwd=None):
        return subprocess.run(
            ["node", str(SCRIPT), *args], cwd=cwd or self.project, capture_output=True, text=True, encoding="utf-8"
        )

    def page(self, name):
        return (self.mockups / name).read_text(encoding="utf-8")

    def test_build_writes_pages_and_check_passes(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Built 1 mockup(s); wrote 3 file(s)", result.stdout)
        self.assertIn("Item &lt;one&gt;", self.page("pick-item.html"))
        self.assertIn('href="pick-item.html"', self.page("index.html"))
        checked = self.run_build("--check")
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertIn("OK: 1 mockup(s)", checked.stdout)

    def test_project_without_its_own_css_gets_the_default(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr)
        css = self.page("mockups.css")
        self.assertEqual(css, (SCRIPT.parent / "default-mockups.css").read_text(encoding="utf-8"))
        for name in ("topbar", "phone", "board", "chip", "btn", "tabbar", "toast", "branch"):
            self.assertIn(f".{name}", css)
        page = self.page("pick-item.html")
        self.assertIn(f"<style>\n{css}</style>", page)
        self.assertNotIn('href="mockups.css"', page)

    def test_check_reports_a_missing_css_before_the_first_build(self):
        result = self.run_build("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("mockups.css", result.stderr)

    def test_the_projects_own_css_wins_and_is_never_overwritten(self):
        own = "/* project palette */\nbody { color: red; }\n"
        (self.mockups / "mockups.css").write_text(own, encoding="utf-8")
        self.assertEqual(self.run_build().returncode, 0)
        self.assertEqual(self.page("mockups.css"), own)
        self.assertEqual(self.run_build("--check").returncode, 0)

    def test_check_fails_when_a_page_is_stale_and_names_the_command(self):
        self.run_build()
        self.write_spec("pick-item", {**SPEC, "title": "Changed"})
        result = self.run_build("--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Stale generated files: pick-item.html, index.html", result.stderr)
        self.assertIn("Run: web-kit-mockups", result.stderr)

    def test_dir_flag_builds_another_folder(self):
        other = self.project / "design" / "wireframes"
        shutil.copytree(self.mockups, other)
        shutil.rmtree(self.mockups)
        result = self.run_build("--dir", "design/wireframes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((other / "pick-item.html").is_file())
        stale = self.run_build("--dir", "design/wireframes", "--check")
        self.assertEqual(stale.returncode, 0, stale.stderr)

    def test_run_from_a_subfolder_uses_the_git_root_and_creates_nothing(self):
        sub = self.project / "frontend"
        sub.mkdir()
        result = self.run_build(cwd=sub)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.mockups / "pick-item.html").is_file())
        self.assertEqual(list(sub.iterdir()), [])

    def test_missing_mockups_folder_is_an_error_and_is_not_created(self):
        shutil.rmtree(self.project / "docs")
        result = self.run_build()
        self.assertEqual(result.returncode, 1)
        self.assertIn("Mockups folder not found: docs/mockups/src", result.stderr)
        self.assertFalse((self.project / "docs").exists())
        missing = self.run_build("--dir", "design/wireframes")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("Mockups folder not found", missing.stderr)
        self.assertFalse((self.project / "design").exists())

    def test_outside_a_git_repository_asks_for_dir(self):
        with tempfile.TemporaryDirectory() as plain:
            result = self.run_build(cwd=plain)
        self.assertEqual(result.returncode, 1)
        self.assertIn("pass --dir", result.stderr)

    def test_user_letters_and_step_title_default_to_neutral_english_and_come_from_config(self):
        spec = json.loads(json.dumps(SPEC))
        spec["phones"]["start"]["blocks"][0]["progress"] = {"current": 0, "total": 2}
        self.write_spec("pick-item", spec)
        self.run_build()
        page = self.page("pick-item.html")
        self.assertIn('<span class="user-tag user-a">A1</span>', page)
        self.assertIn('title="Step 1 of 2"', page)
        config = {"userLetters": {"A": "X"}, "stepTitle": "Krok {current}/{total}"}
        (self.mockups / "mockups.config.json").write_text(json.dumps(config), encoding="utf-8")
        self.run_build()
        page = self.page("pick-item.html")
        self.assertIn('<span class="user-tag user-a">X1</span>', page)
        self.assertIn('title="Krok 1/2"', page)

    def test_list_columns_option_adds_a_class_and_is_validated(self):
        def spec(block):
            return {**SPEC, "phones": {**SPEC["phones"], "done": {"caption": "Item picked", "blocks": [block]}}}

        self.write_spec("pick-item", spec({"type": "list", "rows": [["a", "b"]], "columns": True, "lines": False}))
        self.assertEqual(self.run_build().returncode, 0)
        self.assertIn('<div class="no-lines list-cols"><div class="list-row">', self.page("pick-item.html"))
        self.write_spec("pick-item", spec({"type": "list", "rows": [["a", "b"]]}))
        self.run_build()
        self.assertIn('<div><div class="list-row">', self.page("pick-item.html"))
        self.write_spec("pick-item", spec({"type": "list", "rows": [["a", "b"]], "columns": "yes"}))
        bad = self.run_build()
        self.assertEqual(bad.returncode, 1)
        self.assertIn('list "columns" must be true or false', bad.stderr)

    def test_unknown_block_is_a_spec_error_with_the_file_name(self):
        bad = json.loads(json.dumps(SPEC))
        bad["phones"]["done"]["blocks"] = [{"type": "carousel"}]
        self.write_spec("pick-item", bad)
        result = self.run_build()
        self.assertEqual(result.returncode, 1)
        self.assertIn("docs/mockups/src/pick-item.json", result.stderr)
        self.assertIn('unknown block type "carousel"', result.stderr)

    def test_phone_not_placed_in_layout_is_an_error(self):
        bad = json.loads(json.dumps(SPEC))
        bad["layout"] = [[{"phone": "start"}]]
        self.write_spec("pick-item", bad)
        result = self.run_build()
        self.assertEqual(result.returncode, 1)
        self.assertIn('phone "done" is defined but not placed', result.stderr)

    def test_html_without_a_spec_is_an_error(self):
        (self.mockups / "orphan.html").write_text("<html></html>", encoding="utf-8")
        result = self.run_build()
        self.assertEqual(result.returncode, 1)
        self.assertIn("HTML files without a spec", result.stderr)

    def test_config_texts_replace_the_neutral_defaults(self):
        self.run_build()
        self.assertIn("<title>Mockups</title>", self.page("index.html"))
        self.assertIn("<p>Low-fidelity wireframe. Not an accepted UI.</p>", self.page("pick-item.html"))
        config = {"title": "Shop mockups", "pageNote": "Placeholders only.", "indexNote": "Rules are in `docs/features/`."}
        (self.mockups / "mockups.config.json").write_text(json.dumps(config), encoding="utf-8")
        self.assertEqual(self.run_build().returncode, 0)
        self.assertIn("<h1>Shop mockups</h1>", self.page("index.html"))
        self.assertIn("<p>Rules are in <code>docs/features/</code>.</p>", self.page("index.html"))
        self.assertIn("<p>Placeholders only.</p>", self.page("pick-item.html"))


if __name__ == "__main__":
    unittest.main()
