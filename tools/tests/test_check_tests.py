import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "plugins" / "dev-kit" / "scripts"
SHIM = REPO / "plugins" / "dev-kit" / "bin" / "dev-kit-check-tests"
sys.path.insert(0, str(SCRIPTS))
import check_tests as ct  # noqa: E402

HAS_GIT = shutil.which("git") is not None

CS = """using Xunit;

namespace App.Tests;

[Trait("Kind", "Integration"), Trait("Domain", "Jobs"), Trait("Domain", "Auth")]
public sealed class JobTests(Fixture fixture) : IClassFixture<Fixture>
{
    [Fact]
    [Trait("Protects", "Rule")]
    public async Task Marked_Rule()
    {
        var s = "[Fact] in a string // not a comment";
    }

    [Trait("Protects", "Edge")] [Theory]
    [InlineData(1)]
    public void Marked_Edge_Theory(int x) { }

    [Fact, Trait("Protects", "Flow")]
    public void Marked_In_One_List() { }

    [Fact]
    public Task Unmarked() => Task.CompletedTask;

    // Broke: the job was lost on restart
    [Fact]
    [Trait("Protects", "Bug")]
    public void Bug_With_Broke() { }

    [Fact]
    [Trait("Protects", "Bug")]
    public void Bug_Without_Broke() { }

    [Fact]
    [Trait("Protects", "Rules")]
    public void Wrong_Value() { }

    [Fact]
    [Trait("Protects", "Rule")]
    [Trait("Protects", "Edge")]
    public void Two_Values() { }

    // [Fact]
    // public void Commented_Out() { }
}

public class Plain
{
    [Fact]
    public void In_Plain_Class() { }
}
"""


def cs_tests(text=CS, rel="backend/App.Tests/Jobs/JobTests.cs"):
    return {t.name: t for t in ct.parse_cs(rel, text)}


class CSharpParseTests(unittest.TestCase):
    def test_finds_every_fact_and_theory_and_not_commented_ones(self):
        self.assertEqual(
            {
                "JobTests.Marked_Rule", "JobTests.Marked_Edge_Theory", "JobTests.Marked_In_One_List",
                "JobTests.Unmarked", "JobTests.Bug_With_Broke", "JobTests.Bug_Without_Broke",
                "JobTests.Wrong_Value", "JobTests.Two_Values", "Plain.In_Plain_Class",
            },
            set(cs_tests()),
        )

    def test_marks_in_the_three_attribute_layouts(self):
        tests = cs_tests()
        self.assertEqual("Rule", tests["JobTests.Marked_Rule"].mark)
        self.assertEqual("Edge", tests["JobTests.Marked_Edge_Theory"].mark)
        self.assertEqual("Flow", tests["JobTests.Marked_In_One_List"].mark)
        self.assertIsNone(tests["JobTests.Unmarked"].mark)

    def test_class_traits_give_level_and_domains(self):
        test = cs_tests()["JobTests.Unmarked"]
        self.assertEqual("Integration", test.level)
        self.assertEqual(["Jobs", "Auth"], test.domains)

    def test_without_traits_level_is_unknown_and_domain_is_the_folder_under_the_tests_root(self):
        test = cs_tests()["Plain.In_Plain_Class"]
        self.assertEqual("unknown", test.level)
        self.assertEqual(["Jobs"], test.domains)
        self.assertEqual("-", ct.domain_from_path("backend/App.Tests/Top.cs"))

    def test_two_protects_values_make_an_invalid_mark(self):
        mark = cs_tests()["JobTests.Two_Values"].mark
        self.assertNotIn(mark, ct.MARKS)

    def test_line_is_the_method_name_line(self):
        test = cs_tests()["JobTests.Marked_Rule"]
        self.assertEqual("    public async Task Marked_Rule()", CS.splitlines()[test.line - 1].rstrip())

    def test_invalid_mark_and_bug_without_broke_are_problems(self):
        tests = cs_tests()
        self.assertIn("invalid mark 'Rules'", ct.mark_problem(tests["JobTests.Wrong_Value"]))
        self.assertIn("Broke", ct.mark_problem(tests["JobTests.Bug_Without_Broke"]))
        self.assertIsNone(ct.mark_problem(tests["JobTests.Bug_With_Broke"]))
        self.assertIsNone(ct.mark_problem(tests["JobTests.Unmarked"]))

    def test_broke_line_further_than_three_lines_above_does_not_count(self):
        text = (
            "[Trait(\"Kind\", \"Unit\")]\nclass T\n{\n"
            "    // Broke: far away\n\n\n\n"
            "    [Fact]\n    [Trait(\"Protects\", \"Bug\")]\n    public void Far() { }\n}\n"
        )
        self.assertFalse(cs_tests(text)["T.Far"].broke)

    def test_nested_braces_strings_and_char_literals_do_not_break_class_detection(self):
        text = (
            "[Trait(\"Kind\", \"Unit\")]\nclass T\n{\n"
            "    char c = '{'; string s = \"}}{\"; string v = @\"a \"\"{\"\" b\"; string i = $\"{(1 > 0 ? \"}\" : \"x\")}\";\n"
            "    [Fact]\n    public void A() { }\n}\n"
        )
        test = cs_tests(text)["T.A"]
        self.assertEqual("Unit", test.level)

    def test_partial_class_gets_traits_from_another_file(self):
        registry = {}
        a = "[Trait(\"Kind\", \"Integration\"), Trait(\"Domain\", \"Photos\")]\npublic partial class P { }\n"
        b = "public partial class P\n{\n    [Fact]\n    public void T() { }\n}\n"
        by_file = {
            "x.Tests/A.cs": ct.parse_cs("x.Tests/A.cs", a, registry),
            "x.Tests/B.cs": ct.parse_cs("x.Tests/B.cs", b, registry),
        }
        self.assertEqual("unknown", by_file["x.Tests/B.cs"][0].level)
        ct.resolve_partials(by_file, registry)
        test = by_file["x.Tests/B.cs"][0]
        self.assertEqual(("Integration", ["Photos"]), (test.level, test.domains))


