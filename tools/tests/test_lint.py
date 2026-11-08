import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import lint  # noqa: E402

CORE_SLOTS = """# Slots

| Slot | What it must do |
|---|---|
| run-tests | Run tests |
| check-ui | Check a scenario |
"""

EXTENSION_SLOTS = """| Slot | Skill |
|---|---|
| check-ui | `web-kit:e2e-check` |
"""

PROFILE = """## All agents

Read the docs.

## Slots

| Slot | Skill or command |
|---|---|
| run-tests | `dotnet test` |
| check-ui | `web-kit:e2e-check` |

## coder

Rules.
"""


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def skill_text(description="Use when something happens", name=None):
    name_line = f"name: {name}\n" if name else ""
    return f"---\n{name_line}description: {description}\n---\n\nBody\n"


def agent_text(name="coder", model="sonnet", description="Writes code"):
    lines = [f"name: {name}"]
    if description is not None:
        lines.append(f"description: {description}")
    if model is not None:
        lines.append(f"model: {model}")
    return "---\n" + "\n".join(lines) + "\n---\n\nBody\n"


class LintTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.projects_dir = Path(self.tmp.name) / "projects"
        self.build_repo()

    def build_repo(self):
        entries = [{"name": name, "source": f"./plugins/{name}"} for name in ("dev-kit", "web-kit")]
        write(self.root / ".claude-plugin" / "marketplace.json", json.dumps({"name": "m", "plugins": entries}))
        for name in ("dev-kit", "web-kit"):
            write(self.root / "plugins" / name / ".claude-plugin" / "plugin.json", json.dumps({"name": name}))
        write(self.root / "plugins" / "dev-kit" / "slots.md", CORE_SLOTS)
        write(self.root / "plugins" / "dev-kit" / "agents" / "coder.md", agent_text())
        write(self.root / "plugins" / "dev-kit" / "skills" / "manager" / "SKILL.md", skill_text(name="manager"))
        write(self.root / "plugins" / "web-kit" / "slots.md", EXTENSION_SLOTS)
        write(self.root / "plugins" / "web-kit" / "skills" / "e2e-check" / "SKILL.md", skill_text())

    def set_marketplace(self, data):
        write(self.root / ".claude-plugin" / "marketplace.json", json.dumps(data))

    def register_plugin(self, name):
        path = self.root / ".claude-plugin" / "marketplace.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["plugins"].append({"name": name, "source": f"./plugins/{name}"})
        self.set_marketplace(data)
        write(self.root / "plugins" / name / ".claude-plugin" / "plugin.json", json.dumps({"name": name}))

    def add_profile(self, text=PROFILE, project="Demo"):
        write(self.projects_dir / project / ".claude" / "dev-kit.md", text)
        return {project: str(self.projects_dir / project)}

    def run_lint(self, projects=None):
        return lint.lint(self.root, {} if projects is None else projects)

    def messages(self, findings, level):
        return [f"{path}: {message}" for item_level, path, message in findings.items if item_level == level]

    def assertErrorContains(self, findings, text):
        errors = self.messages(findings, "error")
        self.assertTrue(any(text in error for error in errors), f"no error with '{text}' in {errors}")

    def assertClean(self, findings):
        self.assertEqual([], findings.items)


