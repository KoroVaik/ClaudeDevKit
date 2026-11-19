"""A lead resume never leaves a flag-less copy (plugins/pult/scripts/resume-lib.ps1): the processes of a
just-stopped session are found by its id or its pty host, and the copy note of `claude --bg --resume`
gives the copy's id. Dot-sources resume-lib.ps1 in Windows PowerShell; starts no session."""
import shutil
import subprocess
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

    def test_woken_session_is_no_copy(self):
        note = "note: woke session 1e9f7469 with its saved options (--name, --permission-mode, --model)."
        self.assertEqual(ps(f"[string](Get-ResumeCopyId '{note}') -eq ''"), "True")


if __name__ == "__main__":
    unittest.main()