VITEST = """import { describe, it, test, expect } from "vitest";

describe("[Rule] a describe is not a test", () => {
  it("[Rule] double quotes", () => {});
  it('[Flow] single quotes', () => {});
  test(`[Edge] backticks`, () => {});
  it.each([1, 2])("[Edge] each %s", () => {});
  it.skip("[Edge] skipped", () => {});
  it("unmarked", () => {});
  it("[Nope] bad value", () => {});
  // it("[Rule] commented out", () => {});

  // Broke: the total was doubled
  it("[Bug] with broke", () => {});
  it("[Bug] without broke", () => {});
  it(
    "[Rule] title on the next line",
    () => {},
  );
});
"""


class VitestParseTests(unittest.TestCase):
    def setUp(self):
        self.tests = {t.name: t for t in ct.parse_vitest("frontend/src/api/a.test.ts", VITEST)}

    def test_all_quote_styles_each_skip_and_multiline_titles(self):
        self.assertEqual(
            {
                "[Rule] double quotes", "[Flow] single quotes", "[Edge] backticks", "[Edge] each %s",
                "[Edge] skipped", "unmarked", "[Nope] bad value", "[Bug] with broke", "[Bug] without broke",
                "[Rule] title on the next line",
            },
            set(self.tests),
        )

    def test_marks(self):
        self.assertEqual("Rule", self.tests["[Rule] double quotes"].mark)
        self.assertEqual("Flow", self.tests["[Flow] single quotes"].mark)
        self.assertEqual("Edge", self.tests["[Edge] backticks"].mark)
        self.assertIsNone(self.tests["unmarked"].mark)
        self.assertNotIn(ct.mark_problem(self.tests["[Nope] bad value"]), (None,))

    def test_bug_needs_broke(self):
        self.assertIsNone(ct.mark_problem(self.tests["[Bug] with broke"]))
        self.assertIn("Broke", ct.mark_problem(self.tests["[Bug] without broke"]))

    def test_level_and_domain(self):
        test = self.tests["unmarked"]
        self.assertEqual(("Unit", ["api"]), (test.level, test.domains))
        e2e = ct.parse_vitest("frontend/e2e/flow.spec.ts", 'test("[Flow] x", async () => {});')[0]
        self.assertEqual("E2E", e2e.level)