class MarketplaceTests(LintTestCase):
    def test_clean_repo_passes(self):
        self.assertClean(self.run_lint(self.add_profile()))

    def test_entry_name_mismatch_fails(self):
        write(self.root / "plugins" / "web-kit" / ".claude-plugin" / "plugin.json", json.dumps({"name": "other"}))
        self.assertErrorContains(self.run_lint(), "name 'other' differs from marketplace entry 'web-kit'")

    def test_missing_manifest_fails(self):
        (self.root / "plugins" / "web-kit" / ".claude-plugin" / "plugin.json").unlink()
        self.assertErrorContains(
            self.run_lint(), "plugin web-kit: plugins/web-kit/.claude-plugin/plugin.json not found"
        )

    def test_invalid_manifest_json_fails(self):
        write(self.root / "plugins" / "web-kit" / ".claude-plugin" / "plugin.json", "{")
        self.assertErrorContains(self.run_lint(), "plugins/web-kit/.claude-plugin/plugin.json: invalid JSON")

    def test_invalid_marketplace_json_fails(self):
        write(self.root / ".claude-plugin" / "marketplace.json", "{")
        self.assertErrorContains(self.run_lint(), "marketplace.json: invalid JSON")

    def test_bom_in_marketplace_is_accepted(self):
        path = self.root / ".claude-plugin" / "marketplace.json"
        write_bytes(path, b"\xef\xbb\xbf" + path.read_bytes())
        self.assertClean(self.run_lint())

    def test_missing_marketplace_fails(self):
        (self.root / ".claude-plugin" / "marketplace.json").unlink()
        self.assertErrorContains(self.run_lint(), "marketplace.json: cannot read file")

    def test_missing_plugins_list_fails(self):
        self.set_marketplace({"name": "m"})
        self.assertErrorContains(self.run_lint(), "plugins list is missing or empty")

    def test_empty_plugins_list_fails(self):
        self.set_marketplace({"name": "m", "plugins": []})
        self.assertErrorContains(self.run_lint(), "plugins list is missing or empty")

    def test_non_string_source_fails_without_crash(self):
        self.set_marketplace({"plugins": [{"name": "dev-kit", "source": 5}, {"name": "web-kit", "source": "./plugins/web-kit"}]})
        self.assertErrorContains(self.run_lint(), "plugin dev-kit: source must be a non-empty string")

    def test_entry_that_is_not_an_object_fails(self):
        self.set_marketplace({"plugins": ["dev-kit"]})
        self.assertErrorContains(self.run_lint(), "plugin entry must be an object")

    def test_duplicate_entry_name_fails(self):
        self.register_plugin("web-kit")
        self.assertErrorContains(self.run_lint(), "plugin 'web-kit' is listed twice")

    def test_folder_without_marketplace_entry_fails(self):
        write(self.root / "plugins" / "stray" / "slots.md", "text")
        self.assertErrorContains(self.run_lint(), "plugins/stray: folder is not referenced")


class SkillTests(LintTestCase):
    def test_description_without_use_when_fails(self):
        write(self.root / "plugins" / "dev-kit" / "skills" / "bad" / "SKILL.md", skill_text("Runs the tests"))
        self.assertErrorContains(self.run_lint(), "must start with 'Use when'")

    def test_quoted_description_is_accepted(self):
        write(self.root / "plugins" / "dev-kit" / "skills" / "quoted" / "SKILL.md", skill_text('"Use when quoted"'))
        self.assertClean(self.run_lint())

    def test_empty_description_fails(self):
        write(self.root / "plugins" / "dev-kit" / "skills" / "empty" / "SKILL.md", "---\ndescription:\n---\n")
        self.assertErrorContains(self.run_lint(), "description is missing or empty")

    def test_name_differing_from_folder_fails(self):
        write(self.root / "plugins" / "dev-kit" / "skills" / "folder" / "SKILL.md", skill_text(name="other"))
        self.assertErrorContains(self.run_lint(), "differs from folder")

    def test_missing_frontmatter_fails(self):
        write(self.root / "plugins" / "dev-kit" / "skills" / "plain" / "SKILL.md", "Just text\n")
        self.assertErrorContains(self.run_lint(), "missing or unclosed frontmatter")

    def test_unclosed_frontmatter_fails(self):
        write(self.root / "plugins" / "dev-kit" / "skills" / "open" / "SKILL.md", "---\ndescription: Use when x\n")
        self.assertErrorContains(self.run_lint(), "skills/open/SKILL.md: missing or unclosed frontmatter")

    def test_folder_without_skill_file_fails(self):
        (self.root / "plugins" / "dev-kit" / "skills" / "empty-folder").mkdir()
        self.assertErrorContains(self.run_lint(), "skills/empty-folder: SKILL.md not found")

    def test_bom_in_skill_is_accepted(self):
        data = b"\xef\xbb\xbf" + skill_text().encode("utf-8")
        write_bytes(self.root / "plugins" / "dev-kit" / "skills" / "bom" / "SKILL.md", data)
        self.assertClean(self.run_lint())

    def test_undecodable_skill_is_reported_and_linting_continues(self):
        write_bytes(self.root / "plugins" / "dev-kit" / "skills" / "binary" / "SKILL.md", b"---\n\xff\xfe\n---\n")
        write(self.root / "plugins" / "dev-kit" / "skills" / "bad" / "SKILL.md", skill_text("Runs"))
        findings = self.run_lint()
        self.assertErrorContains(findings, "skills/binary/SKILL.md: not valid UTF-8")
        self.assertErrorContains(findings, "skills/bad/SKILL.md: description must start")


