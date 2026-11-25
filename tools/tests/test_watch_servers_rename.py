"""The Pult watcher (plugins/pult/scripts/watch-servers.ps1) knows a lead that still runs under its old name "P: <project>"
as the lead "L: <project>" of servers.psd1 (plans/role-names.md): it is up, so no second lead is started, and the
versions saved under the old name carry over. Runs a copy of the pult scripts in a temp folder with a fake `claude` and
a stub start-servers.ps1; the "lead" is this test process (its pid is alive), so no real session is touched."""
import json
import os
import unittest

from test_watch_servers_heal import FAKE_CLAUDE, STUB_START
from test_watch_servers_restart import LEAD, LEAD_SID, WatcherEnv

OLD_LEAD = "P: Lead"


class WatchServersRenameTest(WatcherEnv, unittest.TestCase):
    def setUp(self):
        super().setUp()
        (self.scripts / "start-servers.ps1").write_text(STUB_START, encoding="ascii")
        (self.bin / "fake_claude.py").write_text(FAKE_CLAUDE, encoding="ascii")
        (self.bin / "agents.json").write_text(json.dumps([
            {"pid": os.getpid(), "kind": "background", "name": OLD_LEAD, "sessionId": LEAD_SID, "id": "11111111",
             "state": "blocked", "status": "idle"}]), encoding="utf-8")

    # protects: Rule
    def test_running_lead_with_the_old_name_is_up_and_never_healed(self):
        # Two lead sessions of one project would split its chat: the watcher must not start "L: Lead" beside "P: Lead".
        log = self.run_watch(4)
        self.assertIn(True, [f"STATE {LEAD}: up, pid {os.getpid()}" in line for line in log], log)
        self.assertFalse([line for line in log if " HEAL " in line or " DOWN " in line], log)
        self.assertEqual([], self.starts())

    # protects: Rule
    def test_versions_saved_under_the_old_name_belong_to_the_new_one(self):
        # Without this the lead's pid and start versions are forgotten at the rename, and a restart for an old
        # version could be skipped.
        self.lead_record("1.0.0", ext={})
        saved = json.loads((self.tmp / "pult" / "lead-versions.json").read_text(encoding="utf-8"))
        (self.tmp / "pult" / "lead-versions.json").write_text(json.dumps({OLD_LEAD: saved[LEAD]}), encoding="utf-8")
        log = self.run_watch(2)
        self.assertFalse([line for line in log if " LEAD-VERSION " in line], log)
        self.assertEqual("1.0.0", self.lead_versions()["version"])
        self.assertNotIn(OLD_LEAD, json.loads((self.tmp / "pult" / "lead-versions.json").read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
