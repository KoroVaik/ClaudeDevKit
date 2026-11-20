import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "web-kit" / "scripts" / "pair.mjs"

# A 1x1 PNG: only the header matters before the browser starts.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"
)


@unittest.skipUnless(shutil.which("node"), "node is not installed")
class PairArgsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.png = self.dir / "a.png"
        self.png.write_bytes(PNG)

    def run_pair(self, *args):
        return subprocess.run(["node", str(SCRIPT), *args], capture_output=True, text=True, encoding="utf-8")

    def test_missing_title_prints_usage(self):
        r = self.run_pair("--left", str(self.png), "--right", str(self.png), "--out", str(self.dir / "o.png"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("Usage: web-kit-pair", r.stderr)

    def test_long_title_is_refused(self):
        r = self.run_pair("--left", str(self.png), "--right", str(self.png), "--title", "x" * 61,
                          "--out", str(self.dir / "o.png"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("keep it to 60", r.stderr)

    def test_not_a_png_is_refused(self):
        bad = self.dir / "b.png"
        bad.write_text("not a png", encoding="utf-8")
        r = self.run_pair("--left", str(self.png), "--right", str(bad), "--title", "Empty list",
                          "--out", str(self.dir / "o.png"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("not a PNG", r.stderr)


if __name__ == "__main__":
    unittest.main()