PY = """import unittest


class IntegrationFlow(unittest.TestCase):
    # protects: Rule
    def test_marked(self):
        pass

    # protects: Edge
    @unittest.skip("x")
    @other
    def test_marked_above_decorators(self):
        pass

    def test_unmarked(self):
        pass

    # protects: Bug
    # Broke: wrong total
    def test_bug_ok(self):
        pass

    # protects: Bug
    def test_bug_bad(self):
        pass

    # protects: rule
    def test_lower_case_value(self):
        pass


def test_top_level():
    pass
"""


class PythonParseTests(unittest.TestCase):
    def setUp(self):
        self.tests = {t.name: t for t in ct.parse_python("tools/tests/test_a.py", PY)}

    def test_finds_methods_and_top_level_functions(self):
        self.assertEqual(
            {
                "IntegrationFlow.test_marked", "IntegrationFlow.test_marked_above_decorators",
                "IntegrationFlow.test_unmarked", "IntegrationFlow.test_bug_ok", "IntegrationFlow.test_bug_bad",
                "IntegrationFlow.test_lower_case_value", "test_top_level",
            },
            set(self.tests),
        )

    def test_marks_and_comment_above_decorators(self):
        self.assertEqual("Rule", self.tests["IntegrationFlow.test_marked"].mark)
        self.assertEqual("Edge", self.tests["IntegrationFlow.test_marked_above_decorators"].mark)
        self.assertIsNone(self.tests["IntegrationFlow.test_unmarked"].mark)

    def test_bug_and_invalid_value(self):
        self.assertIsNone(ct.mark_problem(self.tests["IntegrationFlow.test_bug_ok"]))
        self.assertIn("Broke", ct.mark_problem(self.tests["IntegrationFlow.test_bug_bad"]))
        self.assertIn("invalid mark 'rule'", ct.mark_problem(self.tests["IntegrationFlow.test_lower_case_value"]))

    def test_level_from_class_name(self):
        self.assertEqual("Integration", self.tests["IntegrationFlow.test_marked"].level)
        self.assertEqual("Unit", self.tests["test_top_level"].level)


class TempProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "proj"
        self.root.mkdir()

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))

    def run_main(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stderr(err):
            code = ct.main(["--root", str(self.root), *args], out=out)
        return code, out.getvalue().splitlines(), err.getvalue()

    def git(self, *args):
        subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
            cwd=self.root, check=True, capture_output=True,
        )

    def commit_all(self):
        if not (self.root / ".git").exists():
            self.git("init", "-q")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "c")


SUSPECT_CS = """[Trait("Kind", "Unit")]
public class S
{
    // Suspect: only asserts the mock was called
    [Fact]
    [Trait("Protects", "Rule")]
    public void Suspected() { }

    // Broke: totals were doubled
    // Suspect: passes with the fix reverted
    [Fact]
    [Trait("Protects", "Bug")]
    public void Both_Lines() { }

    // Suspect:
    [Fact]
    public void Empty_Reason() { }

    // Suspect: too far above



    [Fact]
    public void Fine() { }
}
"""

SUSPECT_VITEST = """describe("x", () => {
  // Suspect: checks only that it renders
  it("[Flow] suspected", () => {});

  // Broke: wrong total
  // Suspect: same as the unit test
  it("[Bug] both lines", () => {});

  // Suspect:
  it("[Rule] empty reason", () => {});

  it("[Rule] fine", () => {});
});
"""

SUSPECT_PY = """class T(unittest.TestCase):
    # protects: Rule
    # Suspect: only checks the return type
    def test_suspected(self):
        pass

    # Broke: wrong total
    # Suspect: passes without the code
    # protects: Bug
    @unittest.skip("x")
    def test_both_lines(self):
        pass

    # protects: Rule
    # Suspect:
    def test_empty_reason(self):
        pass

    def test_fine(self):
        pass
"""