class AgentTests(LintTestCase):
    def test_missing_model_fails(self):
        write(self.root / "plugins" / "dev-kit" / "agents" / "coder.md", agent_text(model=None))
        self.assertErrorContains(self.run_lint(), "model is missing")

    def test_empty_model_fails(self):
        write(self.root / "plugins" / "dev-kit" / "agents" / "coder.md", agent_text(model=""))
        self.assertErrorContains(self.run_lint(), "model is missing or empty")

    def test_missing_description_fails(self):
        write(self.root / "plugins" / "dev-kit" / "agents" / "coder.md", agent_text(description=None))
        self.assertErrorContains(self.run_lint(), "description is missing")

    def test_name_differing_from_file_stem_fails(self):
        write(self.root / "plugins" / "dev-kit" / "agents" / "coder.md", agent_text(name="programmer"))
        self.assertErrorContains(self.run_lint(), "differs from file name")

    def test_nested_agent_is_checked(self):
        write(self.root / "plugins" / "dev-kit" / "agents" / "team" / "tester.md", agent_text(name="x"))
        self.assertErrorContains(self.run_lint(), "team/tester.md")

    def test_undecodable_agent_is_reported(self):
        write_bytes(self.root / "plugins" / "dev-kit" / "agents" / "coder.md", b"\xff\xfe")
        self.assertErrorContains(self.run_lint(), "agents/coder.md: not valid UTF-8")

    def test_unclosed_frontmatter_fails(self):
        write(self.root / "plugins" / "dev-kit" / "agents" / "coder.md", "---\nname: coder\n")
        self.assertErrorContains(self.run_lint(), "agents/coder.md: missing or unclosed frontmatter")


class HookTests(LintTestCase):
    def test_valid_hooks_json_passes(self):
        write(self.root / "plugins" / "dev-kit" / "hooks" / "hooks.json", json.dumps({"hooks": {}}))
        self.assertClean(self.run_lint())

    def test_invalid_hooks_json_fails(self):
        write(self.root / "plugins" / "dev-kit" / "hooks" / "hooks.json", "{")
        self.assertErrorContains(self.run_lint(), "plugins/dev-kit/hooks/hooks.json: invalid JSON")

    def test_hooks_folder_without_hooks_json_is_fine(self):
        write(self.root / "plugins" / "dev-kit" / "hooks" / "script.py", "print(1)")
        self.assertClean(self.run_lint())


