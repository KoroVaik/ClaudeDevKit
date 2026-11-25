"""Leads are named "L: <project>"; the ones already running carry the old "P: <project>" until one resume renames them
(plugins/pult/scripts/resume-lib.ps1: Get-LegacyLeadName, Test-LeadName, Test-LeadEntryName, Get-LeadResumeEntry,
Set-LeadStateName). Dot-sources resume-lib.ps1 in Windows PowerShell with throwaway jobs folders; starts no session."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LIB = ROOT / "plugins" / "pult" / "scripts" / "resume-lib.ps1"
POWERSHELL = shutil.which("powershell.exe") or shutil.which("powershell")


def ps(script):
    out = subprocess.run([POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                          f". '{LIB}'; {script}"], capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise AssertionError(out.stderr)
    return out.stdout.strip()


@unittest.skipUnless(POWERSHELL, "Windows PowerShell needed")
class LeadRenameTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.jobs = self.tmp / "jobs"

    def job(self, short, state_text):
        folder = self.jobs / short
        folder.mkdir(parents=True)
        (folder / "state.json").write_bytes(state_text.encode("utf-8"))
        return folder / "state.json"

    # protects: Rule
    def test_name_helpers_map_and_match_both_prefixes(self):
        # Data rows: (call, expected). Every place that finds a lead by its name goes through these.
        rows = [
            ("Get-LegacyLeadName 'L: X'", "P: X"),
            ("[string](Get-LegacyLeadName 'P: X')", ""),  # no old name for an old name or another role
            ("[string](Get-LegacyLeadName 'M: X')", ""),
            ("Test-LeadName 'L: X'", "True"),
            ("Test-LeadName 'P: X'", "True"),
            ("Test-LeadName 'C: X'", "False"),
            ("Test-LeadName 'Pult'", "False"),
            ("Test-LeadEntryName 'P: X' 'L: X'", "True"),
            ("Test-LeadEntryName 'L: X' 'L: X'", "True"),
            ("Test-LeadEntryName 'P: Y' 'L: X'", "False"),
            ("Test-LeadEntryName 'L: X' 'P: X'", "False"),  # the old name never gets the new one's sessions
            ("Test-AnyLeadEntryName 'P: X' @('L: Y', 'L: X')", "True"),
        ]
        got = ps("; ".join(f"Write-Output ({call})" for call, _ in rows))
        self.assertEqual([want for _, want in rows], got.split("\n") if got else [])

    # protects: Flow
    def test_resume_lookup_falls_back_to_the_old_name_and_prefers_the_new_one(self):
        folder = self.tmp / "proj"
        folder.mkdir()
        old = {"kind": "background", "name": "P: X", "sessionId": "old-id", "cwd": str(folder), "startedAt": 5}
        new = {"kind": "background", "name": "L: X", "sessionId": "new-id", "cwd": str(folder), "startedAt": 1}
        other = {"kind": "background", "name": "P: X", "sessionId": "far-id", "cwd": str(self.tmp), "startedAt": 9}
        for sessions, want in (([old, other], "old-id P: X"), ([old, new, other], "new-id L: X"), ([other], "")):
            f = self.tmp / "agents.json"
            f.write_text(json.dumps(sessions), encoding="utf-8")
            got = ps(f"$e = Get-LeadResumeEntry 'L: X' '{folder}' (Get-Content -Raw '{f}' | ConvertFrom-Json); "
                     "if ($e) { \"$($e.SessionId) $($e.Name)\" }")
            self.assertEqual(want, got, sessions)

    # protects: Flow
    def test_rename_rewrites_the_name_and_flags_and_keeps_every_other_byte(self):
        text = ('{\n  "state": "stopped",\n  "note": "P: X stays in prose",\n  "name": "P: X",\n'
                '  "nameSource": "user",\n  "sessionId": "s1",\n'
                '  "respawnFlags": ["--remote-control", "P: X", "--name", "P: X", "--model", "opus"],\n  "tokens": 5\n}\n')
        state = self.job("abc", text)
        self.assertEqual("True", ps(f"Set-LeadStateName 'L: X' 's1' '{self.jobs}'"))
        want = (text.replace('"name": "P: X"', '"name": "L: X"')
                .replace('["--remote-control", "P: X", "--name", "P: X", "--model", "opus"]',
                         '["--remote-control", "L: X", "--name", "L: X", "--model", "opus"]'))
        self.assertEqual(want, state.read_bytes().decode("utf-8"))
        self.assertEqual("False", ps(f"Set-LeadStateName 'L: X' 's1' '{self.jobs}'"), "already renamed: no change")

    # protects: Rule
    def test_rename_leaves_other_jobs_alone(self):
        # Another lead's job, a job of another session id and a job already on the new name are not touched.
        other_lead = '{"name": "P: Y", "sessionId": "s1", "respawnFlags": ["--name", "P: Y"]}'
        other_sid = '{"name": "P: X", "sessionId": "s2", "respawnFlags": ["--name", "P: X"]}'
        files = [self.job("a", other_lead), self.job("b", other_sid)]
        self.assertEqual("False", ps(f"Set-LeadStateName 'L: X' 's1' '{self.jobs}'"))
        self.assertEqual([other_lead, other_sid], [f.read_text(encoding="utf-8") for f in files])

    # protects: Flow
    def test_saved_model_is_set_on_a_job_that_still_has_the_old_name(self):
        # Resume order: the rename comes first, but a job the rename did not reach must still get its model.
        state = self.job("abc", json.dumps({"name": "P: X", "sessionId": "s1", "respawnFlags": [
            "--name", "P: X", "--model", "sonnet"]}))
        ps(f"Set-LeadRespawnModel 'L: X' 's1' '{self.jobs}' | Out-Null")
        flags = json.loads(state.read_text(encoding="utf-8"))["respawnFlags"]
        self.assertEqual(["--name", "P: X", "--model", "opus", "--effort", "medium",
                          "--permission-mode", "bypassPermissions"], flags)


if __name__ == "__main__":
    unittest.main()