class SuspectParseTests(unittest.TestCase):
    def test_csharp_suspect_reason_with_broke_and_empty_reason(self):
        tests = cs_tests(SUSPECT_CS)
        self.assertEqual("only asserts the mock was called", tests["S.Suspected"].suspect)
        self.assertEqual("passes with the fix reverted", tests["S.Both_Lines"].suspect)
        self.assertTrue(tests["S.Both_Lines"].broke)
        self.assertEqual("", tests["S.Empty_Reason"].suspect)
        self.assertIsNone(tests["S.Fine"].suspect)

    def test_vitest_suspect_reason_with_broke_and_empty_reason(self):
        tests = {t.name: t for t in ct.parse_vitest("web/src/a.test.ts", SUSPECT_VITEST)}
        self.assertEqual("checks only that it renders", tests["[Flow] suspected"].suspect)
        self.assertEqual("same as the unit test", tests["[Bug] both lines"].suspect)
        self.assertTrue(tests["[Bug] both lines"].broke)
        self.assertEqual("", tests["[Rule] empty reason"].suspect)
        self.assertIsNone(tests["[Rule] fine"].suspect)

    def test_python_suspect_reason_with_broke_and_empty_reason(self):
        tests = {t.name: t for t in ct.parse_python("py/test_a.py", SUSPECT_PY)}
        self.assertEqual("only checks the return type", tests["T.test_suspected"].suspect)
        self.assertEqual("Rule", tests["T.test_suspected"].mark)
        self.assertEqual("passes without the code", tests["T.test_both_lines"].suspect)
        self.assertTrue(tests["T.test_both_lines"].broke)
        self.assertEqual("", tests["T.test_empty_reason"].suspect)
        self.assertIsNone(tests["T.test_fine"].suspect)

    def test_empty_reason_is_a_problem_and_a_reason_is_not(self):
        tests = cs_tests(SUSPECT_CS)
        self.assertIn("no reason", ct.suspect_problem(tests["S.Empty_Reason"]))
        self.assertIsNone(ct.suspect_problem(tests["S.Suspected"]))
        self.assertIsNone(ct.suspect_problem(tests["S.Fine"]))


class SuspectCommandTests(TempProject):
    def setUp(self):
        super().setUp()
        self.write("web/src/b.test.ts", 'describe("x", () => {\n  // Suspect: renders only\n  it("[Flow] v", () => {});\n});\n')
        self.write("py/test_a.py", "# protects: Rule\n# Suspect: no assert\ndef test_p():\n    pass\n\ndef test_q():\n    pass\n")
        self.write(
            "api/App.Tests/FooTests.cs",
            '[Trait("Kind", "Unit")]\npublic class FooTests\n{\n    // Suspect: mock only\n    [Fact]\n'
            '    [Trait("Protects", "Edge")]\n    public void C() { }\n}\n',
        )

    def test_suspects_text_is_sorted_by_file_with_a_total_line(self):
        code, lines, _ = self.run_main("--suspects")
        self.assertEqual(0, code)
        self.assertEqual(
            [
                "api/App.Tests/FooTests.cs:7 FooTests.C - mock only",
                "py/test_a.py:3 test_p - no assert",
                "web/src/b.test.ts:3 [Flow] v - renders only",
                "suspect tests: 3",
            ],
            lines,
        )

    def test_suspects_json_is_a_list(self):
        code, lines, _ = self.run_main("--suspects", "--json")
        self.assertEqual(0, code)
        data = json.loads("\n".join(lines))
        self.assertEqual(3, len(data))
        self.assertEqual(
            {"file": "py/test_a.py", "line": 3, "name": "test_p", "suspect": "no assert"}, data[1]
        )

    def test_no_suspects_prints_zero(self):
        (self.root / "py" / "test_a.py").write_text("def test_q():\n    pass\n")
        for rel in ("web/src/b.test.ts", "api/App.Tests/FooTests.cs"):
            (self.root / rel).unlink()
        code, lines, _ = self.run_main("--suspects")
        self.assertEqual((0, ["suspect tests: 0"]), (code, lines))

    def test_report_counts_suspects_per_domain_and_in_json(self):
        code, lines, _ = self.run_main("--report")
        self.assertEqual(0, code)
        text = "\n".join(lines)
        self.assertIn("suspect 3", text)
        self.assertIn("py/test_a.py:3 test_p - no assert", text)
        code, lines, _ = self.run_main("--report", "--json")
        data = json.loads("\n".join(lines))
        self.assertEqual(3, data["total"]["suspects"])
        self.assertEqual(3, data["domains"]["-"]["suspects"])
        self.assertEqual(3, len(data["suspects"]))

    @unittest.skipUnless(HAS_GIT, "git is not installed")
    def test_empty_reason_is_a_check_error_and_suspect_does_not_replace_the_mark(self):
        self.commit_all()
        self.write(
            "py/test_e.py",
            "# Suspect:\ndef test_empty():\n    pass\n\n# Suspect: has a reason\ndef test_unmarked():\n    pass\n",
        )
        code, lines, _ = self.run_main()
        self.assertEqual(1, code)
        self.assertTrue(any("py/test_e.py:2 test_empty - Suspect line has no reason" in line for line in lines))
        self.assertTrue(any("py/test_e.py:6 test_unmarked - new test has no protects mark" in line for line in lines))
        self.assertFalse(any("test_p " in line for line in lines))

    def test_suspects_and_report_cannot_be_combined(self):
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                ct.main(["--root", str(self.root), "--report", "--suspects"])