class SlotTests(LintTestCase):
    def test_core_slot_not_kebab_case_fails(self):
        write(self.root / "plugins" / "dev-kit" / "slots.md", CORE_SLOTS + "| Run_App | Start |\n")
        self.assertErrorContains(self.run_lint(), "not kebab-case")

    def test_core_slot_duplicate_fails(self):
        write(self.root / "plugins" / "dev-kit" / "slots.md", CORE_SLOTS + "| run-tests | Again |\n")
        self.assertErrorContains(self.run_lint(), "listed twice")

    def test_core_wrong_header_fails(self):
        write(self.root / "plugins" / "dev-kit" / "slots.md", CORE_SLOTS.replace("What it must do", "Purpose"))
        self.assertErrorContains(self.run_lint(), "table with header '| Slot | What it must do |'")

    def test_core_missing_separator_fails(self):
        write(self.root / "plugins" / "dev-kit" / "slots.md", CORE_SLOTS.replace("|---|---|\n", ""))
        self.assertErrorContains(self.run_lint(), "table with header '| Slot | What it must do |'")

    def test_core_file_missing_fails(self):
        (self.root / "plugins" / "dev-kit" / "slots.md").unlink()
        self.assertErrorContains(self.run_lint(), "slots.md: core slots file not found")

    def test_core_file_undecodable_is_reported(self):
        write_bytes(self.root / "plugins" / "dev-kit" / "slots.md", b"\xff\xfe")
        self.assertErrorContains(self.run_lint(), "dev-kit/slots.md: not valid UTF-8")

    def test_core_only_first_table_counts(self):
        text = CORE_SLOTS + "\nMore:\n\n| Slot | What it must do |\n|---|---|\n| Bad_Slot | x |\n"
        write(self.root / "plugins" / "dev-kit" / "slots.md", text)
        self.assertClean(self.run_lint())

    def test_core_table_inside_fence_is_ignored(self):
        text = "```\n| Slot | Other |\n|---|---|\n| Bad_Slot | x |\n```\n\n" + CORE_SLOTS
        write(self.root / "plugins" / "dev-kit" / "slots.md", text)
        self.assertClean(self.run_lint())

    def test_bom_in_slots_file_is_accepted(self):
        table_only = CORE_SLOTS.split("\n", 2)[2]
        write_bytes(self.root / "plugins" / "dev-kit" / "slots.md", b"\xef\xbb\xbf" + table_only.encode("utf-8"))
        self.assertClean(self.run_lint())

    def test_extension_slot_not_in_core_fails(self):
        write(self.root / "plugins" / "web-kit" / "slots.md", EXTENSION_SLOTS + "| show-idea | `web-kit:e2e-check` |\n")
        self.assertErrorContains(self.run_lint(), "'show-idea' is not in the core list")

    def test_extension_skill_missing_fails(self):
        write(self.root / "plugins" / "web-kit" / "slots.md", EXTENSION_SLOTS.replace("e2e-check", "ghost"))
        self.assertErrorContains(self.run_lint(), "does not exist")

    def test_extension_skill_is_case_sensitive(self):
        write(self.root / "plugins" / "web-kit" / "slots.md", EXTENSION_SLOTS.replace("e2e-check", "E2E-Check"))
        self.assertErrorContains(self.run_lint(), "does not exist")

    def test_extension_plugin_not_in_marketplace_fails(self):
        write(self.root / "plugins" / "web-kit" / "slots.md", EXTENSION_SLOTS.replace("web-kit:", "unity-kit:"))
        self.assertErrorContains(self.run_lint(), "must be <plugin>:<skill>")

    def test_extension_wrong_header_fails(self):
        write(self.root / "plugins" / "web-kit" / "slots.md", EXTENSION_SLOTS.replace("Skill", "Command"))
        self.assertErrorContains(self.run_lint(), "table with header '| Slot | Skill |'")

    def test_empty_extension_table_is_fine(self):
        write(self.root / "plugins" / "web-kit" / "slots.md", "| Slot | Skill |\n|---|---|\n")
        self.assertClean(self.run_lint())

    def test_slot_filled_twice_warns(self):
        self.register_plugin("extra-kit")
        write(self.root / "plugins" / "extra-kit" / "slots.md", EXTENSION_SLOTS)
        findings = self.run_lint()
        self.assertEqual(0, findings.count("error"), findings.items)
        self.assertEqual(1, findings.count("warning"))


