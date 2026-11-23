"""A lead resume never leaves a flag-less copy (plugins/pult/scripts/resume-lib.ps1): the processes of a
just-stopped session are found by its id or its pty host, and the copy note of `claude --bg --resume`
gives the copy's id. Dot-sources resume-lib.ps1 in Windows PowerShell; starts no session."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LIB = ROOT / "plugins" / "pult" / "scripts" / "resume-lib.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")
SID = "0bf62d3e-513a-4a2e-8e5b-7af818d6a123"
EXE = r"C:\x\claude.exe"


def ps(script):
    out = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                          f". '{LIB}'; {script}"], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise AssertionError(out.stderr)
    return out.stdout.strip()


def procs(*rows):
    items = ",".join(f"[pscustomobject]@{{ ProcessId = {pid}; CommandLine = '{cmd}' }}" for pid, cmd in rows)
    return f"@({items})"


@unittest.skipUnless(POWERSHELL, "Windows PowerShell needed")
class ResumeCopyGuardTest(unittest.TestCase):
    def ids(self, *rows):
        return ps(f"(Get-SessionProcessIds '{SID}' {procs(*rows)}) -join ','")

    def test_worker_and_pty_host_found(self):
        # A resumed lead: the pty pipe carries the job's short id, not the session id's first 8 characters.
        got = self.ids(
            (11, rf"{EXE} --bg-pty-host \\.\pipe\cc-daemon-cd06-pty-27238c40 200 50 -- {EXE} --resume "
                 rf"C:\Users\k\.claude\projects\p\{SID}.jsonl --name t"),
            (12, f"{EXE} --session-id {SID} --name t"),
            (13, f"{EXE} --session-id aaaaaaaa-0000-0000-0000-000000000000"),
            (14, rf"{EXE} --resume C:\Users\k\.claude\projects\p\{SID}.jsonl"))
        self.assertEqual(got, "11,12,14")

    def test_other_sessions_and_forked_copies_ignored(self):
        got = self.ids((21, rf"{EXE} --bg-pty-host \\.\pipe\cc-daemon-cd06-pty-0bf62d3e 200 50 --"),
                       (22, f"{EXE} remote-control"),
                       (23, f"{EXE} --session-id a1f1e8b6-5c43 --fork-session --resume {SID} ok"))
        self.assertEqual(got, "")

    def test_copy_id_from_note(self):
        note = ("note: session 1e9f7469 is already running in the background, so this started a copy as "
                "a1f1e8b6. `claude attach 1e9f7469` opens the original.")
        self.assertEqual(ps(f"Get-ResumeCopyId '{note.replace(chr(39), chr(39) * 2)}'"), "a1f1e8b6")

    # protects: Bug
    def test_session_resumed_after_a_clear_is_found_by_its_new_transcript_id(self):
        # After /clear the list keeps the old id, but a resumed process runs as `--resume <new id>.jsonl`: a stop that
        # waits only for the old id would resume while it still runs, and claude would start a copy.
        new = "9c676bbe-24bd-4552-8a2c-ed959a99feab"
        with tempfile.TemporaryDirectory() as jobs:
            (Path(jobs) / "0bf62d3e").mkdir()
            (Path(jobs) / "0bf62d3e" / "state.json").write_text(json.dumps(
                {"sessionId": SID, "resumeSessionId": new, "linkScanPath": rf"C:\p\{new}.jsonl"}), encoding="utf-8")
            rows = procs((31, rf"{EXE} --resume C:\p\{new}.jsonl --name t"), (32, f"{EXE} --session-id other"))
            self.assertEqual("31", ps(f"(Get-SessionProcessIds (Get-JobSessionIds '{SID}' '{jobs}') {rows}) -join ','"))

    def test_woken_session_is_no_copy(self):
        note = "note: woke session 1e9f7469 with its saved options (--name, --permission-mode, --model)."
        self.assertEqual(ps(f"[string](Get-ResumeCopyId '{note}') -eq ''"), "True")


if __name__ == "__main__":
    unittest.main()
