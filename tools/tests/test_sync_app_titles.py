"""A renamed lead gets its Claude app title set to its name (plugins/pult/scripts/sync-app-titles.py). Runs the script
against a throwaway jobs folder, credentials file and a local HTTP server standing in for the sessions API."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "plugins" / "pult" / "scripts" / "sync-app-titles.py"


class Api(BaseHTTPRequestHandler):
    titles = {}  # bridge id -> title
    calls = []

    def _id(self):
        return self.path.rsplit("/", 1)[-1]

    def do_GET(self):
        Api.calls.append(("GET", self._id(), self.headers.get("Authorization")))
        if self._id() not in Api.titles:
            self.send_response(404); self.end_headers(); return
        body = json.dumps({"response_shape": {"title": Api.titles[self._id()]}}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)

    def do_PUT(self):
        data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        Api.calls.append(("PUT", self._id(), data))
        Api.titles[self._id()] = data["title"]
        self.send_response(200); self.end_headers(); self.wfile.write(b"{}")

    def log_message(self, *a):
        pass


class SyncAppTitlesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (self.tmp / "creds.json").write_text(json.dumps({"claudeAiOauth": {"accessToken": "tok"}}))
        self.server = HTTPServer(("127.0.0.1", 0), Api)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.shutdown)
        Api.titles, Api.calls = {}, []

    def job(self, short, name, bridge, at):
        d = self.tmp / "jobs" / short
        d.mkdir(parents=True)
        s = {"name": name, "updatedAt": at}
        if bridge:
            s["bridgeSessionId"] = bridge
        (d / "state.json").write_text(json.dumps(s), encoding="utf-8")

    def run_sync(self, *names):
        env = dict(os.environ, DEV_KIT_JOBS_DIR=str(self.tmp / "jobs"), DEV_KIT_CREDENTIALS_FILE=str(self.tmp / "creds.json"),
                   DEV_KIT_SESSIONS_API=f"http://127.0.0.1:{self.server.server_port}")
        out = subprocess.run([sys.executable, "-I", "-X", "utf8", str(SCRIPT), *names], env=env,
                             capture_output=True, text=True, encoding="utf-8", timeout=60)
        return out.returncode, out.stdout.strip().splitlines()

    # protects: Rule
    def test_renamed_lead_gets_its_title_and_the_rest_is_left(self):
        self.job("old1", "L: X", "cse_old", "2026-11-20T00:00:00Z")   # an older job of the same name: not touched
        self.job("new1", "L: X", "cse_x", "2026-11-26T00:00:00Z")
        self.job("ok1", "L: Y", "cse_y", "2026-11-26T00:00:00Z")
        self.job("nolink", "L: Z", None, "2026-11-26T00:00:00Z")
        Api.titles = {"cse_x": "P: X", "cse_y": "L: Y", "cse_old": "P: X"}
        code, lines = self.run_sync("L: X", "L: Y", "L: Z", "L: W")
        self.assertEqual(code, 0)
        self.assertEqual(lines, ["TITLE P: X -> L: X new1", "TITLE-OK L: Y ok1",
                                 "TITLE-SKIP L: Z: no job with a Remote Control link",
                                 "TITLE-SKIP L: W: no job with a Remote Control link"])
        self.assertEqual(Api.titles, {"cse_x": "L: X", "cse_y": "L: Y", "cse_old": "P: X"})
        self.assertEqual([c for c in Api.calls if c[0] == "PUT"], [("PUT", "cse_x", {"title": "L: X"})])
        self.assertTrue(all(c[2] == "Bearer tok" for c in Api.calls if c[0] == "GET"))

    # protects: Rule
    def test_failed_call_is_reported_with_exit_1(self):
        self.job("gone", "L: X", "cse_gone", "2026-11-26T00:00:00Z")
        code, lines = self.run_sync("L: X")
        self.assertEqual(code, 1)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("TITLE-FAILED L: X gone: "), lines[0])


if __name__ == "__main__":
    unittest.main()
