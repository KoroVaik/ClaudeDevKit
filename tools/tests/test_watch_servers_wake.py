"""The Pult watcher (plugins/pult/scripts/watch-servers.ps1) wakes Pult and the project leads by a cross-session message
only when something needs them (the wakes in its header). Runs a copy of the pult and dev-kit scripts in a temp folder
with a fake `claude` on PATH (the session list), a fake one-shot sender (-WakeExe: records its stdin and arguments,
prints a json result and, when told to, writes the event id into the target's transcript as a delivered message; a
phone push is such a message to a relay session too), a
fake sessions.py (-SessionsPy: `check` prints a file's lines not marked yet, `mark` records, `size` prints a file; the
rest goes to the real one) and a stub restart-leads.ps1, so no real session, watcher or `claude` is touched. The "lead"
is this test process (its pid is alive)."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
PLUGINS = ROOT / "plugins"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")
sys.path.insert(0, str(PLUGINS / "dev-kit" / "scripts"))
import dev_kit_state  # noqa: E402

LEAD = "P: Lead"
LEAD_SID = "11111111-aaaa-bbbb-cccc-000000000001"
TASK = "22222222-aaaa-bbbb-cccc-000000000002"
PULT_SID = "33333333-aaaa-bbbb-cccc-000000000003"
SERVER = "Srv-wake-test-7f3a"  # a server row no real process matches
OLD_TIME = 946684800  # 2000-01-01: every plugin.json is older than the "lead" process
STALE_KEY = "2026-11-20T09:00:00.000Z"
STALE_LINE = f"stale | C: task | {TASK} | waiting 25 min | {STALE_KEY}"
PING = ("PING keep-warm: run dev-kit-sessions fill for your C sessions and dev-kit-sessions fill --self "
        "for yourself, then answer with your standard status only.")

FAKE_SESSIONS = r'''import json, os, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")  # as the real sessions.py
d = Path(os.environ["TEST_DIR"])
argv = sys.argv[1:]
with open(d / "sessions-calls.txt", "a", encoding="utf-8") as f:
    f.write(json.dumps(argv) + "\n")
words = argv[2:] if argv[:1] == ["--project"] else argv
marks = d / "marks.txt"
done = marks.read_text(encoding="utf-8").splitlines() if marks.exists() else []
if words[0] == "check":
    f = d / "check.txt"
    for line in (f.read_text(encoding="utf-8").splitlines() if f.exists() else []):
        p = [x.strip() for x in line.split(" | ")]
        if f"{p[0]}|{p[2]}|{p[-1]}" not in done:
            print(line)
elif words[0] == "mark":
    a = dict(zip(words[1::2], words[2::2]))
    with open(marks, "a", encoding="utf-8") as f:
        f.write(f"{a['--kind']}|{a.get('--id', '-')}|{a['--key']}\n")
    print("marked")
elif words[0] == "size":
    f = d / "size.txt"
    if f.exists():
        print(f.read_text(encoding="utf-8").strip())
else:
    sys.exit(subprocess.run([sys.executable, os.environ["TEST_REAL_SESSIONS"], *argv]).returncode)
'''

FAKE_WAKE = r'''import json, os, re, sys
from pathlib import Path
d = Path(os.environ["TEST_DIR"])
text = sys.stdin.buffer.read().decode("utf-8")
plan = json.loads((d / "wake-plan.json").read_text(encoding="utf-8"))
with open(d / "wakes.jsonl", "a", encoding="utf-8") as f:
    f.write(json.dumps({"args": sys.argv[1:], "stdin": text, "cwd": os.getcwd()}) + "\n")
to = re.search(r"no quotes or brackets added: (.+)", text)
eid = re.search(r"\[EVT-[^\]]+\]", text)
deliver = plan.get("deliver")  # true: every target takes it; a list: only those
if to and eid and deliver and (deliver is True or to.group(1) in deliver) and to.group(1) in plan["transcripts"]:
    entry = {"type": "user", "isMeta": True, "origin": {"kind": "peer"},
             "message": {"role": "user", "content": eid.group(0) + " Pult server watcher: ..."}}
    with open(plan["transcripts"][to.group(1)], "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
        if plan.get("relimit"):  # the turn the message starts hits the usage limit again: a new notice
            f.write(json.dumps(dict(plan["relimit"], uuid=eid.group(0))) + "\n")
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": plan.get("result", "sent")}))
'''

STUB_RESTART = '''param($Name, $Ready, $ConfigFile, $StateDir)
Add-Content -LiteralPath $env:TEST_CALLS_FILE -Value "Name=$Name Ready=$Ready"
if ($env:TEST_RESTART_BUSY) { Write-Output "Busy, skipped: $($Ready -join ',')"; return }
Write-Output "Resumed lead: $($Name -join ',')"
'''


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "the Pult watcher runs on Windows PowerShell")
class WatchServersWakeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        out = subprocess.run([POWERSHELL, "-NoProfile", "-Command",
                              f"(Get-Process -Id {os.getpid()}).StartTime.ToUniversalTime().ToString('o', "
                              "[Globalization.CultureInfo]::InvariantCulture)"],
                             check=True, capture_output=True, text=True, timeout=60)
        cls.started = out.stdout.strip()

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.plugins = self.tmp / "plugins"
        shutil.copytree(PLUGINS / "pult" / "scripts", self.plugins / "pult" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(PLUGINS / "dev-kit" / "scripts", self.plugins / "dev-kit" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(PLUGINS / "spend-kit" / "scripts", self.plugins / "spend-kit" / "scripts",
                        ignore=shutil.ignore_patterns("__pycache__"))  # the forecast block runs its usage_forecast.py
        self.scripts = self.plugins / "pult" / "scripts"
        (self.scripts / "restart-leads.ps1").write_text(STUB_RESTART, encoding="ascii")
        self.set_version("pult", "1.0.0")
        self.set_version("dev-kit", "0.1.78")
        self.project = self.tmp / "project"
        self.project.mkdir()
        self.state = self.tmp / "devkit-state"
        self.state.mkdir()
        with mock.patch.dict(os.environ, {"DEV_KIT_STATE_DIR": str(self.state)}):
            self.registry = dev_kit_state.project_state_dir(str(self.project))
        self.projects = self.tmp / "projects" / "p1"
        self.projects.mkdir(parents=True)
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.bin / "claude.cmd").write_text('@type "%~dp0agents.json"\r\n', encoding="ascii")
        (self.bin / "fake_sessions.py").write_text(FAKE_SESSIONS, encoding="utf-8")
        (self.bin / "fake_wake.py").write_text(FAKE_WAKE, encoding="utf-8")
        (self.bin / "wake.cmd").write_text(f'@"{sys.executable}" "%~dp0fake_wake.py" %*\r\n', encoding="ascii")
        self.pult = self.tmp / "pult"
        (self.pult / "logs").mkdir(parents=True)
        self.lead_transcript = self.projects / f"{LEAD_SID}.jsonl"
        self.pult_transcript = self.projects / f"{PULT_SID}.jsonl"
        for f in (self.lead_transcript, self.pult_transcript):
            f.write_text(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": "x"}}) + "\n",
                         encoding="utf-8")
        self.wake_plan(deliver=True)
        self.config(lead=True)
        self.agents(lead="idle", task="busy")
        self.lead_record("0.1.78")
        self.wake_state(PultNote=True)

    # ---- the environment ----

    def set_version(self, name, version):
        f = self.plugins / name / ".claude-plugin" / "plugin.json"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"name": name, "version": version}), encoding="ascii")
        os.utime(f, (OLD_TIME, OLD_TIME))

    def config(self, lead=True, server=False):
        rows = []
        if lead:
            rows.append(f"@{{ Session = '{LEAD}'; Lead = $true; Path = '{self.project}' }}")
        if server:
            rows.append(f"@{{ Session = '{SERVER}'; Path = '{self.tmp}' }}")
        self.config_file = self.tmp / "servers.psd1"
        self.config_file.write_text("@{ Servers = @( %s ) }\n" % ", ".join(rows), encoding="utf-8-sig")

    def agents(self, lead="idle", task="busy", pult=False, hub_name=None):
        items = [{"pid": os.getpid(), "kind": "background", "name": LEAD, "sessionId": LEAD_SID, "id": LEAD_SID[:8],
                  "state": "working" if lead == "busy" else "idle", "status": lead},
                 {"pid": 999998, "kind": "background", "name": "C: task", "sessionId": TASK, "id": TASK[:8],
                  "state": "working" if task == "busy" else "idle", "status": task}]
        if pult:
            items.append({"pid": 999997, "kind": "interactive", "name": "Pult", "sessionId": PULT_SID,
                          "id": PULT_SID[:8], "status": "idle"})
        if hub_name:  # the hub's Remote Control session: a system name, cwd = the home folder
            items.append({"pid": 999997, "kind": "interactive", "name": hub_name, "sessionId": PULT_SID,
                          "id": PULT_SID[:8], "status": "idle", "cwd": str(Path.home())})
        (self.bin / "agents.json").write_text(json.dumps(items), encoding="utf-8")

    def registry_task(self, owner=False):
        record = {"id": TASK, "name": "C: task", "worktree": str(self.project), "task": "t", "status": "active"}
        if owner:
            record["owner"] = True
        (self.registry / "sessions.json").write_text(json.dumps([record]), encoding="utf-8")

    def lead_record(self, version):
        (self.pult / "lead-versions.json").write_text(json.dumps(
            {LEAD: {"pid": os.getpid(), "started": self.started, "version": version, "ext": {}}}), encoding="utf-8")

    def wake_state(self, **state):
        (self.pult / "wake-state.json").write_text(json.dumps(state), encoding="utf-8")

    def wake_plan(self, deliver):
        (self.bin / "wake-plan.json").write_text(json.dumps(
            {"deliver": deliver, "transcripts": {LEAD: str(self.lead_transcript), "Pult": str(self.pult_transcript)}}),
            encoding="utf-8")

    def age_transcript(self, minutes):
        when = time.time() - minutes * 60
        os.utime(self.lead_transcript, (when, when))

    def run_watch(self, rounds, *extra, restart_busy=False):
        env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
                   DEV_KIT_PROJECTS_DIR=str(self.projects.parent), DEV_KIT_STATE_DIR=str(self.state),
                   DEV_KIT_JOBS_DIR=str(self.tmp / "jobs"), DEV_KIT_USAGE_LOG=str(self.tmp / "usage"),
                   TEST_DIR=str(self.bin), TEST_CALLS_FILE=str(self.tmp / "restart-calls.txt"),
                   TEST_REAL_SESSIONS=str(self.plugins / "dev-kit" / "scripts" / "sessions.py"))
        env.pop("TEST_RESTART_BUSY", None)
        if restart_busy:  # the stub restart-leads.ps1 answers "Busy, skipped": the ready mark stays
            env["TEST_RESTART_BUSY"] = "1"
        subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(self.scripts / "watch-servers.ps1"),
                        "-Rounds", str(rounds), "-IntervalSec", "0", "-ConfigFile", str(self.config_file),
                        "-StateDir", str(self.pult), "-DevKitStateDir", str(self.state),
                        "-DaemonLog", str(self.tmp / "daemon.log"), "-DevKitDir", str(self.plugins / "dev-kit"),
                        "-SessionsPy", str(self.bin / "fake_sessions.py"), "-WakeExe", str(self.bin / "wake.cmd"),
                        "-WakeCooldownSec", "0", *extra],
                       env=env, check=True, capture_output=True, timeout=300)
        log = (self.pult / "logs" / "servers.log").read_text(encoding="utf-8-sig")
        return [line.split(" ", 1)[1] for line in log.splitlines() if " " in line]

    def wakes(self):
        f = self.bin / "wakes.jsonl"
        return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []

    def marks(self):
        f = self.bin / "marks.txt"
        return f.read_text(encoding="utf-8").splitlines() if f.exists() else []

    def sessions_calls(self, action):
        f = self.bin / "sessions-calls.txt"
        calls = [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []
        return [c for c in calls if action in c]

    @staticmethod
    def message(wake):
        """The text the sender was told to pass on (between its BEGIN-<id> and END-<id> lines)."""
        return re.search(r"\nBEGIN-\S+\n(.*)\nEND-\S+\n", wake["stdin"], re.S).group(1)

    @staticmethod
    def arg(wake, flag):
        return wake["args"][wake["args"].index(flag) + 1]

    @staticmethod
    def to(wake):
        return re.search(r"no quotes or brackets added: (.+)", wake["stdin"]).group(1)

    def push(self, wake):
        """The text a phone push request asks its relay to push, or None for another message."""
        lines = self.message(wake).split("\n")
        if not lines[0].endswith("] Pult server watcher: phone push request."):
            return None
        self.assertEqual("Call the PushNotification tool once with exactly the next line as its text, then write "
                         "nothing else.", lines[1])
        self.assertEqual(3, len(lines))
        return lines[2]

    # ---- the tests ----

    # protects: Flow
    def test_lead_event_reaches_the_lead_in_bypass_and_is_marked_after_delivery(self):
        (self.pult / "logs" / "servers.log").write_text(
            f"2026-11-20T08:00:00 MODE {LEAD} auto (an old line: the sender never reads it)\n", encoding="utf-8")
        (self.bin / "check.txt").write_text(STALE_LINE + "\n", encoding="utf-8")
        log = self.run_watch(2)
        self.assertFalse([line for line in log if line.startswith("WARN")], log)
        wakes = self.wakes()
        self.assertEqual(1, len(wakes), log)
        w = wakes[0]
        self.assertEqual("bypassPermissions", self.arg(w, "--permission-mode"))
        self.assertEqual("SendMessage", self.arg(w, "--tools"))
        self.assertEqual("SendMessage", self.arg(w, "--allowedTools"))
        self.assertEqual("haiku", self.arg(w, "--model"))
        for flag in ("-p", "--no-session-persistence", "--safe-mode"):
            self.assertIn(flag, w["args"])
        self.assertEqual(str(self.pult / "wake"), w["cwd"])
        self.assertIn(f"brackets added: {LEAD}\n", w["stdin"])
        lines = self.message(w).split("\n")
        self.assertRegex(lines[0], r"^\[EVT-[0-9]{10}-[0-9a-f]{4}\] Pult server watcher:$")
        self.assertEqual([f"stale: C: task | {TASK} | waiting 25 min", "Act on these lines per your project-lead skill."],
                         lines[1:])
        event_id = lines[0][5:20]
        self.assertIn(f"WAKE {LEAD} {event_id} cause=event kinds=stale", log)
        self.assertTrue(any(line.startswith(f"WAKE-TAKEN {LEAD} {event_id} (") for line in log), log)
        self.assertEqual([f"stale|{TASK}|{STALE_KEY}"], self.marks())
        self.assertEqual(["--project", str(self.project), "mark"], self.sessions_calls("mark")[0][:3])
        self.assertEqual([], json.loads((self.pult / "wake-pending.json").read_text(encoding="utf-8")))

    # protects: Flow
    def test_handoff_request_reaches_the_lead_as_its_line_and_is_marked(self):
        # A lead that is not quiet is asked to move by this event (the project-lead skill, "Restart P").
        (self.bin / "check.txt").write_text("handoff | - | - | handoff-2.md | handoff-2.md\n", encoding="utf-8")
        log = self.run_watch(2)
        wakes = self.wakes()
        self.assertEqual(1, len(wakes), log)
        self.assertEqual(["handoff requested: handoff-2.md", "Act on these lines per your project-lead skill."],
                         self.message(wakes[0]).split("\n")[1:])
        self.assertEqual(["handoff|-|handoff-2.md"], self.marks())

    # protects: Bug
    def test_delivery_is_seen_in_the_new_transcript_of_a_cleared_lead(self):
        # After /clear the lead keeps its session id but writes a new file; the old one never shows the event.
        new = self.projects / "99999999-aaaa-bbbb-cccc-000000000009.jsonl"
        new.write_text(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": "x"}}) + "\n",
                       encoding="utf-8")
        job = self.tmp / "jobs" / LEAD_SID[:8]
        job.mkdir(parents=True)
        (job / "state.json").write_text(json.dumps({"sessionId": LEAD_SID, "resumeSessionId": new.stem,
                                                    "linkScanPath": str(new), "name": LEAD}), encoding="utf-8")
        (self.bin / "wake-plan.json").write_text(json.dumps(
            {"deliver": True, "transcripts": {LEAD: str(new), "Pult": str(self.pult_transcript)}}), encoding="utf-8")
        (self.bin / "check.txt").write_text(STALE_LINE + "\n", encoding="utf-8")
        log = self.run_watch(2)
        self.assertTrue(any(line.startswith(f"WAKE-TAKEN {LEAD} ") for line in log), log)
        self.assertEqual([f"stale|{TASK}|{STALE_KEY}"], self.marks())

    # protects: Flow
    def test_message_not_taken_is_sent_again_then_pushed_through_pult(self):
        self.wake_plan(deliver=["Pult"])  # the lead takes nothing
        self.agents(pult=True)
        (self.bin / "check.txt").write_text(STALE_LINE + "\n", encoding="utf-8")
        log = self.run_watch(5, "-WakeConfirmSec", "0")
        wakes = self.wakes()
        self.assertEqual([LEAD] * 3 + ["Pult"], [self.to(w) for w in wakes], log)
        self.assertEqual(["SendMessage"] * 4, [self.arg(w, "--tools") for w in wakes], "no one-shot push of its own")
        self.assertEqual(1, len({self.message(w).split("\n")[0] for w in wakes[:3]}), "a retry keeps the event id")
        self.assertEqual("default", self.arg(wakes[3], "--permission-mode"))
        push = self.push(wakes[3])
        self.assertLess(len(push), 200)
        self.assertTrue(push.startswith(f"{LEAD} не взяв повідомлення; stale: C: task | {TASK}"), push)
        self.assertTrue(any(line.startswith(f"WAKE-FALLBACK {LEAD} ") and "not taken after 3 sends" in line
                            for line in log), log)
        self.assertTrue(any(re.match(r"WAKE-TAKEN phone \S+ via Pult \(", line) for line in log), log)
        self.assertEqual([f"stale|{TASK}|{STALE_KEY}"], self.marks(), "marked once, after Pult took the push")

    # protects: Flow
    def test_pult_down_its_giveup_is_pushed_through_a_live_lead_in_bypass(self):
        self.config(lead=True, server=True)
        log = self.run_watch(2, "-MaxHeals", "0", "-WakeDownSec", "0")
        wakes = self.wakes()
        self.assertEqual([LEAD], [self.to(w) for w in wakes], log)
        self.assertEqual("bypassPermissions", self.arg(wakes[0], "--permission-mode"))
        self.assertTrue(self.push(wakes[0]).startswith(f"Pult не піднявся - запусти його на комп'ютері; GIVEUP {SERVER} ("))
        self.assertTrue(any(re.match(rf"WAKE-TAKEN phone \S+ via {LEAD} \(", line) for line in log), log)

    # protects: Rule
    def test_push_with_no_live_relay_waits_and_is_kept(self):
        self.config(lead=False, server=True)
        log = self.run_watch(3, "-MaxHeals", "0", "-WakeDownSec", "0")
        self.assertEqual([], self.wakes(), log)
        self.assertEqual(1, len([line for line in log if line.startswith("WAKE-FALLBACK-NONE phone ")]),
                         "tried again only after the retry time")
        pending = json.loads((self.pult / "wake-pending.json").read_text(encoding="utf-8"))
        self.assertEqual(["phone"], [item["Kind"] for item in pending])

    # protects: Flow
    def test_pult_gets_giveup_lines_and_the_one_time_note(self):
        self.config(lead=False, server=True)
        self.agents(pult=True)
        self.wake_state()
        log = self.run_watch(3, "-MaxHeals", "0")
        self.assertFalse([line for line in log if line.startswith("WARN")], log)
        wakes = self.wakes()
        self.assertEqual(2, len(wakes), log)
        self.assertEqual(["default"] * 2, [self.arg(w, "--permission-mode") for w in wakes])  # the hub holds a bypass sender's message
        self.assertIn("brackets added: Pult\n", wakes[0]["stdin"])
        self.assertIn("watch-log.py) is retired", self.message(wakes[0]))
        giveup = self.message(wakes[1]).split("\n")
        self.assertTrue(giveup[1].startswith(f"GIVEUP {SERVER} ("), giveup)
        self.assertEqual('Act on these lines per your hub rules, section "Phone push".', giveup[2])
        self.assertTrue(any(re.match(r"WAKE Pult \S+ cause=note kinds=note$", line) for line in log), log)
        self.assertTrue(any(re.match(r"WAKE Pult \S+ cause=event kinds=GIVEUP$", line) for line in log), log)
        self.assertEqual(2, len([line for line in log if line.startswith("WAKE-TAKEN Pult ")]), log)
        self.assertTrue(json.loads((self.pult / "wake-state.json").read_text(encoding="utf-8"))["PultNote"])

    # protects: Bug
    def test_pult_hub_listed_with_a_system_name_gets_the_giveup_under_that_name(self):
        # The hub's session shows as "<user>-e9" in the session list, never "Pult": it is still live, the message is
        # addressed by the system name and no "Pult did not come up" phone push goes out.
        system_name = "user-e9"
        self.config(lead=False, server=True)
        self.agents(hub_name=system_name)
        (self.bin / "wake-plan.json").write_text(json.dumps(
            {"deliver": True, "transcripts": {LEAD: str(self.lead_transcript), system_name: str(self.pult_transcript)}}),
            encoding="utf-8")
        log = self.run_watch(3, "-MaxHeals", "0", "-WakeDownSec", "0")
        wakes = self.wakes()
        self.assertEqual([system_name], [self.to(w) for w in wakes], log)
        giveup = self.message(wakes[0]).split("\n")
        self.assertTrue(giveup[1].startswith(f"GIVEUP {SERVER} ("), giveup)
        self.assertTrue(any(re.match(r"WAKE Pult \S+ cause=event kinds=GIVEUP$", line) for line in log), log)
        self.assertTrue(any(line.startswith("WAKE-TAKEN Pult ") for line in log), log)
        self.assertFalse([line for line in log if "FALLBACK" in line or "phone" in line], log)
        self.assertEqual([], json.loads((self.pult / "wake-pending.json").read_text(encoding="utf-8")))

    # protects: Rule
    def test_lead_on_an_older_dev_kit_is_left_to_its_own_watcher(self):
        self.set_version("dev-kit", "0.1.76")
        self.lead_record("0.1.76")
        (self.bin / "check.txt").write_text(STALE_LINE + "\n", encoding="utf-8")
        self.registry_task()
        self.age_transcript(60)
        log = self.run_watch(2)
        self.assertEqual([], self.wakes(), log)
        self.assertEqual([], self.sessions_calls("check"))

    # protects: Rule
    def test_keep_warm_ping_only_for_an_idle_silent_lead_with_a_working_task(self):
        self.registry_task()
        for case, setup in (("lead busy", lambda: self.agents(lead="busy", task="busy")),
                            ("task idle", lambda: self.agents(lead="idle", task="idle")),
                            ("owner session", lambda: self.registry_task(owner=True)),
                            ("lead spoke 10 min ago", lambda: self.age_transcript(10))):
            with self.subTest(case):
                self.agents(lead="idle", task="busy")
                self.registry_task()
                self.age_transcript(60)
                setup()
                self.run_watch(1)
                self.assertEqual([], self.wakes())
        self.agents(lead="idle", task="busy")
        self.registry_task()
        self.age_transcript(60)
        log = self.run_watch(1)
        wakes = self.wakes()
        self.assertEqual(1, len(wakes), log)
        self.assertEqual(PING, self.message(wakes[0]).split("\n")[1])
        self.assertTrue(any(re.match(rf"WAKE {LEAD} \S+ cause=ping kinds=ping$", line) for line in log), log)
        self.age_transcript(60)  # the delivered ping wrote the transcript; a lead that stays silent is not pinged again
        self.run_watch(1)
        self.assertEqual(1, len(self.wakes()), "no second ping within 50 minutes of the last wake")

    # protects: Rule
    def test_lead_with_a_handoff_marker_gets_no_keep_warm_ping(self):
        # It is about to be replaced (or its move failed): keeping its cache warm would only cost a turn.
        self.registry_task()
        self.age_transcript(60)
        subprocess.run([sys.executable, str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                        str(self.project), "handoff", "save", "--file", "handoff-1.md"],
                       env=dict(os.environ, DEV_KIT_STATE_DIR=str(self.state)), check=True, capture_output=True,
                       timeout=60)
        log = self.run_watch(2)
        self.assertEqual([], self.wakes(), log)
        subprocess.run([sys.executable, str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                        str(self.project), "handoff", "clear"],
                       env=dict(os.environ, DEV_KIT_STATE_DIR=str(self.state)), check=True, capture_output=True,
                       timeout=60)
        self.run_watch(1)
        self.assertEqual(1, len(self.wakes()), "without the marker the same lead is pinged")

    # protects: Rule
    def test_conversation_past_0_7_of_its_window_gets_one_phone_push(self):
        (self.bin / "size.txt").write_text(
            f"{LEAD_SID} | 750000 | 1000000 | claude-opus-4-7 | owner=1 peer=2 notify=0 | units=12.5\n"
            f"{TASK} | 600000 | 1000000 | claude-opus-4-7 | owner=0 peer=0 notify=1 | units=3\n"
            f"{PULT_SID} | 900000 | 1000000 | claude-opus-4-7\n", encoding="utf-8")
        self.registry_task()
        self.agents(pult=True)
        self.run_watch(3)
        log = self.run_watch(2)  # a new watcher run (as after WATCH-RESTART) pushes no second time; the log holds both
        pushes = [w for w in self.wakes() if self.push(w) is not None]
        self.assertEqual(1, len(pushes), "the sessions that pass in one round share one push")
        self.assertEqual("Pult", self.to(pushes[0]), "Pult relays the push while it is live")
        self.assertEqual(f"{LEAD}: 750 тис., Pult: 900 тис. токенів - перенеси ці розмови в нові сесії",
                         self.push(pushes[0]))
        self.assertEqual([f"PUSH-SIZE {LEAD} {LEAD_SID} 750000", f"PUSH-SIZE Pult {PULT_SID} 900000"],
                         [line for line in log if line.startswith("PUSH-SIZE")])
        self.assertIn(f"SIZE {LEAD} {LEAD_SID} 750000 owner=1 peer=2 notify=0 units=12.5", log)
        self.assertIn(f"SIZE C: task {TASK} 600000 owner=0 peer=0 notify=1 units=3", log)
        wakes_args = [c for c in self.sessions_calls("size")]
        self.assertEqual(5, len(wakes_args))
        self.assertEqual([True, False, False, True, False], ["--wakes" in c for c in wakes_args],
                         "the SIZE lines every 10 minutes, and at the start of a run")

    def usage_log(self, rows):
        """rows: (hours ago, weekly per cent); the window resets in 3 days."""
        folder = self.tmp / "usage"
        folder.mkdir(exist_ok=True)
        now, resets = time.time(), int(time.time()) + 3 * 24 * 3600
        (folder / "usage-log.jsonl").write_text("".join(json.dumps(
            {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - h * 3600)), "week_pct": p,
             "week_resets": resets, "five_hour_pct": None}) + "\n" for h, p in rows), encoding="utf-8")

    # protects: Rule
    def test_weekly_limit_forecast_gets_one_phone_push_per_window(self):
        self.usage_log([(3, 40), (1, 50)])  # 5 %/h: runs out in about 9 hours, days before the reset
        self.registry_task()
        self.agents(pult=True)
        self.run_watch(2)
        log = self.run_watch(2)  # a new watcher run (as after WATCH-RESTART) pushes no second time
        pushes = [w for w in self.wakes() if self.push(w) is not None]
        self.assertEqual(1, len(pushes), log)
        self.assertEqual("Pult", self.to(pushes[0]))
        self.assertRegex(self.push(pushes[0]),
                         r"^Тижневий ліміт: витрачено 50%, за темпом скінчиться (пн|вт|ср|чт|пт|сб|нд) \d\d:\d\d, "
                         r"оновиться (пн|вт|ср|чт|пт|сб|нд) \d\d:\d\d$")
        self.assertEqual(1, len([line for line in log if line.startswith("LIMIT-FORECAST runout=")]), log)

    # protects: Rule
    def test_weekly_limit_forecast_without_open_task_sessions_pushes_nothing(self):
        self.usage_log([(3, 40), (1, 50)])
        self.agents(pult=True)  # no task session in the lead's registry
        log = self.run_watch(2)
        self.assertEqual([], [w for w in self.wakes() if self.push(w) is not None])
        self.assertFalse([line for line in log if line.startswith("LIMIT-FORECAST")])
        self.assertFalse((self.pult / "limit-forecast.json").exists())
        self.registry_task()  # a task session opens later in the same window: no mark was set, so it still pushes
        self.run_watch(2)
        self.assertEqual(1, len([w for w in self.wakes() if self.push(w) is not None]))

    # protects: Rule
    def test_lead_with_a_working_task_or_busy_is_asked_for_a_critical_dev_kit_not_restarted(self):
        self.set_version("dev-kit", "0.1.79")
        (self.plugins / "dev-kit" / "releases.json").write_text(json.dumps(
            {"0.1.79": {"kind": "critical", "date": "2026-11-23", "reason": "test"}}), encoding="utf-8")
        self.registry_task()
        for n, (case, lead, task, why) in enumerate((("idle, task working", "idle", "busy", "idle, C: task working"),
                                                     ("busy", "busy", "idle", "busy")), 1):
            with self.subTest(case):
                (self.registry / "restart.json").unlink(missing_ok=True)
                self.agents(lead=lead, task=task)
                log = self.run_watch(2)
                self.assertFalse((self.tmp / "restart-calls.txt").exists(), log)
                asked = [line for line in log if line.startswith(f"RESTART-ASKED {LEAD} ")]
                self.assertEqual(n, len(asked), "asked once per run of two rounds")
                self.assertEqual(f"RESTART-ASKED {LEAD} (dev-kit 0.1.78 -> 0.1.79, critical, {why})", asked[-1])
                request = json.loads((self.registry / "restart.json").read_text(encoding="utf-8"))
                self.assertEqual("0.1.79", request["version"])
                self.assertNotIn("ready", request)

    # protects: Bug
    def test_cyrillic_task_name_reaches_the_sender_intact(self):
        (self.bin / "check.txt").write_text(STALE_LINE.replace("C: task", "C: Каталог страв") + "\n", encoding="utf-8")
        log = self.run_watch(1)
        wakes = self.wakes()
        self.assertEqual(1, len(wakes), log)
        self.assertEqual(f"stale: C: Каталог страв | {TASK} | waiting 25 min", self.message(wakes[0]).split("\n")[1])

    # protects: Rule
    def test_lead_marked_ready_gets_no_message_until_after_its_restart(self):
        self.set_version("dev-kit", "0.1.79")
        self.agents(lead="busy", task="idle")
        subprocess.run([sys.executable, str(self.plugins / "dev-kit" / "scripts" / "sessions.py"), "--project",
                        str(self.project), "restart", "ready", "--version", "0.1.79"],
                       env=dict(os.environ, DEV_KIT_STATE_DIR=str(self.state)), check=True, capture_output=True,
                       timeout=60)
        (self.bin / "check.txt").write_text(STALE_LINE + "\n", encoding="utf-8")
        # the -Ready restart finds it busy: the ready mark stays
        log = self.run_watch(2, "-ReadyWarnSec", "0", restart_busy=True)
        self.assertEqual([], self.wakes(), log)
        pending = json.loads((self.pult / "wake-pending.json").read_text(encoding="utf-8"))
        self.assertEqual([f"stale: C: task | {TASK} | waiting 25 min"], [line for item in pending for line in item["Lines"]])
        log = self.run_watch(1, "-ReadyWarnSec", "0")  # restarted with -Ready, the mark cleared: the message goes out
        self.assertIn(f"Name= Ready={LEAD}", (self.tmp / "restart-calls.txt").read_text(encoding="utf-8"))
        self.assertEqual(1, len(self.wakes()), log)

    # ---- a session stopped on the usage limit is woken after the reset ----

    def limit_stop(self, resets_in_sec):
        """The task session is registered, live and its transcript ends with a usage-limit notice whose reset is
        $resets_in_sec from now (negative: past). Returns the transcript path; the sender can deliver to it."""
        self.registry_task()
        transcript = self.projects / f"{TASK}.jsonl"
        notice = {"type": "assistant", "uuid": "task-stop", "apiError": "usage_limit_reached", "isApiErrorMessage": True,
                  "apiErrorParams": {"rate_limit_info": {"resetsAt": int(time.time()) + resets_in_sec}},
                  "message": {"role": "assistant", "model": "<synthetic>", "content": [{"type": "text", "text": "limit"}]}}
        transcript.write_text(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": "x"}}) + "\n"
                              + json.dumps(notice) + "\n", encoding="utf-8")
        plan = json.loads((self.bin / "wake-plan.json").read_text(encoding="utf-8"))
        plan["transcripts"]["C: task"] = str(transcript)
        (self.bin / "wake-plan.json").write_text(json.dumps(plan), encoding="utf-8")
        (self.bin / "check.txt").write_text(f"limited | C: task | {TASK} | resets x | task-stop\n", encoding="utf-8")
        return transcript

    @staticmethod
    def resume_lines(log):
        return [line for line in log if line.startswith("LIMIT")]

    # protects: Flow
    def test_session_past_its_limit_reset_gets_one_continue_message_and_the_lead_none(self):
        self.limit_stop(-3600)
        log = self.run_watch(2)
        wakes = self.wakes()
        self.assertEqual(["C: task"], [self.to(w) for w in wakes], log)
        self.assertIn("the usage limit that stopped you has reset. Go on with your task", self.message(wakes[0]))
        lines = self.resume_lines(log)
        self.assertEqual(3, len(lines), lines)
        self.assertTrue(lines[1].startswith(f"LIMIT-RESUME C: task {TASK} ") and lines[1].endswith("(try 1)"), lines)
        self.assertTrue(lines[2].startswith(f"LIMIT-RESUME-TAKEN C: task {TASK} "), lines)

    # protects: Rule
    def test_session_before_its_limit_reset_gets_no_message(self):
        self.limit_stop(3600)
        log = self.run_watch(2)
        self.assertEqual([], self.wakes(), log)
        self.assertEqual(1, len(self.resume_lines(log)), log)

    # protects: Flow
    def test_resume_not_taken_is_sent_three_times_then_the_lead_hears_of_the_stop(self):
        self.limit_stop(-3600)
        self.wake_plan(deliver=[LEAD])  # the task session never takes it; the lead does
        log = self.run_watch(5, "-WakeConfirmSec", "0")
        to_task = [w for w in self.wakes() if self.to(w) == "C: task"]
        self.assertEqual(3, len(to_task), log)
        self.assertIn(f"LIMIT-RESUME-GIVEUP C: task {TASK} (not taken after 3 sends)", log)
        to_lead = [self.message(w) for w in self.wakes() if self.to(w) == LEAD]
        self.assertEqual(1, len(to_lead), log)
        self.assertIn(f"limited: C: task | {TASK} | resets x", to_lead[0])

    # protects: Bug
    def test_session_that_hits_the_limit_again_is_messaged_at_most_three_times(self):
        transcript = self.limit_stop(-3600)
        plan = json.loads((self.bin / "wake-plan.json").read_text(encoding="utf-8"))
        plan["relimit"] = json.loads(transcript.read_text(encoding="utf-8").splitlines()[-1])
        (self.bin / "wake-plan.json").write_text(json.dumps(plan), encoding="utf-8")
        log = self.run_watch(6, "-WakeConfirmSec", "0")
        self.assertEqual(3, len([w for w in self.wakes() if self.to(w) == "C: task"]), log)
        self.assertTrue([line for line in log if line.startswith(f"LIMIT-RESUME-GIVEUP C: task {TASK}")], log)

    # protects: Bug
    def test_send_refused_while_still_limited_counts_no_try_and_logs_once(self):
        self.limit_stop(-3600)
        plan = json.loads((self.bin / "wake-plan.json").read_text(encoding="utf-8"))
        plan["result"], plan["deliver"] = "You've hit your limit", False
        (self.bin / "wake-plan.json").write_text(json.dumps(plan), encoding="utf-8")
        log = self.run_watch(5, "-LimitRetrySec", "0")
        self.assertGreater(len([w for w in self.wakes() if self.to(w) == "C: task"]), 3, log)  # past $WakeMaxTries
        failed = [line for line in log if line.startswith("LIMIT-RESUME-FAILED")]
        self.assertEqual([f"LIMIT-RESUME-FAILED C: task {TASK} You've hit your limit"], failed)
        self.assertFalse([line for line in log if "GIVEUP" in line], log)

    # ---- limit notices (usage_forecast.py notices is stubbed: the script owns thresholds and marks) ----

    def stub_notices(self, fail=False):
        """Replaces the copied usage_forecast.py: `check` prints nothing, `notices` prints notices.txt once (and logs the
        call), or fails when told to."""
        (self.plugins / "spend-kit" / "scripts" / "usage_forecast.py").write_text(
            "import json, os, sys\nfrom pathlib import Path\nd = Path(os.environ['TEST_DIR'])\n"
            "with open(d / 'forecast-calls.txt', 'a', encoding='utf-8') as f:\n    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "sys.stdout.reconfigure(encoding='utf-8')\n"
            "if sys.argv[1] == 'notices':\n"
            f"    if {fail!r}:\n        print('boom')\n        sys.exit(2)\n"
            "    n = d / 'notices.txt'\n    if n.exists():\n        print(n.read_text(encoding='utf-8').strip())\n"
            "        n.unlink()\n", encoding="utf-8")
        self.usage_log([(1, 10)])

    def notices(self, *lines):
        (self.bin / "notices.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def notices_calls(self):
        f = self.bin / "forecast-calls.txt"
        calls = [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines()] if f.exists() else []
        return [c for c in calls if c[0] == "notices"]

    def two_leads(self, second_live):
        """A second lead 'P: Second' on the same project; listed live (like the first) or not."""
        second, sid = "P: Second", "44444444-aaaa-bbbb-cccc-000000000004"
        transcript = self.projects / f"{sid}.jsonl"
        transcript.write_text(self.lead_transcript.read_text(encoding="utf-8"), encoding="utf-8")
        self.config_file.write_text("@{ Servers = @( @{ Session = '%s'; Lead = $true; Path = '%s' }, "
                                    "@{ Session = '%s'; Lead = $true; Path = '%s' } ) }\n" % (LEAD, self.project, second, self.project),
                                    encoding="utf-8-sig")
        records = json.loads((self.pult / "lead-versions.json").read_text(encoding="utf-8"))
        records[second] = dict(records[LEAD])
        (self.pult / "lead-versions.json").write_text(json.dumps(records), encoding="utf-8")
        items = json.loads((self.bin / "agents.json").read_text(encoding="utf-8"))
        if second_live:
            items.append(dict(items[0], name=second, sessionId=sid, id=sid[:8]))
        (self.bin / "agents.json").write_text(json.dumps(items), encoding="utf-8")
        plan = json.loads((self.bin / "wake-plan.json").read_text(encoding="utf-8"))
        plan["transcripts"][second] = str(transcript)
        (self.bin / "wake-plan.json").write_text(json.dumps(plan), encoding="utf-8")
        return second

    def limit_texts(self):
        """target -> the limit lines of the messages sent to it."""
        out = {}
        for w in self.wakes():
            out.setdefault(self.to(w), []).extend(
                line for line in self.message(w).split("\n") if line.startswith("LIMITTEXT"))
        return out

    # protects: Flow
    def test_limit_notice_goes_to_every_live_lead_and_back_only_to_those_told(self):
        self.stub_notices()
        second = self.two_leads(second_live=False)
        resets = int(time.time()) + 3 * 24 * 3600
        self.notices(f"notice | week | 80 | 83 | {resets} | LIMITTEXT slow down | wind down")
        log = self.run_watch(2)
        self.assertEqual({LEAD: ["LIMITTEXT slow down | wind down"]}, self.limit_texts(), log)  # the dead lead gets none
        self.assertIn("LIMIT-NOTICE week 80 83 leads=P: Lead", log)
        self.assertEqual([LEAD], json.loads((self.pult / "wake-state.json").read_text(encoding="utf-8"))["LimitNotified"][f"week|{resets}"])
        self.assertEqual([], self.marks(), "a limit line needs no sessions.py mark")
        self.assertEqual(1, len(self.notices_calls()), "a second round with an unchanged usage log makes no call")
        (self.bin / "wakes.jsonl").unlink()
        self.two_leads(second_live=True)  # the second lead is live at the reset, but was not told of the limit
        self.notices(f"back | week | {resets} | LIMITTEXT limit is back")
        log = self.run_watch(2)
        self.assertEqual({LEAD: ["LIMITTEXT limit is back"]}, self.limit_texts(), log)
        self.assertNotIn(second, self.limit_texts())
        self.assertIn("LIMIT-BACK week leads=P: Lead", log)
        self.assertEqual({}, json.loads((self.pult / "wake-state.json").read_text(encoding="utf-8"))["LimitNotified"])

    # protects: Flow
    def test_limit_notice_reaches_all_live_leads(self):
        self.stub_notices()
        second = self.two_leads(second_live=True)
        resets = int(time.time()) + 3 * 24 * 3600
        self.notices(f"notice | five | 90 | 91 | {resets} | LIMITTEXT five-hour limit")
        log = self.run_watch(2)
        self.assertEqual({LEAD: ["LIMITTEXT five-hour limit"], second: ["LIMITTEXT five-hour limit"]}, self.limit_texts(), log)
        self.assertIn(f"LIMIT-NOTICE five 90 91 leads={LEAD},{second}", log)

    # protects: Edge
    def test_limit_notices_script_printing_nothing_sends_nothing(self):
        self.stub_notices()
        log = self.run_watch(3)
        self.assertEqual([], self.wakes())
        self.assertFalse([line for line in log if line.startswith("LIMIT-NOTICE") or line.startswith("LIMIT-BACK")], log)
        self.assertEqual(1, len(self.notices_calls()))

    # protects: Edge
    def test_limit_notice_key_more_than_8_days_old_is_dropped(self):
        self.stub_notices()
        old, fresh = int(time.time()) - 9 * 24 * 3600, int(time.time()) + 3600
        self.wake_state(PultNote=True, LimitNotified={f"week|{old}": [LEAD], f"five|{fresh}": [LEAD]})
        self.run_watch(1)
        kept = json.loads((self.pult / "wake-state.json").read_text(encoding="utf-8"))["LimitNotified"]
        self.assertEqual({f"five|{fresh}": [LEAD]}, kept)

    # protects: Bug
    def test_failing_limit_notices_script_warns_once_and_sends_nothing(self):
        self.stub_notices(fail=True)
        self.notices(f"notice | week | 80 | 83 | {int(time.time()) + 3600} | LIMITTEXT never")
        log = self.run_watch(3)
        self.assertEqual(["WARN limit notices failed (exit 2): boom"], [line.strip() for line in log if "limit notices failed" in line], log)
        self.assertEqual([], self.wakes())


if __name__ == "__main__":
    unittest.main()