class RouteTests(unittest.TestCase):
    def test_parameters_match_any_segment_with_or_without_constraint(self):
        self.assertTrue(ct.route_matches("/api/jobs/{id:guid}/ai-calls", "/api/jobs/123/ai-calls"))
        self.assertTrue(ct.route_matches("api/jobs/{id}", "api/jobs/" + ct.HOLE))
        self.assertTrue(ct.route_matches("/api/Jobs", "/api/jobs/"))

    def test_other_shapes_do_not_match(self):
        self.assertFalse(ct.route_matches("/api/jobs/{id}", "/api/jobs"))
        self.assertFalse(ct.route_matches("/api/jobs", "/api/jobs/5"))
        self.assertFalse(ct.route_matches("/api/jobs/{id}/x", "/api/jobs/5/y"))

    def test_optional_catch_all_and_composite_segments(self):
        self.assertTrue(ct.route_matches("/api/f/{id?}", "/api/f"))
        self.assertTrue(ct.route_matches("/api/f/{id?}", "/api/f/3"))
        self.assertTrue(ct.route_matches("/files/{*path}", "/files/a/b/c"))
        self.assertTrue(ct.route_matches("/v{version}/x", "/v2/x"))
        self.assertTrue(ct.route_matches("/a/{x:regex(^\\d{{3}}$)}", "/a/123"))

    def test_hole_inside_a_literal_segment(self):
        self.assertTrue(ct.route_matches("/api/photo-searches", "/api/photo-" + ct.HOLE))
        self.assertFalse(ct.route_matches("/api/dishes", "/api/photo-" + ct.HOLE))

    def test_literals_from_interpolation_concatenation_and_consts(self):
        text = (
            'const string Base = "/api/c/";\n'
            'var a = $"/api/jobs/{job.Id}/ai-calls?x=1";\n'
            'var b = "/api/jobs/" + id + "/ai-response";\n'
            'var c = Base + "mark";\n'
            'var d = $"{Base}items/{id}";\n'
            'var e = "/api/jobs/" + id;\n'
        )
        found = [ct.normalise_literal(v) for v in ct.string_literals(text)]
        self.assertIn("api/c", found)
        self.assertIn("api/jobs/" + ct.HOLE + "/ai-calls", found)
        self.assertIn("api/jobs/" + ct.HOLE + "/ai-response", found)
        self.assertIn("api/c/mark", found)
        self.assertIn("api/c/items/" + ct.HOLE, found)
        self.assertIn("api/jobs/" + ct.HOLE, found)

    def test_non_paths_are_dropped(self):
        self.assertIsNone(ct.normalise_literal("hello world/x"))
        self.assertIsNone(ct.normalise_literal("plain"))
        self.assertEqual("api/x", ct.normalise_literal("https://example.test/api/x?y=1#z"))


