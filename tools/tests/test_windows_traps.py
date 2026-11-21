import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "dev-kit" / "hooks" / "windows-traps.py"
SPEC = importlib.util.spec_from_file_location("windows_traps", SCRIPT)
wt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wt)

BIG_BODY = "print('товар')\n" * 600


class TrapTests(unittest.TestCase):
    """The command shapes come from failed and working calls of the 2026-11-20/21 sessions."""

    def assertBlocked(self, command, fix):
        self.assertEqual(fix, wt.trap(command))

    def assertPasses(self, command):
        self.assertIsNone(wt.trap(command))

    def test_python_without_utf8_mode_is_blocked(self):
        self.assertBlocked("cd data && python script.py", wt.PYTHON_FIX)
        self.assertBlocked("python3 -c \"print('x')\"", wt.PYTHON_FIX)
        self.assertBlocked("timeout 900 python -B tools/run.py", wt.PYTHON_FIX)
        self.assertBlocked("t=$(python -c 'import json')", wt.PYTHON_FIX)
        self.assertBlocked("C:/Python313/python.exe x.py", wt.PYTHON_FIX)
        self.assertBlocked("PYTHONIOENCODING=utf-8 python - <<'EOF'\nprint(1)\nEOF", wt.PYTHON_FIX)

    def test_launchers_after_keywords_and_prefixes(self):
        self.assertBlocked("for f in *.py; do python $f; done", wt.PYTHON_FIX)
        self.assertBlocked("if true; then python x.py; fi", wt.PYTHON_FIX)
        self.assertBlocked("uv run python x.py", wt.PYTHON_FIX)
        self.assertBlocked("python3.13 x.py", wt.PYTHON_FIX)
        self.assertBlocked("python -X utf8 a.py && python b.py", wt.PYTHON_FIX)

    def test_each_launcher_is_judged_alone(self):
        self.assertPasses("PYTHONUTF8=1 python x.py | grep -E foo")
        self.assertPasses("export PYTHONUTF8=1; python x.py")

    def test_pythonutf8_does_not_count_under_isolated_mode(self):
        self.assertPasses("PYTHONUTF8=1 python x.py")
        self.assertBlocked("PYTHONUTF8=1 python -I x.py", wt.PYTHON_FIX)
        self.assertBlocked("PYTHONUTF8=1 python -B -I x.py", wt.PYTHON_FIX)

    def test_utf8_mode_passes_including_read_only_inline_python(self):
        self.assertPasses("python -I -X utf8 x.py")
        self.assertPasses("python -X utf8 -I - <<'EOF'\nimport json\nprint('сир')\nEOF")
        self.assertPasses("python -I -X utf8 -c \"print('Морепродукти')\"")

    def test_python_inside_text_is_not_a_launch(self):
        self.assertPasses("cat > notes.md <<'EOF'\npython x.py\nEOF")
        self.assertPasses("which python; pip list")
        self.assertPasses("git commit -m 'fix the python hook'")
        self.assertPasses("grep -rn python3 docs")
        self.assertPasses('echo "done; python is next"')
        self.assertPasses('git commit -m "title\n\npython hook now refuses"')
        self.assertPasses("x=$((1 << n))\npython -I -X utf8 x.py")

    def test_large_heredoc_is_blocked(self):
        self.assertBlocked("cat > gen.py <<'EOF'\n" + BIG_BODY + "EOF\npython -I -X utf8 gen.py", wt.HEREDOC_FIX)
        self.assertPasses("cat > gen.py <<'EOF'\nprint('товар')\nEOF\npython -I -X utf8 gen.py")

    def test_tmp_inside_python_code_is_blocked(self):
        self.assertBlocked("python -I -X utf8 - <<'EOF'\nopen('/tmp/p01/items.json', 'w')\nEOF", wt.TMP_FIX)
        self.assertBlocked("mkdir -p /tmp/sf01 && cat > /tmp/sf01/d.py <<'EOF'\nopen('/tmp/sf01/d.txt','w')\nEOF",
                           wt.TMP_FIX)
        self.assertBlocked("python -I -X utf8 -c \"open('/tmp/x.json')\"", wt.TMP_FIX)

    def test_tmp_as_a_shell_argument_passes(self):
        self.assertPasses("npm ci > /tmp/npmci.log 2>&1; tail -3 /tmp/npmci.log")
        self.assertPasses("python -I -X utf8 /tmp/sf01/dump.py in.json /tmp/sf01/dump.txt")
        self.assertPasses("bash -c \"cd /tmp && ls\"; grep -c '/tmp' f")
        self.assertPasses("git commit -F - <<'EOF'\nno more /tmp paths\nEOF")
        self.assertPasses("python -I -X utf8 - <<'EOF'\nopen('C:/tmp/x')\nEOF")

    def test_job_tmp_folder_is_not_slash_tmp(self):
        self.assertPasses("python -I -X utf8 - <<'EOF'\nopen('C:/Users/x/.claude/jobs/1/tmp/a.txt')\nEOF")
        self.assertPasses("ls C:/repo/tmp_unused")


@unittest.skipUnless(sys.platform == "win32", "the hook acts only on Windows")
class HookTests(unittest.TestCase):
    def run_hook(self, command):
        call = {"tool_name": "Bash", "tool_input": {"command": command}}
        result = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(call).encode("utf-8"),
                                capture_output=True)
        self.assertEqual(0, result.returncode, result.stderr.decode("utf-8", "replace"))
        return result.stdout.decode("utf-8")

    def test_denies_with_the_working_form(self):
        output = json.loads(self.run_hook("python x.py"))["hookSpecificOutput"]
        self.assertEqual("deny", output["permissionDecision"])
        self.assertIn("python -I -X utf8", output["permissionDecisionReason"])

    def test_silent_on_a_working_command(self):
        self.assertEqual("", self.run_hook("python -I -X utf8 x.py"))

    def test_silent_on_bad_input(self):
        result = subprocess.run([sys.executable, str(SCRIPT)], input=b"not json", capture_output=True)
        self.assertEqual((0, b""), (result.returncode, result.stdout))


if __name__ == "__main__":
    unittest.main()