class ProfileTests(LintTestCase):
    def test_missing_profile_only_warns(self):
        findings = self.run_lint({"Ghost": str(self.projects_dir / "Ghost")})
        self.assertEqual(0, findings.count("error"))
        self.assertEqual(1, findings.count("warning"))

    def test_unknown_slot_fails(self):
        profile = PROFILE.replace("| run-tests |", "| run-everything |")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "'run-everything' is not in the core list")

    def test_unknown_reference_fails(self):
        profile = PROFILE.replace("`web-kit:e2e-check`", "`web-kit:ghost`")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "not a skill or agent of web-kit")

    def test_agent_reference_is_accepted(self):
        profile = PROFILE.replace("`web-kit:e2e-check`", "`dev-kit:coder`")
        self.assertClean(self.run_lint(self.add_profile(profile)))

    def test_leading_slash_reference_is_checked(self):
        profile = PROFILE.replace("`web-kit:e2e-check`", "`/web-kit:ghost`")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "not a skill or agent of web-kit")

    def test_leading_slash_reference_is_accepted(self):
        profile = PROFILE.replace("`web-kit:e2e-check`", "`/web-kit:e2e-check`")
        self.assertClean(self.run_lint(self.add_profile(profile)))

    def test_plugin_prefix_without_name_fails(self):
        profile = PROFILE.replace("`web-kit:e2e-check`", "`web-kit:`")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "must be written as <plugin>:<name>")

    def test_plugin_prefix_with_slash_fails(self):
        profile = PROFILE.replace("`web-kit:e2e-check`", "`web-kit/e2e-check`")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "must be written as <plugin>:<name>")

    def test_empty_value_fails(self):
        profile = PROFILE.replace("`dotnet test`", "")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "slot with an empty value")

    def test_command_value_is_not_checked(self):
        profile = PROFILE.replace("`dotnet test`", "`powershell -File tools/test.ps1`")
        self.assertClean(self.run_lint(self.add_profile(profile)))

    def test_unknown_plugin_value_is_a_command(self):
        profile = PROFILE.replace("`dotnet test`", "`other:thing`")
        self.assertClean(self.run_lint(self.add_profile(profile)))

    def test_slots_table_wrong_header_fails(self):
        profile = PROFILE.replace("Skill or command", "Skill")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "Slots table with header")

    def test_slots_section_without_table_fails(self):
        profile = "## Slots\n\nNothing here.\n"
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "Slots table with header")

    def test_profile_without_slots_section_is_fine(self):
        self.assertClean(self.run_lint(self.add_profile("## All agents\n\nRead the docs.\n")))

    def test_unknown_section_fails(self):
        profile = PROFILE + "\n## ghost\n\nRules.\n"
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "section 'ghost' names no agent or skill")

    def test_misspelled_slots_heading_fails(self):
        profile = PROFILE.replace("## Slots", "## Slot")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "section 'Slot' names no agent or skill")

    def test_misspelled_agent_heading_fails(self):
        profile = PROFILE.replace("## coder", "## codr")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "section 'codr'")

    def test_heading_is_case_sensitive(self):
        profile = PROFILE.replace("## coder", "## Coder")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "section 'Coder'")

    def test_skill_heading_is_accepted(self):
        self.assertClean(self.run_lint(self.add_profile(PROFILE + "\n## e2e-check\n\nRules.\n")))

    def test_qualified_heading_is_accepted(self):
        self.assertClean(self.run_lint(self.add_profile(PROFILE.replace("## coder", "## dev-kit:coder"))))

    def test_qualified_heading_must_exist_in_that_plugin(self):
        profile = PROFILE.replace("## coder", "## web-kit:coder")
        self.assertErrorContains(self.run_lint(self.add_profile(profile)), "section 'web-kit:coder'")

    def test_cyrillic_heading_is_reported(self):
        findings = self.run_lint(self.add_profile(PROFILE + "\n## Страва\n"))
        self.assertErrorContains(findings, "section 'Страва'")

    def test_headings_and_tables_in_fences_are_ignored(self):
        fenced = "```\n## ghost\n\n## Slots\n\n| Slot | Other |\n|---|---|\n| bad | x |\n```\n\n"
        self.assertClean(self.run_lint(self.add_profile(fenced + PROFILE)))

    def test_bom_in_profile_does_not_hide_the_first_heading(self):
        profile = "## ghost\n\nRules.\n"
        write_bytes(self.projects_dir / "Demo" / ".claude" / "dev-kit.md", b"\xef\xbb\xbf" + profile.encode("utf-8"))
        findings = self.run_lint({"Demo": str(self.projects_dir / "Demo")})
        self.assertErrorContains(findings, "section 'ghost'")

    def test_undecodable_profile_is_reported(self):
        write_bytes(self.projects_dir / "Demo" / ".claude" / "dev-kit.md", b"\xff\xfe")
        findings = self.run_lint({"Demo": str(self.projects_dir / "Demo")})
        self.assertErrorContains(findings, "dev-kit.md: not valid UTF-8")


