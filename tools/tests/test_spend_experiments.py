"""spend-kit experiments: the PreToolUse hook that alternates the variants of a helper, the commands, and the daily count
with its alarm, packet and result findings. Synthetic transcripts in temp folders."""
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_spend_signals import SignalsFixture, at, owner, reply, result  # noqa: E402

import experiments  # noqa: E402
import signals  # noqa: E402
import spend  # noqa: E402

HOOK = Path(__file__).resolve().parent.parent.parent / "plugins" / "spend-kit" / "hooks" / "experiment.py"


class ExperimentFixture(SignalsFixture):
    def hook(self, stdin, **payload):
        """(stdout, exit code) of the hook run as Claude runs it, with `payload` as the JSON on stdin (or raw bytes)."""
        data = stdin if isinstance(stdin, bytes) else json.dumps(stdin).encode("utf-8")
        done = subprocess.run([sys.executable, "-I", "-X", "utf8", str(HOOK)], input=data, capture_output=True, timeout=60)
        return done.stdout.decode("utf-8"), done.returncode

    def call(self, kind, number=1, **given):
        """The hook's answer (the `updatedInput` dict, or None for no output) for one `Agent` call."""
        payload = {"tool_input": {"subagent_type": kind, "description": "work", "prompt": "do it", **given},
                   "tool_use_id": f"tu{number}", "session_id": "s1", "cwd": str(self.tmp / "repo")}
        out, code = self.hook(payload)
        self.assertEqual(code, 0)
        return json.loads(out)["hookSpecificOutput"]["updatedInput"] if out else None

    def picks(self):
        return experiments.read_picks()

    def coder_file(self):
        self.agent_file("dev-kit", "coder", model="sonnet", effort="high")


class HookTestCase(ExperimentFixture):
    # protects: Flow
    def test_the_hook_alternates_the_coder_between_the_two_variants_and_logs_each_pick(self):
        self.coder_file()
        answers = [self.call("dev-kit:coder", number) for number in (1, 2, 3)]
        self.assertEqual([(item["model"], item["effort"]) for item in answers],
                         [("sonnet", "high"), ("opus", "low"), ("sonnet", "high")])
        self.assertEqual({item["prompt"] for item in answers}, {"do it"})  # the whole input comes back
        self.assertEqual([(pick["tool_use_id"], pick["variant"], pick["type"], pick["session"]) for pick in self.picks()],
                         [("tu1", "sonnet-high", "dev-kit:coder", "s1"), ("tu2", "opus-low", "dev-kit:coder", "s1"),
                          ("tu3", "sonnet-high", "dev-kit:coder", "s1")])
        self.assertEqual(signals.read_experiments(self.data), {"tu1", "tu2", "tu3"})  # the mismatch check skips them

    # protects: Rule
    def test_a_callers_own_model_for_the_coder_is_left_alone_and_not_logged(self):
        self.coder_file()
        self.assertIsNone(self.call("dev-kit:coder", model="opus"))
        self.assertEqual(self.picks(), [])
        self.assertEqual(self.call("dev-kit:coder", model="sonnet")["effort"], "high")  # the file's own model: not a choice

    # protects: Rule
    def test_opus_for_a_context_heavy_helper_goes_back_to_the_files_model(self):
        self.agent_file("dev-kit", "mechanical-editor", model="sonnet")
        answer = self.call("dev-kit:mechanical-editor", model="opus")
        self.assertNotIn("model", answer)
        self.assertEqual(answer["prompt"], "do it")
        self.assertEqual([(pick["variant"], pick["model"], pick["was"]) for pick in self.picks()],
                         [("reset", "sonnet", "opus")])
        self.assertIsNone(self.call("dev-kit:mechanical-editor", model="sonnet"))
        self.assertIsNone(self.call("dev-kit:mechanical-editor"))
        self.assertIsNone(self.call("dev-kit:investigator", model="opus"))  # not in the list: the caller's choice

    # protects: Rule
    def test_a_stopped_variant_is_skipped_and_with_only_the_old_one_left_nothing_changes(self):
        self.coder_file()
        self.assertEqual(self.run_code("experiment", "stop", "--type", "dev-kit:coder", "--variant", "opus-low",
                                       "--reason", "redone twice")[0], 0)
        self.assertIsNone(self.call("dev-kit:coder"))  # only sonnet-high is left: the agent file's lines apply
        self.assertEqual(self.picks(), [])
        self.assertEqual(self.run_code("experiment", "decide", "--type", "dev-kit:coder", "--variant", "opus-low",
                                       "--reason", "cheaper")[0], 0)
        self.assertEqual(self.call("dev-kit:coder")["model"], "opus")  # a decided type always gives the winner
        self.assertEqual(self.call("dev-kit:coder", 2)["model"], "opus")
        code, _, err = self.run_code("experiment", "stop", "--type", "dev-kit:coder", "--variant", "nope", "--reason", "x")
        self.assertEqual(code, 2)
        self.assertIn("unknown", err)

    # protects: Bug
    # Broke: under a non-UTF-8 console code page (cp1252) the Cyrillic output raised and the pick was already logged
    def test_a_cyrillic_prompt_comes_back_as_utf8_under_another_console_encoding(self):
        self.coder_file()
        payload = {"tool_input": {"subagent_type": "dev-kit:coder", "description": "робота", "prompt": "Зроби це, будь ласка"},
                   "tool_use_id": "tu1", "session_id": "s1", "cwd": str(self.tmp / "repo")}
        done = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload).encode("utf-8"), capture_output=True,
                              timeout=60, env={**os.environ, "PYTHONIOENCODING": "cp1252"})
        self.assertEqual(done.returncode, 0)
        given = json.loads(done.stdout.decode("utf-8"))["hookSpecificOutput"]["updatedInput"]
        self.assertEqual((given["prompt"], given["description"], given["model"]), ("Зроби це, будь ласка", "робота", "sonnet"))
        self.assertEqual(len(self.picks()), 1)

    # protects: Rule
    def test_a_failed_write_leaves_no_pick_and_does_not_advance_the_turn(self):
        self.coder_file()
        hook = importlib.util.spec_from_file_location("experiment_hook", HOOK)
        module = importlib.util.module_from_spec(hook)
        hook.loader.exec_module(module)
        payload = {"tool_input": {"subagent_type": "dev-kit:coder", "prompt": "x"}, "tool_use_id": "tu1", "cwd": str(self.tmp)}

        def broken(changed):
            raise OSError("closed pipe")

        with self.assertRaises(OSError):
            module.run(payload, broken)
        self.assertEqual(self.picks(), [])
        self.assertEqual(experiments.load_state()["types"].get("dev-kit:coder", {}).get("next", 0), 0)
        self.assertEqual(self.call("dev-kit:coder")["model"], "sonnet")  # the first variant is still the next one

    # protects: Edge
    def test_broken_input_prints_nothing_and_never_fails(self):
        for raw in (b"not json", b"", b'{"tool_input": 5}', b"[1, 2]", b'{"tool_input": {"subagent_type": 7}}'):
            self.assertEqual(self.hook(raw), ("", 0), raw)
        with mock.patch.dict(os.environ, {"SPEND_KIT_DIR": str(self.tmp / "file")}):  # a data folder that is a file
            (self.tmp / "file").write_text("x", encoding="utf-8")
            self.coder_file()
            self.assertEqual(self.hook({"tool_input": {"subagent_type": "dev-kit:coder"}})[1], 0)


