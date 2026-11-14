import io
import random
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:  # the script needs Pillow; without it the tests have nothing to run
    Image = None

SCRIPT = Path(__file__).resolve().parents[2] / "plugins" / "unity-kit" / "scripts" / "frames_to_gif.py"
if Image:
    sys.path.insert(0, str(SCRIPT.parent))
    import frames_to_gif as gif


def make_frames(folder, count, fps, noise=False, extension="png"):
    """Synthetic frames: a square moving over a gradient; the index has the real times."""
    rows = ["file,sinceStartSeconds,note"]
    rng = random.Random(1)
    for i in range(count):
        image = Image.new("RGB", (640, 360))
        draw = ImageDraw.Draw(image)
        for y in range(0, 360, 8):
            draw.rectangle([0, y, 640, y + 8], fill=(y // 2, 60, 200 - y // 2))
        draw.rectangle([i * 8, 140, i * 8 + 60, 200], fill=(255, 220, 0))
        if noise:
            for _ in range(4000):
                draw.point((rng.randrange(640), rng.randrange(360)), fill=tuple(rng.randrange(256) for _ in range(3)))
        name = f"frame_{i:04d}.{extension}"
        image.save(folder / name)
        rows.append(f"{name},{i / fps:.4f},x")
    (folder / "index.csv").write_text("\n".join(rows), encoding="utf-8")


def read_gif(path):
    with Image.open(path) as image:
        total, count = 0, 0
        while True:
            total += image.info.get("duration", 0)
            count += 1
            try:
                image.seek(count)
            except EOFError:
                return count, total / 1000.0, image.size, image.info.get("loop")


@unittest.skipUnless(Image, "Pillow is not installed")
class FramesToGif(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def run_script(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = gif.main([str(self.folder), *args])
        return code, out.getvalue(), err.getvalue()

    def test_even_picking_and_true_duration(self):
        make_frames(self.folder, 60, 30)  # 2 s of source at 30 fps
        target = self.folder / "a.gif"
        code, out, err = self.run_script("--fps", "12", "--width", "320", "--out", str(target))
        self.assertEqual(code, 0, err)
        count, seconds, size, loop = read_gif(target)
        self.assertEqual(loop, 0)
        self.assertEqual(size[0], 320)
        self.assertEqual(count, 24)
        self.assertAlmostEqual(seconds, 59 / 30, delta=0.15)
        self.assertIn("frames=24", out)
        self.assertIn("width=320", out)

    def test_window_and_speed(self):
        make_frames(self.folder, 90, 30)
        target = self.folder / "b.gif"
        self.assertEqual(self.run_script("--from", "1", "--to", "2", "--speed", "2", "--out", str(target))[0], 0)
        count, seconds, _, _ = read_gif(target)
        self.assertAlmostEqual(seconds, 0.5, delta=0.12)  # 1 s of play shown at double speed
        self.assertGreaterEqual(count, 5)

    def test_slower_source_has_no_duplicates(self):
        make_frames(self.folder, 10, 5)  # 2 s at 5 fps, target 12 fps
        target = self.folder / "c.gif"
        code, out, err = self.run_script("--out", str(target))
        self.assertEqual(code, 0, err)
        count, seconds, _, _ = read_gif(target)
        self.assertEqual(count, 10)
        self.assertAlmostEqual(seconds, 2.0, delta=0.15)

    def test_default_name_and_max_seconds(self):
        make_frames(self.folder, 30 * 12, 30, extension="jpg")
        code, out, err = self.run_script("--fps", "6", "--width", "240", "--max-seconds", "3")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.folder / "clip_0-3.gif").is_file(), out)
        self.assertIn("cut to", err)

    def test_no_index_uses_name_order(self):
        make_frames(self.folder, 30, 30)
        (self.folder / "index.csv").unlink()
        target = self.folder / "d.gif"
        code, _, err = self.run_script("--source-fps", "15", "--fps", "15", "--out", str(target))
        self.assertEqual(code, 0, err)
        count, seconds, _, _ = read_gif(target)
        self.assertEqual(count, 30)
        self.assertAlmostEqual(seconds, 2.0, delta=0.1)

    def test_smaller_file_on_retry(self):
        make_frames(self.folder, 90, 30, noise=True)
        target = self.folder / "e.gif"
        code, out, err = self.run_script("--max-mb", "0.7", "--out", str(target))
        self.assertEqual(code, 0, err)
        self.assertIn("retry with fewer fps", err)
        self.assertLess(target.stat().st_size, 0.7 * 1024 * 1024)

    def test_crop_takes_the_right_area(self):
        for i in range(12):  # grey frame, a red square at 200,100 (40x40), a blue one at 10,10 (40x40)
            image = Image.new("RGB", (640, 360), (128, 128, 128))
            draw = ImageDraw.Draw(image)
            draw.rectangle([200, 100, 239, 139], fill=(255, 0, 0))
            draw.rectangle([10, 10, 49, 49], fill=(0, 0, 255))
            image.save(self.folder / f"f{i:03d}.png")
        target = self.folder / "g.gif"
        code, out, err = self.run_script("--source-fps", "12", "--crop", "190,90,60,60", "--out", str(target))
        self.assertEqual(code, 0, err)
        self.assertIn("crop=190,90,60,60", out)
        self.assertIn("width=60", out)  # not scaled up to 480
        with Image.open(target) as image:
            self.assertEqual(image.size, (60, 60))
            rgb = image.convert("RGB")
        centre, corner = rgb.getpixel((30, 30)), rgb.getpixel((2, 2))
        self.assertTrue(centre[0] > 200 and centre[1] < 60 and centre[2] < 60, centre)
        self.assertTrue(all(abs(c - 128) < 25 for c in corner), corner)
        code, out, err = self.run_script("--source-fps", "12", "--crop", "600,300,100,100", "--width", "40",
                                         "--out", str(target))
        self.assertEqual(code, 0, err)
        self.assertIn("clipped to 600,300,40,60", err)
        self.assertIn("crop=600,300,40,60", out)
        code, _, err = self.run_script("--source-fps", "12", "--crop", "700,10,50,50")
        self.assertEqual((code, "outside" in err), (2, True))

    def test_errors(self):
        make_frames(self.folder, 10, 10)
        code, _, err = self.run_script("--from", "50", "--to", "60")
        self.assertEqual((code, "no frames between" in err), (2, True))
        code, _, err = self.run_script("--time-column", "nope")
        self.assertEqual((code, "column 'nope'" in err), (2, True))
        code, _, err = self.run_script("--file-column", "nope")
        self.assertEqual((code, "column 'nope'" in err), (2, True))
        code, _, err = self.run_script("--from", "2", "--to", "1")
        self.assertEqual(code, 2)

    def test_empty_folder(self):
        code, _, err = self.run_script()
        self.assertEqual((code, "no frames" in err), (2, True))

    def test_command_line_with_isolated_python(self):
        make_frames(self.folder, 30, 30)
        target = self.folder / "f.gif"
        result = subprocess.run([sys.executable, "-I", str(SCRIPT), str(self.folder), "--out", str(target)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)
        self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()