class ProfileTableTests(LintTestCase):
    MANAGER = """## manager

| Task | Skill |
|---|---|
| Plan a step | `dev-kit:manager`, `own-skill` |

| Type | Model | When | Returns |
|---|---|---|---|
| `own-agent`, `dev-kit:coder` | sonnet | a lot of code | the change |
"""
    FIX_BUG = """## fix-bug

| The report sounds like... | It is a... | UI check, if authorized |
|---|---|---|
| a job is stuck | pipeline bug | job row |
"""

    def setUp(self):
        super().setUp()
        write(self.root / "plugins" / "dev-kit" / "skills" / "fix-bug" / "SKILL.md", skill_text(name="fix-bug"))

    def profile(self, extra):
        return self.add_profile(PROFILE + "\n" + extra)

    def test_valid_manager_and_fix_bug_tables_pass(self):
        self.assertClean(self.run_lint(self.profile(self.MANAGER + "\n" + self.FIX_BUG)))

    def test_manager_section_without_tables_is_fine(self):
        self.assertClean(self.run_lint(self.profile("## manager\n\nOpus only for large changes.\n")))

    def test_manager_table_with_wrong_header_fails(self):
        findings = self.run_lint(self.profile(self.MANAGER.replace("| Task | Skill |", "| Job | Skill |")))
        self.assertErrorContains(findings, "section 'manager': table must have header | Task | Skill |")

    def test_manager_table_without_separator_fails(self):
        manager = self.MANAGER.replace("| Task | Skill |\n|---|---|\n", "| Task | Skill |\n")
        self.assertErrorContains(self.run_lint(self.profile(manager)), "section 'manager': table must have header")

    def test_manager_row_with_missing_cell_fails(self):
        row = "| `own-agent`, `dev-kit:coder` | sonnet | a lot of code | the change |"
        manager = self.MANAGER.replace(row, "| `own-agent` | sonnet |")
        self.assertErrorContains(self.run_lint(self.profile(manager)), "row 'own-agent' has 2 cells, expected 4")

    def test_manager_unknown_plugin_skill_fails(self):
        manager = self.MANAGER.replace("`dev-kit:manager`", "`dev-kit:ghost`")
        self.assertErrorContains(self.run_lint(self.profile(manager)), "'dev-kit:ghost' is not a skill or agent of dev-kit")

    def test_manager_unknown_plugin_agent_fails(self):
        manager = self.MANAGER.replace("`dev-kit:coder`", "`dev-kit:ghost`")
        self.assertErrorContains(self.run_lint(self.profile(manager)), "'dev-kit:ghost' is not a skill or agent of dev-kit")

    def test_manager_table_in_a_fence_is_ignored(self):
        fenced = "```\n## manager\n\n| Bad | Header |\n|---|---|\n```\n\n"
        self.assertClean(self.run_lint(self.profile(fenced + self.MANAGER)))

    def test_fix_bug_table_with_wrong_header_fails(self):
        findings = self.run_lint(self.profile(self.FIX_BUG.replace("It is a...", "Kind")))
        self.assertErrorContains(findings, "section 'fix-bug': table must have header")

    def test_other_sections_tables_are_not_checked(self):
        self.assertClean(self.run_lint(self.profile("## e2e-check\n\n| Any | Header |\n|---|---|\n| a | b |\n")))