CONTROLLER = """using Microsoft.AspNetCore.Mvc;

[ApiController, Authorize, Route("api/[controller]")]
public sealed partial class WidgetsController : ControllerBase
{
    [HttpGet]
    public IActionResult List() => Ok();

    [HttpGet("{id:guid}"), ProducesResponseType(200)]
    public IActionResult One(Guid id) => Ok();

    [HttpPost("login"), AllowAnonymous]
    public IActionResult Login() => Ok();

    [HttpDelete("~/api/other/{id}")]
    public IActionResult Other(string id) => Ok();

    // [HttpGet("commented")]
}
"""

PARTIAL = """public sealed partial class WidgetsController
{
    [HttpPut("{id:guid}/rename")]
    public IActionResult Rename(Guid id) => Ok();
}
"""

PROGRAM = """var app = builder.Build();
app.MapGet("/health", () => "ok");
app.MapPost("/api/worker/wake", () => 1);
"""


class EndpointTests(unittest.TestCase):
    def collect(self):
        return ct.collect_endpoints([("Api/WidgetsController.cs", CONTROLLER), ("Api/Widgets.Rename.cs", PARTIAL),
                                     ("Api/Program.cs", PROGRAM)])

    def test_controller_and_minimal_routes(self):
        found = {(e.verb, e.route) for e in self.collect()}
        self.assertEqual(
            {
                ("GET", "/api/widgets"), ("GET", "/api/widgets/{id:guid}"), ("POST", "/api/widgets/login"),
                ("DELETE", "/api/other/{id}"), ("PUT", "/api/widgets/{id:guid}/rename"),
                ("GET", "/health"), ("POST", "/api/worker/wake"),
            },
            found,
        )

    def test_file_and_line_point_at_the_attribute(self):
        by = {(e.verb, e.route): e for e in self.collect()}
        endpoint = by[("POST", "/api/widgets/login")]
        self.assertEqual("Api/WidgetsController.cs", endpoint.file)
        self.assertEqual(12, endpoint.line)
        self.assertEqual("WidgetsController", endpoint.controller)


def cs_class(name, *methods, head='[Trait("Kind", "Unit")]'):
    body = "\n".join(
        f'    [Fact]\n' + (f'    [Trait("Protects", "{m[1]}")]\n' if m[1] else "") + f"    public void {m[0]}() {{ }}\n"
        for m in methods
    )
    return f"{head}\npublic class {name}\n{{\n{body}}}\n"


