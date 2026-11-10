import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "unity-kit" / "scripts" / "user_check.py"
spec = importlib.util.spec_from_file_location("user_check", SCRIPT)
uc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uc)

PROFILE = """# Profile

## user-check

| Setting | Value |
|---|---|
| recipes | `checks` |
| reports | `reports` |
| scene | `Assets/Main.unity` |
| state-command | `game-state` |
| ready | `Loaded=true` |
| ready-within | 5 |
| click-command | `game-gui` |
| panel-height | 1080 |

## other

| Setting | Value |
|---|---|
| ignored | x |
"""


class Clock:
    def __init__(self):
        self.now = 1000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Bridge:
    """A fake uloop: answers like the editor, records the calls."""

    def __init__(self, clock, loaded_after=0.0):
        self.clock, self.loaded_after = clock, loaded_after
        self.calls, self.logs, self.errors = [], [], []
        self.playing, self.started = False, None
        self.scene = "Assets/Main.unity"

    def __call__(self, *args, timeout=60):
        self.calls.append(args)
        command = args[0]
        if command == "game-state":
            loaded = self.playing and self.clock.now - self.started >= self.loaded_after
            return {"Playing": self.playing, "Compiling": False, "Scene": self.scene, "GameWidth": 1920,
                    "GameHeight": 2160, "Loaded": loaded}
        if command == "control-play-mode":
            self.playing = args[2] == "Play"
            self.started = self.clock.now
            return {"IsPlaying": self.playing}
        if command == "get-logs":
            pool = self.errors if "--log-type" in args else self.logs + self.errors
            count = int(args[args.index("--max-count") + 1])
            return {"TotalCount": len(pool), "Logs": [{"Message": m} for m in reversed(pool)][:count]}
        if command == "game-gui":
            if args[2] == "click":
                self.logs.append("button pressed")
            return {"Success": True, "Message": "clicked"}
        if command == "game-fault":
            return {"Success": False, "Message": "unknown kind"}
        return {"Success": True, "Message": command + " done"}


class UserCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".claude").mkdir()
        (self.root / ".claude" / "dev-kit.md").write_text(PROFILE, encoding="utf-8")
        (self.root / "checks" / "blocks").mkdir(parents=True)

    def recipe(self, steps, **extra):
        (self.root / "checks" / "probe.json").write_text(json.dumps({"about": "probe", "steps": steps, **extra}),
                                                         encoding="utf-8")

    def run_check(self, bridge, clock):
        root, settings, recipe, name, steps, on_failure = uc.prepare("probe", str(self.root))
        check = uc.Check(bridge, root, settings, name, clock=clock)
        with redirect_stdout(io.StringIO()):
            code = check.run(recipe, steps, on_failure)
        return code, (Path(check.folder) / "report.txt").read_text(encoding="utf-8")

    def test_settings_come_from_the_profile_section(self):
        settings = uc.read_settings(str(self.root))
        self.assertEqual(settings["state-command"], "game-state")
        self.assertEqual(settings["uloop"], "uloop")
        self.assertNotIn("ignored", settings)

    def test_unknown_setting_is_refused(self):
        (self.root / ".claude" / "dev-kit.md").write_text(PROFILE.replace("| scene |", "| scenes |"), encoding="utf-8")
        with self.assertRaisesRegex(uc.NotRun, "unknown setting 'scenes'"):
            uc.read_settings(str(self.root))

    def test_bad_steps_are_found_before_play_mode(self):
        for step, message in [("jump 3", "unknown step"), ("wait soon", "not a number"), ("click 2,0.5", "fractions"),
                              ("expect-state Loaded", "expect-state"), ("expect-log \"(\"", "bad regex"),
                              ("use missing", "no block 'missing'"), ("wait 9999", "outside")]:
            self.recipe([step])
            with self.subTest(step=step), self.assertRaisesRegex(uc.NotRun, message):
                uc.prepare("probe", str(self.root))

    def test_blocks_expand_and_a_project_block_wins(self):
        self.recipe(["use ready", "use no-errors"])
        steps = uc.prepare("probe", str(self.root))[4]
        self.assertEqual([(label, text) for label, text, _ in steps],
                         [("[ready] ", "expect-state ready within 5"), ("[no-errors] ", "expect-no-errors")])
        self.assertEqual(steps[0][2], ("expect-state", ["ready"], 5.0))
        (self.root / "checks" / "blocks" / "ready.json").write_text('{"steps": ["wait 1"]}', encoding="utf-8")
        self.assertEqual(uc.prepare("probe", str(self.root))[4][0][1], "wait 1")

    def test_a_block_that_includes_itself_is_refused(self):
        (self.root / "checks" / "blocks" / "loop.json").write_text('{"steps": ["use loop"]}', encoding="utf-8")
        self.recipe(["use loop"])
        with self.assertRaisesRegex(uc.NotRun, "includes itself"):
            uc.prepare("probe", str(self.root))

    def test_a_passing_check(self):
        clock = Clock()
        bridge = Bridge(clock, loaded_after=2.0)
        self.recipe(["use ready", "click panel:100,50", "expect-log \"button pressed\" within 1", "key Space 0.5",
                     "use no-errors"])
        code, report = self.run_check(bridge, clock)
        self.assertEqual(code, 0, report)
        self.assertIn("PASS  1 [ready] expect-state ready within 5 | Loaded True", report)
        self.assertIn("PASS  3 expect-log \"button pressed\" within 1 | button pressed", report)
        self.assertIn("result: passed (code 0)", report)
        self.assertFalse(bridge.playing)
        # panel units: 2160 / 1080 = 2 pixels a unit
        gui = next(c for c in bridge.calls if c[0] == "game-gui")
        self.assertEqual(gui[3:7], ("--x", "0.10417", "--y", "0.04630"))
        self.assertIn(("simulate-keyboard", "--action", "Press", "--key", "Space", "--duration", "0.5"), bridge.calls)

    def test_a_failed_step_stops_the_check_and_runs_on_failure(self):
        clock = Clock()
        bridge = Bridge(clock)
        self.recipe(["call game-fault --kind nope", "wait 1"], **{"on-failure": ["call game-note"]})
        code, report = self.run_check(bridge, clock)
        self.assertEqual(code, 1, report)
        self.assertIn("FAIL  1 call game-fault --kind nope | unknown kind", report)
        self.assertIn("PASS  1 on failure: call game-note | game-note done", report)
        self.assertNotIn("wait 1", report)
        self.assertIn(("control-play-mode", "--action", "Stop"), bridge.calls)

    def test_a_wait_is_bounded_by_within(self):
        clock = Clock()
        bridge = Bridge(clock, loaded_after=100.0)
        self.recipe(["expect-state ready within 3"], **{"on-failure": []})
        start = clock.now
        code, report = self.run_check(bridge, clock)
        self.assertEqual(code, 1)
        self.assertIn("FAIL  1 expect-state ready within 3 | Loaded False", report)
        self.assertLess(clock.now - start, 3.5)

    def test_errors_since_the_start_fail_no_errors(self):
        clock = Clock()
        bridge = Bridge(clock)
        bridge.errors.append("old error")
        self.recipe(["call game-break", "use no-errors"], **{"on-failure": []})
        original = bridge.__call__

        def breaking(*args, timeout=60):
            if args[0] == "game-break":
                bridge.errors.append("NullReferenceException")
            return original(*args, timeout=timeout)
        code, report = self.run_check(breaking, clock)
        self.assertEqual(code, 1, report)
        self.assertIn("1 console errors since the start: NullReferenceException", report)

    def test_refuses_in_another_scene_without_play_mode(self):
        clock = Clock()
        bridge = Bridge(clock)
        bridge.scene = "Assets/Other.unity"
        self.recipe(["wait 1"])
        code, report = self.run_check(bridge, clock)
        self.assertEqual(code, 2)
        self.assertIn("the open scene is Assets/Other.unity", report)
        self.assertFalse(any(c[0] == "control-play-mode" for c in bridge.calls))

    def test_a_bridge_that_stops_answering_still_leaves_play_mode(self):
        clock = Clock()
        bridge = Bridge(clock)
        self.recipe(["call game-hang"])

        def hanging(*args, timeout=60):
            if args[0] == "game-hang":
                raise uc.NotRun("uloop game-hang did not answer in 60 s")
            return bridge(*args, timeout=timeout)
        code, report = self.run_check(hanging, clock)
        self.assertEqual(code, 2)
        self.assertIn("Play Mode left", report)
        self.assertIn("not run to the end: uloop game-hang did not answer", report)

    def test_expect_file_reads_a_json_path(self):
        clock = Clock()
        bridge = Bridge(clock)
        self.recipe(["call game-save", "expect-file out/*.json items.length=2", "expect-file out/*.json items.1.n=7"])
        out = self.root / "out"
        out.mkdir()
        original = bridge.__call__

        def saving(*args, timeout=60):
            if args[0] == "game-save":
                (out / "a.json").write_text('{"items": [{"n": 1}, {"n": 7}]}', encoding="utf-8")
            return original(*args, timeout=timeout)
        import time as real_time
        clock.now = real_time.time()
        code, report = self.run_check(saving, clock)
        self.assertEqual(code, 0, report)
        self.assertIn("items.1.n = 7", report)

    def test_dry_run_needs_no_unity(self):
        self.recipe(["use ready", "shot start"])
        with redirect_stdout(io.StringIO()) as out:
            code = uc.main(["probe", "--project", str(self.root), "--dry-run"])
        self.assertEqual(code, 0)
        self.assertIn(" 1 [ready] expect-state ready within 5", out.getvalue())
        self.assertIn("on failure: shot failure", out.getvalue())
        self.assertFalse((self.root / "reports").exists())


if __name__ == "__main__":
    unittest.main()