class CommandTestCase(ExperimentFixture):
    # protects: Flow
    def test_experiment_next_for_a_manager_alternates_the_effort_and_logs_the_task(self):
        words = [self.run_cmd("experiment", "next", "--type", "manager", "--task", f"M: task {n}").strip()
                 for n in range(4)]
        self.assertEqual(words, ["medium", "low", "medium", "low"])
        self.assertEqual([(pick["variant"], pick["task"]) for pick in self.picks()][:2],
                         [("opus-medium", "M: task 0"), ("opus-low", "M: task 1")])
        self.run_cmd("experiment", "stop", "--type", "manager", "--variant", "opus-low", "--reason", "x")
        self.assertEqual(self.run_cmd("experiment", "next", "--type", "manager", "--task", "M: task 4").strip(), "medium")
        self.assertEqual(len(self.picks()), 4)  # no override: nothing to log
        self.assertEqual(self.run_code("experiment", "next", "--type", "nope")[0], 2)


class CountTestCase(ExperimentFixture):
    def runs(self, plan, session="sess1"):
        """A session with one helper run per `(variant, failed check after it)` of `plan`, picks in the log. Every run is
        5000 units; a run is followed by a failed `pytest` when asked, before the next owner message."""
        entries, picks, minute = [owner(0, "start")], [], 1
        for number, (variant, failed) in enumerate(plan, 1):
            call = f"tu{number}"
            entries += [owner(minute, f"step {number}"),
                        reply(f"m{number}", minute + 1, ("Agent", call, "dev-kit:coder", f"task {number} work")),
                        result(minute + 6, call)]
            if failed:
                entries += [reply(f"c{number}", minute + 7, ("Bash", f"b{number}", "python -m pytest")),
                            result(minute + 8, f"b{number}", "FAILED test_x", error=True)]
            self.helper(session, f"agent-{number}", "dev-kit:coder", call,
                        [reply(f"h{number}", minute + 3)], f"task {number} work")
            model, effort = experiments.EXPERIMENTS["dev-kit:coder"]["variants"][variant]
            picks.append({"time": at(minute), "session": session, "type": "dev-kit:coder", "variant": variant,
                          "model": model, "effort": effort, "tool_use_id": call})
            minute += 10
        main = self.write(f"proj/{session}.jsonl", entries)
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / signals.EXPERIMENTS_NAME).write_text("".join(json.dumps(pick) + "\n" for pick in picks),
                                                          encoding="utf-8")
        return main

    def lines(self, kind):
        with mock.patch.object(spend, "WEEKLY_LIMIT_UNITS", 100000):
            lines, _ = self.findings()
        return [line for line in lines if f"| {kind} |" in line]

    # protects: Flow
    def test_three_runs_per_variant_with_an_alarming_sign_give_one_alarm_with_a_packet(self):
        self.runs([("sonnet-high", False)] * 3 + [("opus-low", True)] * 3)
        found = self.lines("experiment alarm")
        self.assertEqual(len(found), 1)
        packet = self.data / "experiment-packets" / f"dev-kit-coder-opus-low-{spend.today()}.md"
        self.assertEqual(found[0], f"- proj | sess1 | experiment alarm | dev-kit:coder opus-low: 3/3 signs, 5.0k units per "
                                   f"run vs sonnet-high 0/3 signs, 5.0k units per run; packet: {packet}; 15.0% of the "
                                   f"weekly limit")
        text = packet.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 40)
        self.assertRegex(text, r"- failed check, line \d+: python -m pytest -> FAILED test_x")
        self.assertIn("agent-4.jsonl", text)
        self.assertEqual(self.lines("experiment alarm"), [])  # no new runs: not again on the next scan
        self.assertEqual(self.lines("experiment result"), [])  # under 10 runs per variant

    # protects: Rule
    def test_three_runs_per_variant_without_an_alarming_sign_give_no_alarm(self):
        self.runs([("sonnet-high", True), ("sonnet-high", False), ("sonnet-high", False),
                   ("opus-low", True), ("opus-low", False), ("opus-low", False)])  # one sign each: not 2 times
        self.assertEqual(self.lines("experiment alarm"), [])

    # protects: Flow
    def test_ten_runs_per_variant_give_one_result_with_both_variants_numbers(self):
        self.runs([("sonnet-high", False), ("opus-low", False)] * 10)
        found = self.lines("experiment result")
        self.assertEqual(found, ["- proj | sess1 | experiment result | dev-kit:coder: sonnet-high 0/10 signs, 5.0k units per "
                                 "run; opus-low 0/10 signs, 5.0k units per run"])
        self.assertEqual(self.lines("experiment result"), [])  # once per type
        self.assertEqual(self.lines("experiment alarm"), [])

    # protects: Rule
    def test_a_decided_type_gives_no_more_findings(self):
        self.runs([("sonnet-high", False), ("opus-low", False)] * 10)
        experiments.decide("dev-kit:coder", "sonnet-high", "cheaper is worse")
        self.assertEqual(self.lines("experiment result"), [])

    # protects: Rule
    def test_a_manager_run_is_the_session_with_its_re_asks_and_failed_checks_as_signs(self):
        self.write("proj/mgr1.jsonl", [
            {"type": "custom-title", "customTitle": "M: build it"},
            owner(0, "start"), reply("m1", 1, ("Bash", "b1", "python -m unittest")), result(2, "b1", "boom", error=True),
            owner(10, "?"), reply("m2", 11)])
        self.data.mkdir(parents=True, exist_ok=True)
        (self.data / signals.EXPERIMENTS_NAME).write_text(json.dumps(
            {"time": at(0), "session": "mgr1", "type": "manager", "variant": "opus-low", "model": "opus",
             "effort": "low", "task": "M: build it"}) + "\n", encoding="utf-8")
        self.run_cmd("scan", "--force")  # the scan records the session's title
        found = spend.experiment_runs(spend.load_state(self.data), self.projects, spend.now_utc())
        run = found["manager"]["opus-low"][0]
        self.assertEqual((run["units"], [sign["kind"] for sign in run["signs"]]), (10000, ["failed check", "re-ask"]))

    # protects: Flow
    def test_the_status_shows_each_type_with_its_runs_and_what_is_stopped(self):
        self.runs([("sonnet-high", False), ("opus-low", True)] * 2)
        experiments.stop("dev-kit:coder", "opus-low", "too many failed checks")
        out = self.run_cmd("experiments")
        self.assertIn("dev-kit:coder (старий sonnet-high)", out)
        self.assertIn("  opus-low: 2 запусків, 5.0k одиниць на запуск, 1.0 ознак на запуск", out)
        self.assertIn("  зупинено opus-low: too many failed checks", out)
        self.assertIn("manager (старий opus-medium)", out)
        self.assertTrue(re.search(r"rule-reviewer \(старий sonnet-high\)", out))