@unittest.skipUnless(HAS_GIT, "git is not installed")
class CheckModeTests(TempProject):
    PATH = "backend/App.Tests/FooTests.cs"

    def test_new_unmarked_test_is_an_error_old_unmarked_is_not(self):
        self.write(self.PATH, cs_class("FooTests", ("Old", None)))
        self.commit_all()
        self.write(self.PATH, cs_class("FooTests", ("Old", None), ("Fresh", None), ("FreshMarked", "Rule")))
        code, lines, _ = self.run_main()
        self.assertEqual(1, code)
        self.assertEqual(2, len(lines))
        self.assertRegex(lines[0], r"^backend/App\.Tests/FooTests\.cs:\d+ FooTests\.Fresh - new test has no protects mark")
        self.assertIn("1 errors, 2 new tests checked", lines[1].replace("tests check: ", ""))

    def test_clean_tree_exits_zero(self):
        self.write(self.PATH, cs_class("FooTests", ("Old", None)))
        self.commit_all()
        code, lines, _ = self.run_main()
        self.assertEqual(0, code)
        self.assertEqual(["tests check: 0 errors, 0 new tests checked"], lines)

    def test_new_file_untracked_makes_all_its_tests_new(self):
        self.write(self.PATH, cs_class("FooTests", ("Old", None)))
        self.commit_all()
        self.write("backend/App.Tests/BarTests.cs", cs_class("BarTests", ("A", None), ("B", "Edge")))
        code, lines, _ = self.run_main()
        self.assertEqual(1, code)
        self.assertEqual(2, len(lines))
        self.assertIn("BarTests.A", lines[0])

    def test_invalid_mark_on_an_old_test_is_an_error(self):
        self.write(self.PATH, cs_class("FooTests", ("Old", "Rules")))
        self.commit_all()
        code, lines, _ = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("invalid mark 'Rules'", lines[0])

    def test_bug_without_broke_is_an_error(self):
        self.write(self.PATH, cs_class("FooTests", ("Old", None)))
        self.commit_all()
        self.write(self.PATH, cs_class("FooTests", ("Old", None), ("B", "Bug")))
        code, lines, _ = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("Broke", lines[0])

    def test_staged_new_test_counts_and_base_ref_can_be_given(self):
        self.write(self.PATH, cs_class("FooTests", ("Old", None)))
        self.commit_all()
        self.write(self.PATH, cs_class("FooTests", ("Old", None), ("Fresh", None)))
        self.commit_all()
        self.assertEqual(0, self.run_main()[0])
        code, lines, _ = self.run_main("--base", "HEAD~1")
        self.assertEqual(1, code)
        self.assertIn("FooTests.Fresh", lines[0])

    def test_renamed_file_compares_with_its_old_path(self):
        self.write(self.PATH, cs_class("FooTests", ("Old", None)))
        self.commit_all()
        (self.root / self.PATH).rename(self.root / "backend/App.Tests/RenamedTests.cs")
        self.git("add", "-A")
        code, lines, _ = self.run_main()
        self.assertEqual(0, code, lines)

    def test_vitest_and_python_new_tests(self):
        self.write("web/src/a.test.ts", 'it("[Rule] old", () => {});\n')
        self.write("py/test_a.py", "def test_old():\n    pass\n")
        self.commit_all()
        self.write("web/src/a.test.ts", 'it("[Rule] old", () => {});\nit("new one", () => {});\n')
        self.write("py/test_a.py", "def test_old():\n    pass\n\n# protects: Edge\ndef test_new():\n    pass\n\ndef test_bad():\n    pass\n")
        code, lines, _ = self.run_main()
        self.assertEqual(1, code)
        self.assertEqual(3, len(lines))
        self.assertTrue(any("web/src/a.test.ts:2 new one" in line for line in lines))
        self.assertTrue(any("py/test_a.py:8 test_bad" in line for line in lines))

    def test_unknown_base_exits_two(self):
        self.write(self.PATH, cs_class("FooTests", ("Old", None)))
        self.commit_all()
        code, _, err = self.run_main("--base", "nope")
        self.assertEqual(2, code)
        self.assertIn("nope", err)


class DiscoveryAndProfileTests(TempProject):
    def test_pattern_discovery_and_skipped_folders(self):
        for rel in (
            "backend/App.Tests/A.cs", "backend/App/B.cs", "web/src/x.test.tsx", "web/y.spec.js", "web/z.ts",
            "web/node_modules/p/q.test.js", "py/test_a.py", "py/a.py", "py/__pycache__/test_b.py",
            "backend/App.Tests/obj/C.cs", "extra/test_skipped.py",
        ):
            self.write(rel, "")
        self.assertEqual(
            ["backend/App.Tests/A.cs", "py/test_a.py", "web/src/x.test.tsx", "web/y.spec.js"],
            ct.discover(str(self.root), ["extra"]),
        )

    def test_profile_skip_dirs_and_errors(self):
        self.write(".claude/dev-kit.md", "# P\n\n## check-tests\n\n| Setting | Value |\n|---|---|\n| skip-dirs | `a, b` |\n")
        self.assertEqual((["a", "b"], []), ct.load_profile(str(self.root)))
        self.write(".claude/dev-kit.md", "## check-tests\n\n| Setting | Value |\n|---|---|\n| bogus | 1 |\n")
        self.assertIn("unknown setting 'bogus'", ct.load_profile(str(self.root))[1][0])
        code, _, err = self.run_main()
        self.assertEqual(2, code)
        self.assertIn("bogus", err)

    def test_no_profile_is_fine(self):
        self.assertEqual(([], []), ct.load_profile(str(self.root)))


