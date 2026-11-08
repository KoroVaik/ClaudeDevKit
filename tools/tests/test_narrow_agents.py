import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "dev-kit" / "hooks" / "narrow-agents.py"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def settings(**plugins):
    return json.dumps({"enabledPlugins": plugins})


class NarrowAgentsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.project = base / "project"
        self.home = base / "home"
        self.plugins = base / "plugins"
        self.plugin_root = self.plugins / "dev-kit"
        write(self.project / ".claude" / "agents" / "local-coder.md", "x")
        write(self.plugin_root / "agents" / "coder.md", "x")
        write(self.plugins / "web-kit" / "agents" / "layout.md", "x")
        self.home.mkdir()

    def run_hook(self, kind, project_env=True, **extra_input):
        # Path.home() reads USERPROFILE on Windows and HOME elsewhere, so both point to the fake home.
        env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_")}
        env.update({"USERPROFILE": str(self.home), "HOME": str(self.home), "CLAUDE_PLUGIN_ROOT": str(self.plugin_root)})
        if project_env:
            env["CLAUDE_PROJECT_DIR"] = str(self.project)
        call = {"tool_input": {"subagent_type": kind}, "cwd": str(self.project), **extra_input}
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(call).encode("utf-8"),
                                capture_output=True, env=env)
        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", "replace"))
        return result.stdout.decode("utf-8")

    def assertAllowed(self, kind, **kwargs):
        self.assertEqual("", self.run_hook(kind, **kwargs))

    def assertDenied(self, kind, **kwargs):
        output = json.loads(self.run_hook(kind, **kwargs))["hookSpecificOutput"]
        self.assertEqual("PreToolUse", output["hookEventName"])
        self.assertEqual("deny", output["permissionDecision"])
        return output["permissionDecisionReason"]

    def enable(self, scope, **plugins):
        paths = {
            "user": self.home / ".claude" / "settings.json",
            "project": self.project / ".claude" / "settings.json",
            "local": self.project / ".claude" / "settings.local.json",
        }
        write(paths[scope], settings(**plugins))

    def install(self, key, agents, scope="project", project_path="same", folder="cache"):
        """Record a plugin install in the fake installed_plugins.json (several entries per key accumulate)."""
        path = self.home / ".claude" / "plugins" / "installed_plugins.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"version": 2, "plugins": {}}
        install_dir = Path(self.tmp.name) / folder / key.replace("@", "-") / scope
        for agent in agents:
            write(install_dir / "agents" / f"{agent}.md", "x")
        install_dir.mkdir(parents=True, exist_ok=True)
        entry = {"scope": scope, "installPath": str(install_dir)}
        if scope in ("project", "local"):
            entry["projectPath"] = str(self.project) if project_path == "same" else project_path
        data["plugins"].setdefault(key, []).append(entry)
        write(path, json.dumps(data))

    def use_cache_layout(self):
        """CLAUDE_PLUGIN_ROOT inside a cache folder, where no sibling plugin folders exist."""
        self.plugin_root = Path(self.tmp.name) / "cache" / "korov-dev" / "dev-kit" / "0.1.0"
        self.plugin_root.mkdir(parents=True)

    def add_marketplace(self, marketplace, kind, agents, plugin="dev-kit", source="./plugins/dev-kit"):
        """Record a marketplace in the fake known_marketplaces.json; a directory one also gets its source folder."""
        path = self.home / ".claude" / "plugins" / "known_marketplaces.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        location = Path(self.tmp.name) / "marketplaces" / marketplace
        for agent in agents:
            write(location / source / "agents" / f"{agent}.md", "x")
        write(location / ".claude-plugin" / "marketplace.json",
              json.dumps({"name": marketplace, "plugins": [{"name": plugin, "source": source}]}))
        data[marketplace] = {"source": {"source": kind, "path": str(location)}, "installLocation": str(location)}
        write(path, json.dumps(data))

    def test_directory_marketplace_wins_over_stale_installed_entry(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["stale"])
        self.add_marketplace("korov-dev", "directory", ["fresh"])
        self.assertAllowed("dev-kit:fresh")
        self.assertDenied("dev-kit:stale")

    def test_non_directory_marketplace_still_uses_installed_entry(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["installed"])
        self.add_marketplace("korov-dev", "github", ["from-source"])
        self.assertAllowed("dev-kit:installed")
        self.assertDenied("dev-kit:from-source")

    def test_broken_known_marketplaces_falls_through(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["installed"])
        write(self.home / ".claude" / "plugins" / "known_marketplaces.json", "{")
        self.assertAllowed("dev-kit:installed")
        self.assertDenied("dev-kit:ghost")

    def test_directory_marketplace_without_the_plugin_falls_through(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["installed"])
        self.add_marketplace("korov-dev", "directory", ["x"], plugin="other-kit")
        self.assertAllowed("dev-kit:installed")

    def test_directory_marketplace_with_non_relative_source_falls_through(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["installed"])
        self.add_marketplace("korov-dev", "directory", ["x"], source="github")
        self.assertAllowed("dev-kit:installed")

    def test_installed_project_entry_limits_agents(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["coder"])
        self.assertAllowed("dev-kit:coder")
        self.assertIn("dev-kit:coder", self.assertDenied("dev-kit:ghost"))

    def test_installed_entry_for_another_project_is_ignored(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["other"], project_path=str(Path(self.tmp.name) / "elsewhere"))
        self.assertAllowed("dev-kit:ghost")

    def test_installed_project_path_is_compared_case_insensitively(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["coder"], project_path=str(self.project).swapcase())
        self.assertDenied("dev-kit:ghost")

    def test_installed_local_scope_entry_is_used(self):
        self.use_cache_layout()
        self.enable("local", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["coder"], scope="local")
        self.assertAllowed("dev-kit:coder")
        self.assertDenied("dev-kit:ghost")

    def test_installed_user_entry_is_the_fallback(self):
        self.use_cache_layout()
        self.enable("user", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["coder"], scope="user")
        self.assertAllowed("dev-kit:coder")
        self.assertDenied("dev-kit:ghost")

    def test_installed_project_entry_wins_over_user_entry(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["from-user"], scope="user")
        self.install("dev-kit@korov-dev", ["from-project"])
        self.assertAllowed("dev-kit:from-project")
        self.assertDenied("dev-kit:from-user")

    def test_same_plugin_name_in_two_marketplaces_is_kept_apart(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["coder"])
        self.install("dev-kit@other", ["foreign"])
        self.assertDenied("dev-kit:foreign")

    def test_installed_folder_is_used_before_sibling_folder(self):
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["installed-only"])
        self.assertAllowed("dev-kit:installed-only")
        self.assertDenied("dev-kit:coder")

    def test_missing_install_folder_falls_back_to_sibling(self):
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.install("dev-kit@korov-dev", ["coder"])
        data = json.loads((self.home / ".claude" / "plugins" / "installed_plugins.json").read_text(encoding="utf-8"))
        data["plugins"]["dev-kit@korov-dev"][0]["installPath"] = str(Path(self.tmp.name) / "gone")
        write(self.home / ".claude" / "plugins" / "installed_plugins.json", json.dumps(data))
        self.assertAllowed("dev-kit:coder")
        self.assertDenied("dev-kit:ghost")

    def test_broken_installed_plugins_json_falls_back_to_prefix(self):
        self.use_cache_layout()
        self.enable("project", **{"dev-kit@korov-dev": True})
        write(self.home / ".claude" / "plugins" / "installed_plugins.json", "{")
        self.assertAllowed("dev-kit:anything")

    def test_project_agent_is_allowed(self):
        self.assertAllowed("local-coder")

    def test_project_agent_found_through_cwd_without_env(self):
        self.assertAllowed("local-coder", project_env=False)

    def test_builtin_is_denied(self):
        reason = self.assertDenied("general-purpose")
        self.assertIn("local-coder", reason)

    def test_empty_type_is_denied(self):
        self.assertIn("(none)", self.assertDenied(""))

    def test_missing_type_is_denied(self):
        output = json.loads(self.run_hook(None))["hookSpecificOutput"]
        self.assertEqual("deny", output["permissionDecision"])

    def test_enabled_plugin_agent_is_allowed(self):
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.assertAllowed("dev-kit:coder")

    def test_enabled_plugin_unknown_agent_is_denied(self):
        self.enable("project", **{"dev-kit@korov-dev": True})
        reason = self.assertDenied("dev-kit:ghost")
        self.assertIn("dev-kit:coder", reason)

    def test_disabled_plugin_is_denied(self):
        self.enable("project", **{"dev-kit@korov-dev": False})
        self.assertDenied("dev-kit:coder")

    def test_plugin_not_in_settings_is_denied(self):
        self.assertDenied("dev-kit:coder")

    def test_local_false_overrides_project_true(self):
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.enable("local", **{"dev-kit@korov-dev": False})
        self.assertDenied("dev-kit:coder")

    def test_local_true_overrides_user_false(self):
        self.enable("user", **{"dev-kit@korov-dev": False})
        self.enable("local", **{"dev-kit@korov-dev": True})
        self.assertAllowed("dev-kit:coder")

    def test_user_scope_enable_works(self):
        self.enable("user", **{"dev-kit@korov-dev": True})
        self.assertAllowed("dev-kit:coder")

    def test_broken_settings_json_is_skipped(self):
        write(self.project / ".claude" / "settings.json", "{")
        self.enable("user", **{"dev-kit@korov-dev": True})
        self.assertAllowed("dev-kit:coder")

    def test_broken_local_settings_keeps_project_value(self):
        self.enable("project", **{"dev-kit@korov-dev": True})
        write(self.project / ".claude" / "settings.local.json", "[1]")
        self.assertAllowed("dev-kit:coder")

    def test_plugin_without_sibling_folder_is_allowed_by_prefix(self):
        self.enable("project", **{"other-kit@elsewhere": True})
        self.assertAllowed("other-kit:anything")

    def test_prefix_wildcard_is_listed_in_the_reason(self):
        self.enable("project", **{"other-kit@elsewhere": True})
        self.assertIn("other-kit:*", self.assertDenied("general-purpose"))

    def test_plugin_agent_name_without_plugin_is_denied(self):
        self.enable("project", **{"dev-kit@korov-dev": True})
        self.assertDenied("coder")

    def test_empty_agent_after_prefix_is_denied(self):
        self.enable("project", **{"other-kit@elsewhere": True})
        self.assertDenied("other-kit:")


if __name__ == "__main__":
    unittest.main()
