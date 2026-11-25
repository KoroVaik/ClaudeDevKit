import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "dev-kit" / "scripts"))
import dev_kit_state  # noqa: E402
import sessions  # noqa: E402


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


class SessionsTestCase(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        self.tmp = tmp
        self.state = tmp / "state"
        self.projects = tmp / "projects"
        (self.projects / "p1").mkdir(parents=True)
        self.project = tmp / "work"
        self.project.mkdir()
        self.jobs = tmp / "jobs"  # no job: transcripts are found by file name unless a test writes a job state
        env = mock.patch.dict(os.environ, {"DEV_KIT_STATE_DIR": str(self.state), "DEV_KIT_PROJECTS_DIR": str(self.projects),
                                           "DEV_KIT_JOBS_DIR": str(self.jobs)})
        env.start()
        self.addCleanup(env.stop)

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sessions.main(["--project", str(self.project), *argv])
        return code, out.getvalue() + err.getvalue()

    def add(self, session_id, name="C: x", **extra):
        argv = ["add", "--id", session_id, "--name", name, "--worktree", "wt", "--task", "t.md"]
        for key, value in extra.items():
            if value:  # True is a flag without a value
                argv += [f"--{key}"] + ([] if value is True else [value])
        return self.run_main(*argv)

    def records(self):
        return json.loads((dev_kit_state.project_state_dir(self.project) / "sessions.json").read_text())

    def transcript(self, session_id, entries):
        lines = [json.dumps(entry) for entry in entries]
        (self.projects / "p1" / f"{session_id}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def assistant(i, c, r, model="claude-haiku-4-5-20251001"):  # a 200K model unless a test says otherwise
        usage = {"input_tokens": i, "cache_creation_input_tokens": c, "cache_read_input_tokens": r, "output_tokens": 5}
        return {"type": "assistant", "message": {"role": "assistant", "model": model, "usage": usage}}

    def test_add_list_end(self):
        self.assertEqual(0, self.add("a1")[0])
        code, output = self.run_main("list")
        self.assertEqual(0, code)
        self.assertIn("C: x | a1 | wt | t.md |", output)
        self.assertEqual(0, self.run_main("end", "--id", "a1")[0])
        self.assertIn("no active sessions", self.run_main("list")[1])
        record = self.records()[0]
        self.assertEqual("done", record["status"])
        self.assertTrue(record["ended"])

    def test_duplicate_and_unknown_id(self):
        self.add("a1")
        self.assertEqual(1, self.add("a1")[0])
        self.assertEqual(1, self.run_main("end", "--id", "zz")[0])

    def test_end_by_short_id(self):
        self.add("abcd1234-0000")
        self.add("abcd9999-0000")
        self.assertEqual(1, self.run_main("end", "--id", "abcd")[0])  # too short
        self.assertEqual(1, self.run_main("end", "--id", "")[0])
        self.assertEqual(0, self.run_main("end", "--id", "abcd1234")[0])
        self.assertEqual("done", self.records()[0]["status"])
        self.assertEqual("active", self.records()[1]["status"])
        self.assertEqual(0, self.add("abcd5555-0000", predecessor="abcd9999")[0])
        self.assertEqual("replaced", self.records()[1]["status"])
        self.assertEqual("abcd9999-0000", self.records()[2]["predecessor"])

    def test_predecessor_marked_replaced(self):
        self.add("a1")
        self.assertEqual(0, self.add("a2", name="C: y", predecessor="a1", parent="p0")[0])
        records = self.records()
        self.assertEqual("replaced", records[0]["status"])
        self.assertEqual("a1", records[1]["predecessor"])
        self.assertEqual("p0", records[1]["parent"])
        self.assertEqual(1, self.add("a3", predecessor="nope")[0])

    def test_fill_sums_last_assistant_message(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(1, 1, 1), {"type": "user"}, self.assistant(10, 200, 99790), {"type": "user"}])
        code, output = self.run_main("fill")
        self.assertEqual(0, code)
        self.assertIn("100000 tokens | window 200000 | 50% OVER", output)

    def test_fill_under_limit_and_window(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(0, 0, 50000)])
        self.assertNotIn("OVER", self.run_main("fill")[1])
        self.assertIn("window 1000000 | 5%", self.run_main("fill", "--window", "1000000")[1])
        self.assertIn("OVER", self.run_main("fill", "--limit", "0.2")[1])

    def test_fill_default_limit_is_a_third(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(0, 0, 64000)])
        self.assertNotIn("OVER", self.run_main("fill")[1])
        self.transcript("a1", [self.assistant(0, 0, 68000)])
        self.assertIn("OVER", self.run_main("fill")[1])

    def test_fill_one_million_model(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(0, 0, 300000, model="claude-opus-4-6[1m]")])
        self.assertIn("window 1000000 | 30%", self.run_main("fill")[1])

    def test_fill_native_one_million_model_without_suffix(self):
        # Seen live: a fresh Sonnet 5.5 Manager at 80k tokens showed 40% against an assumed 200K window.
        self.add("a1")
        self.transcript("a1", [self.assistant(0, 0, 80000, model="claude-sonnet-5-5")])
        self.assertIn("window 1000000 | 8%", self.run_main("fill")[1])

    def test_window_for_models(self):
        one_m, two_k = sessions.NATIVE_1M_WINDOW, sessions.DEFAULT_WINDOW
        cases = {"claude-opus-5-5": one_m, "claude-sonnet-5-5": one_m, "claude-haiku-5-5": one_m,
                 "claude-fable-5-2": one_m, "claude-opus-4-7": one_m, "sonnet": one_m,
                 "claude-haiku-4-5-20251001": two_k, "claude-sonnet-4-6": two_k, "claude-opus-4-6": two_k,
                 "claude-sonnet-4-6[1m]": one_m, "": two_k}
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_DISABLE_1M_CONTEXT": ""}):
            for model, window in cases.items():
                self.assertEqual(window, sessions.window_for(model), model)
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_DISABLE_1M_CONTEXT": "1"}):
            self.assertEqual(two_k, sessions.window_for("claude-opus-5-5"))

    def test_fill_large_transcript_reads_from_end(self):
        self.add("a1")
        filler = [{"type": "user", "text": "x" * 1000}] * 2000
        self.transcript("a1", [self.assistant(7, 0, 0)] + filler)
        self.assertIn("7 tokens", self.run_main("fill")[1])

    def test_fill_skips_zero_usage_messages(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(3, 0, 40), self.assistant(0, 0, 0)])
        self.assertIn("43 tokens", self.run_main("fill")[1])

    def test_fill_non_ascii_and_chunk_boundary(self):
        self.add("a1")
        entries = [self.assistant(5, 0, 0)] + [{"type": "user", "text": "Привіт, світе " * 20}] * 30
        self.transcript("a1", entries)
        path = self.projects / "p1" / "a1.jsonl"
        for chunk in (7, 64, 1000, 4097):
            with mock.patch.object(sessions, "CHUNK", chunk):
                self.assertEqual((5, "claude-haiku-4-5-20251001"), sessions.last_usage(path), chunk)
        # a usage line cut in the middle by the first read must still be found whole
        self.transcript("a1", [self.assistant(9, 0, 0, model="модель")] + [{"type": "user", "text": "й" * 50}] * 3)
        lines = path.read_bytes().split(b"\n")
        with mock.patch.object(sessions, "CHUNK", len(lines[-2]) + len(lines[-3]) + 10):
            self.assertEqual((9, "модель"), sessions.last_usage(path))

    def test_fill_missing_transcript(self):
        self.add("a1")
        code, output = self.run_main("fill")
        self.assertEqual(0, code)
        self.assertIn("a1 | no transcript", output)

    def test_unreadable_registry(self):
        (dev_kit_state.project_state_dir(self.project) / "sessions.json").write_text("{nope", encoding="utf-8")
        self.assertEqual(2, self.run_main("list")[0])

    def test_state_dir_same_for_worktrees(self):
        repo = self.tmp / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
        git(repo, "worktree", "add", "-q", str(self.tmp / "wt"), "-b", "side")
        first = dev_kit_state.project_state_dir(repo)
        self.assertEqual(first, dev_kit_state.project_state_dir(self.tmp / "wt"))
        self.assertTrue(first.name.startswith("repo-"))
        self.assertNotEqual(first, dev_kit_state.project_state_dir(self.project))

    def others_setup(self):
        """A repo on main with a worktree on branch `side` (one committed, one untracked file), and a session list."""
        repo, wt = self.tmp / "repo", self.tmp / "repo" / ".claude" / "worktrees" / "side"
        repo.mkdir()
        git(repo, "init", "-q", "-b", "main")
        git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "i")
        git(repo, "worktree", "add", "-q", str(wt), "-b", "side")
        (wt / "a.md").write_text("a", encoding="utf-8")
        git(wt, "add", "a.md")
        git(wt, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "a")
        (wt / "b.py").write_text("b", encoding="utf-8")
        self.project = repo
        agents = [
            {"sessionId": "me", "name": "M: me", "cwd": str(repo), "kind": "background", "status": "busy"},
            {"sessionId": "lead", "name": "L: repo", "cwd": str(repo), "kind": "background", "status": "idle"},
            {"sessionId": "r1", "name": "Retro: repo", "cwd": str(repo), "kind": "background", "status": "busy"},
            {"sessionId": "d1", "name": "Docs: repo", "cwd": str(repo), "kind": "background",
             "status": "busy"},
            # Edge: sessions that still run under the old titles are left out too
            {"sessionId": "lead-old", "name": "P: repo", "cwd": str(repo), "kind": "background", "status": "idle"},
            {"sessionId": "r1-old", "name": "Ретро: repo", "cwd": str(repo), "kind": "background", "status": "busy"},
            {"sessionId": "d1-old", "name": "Документація: repo", "cwd": str(repo), "kind": "background",
             "status": "busy"},
            {"sessionId": "c1", "name": "M: side", "cwd": str(wt), "kind": "background", "status": "busy",
             "state": "working"},
            {"sessionId": "o1", "name": "Own idea", "cwd": str(repo), "kind": "interactive", "status": "idle"},
            {"sessionId": "x1", "name": "Elsewhere", "cwd": str(self.tmp), "kind": "interactive", "status": "idle"},
        ]
        listing = self.tmp / "agents.json"
        listing.write_text(json.dumps(agents), encoding="utf-8")
        env = mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(listing), "CLAUDE_CODE_SESSION_ID": "me"})
        env.start()
        self.addCleanup(env.stop)
        self.add("c1", name="M: side")
        return repo, wt

    def test_others_lists_sessions_of_this_repo(self):
        self.others_setup()
        self.transcript("c1", [
            {"type": "user", "isMeta": True, "message": {"content": "<local-command-caveat>x</local-command-caveat>"}},
            {"type": "user", "origin": {"kind": "human"}, "message": {"content": "<command-name>/x</command-name>"
                                                                               "<command-args>Fix login</command-args>"}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "noise"}]}},
            {"type": "user", "isMeta": True, "origin": {"kind": "peer", "body": "Full task:  login bug"},
             "message": {"content": "wrapper"}},
            {"type": "user", "origin": {"kind": "human"}, "message": {"content": "third, not shown"}},
        ])
        code, output = self.run_main("others", "--json")
        self.assertEqual(0, code)
        rows = {row["sessionId"]: row for row in json.loads(output)}
        # not the caller, the lead, the retro, the docs session (old titles too) or another repo's session
        self.assertEqual({"c1", "o1"}, set(rows))
        self.assertEqual("lead", rows["c1"]["startedBy"])
        self.assertEqual("owner", rows["o1"]["startedBy"])
        self.assertEqual("side", rows["c1"]["branch"])
        self.assertEqual("working", rows["c1"]["status"])
        self.assertEqual(["a.md", "b.py"], rows["c1"]["files"])
        self.assertEqual("Fix login // Full task: login bug", rows["c1"]["task"])
        self.assertEqual("main", rows["o1"]["branch"])
        self.assertEqual([], rows["o1"]["files"])
        text = self.run_main("others")[1]
        self.assertIn("M: side | background working | started by lead | branch side |", text)
        self.assertIn("  files: a.md, b.py", text)
        self.assertIn("  task: (no transcript)", text)  # o1 has none

    def test_others_none_self_flag_and_unreadable_list(self):
        self.others_setup()
        with mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(self.tmp / "agents.json")}):
            (self.tmp / "agents.json").write_text(json.dumps([{"sessionId": "me", "cwd": str(self.project)}]))
            self.assertIn("no other sessions", self.run_main("others")[1])
            self.assertIn("(no name)", self.run_main("others", "--self", "other")[1])
            (self.tmp / "agents.json").write_text("{not json")
            self.assertEqual(3, self.run_main("others")[0])

    def test_others_task_text_is_cut(self):
        self.others_setup()
        self.transcript("c1", [{"type": "user", "message": {"content": "w " * 1000}}])
        rows = {row["sessionId"]: row for row in json.loads(self.run_main("others", "--json")[1])}
        self.assertEqual(sessions.TASK_CHARS + 3, len(rows["c1"]["task"]))


    def listing(self, agents):
        listing = self.tmp / "agents.json"
        listing.write_text(json.dumps(agents), encoding="utf-8")
        env = mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(listing)})
        env.start()
        self.addCleanup(env.stop)
        return listing

    def lock(self):
        return dev_kit_state.project_state_dir(self.project) / sessions.WATCH_LOCK

    def test_watch_exits_when_a_registered_session_is_gone(self):
        self.add("c1-live-session", name="C: live")
        self.add("c2-dead-session", name="C: dead")
        self.listing([{"sessionId": "c1-live-session", "pid": 11, "state": "working"}])  # c2 is not in the list
        code, out = self.run_main("watch", "--interval", "0")
        self.assertEqual(0, code)
        self.assertEqual("gone: C: dead | c2-dead-session | not in the session list\n", out)
        self.assertFalse(self.lock().exists())

    def test_watch_and_state_report_stopped_and_missing_sessions_as_gone(self):  # Rule
        self.add("c1-stopped-session", name="C: stopped")
        self.add("c2-missing-session", name="C: missing")
        self.listing([{"sessionId": "c1-stopped-session", "state": "stopped"}])
        gone = sessions.gone_sessions([("C: stopped", "c1-stopped-session"), ("C: missing", "c2-missing-session")],
                                      sessions.agents_list(include_ended=True))
        self.assertEqual([("C: stopped", "c1-stopped-session", "stopped"),
                          ("C: missing", "c2-missing-session", "not in the session list")], gone)
        self.assertEqual(["C: stopped | c1-stopped-session | gone | (no reply text)",
                          "C: missing | c2-missing-session | gone | (no reply text)"], self.state_lines())

    def test_watch_missing_session_and_short_ids(self):
        self.listing([{"sessionId": "aaaaaaaa-1111", "name": "C: a", "pid": 1, "state": "done"}])
        code, out = self.run_main("watch", "--id", "aaaaaaaa", "--id", "bbbbbbbb", "--interval", "0")
        self.assertEqual(0, code)
        self.assertEqual("gone: (no name) | bbbbbbbb | not in the session list\n", out)

    def test_watch_waits_then_wakes_on_a_session_that_ends(self):
        self.add("c1-session", name="C: x")
        listing = self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])
        rounds = []

        def sleep(_seconds):
            rounds.append(1)
            if len(rounds) == 2:
                listing.write_text("[]", encoding="utf-8")

        with mock.patch.object(sessions.time, "sleep", sleep):
            code, out = self.run_main("watch", "--interval", "1")
        self.assertEqual((0, 2), (code, len(rounds)))
        self.assertIn("gone: C: x | c1-session | not in the session list", out)

    def test_watch_time_limit_and_nothing_to_watch(self):
        code, out = self.run_main("watch", "--interval", "0")
        self.assertEqual((5, "nothing to watch\n"), (code, out))
        self.add("c1-session")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])
        code, out = self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")
        self.assertEqual((4, "time limit: 0.5 min, all alive\n"), (code, out))

    def test_watch_one_watcher_per_project(self):
        self.add("c1-session")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])
        lock = self.lock()
        lock.write_text(json.dumps({"pid": 999999, "beat": time.time()}), encoding="utf-8")

        def live_holder_beats(_seconds):
            lock.write_text(json.dumps({"pid": 999999, "beat": time.time() + 1}), encoding="utf-8")

        with mock.patch.object(sessions.time, "sleep", live_holder_beats), \
                mock.patch.object(sessions, "pid_alive", lambda _pid: True):
            code, out = self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")
        self.assertEqual((6, "already watching: pid 999999\n"), (code, out))
        self.assertTrue(lock.exists())

    def test_watch_takes_over_the_lock_of_a_killed_watcher(self):
        self.add("c1-session")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])
        self.lock().write_text(json.dumps({"pid": 999999, "beat": time.time() - 170}), encoding="utf-8")
        clock = [time.time()]

        def sleep(seconds):
            clock[0] += seconds

        with mock.patch.object(sessions.time, "sleep", sleep), \
                mock.patch.object(sessions.time, "time", lambda: clock[0]), \
                mock.patch.object(sessions, "pid_alive", lambda _pid: True):  # only the stale beat shows it is dead
            code, out = self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")
        self.assertEqual((4, "time limit: 0.5 min, all alive\n"), (code, out))
        self.assertFalse(self.lock().exists())

    def test_take_lock_takes_at_once_the_lock_of_a_dead_pid(self):  # Bug
        # Without this a watcher killed on low memory blocks the new one for 3 intervals (3 minutes).
        lock = self.lock()
        lock.write_text(json.dumps({"pid": 999999, "beat": time.time()}), encoding="utf-8")  # fresh beat
        with mock.patch.object(sessions, "pid_alive", lambda _pid: False), \
                mock.patch.object(sessions.time, "sleep", side_effect=AssertionError("must not wait")):
            self.assertIsNone(sessions.take_lock(lock, 60))
        self.assertEqual(os.getpid(), json.loads(lock.read_text(encoding="utf-8"))["pid"])

    def test_pid_alive_tells_a_live_process_from_an_ended_one(self):  # Edge
        self.assertTrue(sessions.pid_alive(os.getpid()))
        child = subprocess.Popen([sys.executable, "-c", "pass"])
        child.wait()
        self.assertFalse(sessions.pid_alive(child.pid))
        for bad in (None, 0, -1, "12", True):
            self.assertFalse(sessions.pid_alive(bad))

    def watch_with_clock(self, listing, on_sleep=None):
        """Run the registry watcher on a fake clock; returns (code, out, seconds waited)."""
        clock = [0.0]

        def sleep(seconds):
            clock[0] += seconds
            if on_sleep:
                on_sleep(clock[0], listing)

        with mock.patch.object(sessions.time, "sleep", sleep), \
                mock.patch.object(sessions.time, "monotonic", lambda: clock[0]):
            code, out = self.run_main("watch", "--interval", "60", "--max-minutes", "20")
        return code, out, clock[0]

    def test_watch_gives_every_session_without_a_pid_the_grace_whatever_its_state(self):  # Rule
        # Live facts: an idle session shows done with a pid and keeps done after its process dies; Claude Code's own
        # retire leaves stopped, the same as `claude stop`.
        self.add("c1-session", name="C: x")
        for state in ("done", "stopped", "blocked"):
            listing = self.listing([{"sessionId": "c1-session", "state": state}])
            code, out, waited = self.watch_with_clock(listing)
            self.assertEqual((0, f"gone: C: x | c1-session | {state}\n"), (code, out), state)
            self.assertEqual(sessions.CLOSED_GRACE, waited, state)

    def test_watch_forgets_a_closed_session_that_comes_back(self):  # Rule
        self.add("c1-session", name="C: x")
        listing = self.listing([{"sessionId": "c1-session", "state": "blocked"}])
        closed, back = [{"sessionId": "c1-session", "state": "blocked"}], [{"sessionId": "c1-session", "pid": 7}]

        def on_sleep(at, path):
            if at == 120:
                path.write_text(json.dumps(back), encoding="utf-8")
            elif at == 180:
                path.write_text(json.dumps(closed), encoding="utf-8")

        code, out, waited = self.watch_with_clock(listing, on_sleep)
        self.assertEqual((0, "gone: C: x | c1-session | blocked\n"), (code, out))
        self.assertEqual(180 + sessions.CLOSED_GRACE, waited)  # the grace starts again, not at the first closing

    def test_watch_keeps_quiet_when_the_last_session_ends(self):
        self.add("c1-session")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])
        calls, clock = [], [0.0]

        def sleep(seconds):
            calls.append(1)
            clock[0] += seconds
            if len(calls) == 1:
                self.run_main("end", "--id", "c1-session")

        with mock.patch.object(sessions.time, "sleep", sleep), \
                mock.patch.object(sessions.time, "monotonic", lambda: clock[0]):
            code, out = self.run_main("watch", "--interval", "10", "--max-minutes", "0.5")
        self.assertEqual((5, "nothing to watch\n"), (code, out))
        self.assertEqual(3, len(calls))  # waited for the time limit, no early wake-up

    def test_watch_survives_a_momentary_unreadable_registry(self):
        self.add("c1-session")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])
        real_load = sessions.load
        calls = []

        def flaky_load(path):
            calls.append(1)
            if len(calls) == 2:  # the first call is main's own read, the second the watcher's first round
                raise sessions.Unreadable("busy")
            return real_load(path)

        clock = [0.0]

        def sleep(seconds):
            clock[0] += seconds

        with mock.patch.object(sessions, "load", flaky_load), mock.patch.object(sessions.time, "sleep", sleep), \
                mock.patch.object(sessions.time, "monotonic", lambda: clock[0]):
            code, out = self.run_main("watch", "--interval", "10", "--max-minutes", "0.5")
        self.assertEqual((4, "time limit: 0.5 min, all alive\n"), (code, out))
        self.assertGreaterEqual(len(calls), 3)

    def test_watch_unreadable_list_gives_up_after_several_rounds(self):
        self.add("c1-session")
        with mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(self.tmp / "missing.json")}), \
                mock.patch.object(sessions.time, "sleep") as sleep:
            code, out = self.run_main("watch", "--interval", "1")
        self.assertEqual(3, code)
        self.assertEqual(sessions.WATCH_FAILURES - 1, sleep.call_count)
        self.assertIn("could not be read", out)

    @staticmethod
    def reply(text, **extra):
        return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
                **extra}

    @staticmethod
    def human(text):
        return {"type": "user", "origin": {"kind": "human"}, "message": {"role": "user", "content": text}}

    def state_lines(self, *argv):
        code, out = self.run_main("state", *argv)
        self.assertEqual(0, code, out)
        return out.splitlines()

    def test_add_owner_flag_is_stored_only_when_given(self):  # Rule
        self.add("a1")
        self.run_main("add", "--id", "a2", "--name", "Own", "--worktree", "wt", "--task", "t", "--owner")
        records = self.records()
        self.assertNotIn("owner", records[0])
        self.assertIs(True, records[1]["owner"])

    def test_state_has_four_outcomes(self):  # Flow
        for name in ("busy", "idle", "dead", "done"):
            self.add(f"{name}-session", name=f"S: {name}", owner=name == "done")
        self.listing([
            {"sessionId": "busy-session", "pid": 1, "status": "busy"},
            {"sessionId": "idle-session", "pid": 2, "status": "waiting", "waitingFor": "approval"},
            {"sessionId": "dead-session", "status": "stopped"},
            {"sessionId": "done-session", "pid": 4, "status": "idle"},
        ])
        self.transcript("busy-session", [self.human("go"), self.reply("Reading the files.")])
        self.transcript("idle-session", [self.reply("Which arbiter do you mean?")])
        self.transcript("done-session", [self.reply("Fixed it.\n\nРоботу завершено.")])
        lines = self.state_lines()
        self.assertEqual(["S: busy | busy-session | working | Reading the files.",
                          "S: idle | idle-session | waiting | Which arbiter do you mean?",
                          "S: dead | dead-session | gone | (no reply text)",
                          "S: done | done-session | finished | Fixed it."], lines)

    @staticmethod
    def sent(to, text, stamp):
        return {"type": "assistant", "timestamp": stamp, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "SendMessage", "input": {"to": to, "message": text}}]}}

    def answers_lines(self, *argv):
        code, out = self.run_main("answers", *argv)
        self.assertEqual(0, code, out)
        return out.splitlines()

    def test_answers_shows_the_owner_answer_after_the_last_report(self):  # Bug
        # 2026-11-21: the owner said «Так» in a discussion after its report; the lead asked him again.
        self.add("d1", name="Discuss: x")
        self.listing([{"sessionId": "d1", "pid": 1, "status": "idle"}])
        self.transcript("d1", [
            self.human("old talk"), self.sent("L: x", "ПИТАННЯ old", "2026-11-21T09:00:00Z"),
            self.human("між"), self.sent("L: x", "ЗАКРИТО plan agreed", "2026-11-21T10:11:00Z"),
            self.reply("Закриваю цю сесію обговорення?"),
            {"type": "user", "timestamp": "2026-11-21T10:19:16Z", "origin": {"kind": "human"},
             "message": {"role": "user", "content": "Так"}},
            {"type": "user", "origin": {"kind": "peer", "body": "the Lead asks something"}, "message": {"content": "x"}},
            self.reply("Закрито."),
            self.sent("ad9edd9da0e244387", "subagent follow-up", "2026-11-21T10:20:00Z"),  # not a report
        ])
        lines = self.answers_lines()
        self.assertEqual(3, len(lines), lines)
        self.assertTrue(lines[0].startswith("Discuss: x | d1 | after report 2026-11-21 "), lines[0])
        self.assertTrue(lines[0].endswith(" | 1 owner message"), lines[0])
        self.assertTrue(lines[1].endswith(" owner: Так"), lines[1])
        self.assertEqual("  session after it: Закрито.", lines[2])

    def test_answers_without_owner_message_or_report(self):  # Edge
        self.add("c1")
        self.add("o1", name="Own", owner=True)
        self.listing([{"sessionId": "c1", "pid": 1, "status": "busy"}, {"sessionId": "o1", "pid": 2, "status": "idle"}])
        self.transcript("c1", [self.human("task"), self.sent("P: x", "ГОТОВО", "2026-11-21T10:00:00Z"),
                               self.reply("Готово")])
        self.transcript("o1", [self.human(f"m{i}") for i in range(5)] + [self.reply("ok")])
        lines = self.answers_lines()
        self.assertTrue(lines[0].endswith(" | no owner message"), lines[0])
        self.assertTrue(lines[1].startswith("Own | o1 | last 3, no report sent | 3 owner messages"), lines[1])
        self.assertEqual(["m2", "m3", "m4"], [line.rsplit(" owner: ", 1)[1] for line in lines[2:5]])
        self.assertEqual("  session after it: ok", lines[5])

    def test_state_matches_interactive_session_by_session_id_and_prefix(self):  # Flow
        self.add("12345678-aaaa-bbbb", name="Own idea")
        self.listing([{"sessionId": "12345678-aaaa-bbbb", "name": "Own idea", "kind": "interactive", "pid": 9,
                       "status": "idle"}, {"id": "abcd1234", "sessionId": "abcd1234-0000", "pid": 3, "status": "busy"}])
        self.transcript("12345678-aaaa-bbbb", [self.reply("Done?")])
        self.assertEqual(["Own idea | 12345678-aaaa-bbbb | waiting | Done?"], self.state_lines())
        self.assertEqual(["Own idea | 12345678-aaaa-bbbb | waiting | Done?"], self.state_lines("--id", "12345678"))
        self.assertEqual("(no name) | abcd1234 | working | (no reply text)",
                         self.state_lines("--id", "abcd1234")[0])  # the short `id` of a background entry

    def test_state_finished_marker_forms(self):  # Edge
        self.add("s1", name="Own", owner=True)
        self.listing([{"sessionId": "s1", "pid": 1, "status": "idle"}])
        cases = {"Роботу завершено": True, "  **Роботу завершено**!  ": True, "«Роботу завершено»": True,
                 "Work finished.": True, "роботу завершено": True,
                 "Я напишу «Роботу завершено», коли закінчу": False, "Роботу завершено частково": False}
        for text, finished in cases.items():
            self.transcript("s1", [self.reply(f"Result line\n{text}\n")])
            state = self.state_lines("--id", "s1")[0].split(" | ")[2]
            self.assertEqual("finished" if finished else "waiting", state, text)

    def test_state_is_not_finished_when_the_owner_asked_again(self):  # Bug
        # Without this a follow-up to a finished session would be closed at once by the lead.
        self.add("s1", name="Own", owner=True)
        self.listing([{"sessionId": "s1", "pid": 1, "status": "busy"}])
        self.transcript("s1", [self.reply("Роботу завершено"), self.human("one more thing"),
                               {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}}])
        self.assertEqual("working", self.state_lines("--id", "s1")[0].split(" | ")[2])

    def test_state_uses_last_text_reply_and_cuts_the_gist(self):  # Edge
        self.listing([{"sessionId": "s1", "pid": 1, "status": "idle"}])
        tool_only = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}}
        long_text = "start " + "x" * 300 + " the question?"
        filler = [self.human("y" * 1000)] * 600  # pushes the reply out of the first chunk
        self.transcript("s1", [self.reply("old"), self.reply(long_text), tool_only, self.reply("ignored", isSidechain=True)])
        gist = self.state_lines("--id", "s1")[0].split(" | ", 3)[3]
        self.assertEqual(sessions.GIST_CHARS, len(gist))
        self.assertTrue(gist.startswith("...") and gist.endswith("the question?"))
        self.transcript("s1", [self.reply("far back")] + filler)
        self.assertIn("far back", self.state_lines("--id", "s1")[0])

    def test_state_unreadable_list_and_no_sessions(self):  # Edge
        self.listing([])
        self.assertEqual(["no active sessions"], self.state_lines())
        with mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(self.tmp / "missing.json")}):
            self.assertEqual(3, self.run_main("state")[0])

    def test_watch_exits_on_a_finished_session(self):  # Flow
        self.add("c1-session", name="Own idea", owner=True)
        self.add("c2-session", name="C: busy")
        self.listing([{"sessionId": "c1-session", "pid": 5, "status": "idle"},
                      {"sessionId": "c2-session", "pid": 6, "status": "busy"}])
        self.transcript("c1-session", [self.reply("All done.\nРоботу завершено")])
        code, out = self.run_main("watch", "--interval", "0")
        self.assertEqual((0, "finished: Own idea | c1-session\n"), (code, out))

    def test_a_c_session_never_reports_finished(self):  # Bug
        # A Manager whose last line is the marker would otherwise make every re-armed watcher exit at once.
        self.add("c1-session", name="C: task")
        self.listing([{"sessionId": "c1-session", "pid": 5, "status": "idle"}])
        self.transcript("c1-session", [self.reply("Work finished")])
        self.assertEqual(["C: task | c1-session | waiting | Work finished"], self.state_lines())
        code, out = self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")
        self.assertEqual((4, "time limit: 0.5 min, all alive\n"), (code, out))
        code, out = self.run_main("watch", "--id", "c1-session", "--interval", "60", "--max-minutes", "0.5")
        self.assertEqual(4, code)

    def test_watch_finished_and_gone_are_both_reported_once(self):  # Edge
        self.add("c1-session", name="A", owner=True)
        self.add("c2-session", name="B")
        self.listing([{"sessionId": "c1-session", "status": "stopped"}])  # c2 is not in the list
        self.transcript("c1-session", [self.reply("Роботу завершено")])
        code, out = self.run_main("watch", "--interval", "0")
        self.assertEqual((0, "gone: B | c2-session | not in the session list\nfinished: A | c1-session\n"), (code, out))

    def restart_file(self):
        return dev_kit_state.project_state_dir(self.project) / sessions.RESTART

    def restart_status(self):
        return self.run_main("restart", "status")[1]

    # protects: Flow
    def test_restart_handshake_request_ready_status_clear(self):
        self.assertEqual((0, "none\n"), self.run_main("restart", "status"))
        self.assertEqual((1, "dev-kit-sessions: no restart request is open\n"), self.run_main("restart", "ready"))
        self.assertEqual(0, self.run_main("restart", "request", "--version", "0.1.47")[0])
        self.assertRegex(self.restart_status(), r"^asked 0\.1\.47 \d+\n$")
        self.assertEqual(0, self.run_main("restart", "ready")[0])
        self.assertRegex(self.restart_status(), r"^ready 0\.1\.47 \d+\n$")
        self.assertEqual(0, self.run_main("restart", "clear")[0])
        self.assertFalse(self.restart_file().exists())
        self.assertEqual(0, self.run_main("restart", "clear")[0])  # absent is fine
        self.assertEqual("none\n", self.restart_status())

    # protects: Rule
    def test_restart_status_prints_the_age_of_the_last_mark(self):
        # The Pult watcher restarts only on a ready mark younger than 10 minutes: it parses this number.
        self.restart_file().parent.mkdir(parents=True, exist_ok=True)
        self.restart_file().write_text(json.dumps({"version": "0.1.47", "asked": time.time() - 900,
                                                   "ready": time.time() - 120}), encoding="utf-8")
        age = int(self.restart_status().split()[2])
        self.assertTrue(120 <= age < 130, age)
        self.restart_file().write_text(json.dumps({"version": "0.1.47", "asked": time.time() - 900}), encoding="utf-8")
        self.assertTrue(900 <= int(self.restart_status().split()[2]) < 910)

    # protects: Rule
    def test_restart_request_for_the_same_version_keeps_it_and_another_replaces_it(self):
        self.run_main("restart", "request", "--version", "0.1.47")
        self.run_main("restart", "ready")
        asked = json.loads(self.restart_file().read_text())["asked"]
        self.run_main("restart", "request", "--version", "0.1.47")
        self.assertTrue(self.restart_status().startswith("ready 0.1.47 "))
        self.assertEqual(asked, json.loads(self.restart_file().read_text())["asked"])
        self.run_main("restart", "request", "--version", "0.1.48")
        self.assertTrue(self.restart_status().startswith("asked 0.1.48 "))

    # protects: Flow
    def test_restart_ready_with_a_version_needs_no_request(self):
        # The lead notices the bump itself, so no request exists when it marks itself ready.
        self.assertEqual(0, self.run_main("restart", "ready", "--version", "0.1.47")[0])
        self.assertTrue(self.restart_status().startswith("ready 0.1.47 "))
        self.assertNotIn("asked", json.loads(self.restart_file().read_text()))

    # protects: Edge
    def test_restart_ready_with_a_version_keeps_a_request_for_it_and_replaces_another(self):
        self.run_main("restart", "request", "--version", "0.1.47")
        self.run_main("restart", "ready", "--version", "0.1.47")
        self.assertIn("asked", json.loads(self.restart_file().read_text()))
        self.run_main("restart", "ready", "--version", "0.1.48")  # a request for an older version is not this one
        saved = json.loads(self.restart_file().read_text())
        self.assertEqual(("0.1.48", False), (saved["version"], "asked" in saved))

    # protects: Flow
    def test_watch_exits_7_on_an_open_restart_request_even_with_nothing_to_watch(self):
        self.run_main("restart", "request", "--version", "0.1.47")
        self.assertEqual((7, "restart requested: 0.1.47\n"), self.run_main("watch", "--interval", "0"))
        self.assertFalse(self.lock().exists())  # the exit leaves no lock of this watcher behind
        self.run_main("restart", "clear")
        self.run_main("restart", "request", "--version", "0.1.47")
        self.assertEqual(7, self.run_main("watch", "--id", "c1-session", "--interval", "0")[0])

    # protects: Bug
    # Broke: the lead's re-armed watcher exited 7 again at once on the same request, a wake-up loop
    def test_watch_exits_7_once_per_request(self):
        self.add("c1-session")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])
        self.run_main("restart", "request", "--version", "0.1.47")
        self.assertEqual(7, self.run_main("watch", "--interval", "0")[0])
        self.assertTrue(json.loads(self.restart_file().read_text())["notified"])
        self.assertEqual(4, self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")[0])
        self.run_main("restart", "request", "--version", "0.1.47")  # the same version keeps the notified mark
        self.assertEqual(4, self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")[0])
        self.run_main("restart", "request", "--version", "0.1.48")  # a new version is a new request
        self.assertEqual(7, self.run_main("watch", "--interval", "0")[0])

    # protects: Rule
    def test_watch_ignores_a_ready_or_absent_restart_request(self):
        self.add("c1-session")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])
        self.run_main("restart", "ready", "--version", "0.1.47")
        self.assertEqual(4, self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")[0])
        self.run_main("restart", "clear")
        self.assertEqual(4, self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")[0])

    # protects: Flow
    def test_watch_exits_7_when_a_request_arrives_while_it_waits(self):
        self.add("c1-session")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "working"}])

        def sleep(_seconds):
            self.run_main("restart", "request", "--version", "0.1.47")

        with mock.patch.object(sessions.time, "sleep", sleep):
            code, out = self.run_main("watch", "--interval", "1")
        self.assertEqual((7, "restart requested: 0.1.47\n"), (code, out))


    # protects: Bug
    def test_an_id_with_a_carriage_return_still_matches(self):  # the Lead pasted `claude --bg` output with a CR
        state = dev_kit_state.project_state_dir(self.project)
        (state / "sessions.json").write_text(json.dumps([{"id": "c1-session\r", "name": "C: cr", "status": "active"}]),
                                             encoding="utf-8")
        self.listing([{"sessionId": "c1-session", "pid": 5, "status": "busy"}])
        self.assertEqual(["C: cr | c1-session | working | (no reply text)"], self.state_lines())
        self.add("c2-session\r\n", name="C: two")
        self.assertEqual("c2-session", self.records()[-1]["id"])
        self.assertEqual(0, self.run_main("end", "--id", "c2-session \r")[0])

    # protects: Bug
    def test_claude_is_found_in_the_usual_install_places_when_not_on_path(self):
        home = self.tmp / "home"
        native = home / ".local" / "bin" / ("claude.exe" if os.name == "nt" else "claude")
        with mock.patch.object(sessions.shutil, "which", lambda _name: None), \
                mock.patch.object(sessions.Path, "home", lambda: home), \
                mock.patch.dict(os.environ, {"APPDATA": str(self.tmp / "roaming"), "LOCALAPPDATA": str(self.tmp / "local")}):
            self.assertIsNone(sessions.find_claude())
            with self.assertRaisesRegex(RuntimeError, "not on PATH or in the usual install places"), \
                    mock.patch.dict(os.environ, {sessions.AGENTS_ENV: ""}):
                sessions.agents_list()
            native.parent.mkdir(parents=True)
            native.write_text("", encoding="utf-8")
            self.assertEqual(str(native), sessions.find_claude())
            if os.name == "nt":
                npm = self.tmp / "roaming" / "npm" / "claude.cmd"
                npm.parent.mkdir(parents=True)
                npm.write_text("", encoding="utf-8")
                native.unlink()
                self.assertEqual(str(npm), sessions.find_claude())
        with mock.patch.object(sessions.shutil, "which", lambda _name: "/on/path/claude"):
            self.assertEqual("/on/path/claude", sessions.find_claude())

    @staticmethod
    def limit_notice(uuid="lim-1", resets=1795014000):
        return {"type": "assistant", "uuid": uuid, "isSidechain": False, "apiError": "usage_limit_reached",
                "error": "rate_limit", "isApiErrorMessage": True,
                "apiErrorParams": {"rate_limit_info": {"status": "rejected", "resetsAt": resets}},
                "message": {"role": "assistant", "model": "<synthetic>",
                            "content": [{"type": "text", "text": "You've hit your weekly limit"}]}}

    # protects: Rule
    def test_usage_limit_is_the_last_notice_only(self):
        path = self.projects / "p1" / "s1.jsonl"
        self.transcript("s1", [self.human("go"), self.reply("Working on it."), self.limit_notice()])
        self.assertEqual(("lim-1", 1795014000), sessions.usage_limit(path))
        meta = {"type": "user", "isMeta": True, "message": {"content": "<reminder>"}}
        side = dict(self.reply("subagent text"), isSidechain=True)
        self.transcript("s1", [self.reply("x"), self.limit_notice(), meta, side])
        self.assertEqual("lim-1", sessions.usage_limit(path)[0])
        self.transcript("s1", [self.limit_notice(), self.human("продовж")])  # asked again: not stopped any more
        self.assertIsNone(sessions.usage_limit(path))
        self.transcript("s1", [self.limit_notice(), self.reply("Back to work.")])
        self.assertIsNone(sessions.usage_limit(path))
        old = {k: v for k, v in self.limit_notice().items() if k not in ("apiError", "apiErrorParams")}
        self.transcript("s1", [old])
        self.assertEqual(("lim-1", None), sessions.usage_limit(path))

    # protects: Bug
    def test_usage_limit_ignores_helper_reports_that_arrive_after_the_notice(self):
        path = self.projects / "p1" / "s1.jsonl"
        report = {"type": "user", "uuid": "rep-1", "isSidechain": False,
                  "origin": {"kind": "task-notification", "producer": "session-task"},
                  "message": {"role": "user", "content": "<task-notification>\n<task-id>a1</task-id>\n</task-notification>"}}
        self.transcript("s1", [self.limit_notice(), report, dict(report, uuid="rep-2")])
        self.assertEqual(("lim-1", 1795014000), sessions.usage_limit(path))
        self.transcript("s1", [self.limit_notice(), report, self.reply("Back to work.")])
        self.assertIsNone(sessions.usage_limit(path))
        self.transcript("s1", [self.limit_notice(), report, self.human("продовж")])
        self.assertIsNone(sessions.usage_limit(path))

    # protects: Flow
    def test_state_shows_a_session_stopped_on_the_limit_as_limited(self):
        self.add("c1-session", name="C: lim")
        self.listing([{"sessionId": "c1-session", "pid": 5, "status": "idle", "state": "blocked"}])
        self.transcript("c1-session", [self.reply("Halfway."), self.limit_notice(resets=None)])
        self.assertEqual(["C: lim | c1-session | limited | resets unknown; Halfway."], self.state_lines())

    # protects: Flow
    def test_watch_reports_a_limit_stop_once_and_a_new_one_again(self):
        self.add("c1-session", name="C: lim")
        self.add("c2-session", name="C: ok")
        self.listing([{"sessionId": "c1-session", "pid": 5, "state": "blocked"},
                      {"sessionId": "c2-session", "pid": 6, "state": "working"}])
        self.transcript("c1-session", [self.reply("x"), self.limit_notice(resets=None)])
        code, out = self.run_main("watch", "--interval", "0")
        self.assertEqual((0, "limited: C: lim | c1-session | resets unknown\n"), (code, out))
        code, out = self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")  # re-armed: same stop
        self.assertEqual((4, "time limit: 0.5 min, all alive\n"), (code, out))
        self.transcript("c1-session", [self.limit_notice(), self.human("продовж"), self.limit_notice("lim-2", None)])
        code, out = self.run_main("watch", "--interval", "0")
        self.assertEqual((0, "limited: C: lim | c1-session | resets unknown\n"), (code, out))

    # protects: Flow
    def test_limited_command_reads_transcripts_only(self):
        self.transcript("s1", [self.limit_notice(resets=None)])
        self.transcript("s2", [self.reply("fine")])
        with mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(self.tmp / "missing.json")}):
            code, out = self.run_main("limited", "--id", "s1", "--id", "s2", "--id", "s3")
        self.assertEqual((0, "s1 | unknown | lim-1\n"), (code, out))

    # protects: Edge
    def test_usage_limit_reads_past_the_first_window(self):
        path = self.projects / "p1" / "s1.jsonl"
        big = self.reply("y" * (sessions.CHUNK + 10))
        self.transcript("s1", [self.limit_notice("old"), self.human("go"), big, self.limit_notice("new")])
        self.assertEqual("new", sessions.usage_limit(path)[0])
        self.transcript("s1", [self.limit_notice("old"), big])  # the last entry is larger than one window
        self.assertIsNone(sessions.usage_limit(path))
        entries = list(sessions.tail_entries(path))
        self.assertEqual(["assistant", "assistant"], [entry["type"] for entry in entries])
        self.assertEqual("old", entries[1]["uuid"])

    # protects: Rule
    def test_a_limited_session_without_a_pid_is_gone(self):
        self.add("c1-session", name="C: lim")
        self.listing([{"sessionId": "c1-session", "status": "stopped"}])
        self.transcript("c1-session", [self.limit_notice(resets=None)])
        self.assertEqual(["C: lim | c1-session | gone | (no reply text)"], self.state_lines())
        self.assertEqual([], sessions.limited_sessions([("C: lim", "c1-session")], sessions.agents_list(True)))

    # protects: Bug
    def test_limits_file_keeps_the_stops_of_other_watchers(self):
        path = dev_kit_state.project_state_dir(self.project) / sessions.REGISTRY
        (path.with_name(sessions.LIMITS)).write_text(json.dumps({"other": "k0"}), encoding="utf-8")
        self.assertEqual([("n", "me", "k1", None)], sessions.new_limits([("n", "me", "k1", None)], path, {"me"}))
        self.assertEqual({"other": "k0", "me": "k1"}, json.loads(path.with_name(sessions.LIMITS).read_text()))
        self.assertEqual([], sessions.new_limits([], path, {"me"}))
        self.assertEqual({"other": "k0"}, json.loads(path.with_name(sessions.LIMITS).read_text()))

    # protects: Edge
    def test_reset_time_in_seconds_or_milliseconds(self):
        self.assertEqual(sessions.reset_text(1795014000), sessions.reset_text(1795014000000))
        self.assertEqual("unknown", sessions.reset_text(None))

    @staticmethod
    def ago(minutes):
        from datetime import datetime, timedelta, timezone
        return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")

    # protects: Flow
    def test_watch_reports_a_long_wait_once(self):
        self.add("c1-session", name="C: wait")
        self.listing([{"sessionId": "c1-session", "pid": 5, "status": "idle", "state": "idle"}])
        self.transcript("c1-session", [self.human("go"), self.reply("Question?", timestamp=self.ago(19))])
        code, out = self.run_main("watch", "--interval", "60", "--max-minutes", "0.5", "--stale-minutes", "20")
        self.assertEqual((4, "time limit: 0.5 min, all alive\n"), (code, out))
        wait = self.ago(21)
        self.transcript("c1-session", [self.human("go"), self.reply("Question?", timestamp=wait)])
        code, out = self.run_main("watch", "--interval", "0", "--stale-minutes", "20")
        self.assertEqual((0, "stale: C: wait | c1-session | waiting 21 min\n"), (code, out))
        self.listing([{"sessionId": "c1-session", "pid": 5, "status": "busy"}])  # a busy flicker keeps the record
        self.assertEqual(4, self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")[0])
        self.listing([{"sessionId": "c1-session", "pid": 5, "status": "idle", "state": "idle"}])
        code, out = self.run_main("watch", "--interval", "60", "--max-minutes", "0.5")  # restarted: same wait
        self.assertEqual((4, "time limit: 0.5 min, all alive\n"), (code, out))
        self.transcript("c1-session", [self.reply("Question?", timestamp=wait), self.human("yes"),
                                       self.reply("Next question?", timestamp=self.ago(20))])
        code, out = self.run_main("watch", "--interval", "0")  # a new wait reports again
        self.assertEqual((0, "stale: C: wait | c1-session | waiting 20 min\n"), (code, out))

    # protects: Rule
    def test_a_busy_asked_or_limited_session_is_not_stale(self):
        self.add("c1-session", name="C: busy")
        self.add("c2-session", name="C: asked")
        self.listing([{"sessionId": "c1-session", "pid": 5, "status": "busy"},
                      {"sessionId": "c2-session", "pid": 6, "status": "idle"}])
        self.transcript("c1-session", [self.reply("x", timestamp=self.ago(30))])
        self.transcript("c2-session", [self.reply("x", timestamp=self.ago(30)), self.human("go on")])
        agents = sessions.agents_list(True)
        watched = [("C: busy", "c1-session"), ("C: asked", "c2-session")]
        self.assertEqual([], sessions.stale_sessions(watched, agents, 20, time.time()))
        self.transcript("c2-session", [self.reply("x", timestamp=self.ago(30)), self.limit_notice(resets=None)])
        self.assertEqual([], sessions.stale_sessions(watched, agents, 20, time.time()))

    def check_setup(self):
        """Six registered sessions, one of each kind of event, and an open restart request. Returns the lines
        `check` must print."""
        self.add("o1-session", name="O: done", owner=True)
        self.add("g1-session", name="C: gone")
        self.add("l1-session", name="C: lim")
        self.add("s1-session", name="C: wait")
        self.add("f1-session", name="C: big")
        self.listing([{"sessionId": "o1-session", "pid": 1, "state": "idle"},
                      {"sessionId": "l1-session", "pid": 2, "state": "blocked"},
                      {"sessionId": "s1-session", "pid": 3, "state": "idle"},
                      {"sessionId": "f1-session", "pid": 4, "status": "busy"}])  # g1 is not in the list
        self.transcript("o1-session", [self.human("go"), self.reply("Done.\nWork finished", timestamp="2026-11-20T10:00:00Z")])
        self.transcript("g1-session", [self.reply("bye", timestamp="2026-11-20T09:00:00Z")])
        self.transcript("l1-session", [self.reply("x"), self.limit_notice(resets=None)])
        self.transcript("s1-session", [self.human("go"), self.reply("Question?", timestamp=self.ago(30))])
        self.transcript("f1-session", [self.assistant(0, 0, 130000)])
        self.run_main("restart", "request", "--version", "9.9.9")
        return ["restart | - | - | 9.9.9 | 9.9.9",
                "gone | C: gone | g1-session | not in the session list | 2026-11-20T09:00:00Z",
                "finished | O: done | o1-session | finished | 2026-11-20T10:00:00Z",
                "limited | C: lim | l1-session | resets unknown | lim-1",
                "fill | C: big | f1-session | 65% of 200000 | fill"]

    # protects: Flow
    def test_check_prints_each_kind_of_event_and_writes_no_marks(self):
        expected = self.check_setup()
        code, out = self.run_main("check")
        self.assertEqual(0, code)
        lines = out.splitlines()
        stale = [line for line in lines if line.startswith("stale | ")]
        self.assertEqual(1, len(stale))
        self.assertRegex(stale[0], r"^stale \| C: wait \| s1-session \| waiting 30 min \| \S+Z$")
        self.assertEqual(expected, [line for line in lines if not line.startswith("stale | ")])
        folder = dev_kit_state.project_state_dir(self.project)
        for name in (sessions.LIMITS, sessions.STALE, sessions.DELIVERED):
            self.assertFalse((folder / name).exists(), name)
        self.assertNotIn("notified", json.loads((folder / sessions.RESTART).read_text()))
        self.assertEqual(out, self.run_main("check")[1])  # nothing was marked: the same lines again

    # protects: Flow
    def test_check_leaves_out_what_mark_recorded_and_reports_a_new_key(self):
        self.check_setup()
        lines = [line.split(" | ") for line in self.run_main("check")[1].splitlines()]
        self.assertEqual(6, len(lines))
        for kind, _name, wanted, _detail, key in lines:
            argv = ["mark", "--kind", kind, "--key", key] + ([] if kind == "restart" else ["--id", wanted])
            self.assertEqual((0, f"marked {kind} {'-' if kind == 'restart' else wanted}\n"), self.run_main(*argv))
        self.assertEqual((0, ""), self.run_main("check"))
        folder = dev_kit_state.project_state_dir(self.project)
        self.assertEqual({"g1-session": {"gone": "2026-11-20T09:00:00Z"}, "o1-session": {"finished": "2026-11-20T10:00:00Z"},
                          "f1-session": {"fill": "fill"}}, json.loads((folder / sessions.DELIVERED).read_text()))
        self.assertEqual("lim-1", json.loads((folder / sessions.LIMITS).read_text())["l1-session"])
        self.assertIn("notified", json.loads((folder / sessions.RESTART).read_text()))
        self.assertEqual("not marked", self.run_main("mark", "--kind", "restart", "--key", "1.0.0")[1][:10])
        self.transcript("g1-session", [self.reply("back", timestamp="2026-11-20T11:00:00Z")])  # came back, went again
        self.assertEqual((0, "gone | C: gone | g1-session | not in the session list | 2026-11-20T11:00:00Z\n"),
                         self.run_main("check", "--id", "g1-session"))

    # protects: Rule
    def test_check_keeps_the_closed_grace_across_calls(self):
        self.add("c1-session", name="C: x")
        self.listing([{"sessionId": "c1-session", "state": "stopped"}])
        closed = dev_kit_state.project_state_dir(self.project) / sessions.CLOSED
        self.assertEqual((0, ""), self.run_main("check"))
        first = json.loads(closed.read_text())["c1-session"]
        self.assertEqual((0, ""), self.run_main("check"))
        self.assertEqual(first, json.loads(closed.read_text())["c1-session"])  # the clock is not restarted
        closed.write_text(json.dumps({"c1-session": first - sessions.CLOSED_GRACE - 1}), encoding="utf-8")
        self.assertEqual((0, "gone | C: x | c1-session | stopped | none\n"), self.run_main("check"))
        self.listing([{"sessionId": "c1-session", "pid": 7}])  # a pid again clears the clock
        self.assertEqual((0, ""), self.run_main("check"))
        self.assertEqual({}, json.loads(closed.read_text()))

    # protects: Edge
    def test_check_with_an_unreadable_session_list_exits_3(self):
        self.add("c1-session")
        with mock.patch.dict(os.environ, {sessions.AGENTS_ENV: str(self.tmp / "missing.json")}):
            code, out = self.run_main("check")
        self.assertEqual(3, code)
        self.assertIn("could not be read", out)

    # protects: Rule
    def test_fill_over_only_prints_only_the_over_rows(self):
        self.assertEqual((0, ""), self.run_main("fill", "--over-only"))
        self.add("c1-session", name="C: big")
        self.add("c2-session", name="C: small")
        self.add("c3-session", name="C: none")
        self.transcript("c1-session", [self.assistant(0, 0, 150000)])
        self.transcript("c2-session", [self.assistant(0, 0, 1000)])
        self.assertEqual((0, "C: big | c1-session | 150000 tokens | window 200000 | 75% OVER\n"),
                         self.run_main("fill", "--over-only"))
        self.assertIn("C: none | c3-session | no transcript", self.run_main("fill")[1])

    # protects: Bug
    def test_last_usage_skips_side_chain_lines(self):
        path = self.projects / "p1" / "s1.jsonl"
        side = dict(self.assistant(0, 0, 500), isSidechain=True)  # a subagent's small context, written last
        self.transcript("s1", [self.assistant(0, 0, 150000), side])
        self.assertEqual(150000, sessions.last_usage(path)[0])
        self.transcript("s1", [side])
        self.assertIsNone(sessions.last_usage(path))

    # protects: Flow
    def test_size_prints_the_context_and_counts_turn_starts_and_units_since_the_last_call(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "spend-kit" / "scripts"))
        import spend  # the test reads the expected units from spend-kit; sessions.py itself runs the `spend-kit` command
        path = self.projects / "p1" / "s1.jsonl"
        state = self.tmp / "wakes.json"
        first = self.assistant(100, 0, 5000)
        first["message"]["id"] = "m1"
        self.transcript("s1", [self.human("go"), first])
        self.assertEqual((0, "s1 | 5100 | 200000 | claude-haiku-4-5-20251001\n"), self.run_main("size", "--id", "s1", "--id", "none"))
        self.assertFalse(state.exists())
        self.assertEqual((0, "s1 | 5100 | 200000 | claude-haiku-4-5-20251001 | owner=0 peer=0 notify=0 | units=0\n"),
                         self.run_main("size", "--id", "s1", "--wakes", str(state)))  # the first call counts nothing
        second = self.assistant(10, 0, 6000)
        second["message"]["id"] = "m2"
        entries = [{"type": "user", "message": {"role": "user", "content": "next"}},
                   {"type": "user", "isMeta": True, "origin": {"kind": "peer", "body": "hi"},
                    "message": {"role": "user", "content": "<cross-session>hi</cross-session>"}},
                   {"type": "user", "origin": {"kind": "task-notification"},
                    "message": {"role": "user", "content": "<task-notification>done</task-notification>"}},
                   {"type": "user", "isMeta": True, "message": {"role": "user", "content": "<reminder>x</reminder>"}},
                   {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}},
                   dict(self.human("side question"), isSidechain=True),
                   second, second, dict(self.assistant(0, 0, 9000), isSidechain=True)]
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(json.dumps(entry) for entry in entries) + "\n")
        units = round(spend.units_of(second["message"]["usage"], second["message"]["model"]))  # the twin counts once
        code, out = self.run_main("size", "--id", "s1", "--wakes", str(state))
        self.assertEqual((0, f"s1 | 6010 | 200000 | claude-haiku-4-5-20251001 | owner=1 peer=1 notify=2 | units={units}\n"),
                         (code, out))
        self.assertIn("owner=0 peer=0 notify=0 | units=0", self.run_main("size", "--id", "s1", "--wakes", str(state))[1])

    def handoff_file(self):
        return dev_kit_state.project_state_dir(self.project) / sessions.HANDOFF

    # protects: Flow
    def test_handoff_save_status_go_clear(self):
        # The lead saves, the Pult watcher reads the status and clears the marker once the new lead runs.
        self.assertEqual((0, "none\n"), self.run_main("handoff", "status"))
        self.assertEqual((0, "handoff saved: handoff-1.md\n"), self.run_main("handoff", "save", "--file", "handoff-1.md"))
        self.assertRegex(self.run_main("handoff", "status")[1], r"^saved handoff-1\.md \d+\n$")
        self.assertEqual({"file": "handoff-1.md", "go": False}, {k: json.loads(self.handoff_file().read_text())[k] for k in ("file", "go")})
        self.assertEqual((0, "handoff go: handoff-1.md\n"), self.run_main("handoff", "go"))
        self.assertRegex(self.run_main("handoff", "status")[1], r"^go handoff-1\.md \d+\n$")
        self.assertEqual((0, "handoff cleared\n"), self.run_main("handoff", "clear"))
        self.assertFalse(self.handoff_file().exists())
        self.assertEqual((0, "handoff cleared\n"), self.run_main("handoff", "clear"))  # absent is fine
        self.assertEqual("none\n", self.run_main("handoff", "status")[1])

    # protects: Rule
    def test_handoff_save_accepts_only_a_bare_markdown_file_name(self):
        # The name ends up in a command line of the watcher: no path, no space, no quote.
        for bad in ("../x.md", "a/b.md", "a\\b.md", "x.txt", "x", ".x.md", "a b.md", 'a"b.md', "a;b.md", "-x.md", "a.md\nb", ""):
            code, out = self.run_main("handoff", "save", f"--file={bad}")
            self.assertEqual(1, code, bad)
            self.assertFalse(self.handoff_file().exists(), bad)
        self.assertEqual(0, self.run_main("handoff", "save", "--file", "Handoff-a.b_2.md")[0])

    # protects: Edge
    def test_handoff_go_without_a_saved_handoff_fails(self):
        self.assertEqual((1, "dev-kit-sessions: no handoff is saved\n"), self.run_main("handoff", "go"))
        self.assertFalse(self.handoff_file().exists())

    # protects: Rule
    def test_handoff_save_with_go_and_a_re_save_keeps_go(self):
        # A lead that was told "go" must not lose it when it saves the file again.
        self.run_main("handoff", "save", "--file", "a.md", "--go")
        self.assertTrue(json.loads(self.handoff_file().read_text())["go"])
        self.run_main("handoff", "save", "--file", "b.md")
        saved = json.loads(self.handoff_file().read_text())
        self.assertEqual(("b.md", True), (saved["file"], saved["go"]))
        self.assertRegex(self.run_main("handoff", "status")[1], r"^go b\.md \d+\n$")
        self.run_main("handoff", "clear")
        self.run_main("handoff", "save", "--file", "c.md")
        self.assertFalse(json.loads(self.handoff_file().read_text())["go"])

    # protects: Rule
    def test_handoff_status_prints_the_age_since_the_save(self):
        # The Pult watcher parses this number.
        self.handoff_file().parent.mkdir(parents=True, exist_ok=True)
        self.handoff_file().write_text(json.dumps({"file": "a.md", "saved": time.time() - 700, "go": False}), encoding="utf-8")
        self.assertTrue(700 <= int(self.run_main("handoff", "status")[1].split()[2]) < 710)

    # protects: Edge
    def test_handoff_works_with_an_unreadable_registry(self):
        # The lead hands off when it is full, whatever state the registry is in.
        (dev_kit_state.project_state_dir(self.project) / "sessions.json").write_text("{nope", encoding="utf-8")
        self.assertEqual(0, self.run_main("handoff", "save", "--file", "a.md")[0])
        self.assertTrue(self.run_main("handoff", "status")[1].startswith("saved a.md "))
        self.assertEqual(0, self.run_main("handoff", "go")[0])
        self.assertEqual(0, self.run_main("handoff", "clear")[0])

    # protects: Edge
    def test_handoff_status_of_a_broken_file_is_none(self):
        self.handoff_file().parent.mkdir(parents=True, exist_ok=True)
        self.handoff_file().write_text("{nope", encoding="utf-8")
        self.assertEqual((0, "none\n"), self.run_main("handoff", "status"))

    # protects: Rule
    def test_handoff_go_status_counts_from_the_go_not_from_the_save(self):
        # The watcher moves a go lead 30 s after its CAPS warning, which comes right before `handoff go`.
        self.handoff_file().parent.mkdir(parents=True, exist_ok=True)
        self.handoff_file().write_text(json.dumps({"file": "a.md", "saved": time.time() - 700, "go": False}), encoding="utf-8")
        self.assertEqual((0, "handoff go: a.md\n"), self.run_main("handoff", "go"))
        self.assertLess(int(self.run_main("handoff", "status")[1].split()[2]), 10)
        self.run_main("handoff", "save", "--file", "b.md")  # a re-save keeps the go time
        self.assertRegex(self.run_main("handoff", "status")[1], r"^go b\.md \d\n$")
        # A go file written before go_at existed: the age since the save, as before.
        self.handoff_file().write_text(json.dumps({"file": "a.md", "saved": time.time() - 700, "go": True}), encoding="utf-8")
        self.assertTrue(700 <= int(self.run_main("handoff", "status")[1].split()[2]) < 710)

    # protects: Flow
    def test_handoff_request_reaches_the_lead_once_through_check_and_mark(self):
        # A lead that is not quiet is asked once; the watcher delivers the event and marks it.
        self.assertEqual((1, "dev-kit-sessions: no handoff is saved\n"), self.run_main("handoff", "request"))
        self.run_main("handoff", "save", "--file", "a.md")
        self.assertEqual((0, ""), self.run_main("check"))
        self.assertEqual((0, "handoff asked: a.md\n"), self.run_main("handoff", "request"))
        self.assertEqual((0, "handoff already asked: a.md\n"), self.run_main("handoff", "request"))
        self.assertEqual((0, "handoff | - | - | a.md | a.md\n"), self.run_main("check"))
        self.assertEqual((0, "not marked handoff - (no open request for b.md)\n"),
                         self.run_main("mark", "--kind", "handoff", "--key", "b.md"))
        self.assertEqual((0, "marked handoff -\n"), self.run_main("mark", "--kind", "handoff", "--key", "a.md"))
        self.assertEqual((0, ""), self.run_main("check"))
        self.run_main("handoff", "save", "--file", "b.md")  # a new file is the same move: no second request
        saved = json.loads(self.handoff_file().read_text())
        self.assertTrue(saved["asked"] and saved["notified"])
        self.assertEqual((0, ""), self.run_main("check"))
        self.run_main("handoff", "clear")
        self.run_main("handoff", "save", "--file", "c.md")
        self.run_main("handoff", "request")
        self.run_main("handoff", "go")  # the lead answered before the event reached it
        self.assertEqual((0, ""), self.run_main("check"))

    def job(self, short, session_id, link, resume_id=None):
        folder = self.jobs / short
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "state.json").write_text(json.dumps({"sessionId": session_id, "resumeSessionId": resume_id or session_id,
                                                       "linkScanPath": str(link), "name": "P: x"}), encoding="utf-8")

    # protects: Bug
    def test_transcript_follows_the_jobs_new_file_after_a_clear(self):
        # After /clear the job keeps its sessionId but writes a new file; the old one would make the lead look full.
        self.transcript("old-session", [self.assistant(0, 0, 150000)])
        self.transcript("new-session", [self.assistant(0, 0, 2000)])
        self.job("oldsess1", "old-session", self.projects / "p1" / "new-session.jsonl", resume_id="new-session")
        self.job("other111", "other-session", self.projects / "p1" / "other-session.jsonl")
        for own in ("old-session", "new-session"):  # CLAUDE_CODE_SESSION_ID may hold either after the clear
            with mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": own}):
                self.assertEqual((0, f"self | {own} | 2000 tokens | window 200000 | 1%\n"), self.run_main("fill", "--self"))
        self.assertEqual((0, "old-session | 2000 | 200000 | claude-haiku-4-5-20251001\n"),
                         self.run_main("size", "--id", "old-session"))
        (self.projects / "p1" / "new-session.jsonl").unlink()  # a job whose file is gone: the id's own file
        self.assertEqual((0, "self | old-session | 150000 tokens | window 200000 | 75% OVER\n"),
                         self.run_main("fill", "--self", "old-session"))

    # protects: Flow
    def test_fill_self_reads_the_own_transcript_by_env_or_by_id(self):
        # The lead asks about its own context; the registry holds only the Manager sessions.
        self.transcript("me-session", [self.assistant(0, 0, 50000)])
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": "me-session"}):
            self.assertEqual((0, "self | me-session | 50000 tokens | window 200000 | 25%\n"), self.run_main("fill", "--self"))
        self.assertEqual((0, "self | me-session | 50000 tokens | window 200000 | 25%\n"),
                         self.run_main("fill", "--self", "me-session"))
        self.assertEqual((0, "self | other | no transcript\n"), self.run_main("fill", "--self", "other"))

    # protects: Edge
    def test_fill_self_without_an_id_fails(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CODE_SESSION_ID": ""}):
            code, out = self.run_main("fill", "--self")
        self.assertEqual(1, code)
        self.assertIn("session id", out)

    # protects: Rule
    def test_fill_self_ignores_the_registry_and_honours_limit_window_and_over_only(self):
        self.add("a1")
        self.transcript("a1", [self.assistant(0, 0, 150000)])  # a Manager row that must not show up
        (dev_kit_state.project_state_dir(self.project) / "sessions.json").write_text("{nope", encoding="utf-8")
        self.transcript("me-session", [self.assistant(0, 0, 150000)])
        self.assertEqual((0, "self | me-session | 150000 tokens | window 200000 | 75% OVER\n"),
                         self.run_main("fill", "--self", "me-session"))
        self.assertEqual((0, "self | me-session | 150000 tokens | window 200000 | 75% OVER\n"),
                         self.run_main("fill", "--self", "me-session", "--over-only"))
        self.assertIn("window 1000000 | 15%\n", self.run_main("fill", "--self", "me-session", "--window", "1000000")[1])
        self.assertEqual((0, ""), self.run_main("fill", "--self", "me-session", "--limit", "0.9", "--over-only"))
        self.assertEqual((0, ""), self.run_main("fill", "--self", "other", "--over-only"))

    def releases(self, data):
        path = self.tmp / "releases.json"
        path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
        return str(path)

    # protects: Rule
    def test_release_names_the_newest_critical_release_the_lead_lacks(self):
        marks = self.releases({
            "0.1.9": {"kind": "critical", "date": "2026-11-20", "reason": "old"},
            "0.1.10": {"kind": "critical", "date": "2026-11-21", "reason": "a"},
            "0.1.11": {"kind": "routine", "date": "2026-11-21", "reason": "r"},
            "0.1.12": {"kind": "critical", "date": "2026-11-22", "reason": "b"},
            "0.1.13": {"kind": "critical", "date": "2026-11-23", "reason": "c"}})
        for start, to, said in (("0.1.9", "0.1.12", "critical 0.1.12: b\n"),  # 0.1.10 > 0.1.9: compared as numbers
                                ("0.1.9", "0.1.10", "critical 0.1.10: a\n"),
                                ("0.1.10", "0.1.11", "routine\n"),  # the version it started on is not lacked
                                ("0.1.12", "0.1.12", "routine\n")):
            with self.subTest(start=start, to=to):
                self.assertEqual((0, said), self.run_main("release", "--from", start, "--to", to, "--file", marks))

    # protects: Rule
    def test_release_for_an_unknown_start_version_goes_by_the_start_day(self):
        marks = self.releases({"0.1.10": {"kind": "critical", "date": "2026-11-21", "reason": "a"},
                               "0.1.11": {"kind": "critical", "date": "2026-11-22", "reason": "b"},
                               "0.1.12": {"kind": "routine", "date": "2026-11-23", "reason": "r"}})
        started = datetime_local(2026, 11, 22, 12)
        self.assertEqual((0, "critical 0.1.11: b\n"), self.run_main(
            "release", "--from", "older", "--to", "0.1.12", "--started", started, "--file", marks))
        self.assertEqual((0, "routine\n"), self.run_main(
            "release", "--from", "older", "--to", "0.1.12", "--started", datetime_local(2026, 11, 23, 9), "--file", marks))
        self.assertEqual((0, "routine\n"), self.run_main("release", "--from", "older", "--to", "0.1.12", "--file", marks),
                         "no start time either: nothing is known, so routine")

    # protects: Edge
    def test_release_with_a_missing_or_broken_mark_counts_as_routine(self):
        missing = str(self.tmp / "none.json")
        self.assertEqual((0, "routine\n"), self.run_main("release", "--from", "0.1.1", "--to", "0.1.2", "--file", missing))
        for data in ("{nope", "[]", {"0.1.2": {"kind": "urgent", "date": "2026-11-23", "reason": "x"}},
                     {"0.1.2": {"kind": "critical", "date": "23.11.2026", "reason": "x"}}):
            with self.subTest(data=data):
                code, out = self.run_main("release", "--from", "0.1.1", "--to", "0.1.2", "--file", self.releases(data))
                self.assertEqual(0, code)
                self.assertIn("routine\n", out)
                self.assertIn("dev-kit-sessions: ", out)
                self.assertNotIn("critical", out)

    def owner(self, text, minutes_ago):
        return {"type": "user", "timestamp": self.ago(minutes_ago), "origin": {"kind": "human"},
                "message": {"role": "user", "content": text}}

    # protects: Rule
    def test_quiet_tells_a_recent_owner_message_and_an_open_question(self):
        tool_result = {"type": "user", "timestamp": self.ago(0),
                       "message": {"role": "user", "content": [{"type": "tool_result", "content": "ok"}]}}
        peer = {"type": "user", "timestamp": self.ago(1), "isMeta": True, "origin": {"kind": "peer", "body": "C: done"},
                "message": {"role": "user", "content": "C: done"}}
        question = "Звіт.\n\nЛишаємо X? (бо так простіше)\n   Рекомендую: так - це дешевше.\n"
        cases = (("owner wrote 2 min ago", [self.owner("go on", 2), self.reply("Done.")], "active owner "),
                 ("question with its recommendation", [self.owner("go", 10), self.reply(question)], "active open question"),
                 ("bold question", [self.owner("go", 10), self.reply("Merge it?**  ")], "active open question"),
                 ("answered long ago", [self.reply(question), self.owner("так", 10), self.reply("Merged.")], "quiet"),
                 ("question answered", [self.reply(question), self.owner("так", 10)], "quiet"),
                 ("peer and tool result are not the owner", [self.owner("go", 10), self.reply("Done."), peer, tool_result],
                  "quiet"),
                 ("a subagent's question is not the lead's", [self.owner("go", 10), self.reply("Done."),
                                                             self.reply("Which file?", isSidechain=True)], "quiet"))
        for case, entries, said in cases:
            with self.subTest(case):
                self.transcript("lead-1", entries)
                code, out = self.run_main("quiet", "--id", "lead-1")
                self.assertEqual(0, code)
                self.assertTrue(out.startswith(said), out)
        self.transcript("lead-1", [self.owner("go on", 2), self.reply("Done.")])
        self.assertEqual("quiet\n", self.run_main("quiet", "--id", "lead-1", "--minutes", "1")[1])
        self.assertEqual("active no transcript\n", self.run_main("quiet", "--id", "missing")[1])


def datetime_local(*parts):
    """An ISO time with the local offset: its local date is the given one in any time zone."""
    from datetime import datetime
    return datetime(*parts).astimezone().isoformat()


class ReleaseMarksRepoTest(unittest.TestCase):
    # protects: Rule
    def test_installed_version_of_every_plugin_has_a_release_mark(self):
        # The Pult watcher reads each plugin's own file to decide when the leads restart; a bump without a mark counts
        # as routine.
        plugins = Path(__file__).resolve().parent.parent.parent / "plugins"
        for plugin in ("dev-kit", "pult", "rules-kit", "spend-kit", "unity-kit", "web-kit"):
            with self.subTest(plugin=plugin):
                folder = plugins / plugin
                version = json.loads((folder / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
                marks = json.loads((folder / "releases.json").read_text(encoding="utf-8"))
                self.assertIn(version, marks, f"add the release mark of the new version to plugins/{plugin}/releases.json")
                entries, warnings = sessions.read_releases(folder / "releases.json")
                self.assertEqual([], warnings)
                self.assertIn(version, [entry[1] for entry in entries])
                self.assertTrue(marks[version]["reason"].strip())

if __name__ == "__main__":
    unittest.main()