class ReportTests(TempProject):
    def build(self):
        self.write("api/Widgets.Api/WidgetsController.cs", CONTROLLER)
        self.write("api/Widgets.Api/Program.cs", PROGRAM)
        self.write(
            "api/Widgets.Tests/Jobs/ApiTests.cs",
            '[Trait("Kind", "Integration"), Trait("Domain", "Widgets")]\npublic class ApiTests\n{\n'
            '    [Fact]\n    [Trait("Protects", "Flow")]\n    public async Task A()\n    {\n'
            '        await client.GetAsync("/api/widgets");\n'
            '        await client.GetAsync($"/api/widgets/{id}?q=1");\n'
            '        await client.PostAsync("/api/widgets/" + "login", null);\n'
            '        await client.GetAsync("/health");\n    }\n\n'
            '    [Fact]\n    public void B() { }\n}\n',
        )
        self.write(
            "api/Widgets.Tests/UnitTests.cs",
            '[Trait("Kind", "Unit")]\npublic class UnitTests\n{\n    [Fact]\n    [Trait("Protects", "Rule")]\n'
            '    public void U() { var s = "/api/widgets/{id}/rename"; }\n}\n',
        )

    def test_counts_by_domain_mark_and_level(self):
        self.build()
        report = ct.build_report(ct.load_tests(str(self.root)))
        self.assertEqual(3, report["total"]["tests"])
        widgets = report["domains"]["Widgets"]
        self.assertEqual(2, widgets["tests"])
        self.assertEqual(1, widgets["marks"]["Flow"])
        self.assertEqual(1, widgets["marks"]["none"])
        self.assertEqual({"Integration": 2}, widgets["levels"])
        self.assertEqual({"Unit": 1}, report["domains"]["-"]["levels"])

    def test_endpoint_coverage_uses_integration_files_only(self):
        self.build()
        tests = ct.load_tests(str(self.root))
        endpoints = {(e.verb, e.route): e.covered for e in ct.endpoint_coverage(str(self.root), tests)}
        self.assertTrue(endpoints[("GET", "/api/widgets")])
        self.assertTrue(endpoints[("GET", "/api/widgets/{id:guid}")])
        self.assertTrue(endpoints[("POST", "/api/widgets/login")])
        self.assertTrue(endpoints[("GET", "/health")])
        self.assertFalse(endpoints[("DELETE", "/api/other/{id}")])
        self.assertFalse(endpoints[("POST", "/api/worker/wake")])

    def test_report_text_and_json(self):
        self.build()
        code, lines, _ = self.run_main("--report")
        self.assertEqual(0, code)
        text = "\n".join(lines)
        self.assertIn("domain", text)
        self.assertIn("Widgets", text)
        self.assertIn("4 of 6 endpoints have an integration test", text)
        self.assertIn("DELETE /api/other/{id}", text)
        code, lines, _ = self.run_main("--report", "--json")
        self.assertEqual(0, code)
        data = json.loads("\n".join(lines))
        self.assertEqual(3, data["total"]["tests"])
        self.assertEqual(6, data["endpoints"]["total"])
        self.assertEqual(4, data["endpoints"]["covered"])

    def test_without_kind_traits_files_using_httpclient_count(self):
        self.write("api/W.Api/C.cs", '[Route("x")]\nclass C : ControllerBase\n{\n    [HttpGet("a")]\n    void A() { }\n}\n')
        self.write(
            "api/W.Tests/T.cs",
            'class T\n{\n    HttpClient c;\n    [Fact]\n    void X() { c.GetAsync("/x/a"); }\n}\n',
        )
        self.write("api/W.Tests/U.cs", 'class U\n{\n    [Fact]\n    void Y() { var s = "/x/a"; }\n}\n')
        tests = ct.load_tests(str(self.root))
        files, _ = ct.integration_files(str(self.root), tests)
        self.assertEqual(["api/W.Tests/T.cs"], files)

    def test_json_needs_report(self):
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                ct.main(["--root", str(self.root), "--json"])


class ShimTests(unittest.TestCase):
    def test_shim_runs_the_script(self):
        result = subprocess.run([sys.executable, str(SHIM), "--help"], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("--report", result.stdout)


if __name__ == "__main__":
    unittest.main()