class ProjectsFileTests(LintTestCase):
    def test_invalid_projects_json_is_reported_and_linting_continues(self):
        write(self.root / "tools" / "projects.json", "{")
        write(self.root / "plugins" / "dev-kit" / "skills" / "bad" / "SKILL.md", skill_text("Runs"))
        findings = lint.lint(self.root)
        self.assertErrorContains(findings, "tools/projects.json: invalid JSON")
        self.assertErrorContains(findings, "skills/bad/SKILL.md")

    def test_undecodable_projects_json_is_reported(self):
        write_bytes(self.root / "tools" / "projects.json", b"\xff\xfe")
        self.assertErrorContains(lint.lint(self.root), "tools/projects.json: not valid UTF-8")

    def test_projects_json_is_read_when_no_mapping_is_passed(self):
        write(self.root / "tools" / "projects.json", json.dumps({"Ghost": str(self.projects_dir / "Ghost")}))
        findings = lint.lint(self.root)
        self.assertEqual(0, findings.count("error"))
        self.assertEqual(1, findings.count("warning"))

    def test_non_string_folder_is_reported(self):
        write(self.root / "tools" / "projects.json", json.dumps({"Ghost": 5}))
        self.assertErrorContains(lint.lint(self.root), "project 'Ghost': folder must be a string")

    def test_bom_in_projects_json_is_accepted(self):
        data = b"\xef\xbb\xbf" + json.dumps({}).encode("utf-8")
        write_bytes(self.root / "tools" / "projects.json", data)
        self.assertClean(lint.lint(self.root))


DOCUMENTATION = """
## documentation

| Setting | Value |
|---|---|
| scan | `backend: .cs` |
| code-root | `backend 3` |
| area-alias | `src/ -> frontend/src/` |
| skip-dirs | `data, logs` |
| size-limit | `200` |
"""


class DocumentationSettingsTests(LintTestCase):
    def setUp(self):
        super().setUp()
        write(self.root / "plugins" / "dev-kit" / "skills" / "documentation" / "SKILL.md", skill_text(name="documentation"))

    def profile_with(self, documentation):
        return self.run_lint(self.add_profile(PROFILE + documentation))

    def test_valid_table_passes(self):
        self.assertClean(self.profile_with(DOCUMENTATION))

    def test_profile_without_the_section_is_fine(self):
        self.assertClean(self.run_lint(self.add_profile()))

    def test_unknown_setting_fails(self):
        findings = self.profile_with(DOCUMENTATION + "| ghost | `x` |\n")
        self.assertErrorContains(findings, "documentation section: unknown setting 'ghost'")

    def test_bad_value_shape_fails(self):
        findings = self.profile_with(DOCUMENTATION.replace("`backend 3`", "`backend`"))
        self.assertErrorContains(findings, "documentation section: setting 'code-root': expected '<folder> <depth>'")

    def test_limit_must_be_a_number(self):
        findings = self.profile_with(DOCUMENTATION.replace("`200`", "`many`"))
        self.assertErrorContains(findings, "setting 'size-limit': expected a whole number")

    def test_scan_needs_extensions_with_a_dot(self):
        findings = self.profile_with(DOCUMENTATION.replace("`backend: .cs`", "`backend: cs`"))
        self.assertErrorContains(findings, "'cs' is not an extension")

    def test_alias_needs_an_arrow(self):
        findings = self.profile_with(DOCUMENTATION.replace("`src/ -> frontend/src/`", "`src/`"))
        self.assertErrorContains(findings, "setting 'area-alias': expected '<prefix> -> <replacement>'")

    def test_single_setting_twice_fails(self):
        findings = self.profile_with(DOCUMENTATION + "| size-limit | `300` |\n")
        self.assertErrorContains(findings, "setting 'size-limit' is set twice")

    def test_wrong_header_fails(self):
        findings = self.profile_with(DOCUMENTATION.replace("| Setting | Value |", "| Name | Value |"))
        self.assertErrorContains(findings, "documentation table with header '| Setting | Value |'")

    def test_section_without_a_table_fails(self):
        findings = self.profile_with("\n## documentation\n\nNothing here.\n")
        self.assertErrorContains(findings, "documentation table with header")

    def test_wrong_case_heading_fails(self):
        findings = self.run_lint(self.add_profile(PROFILE + DOCUMENTATION.replace("## documentation", "## Documentation")))
        self.assertErrorContains(findings, "heading '## Documentation' must be written '## documentation'")

    def test_row_without_a_value_fails(self):
        findings = self.profile_with(DOCUMENTATION + "| skip-dirs | |\n")
        self.assertErrorContains(findings, "needs a setting and a value")

    def test_table_in_a_fence_is_ignored(self):
        fenced = "\n```\n## documentation\n\n| Setting | Value |\n|---|---|\n| ghost | x |\n```\n"
        self.assertClean(self.run_lint(self.add_profile(PROFILE + fenced)))

    def test_heading_needs_the_documentation_skill(self):
        shutil.rmtree(self.root / "plugins" / "dev-kit" / "skills" / "documentation")
        findings = self.profile_with(DOCUMENTATION)
        self.assertErrorContains(findings, "section 'documentation' names no agent or skill")


class ParsingTests(unittest.TestCase):
    def test_parse_table_takes_only_the_first_table(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |\n\n| C | D |\n|---|---|\n| 3 | 4 |\n"
        self.assertEqual((["A", "B"], [["1", "2"]]), lint.parse_table(text))

    def test_parse_table_strips_backticks(self):
        self.assertEqual((["A", "B"], [["x", "y z"]]), lint.parse_table("| A | B |\n|---|---|\n| `x` | `y z` |\n"))

    def test_parse_table_skips_fenced_blocks(self):
        text = "```\n| X | Y |\n|---|---|\n```\n| A | B |\n|---|---|\n"
        self.assertEqual((["A", "B"], []), lint.parse_table(text))

    def test_parse_table_without_separator_is_none(self):
        self.assertIsNone(lint.parse_table("| A | B |\n| 1 | 2 |\n"))

    def test_parse_table_without_table_is_none(self):
        self.assertIsNone(lint.parse_table("Just text\n"))

    def test_headings_ignore_fenced_blocks(self):
        self.assertEqual(["Real"], lint.headings("```\n## Fake\n```\n## Real\n"))

    def test_section_ignores_fenced_blocks(self):
        text = "## Slots\n\n```\n## Other\n```\ntext\n## Next\n"
        self.assertEqual("text", lint.section(text, "Slots").strip())


class CommandLineTests(LintTestCase):
    def test_non_ascii_output_survives_a_legacy_console_encoding(self):
        tools = self.root / "tools"
        tools.mkdir(exist_ok=True)
        shutil.copy(Path(lint.__file__), tools / "lint.py")
        scripts = self.root / "plugins" / "dev-kit" / "scripts"
        scripts.mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(lint.check_docs.__file__), scripts / "check_docs.py")
        self.add_profile(PROFILE + "\n## Страва\n")
        write(tools / "projects.json", json.dumps({"Demo": str(self.projects_dir / "Demo")}))
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        env.pop("PYTHONUTF8", None)
        result = subprocess.run([sys.executable, str(tools / "lint.py")], capture_output=True, env=env)
        self.assertNotIn(b"Traceback", result.stderr)
        self.assertEqual(1, result.returncode)
        self.assertIn("section 'Страва'", result.stdout.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
