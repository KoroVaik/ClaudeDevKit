"""A user check: an agent's short piece of play in the open Unity editor, written as a recipe and run in one command.

    unity-kit-user-check <name or path of a recipe> [--project <folder>] [--dry-run]

The recipe <recipes>/<name>.json ({"about": ..., "steps": [...], "on-failure": [...]}) is played in Play Mode through the
Unity CLI Loop bridge (`uloop`): the game's real input, the project's own bridge commands, and expectations on the console,
the project's state command and written files. Each step waits at most its own bound. The report and the screenshots go to
<reports>/<stamp>_<name>/. The settings are the `## user-check` table of the project's `.claude/dev-kit.md`. Exit code: 0
passed, 1 a step failed, 2 not run (a refusal before Play Mode, a bridge that does not answer, a bad recipe or profile).
Format, steps and blocks: the `unity-kit:user-check` skill.
"""
import argparse
import datetime
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN_BLOCKS = os.path.join(PLUGIN, "skills", "user-check", "blocks")
PROFILE = os.path.join(".claude", "dev-kit.md")
SECTION = "user-check"
SETTINGS = {
    "uloop": "uloop", "uloop-env": "", "recipes": "", "reports": "", "scene": "", "state-command": "",
    "ready": "Playing=true", "ready-within": "60", "click-command": "", "panel-height": "",
}
REQUIRED = ("recipes", "reports", "state-command")
POLL = 0.25
MAX_WAIT = 600.0
# The steps, each with the number of its arguments (at least, at most) and whether it takes "within S".
STEPS = {
    "wait": (1, 1, False), "key": (1, 2, False), "click": (1, 1, False), "drag": (2, 3, False),
    "mouse": (2, 99, False), "call": (1, 99, False), "expect-log": (1, 1, True), "expect-file": (1, 2, True),
    "expect-state": (1, 2, True), "expect-no-errors": (0, 0, False), "shot": (0, 1, False),
}
ACTIONS = ("key", "click", "drag", "mouse", "call")


class NotRun(Exception):
    """The check cannot run or go on: exit code 2."""


class StepFailed(Exception):
    pass


# --- the profile and the recipe ---------------------------------------------------------------------------------

def find_root(start):
    folder = os.path.abspath(start)
    while True:
        if os.path.isfile(os.path.join(folder, PROFILE)):
            return folder
        parent = os.path.dirname(folder)
        if parent == folder:
            raise NotRun(f"no {PROFILE} in {start} or above it; run from the project folder or pass --project")
        folder = parent


def read_settings(root):
    with open(os.path.join(root, PROFILE), encoding="utf-8") as file:
        text = file.read()
    match = re.search(rf"^## {re.escape(SECTION)}[ \t]*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not match:
        raise NotRun(f"no section '## {SECTION}' in {PROFILE}")
    settings = dict(SETTINGS)
    for line in match.group(1).splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or cells[0] == "Setting" or set(cells[0]) <= set("-: "):
            continue
        name, value = cells[0].strip("`"), cells[1].strip().strip("`").strip()
        if name not in SETTINGS:
            raise NotRun(f"unknown setting '{name}' in '## {SECTION}'; known: {', '.join(SETTINGS)}")
        if value:
            settings[name] = value
    missing = [name for name in REQUIRED if not settings[name]]
    if missing:
        raise NotRun(f"'## {SECTION}' misses {', '.join(missing)}")
    return settings


def conditions(text):
    """'Presentation=Live; StartupBusy=false' -> [('Presentation', 'Live'), ('StartupBusy', 'false')]."""
    pairs = []
    for part in filter(None, (p.strip() for p in text.split(";"))):
        if "=" not in part:
            raise NotRun(f"'{part}' is not Field=value")
        field, value = part.split("=", 1)
        pairs.append((field.strip(), value.strip()))
    return pairs


def number(text, what):
    try:
        value = float(text.rstrip("s"))
    except ValueError:
        raise NotRun(f"{what} '{text}' is not a number of seconds")
    if not 0 <= value <= MAX_WAIT:
        raise NotRun(f"{what} {value} is outside 0..{MAX_WAIT:.0f} s")
    return value


def parse_point(text):
    panel = text.startswith("panel:")
    try:
        x, y = (float(v) for v in text[6 if panel else 0:].split(","))
    except ValueError:
        raise NotRun(f"'{text}' is not a point: x,y (fractions of the game picture) or panel:x,y")
    if not panel and not (0 <= x <= 1 and 0 <= y <= 1):
        raise NotRun(f"'{text}': a point without panel: is fractions of the game picture, 0..1")
    return panel, x, y


def substitute(text, settings):
    """`{setting}` -> that profile setting's value."""
    return re.sub(r"\{([a-z-]+)\}", lambda m: settings.get(m.group(1), m.group(0)), text)


def parse_step(text, settings):
    """A recipe line (settings substituted) -> (kind, args, within); every mistake is found here, before Play Mode."""
    try:
        words = shlex.split(text)
    except ValueError as error:
        raise NotRun(f"'{text}': {error}")
    if not words:
        raise NotRun("an empty step")
    kind, args = words[0], words[1:]
    if kind not in STEPS:
        raise NotRun(f"unknown step '{kind}'; known: {', '.join(STEPS)}, use")
    least, most, waits = STEPS[kind]
    within = 0.0
    if waits and len(args) >= 2 and args[-2] == "within":
        within, args = number(args[-1], "within"), args[:-2]
    if not least <= len(args) <= most:
        raise NotRun(f"'{text}': {kind} takes {least}..{most} arguments" + (" and within S" if waits else ""))
    if kind == "wait":
        number(args[0], "wait")
    if kind in ("key", "drag") and len(args) == (2 if kind == "key" else 3):
        number(args[-1], kind)
    if kind in ("click", "drag"):
        for point in args[:2]:
            parse_point(point)
    if kind == "mouse":
        parse_point(args[1])
    if kind == "expect-log":
        try:
            re.compile(args[0])
        except re.error as error:
            raise NotRun(f"'{text}': bad regex ({error})")
    if kind == "expect-file" and len(args) == 2 and "=" not in args[1]:
        raise NotRun(f"'{text}': the second argument is path=value")
    if kind == "expect-state":
        rest = args[1:] if args[0] == "not" else args
        if len(rest) != 1 or (rest[0] != "ready" and "=" not in rest[0]):
            raise NotRun(f"'{text}': expect-state [not] ready|Field=value")
    if kind == "shot" and args and not re.fullmatch(r"[\w-]+", args[0]):
        raise NotRun(f"'{text}': a shot label is letters, digits, - and _")
    return kind, args, within


def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, ValueError) as error:
        raise NotRun(f"{what} {path}: {error}")
    if not isinstance(data, dict) or not isinstance(data.get("steps", []), list):
        raise NotRun(f"{what} {path}: must be {{\"about\": ..., \"steps\": [...]}}")
    return data


def block_path(root, settings, name):
    for folder in (os.path.join(root, settings["recipes"], "blocks"), PLUGIN_BLOCKS):
        path = os.path.join(folder, name + ".json")
        if os.path.isfile(path):
            return path
    raise NotRun(f"no block '{name}' in {settings['recipes']}/blocks or the plugin")


def expand(lines, root, settings, chain=()):
    """Recipe lines -> [(label, text, parsed)], each `use <block>` replaced by the block's steps."""
    steps = []
    for text in lines:
        if not isinstance(text, str):
            raise NotRun(f"a step must be a line of words, not {text!r}")
        words = text.split()
        if words and words[0] == "use":
            if len(words) != 2:
                raise NotRun(f"'{text}': use <block>")
            name = words[1]
            if name in chain:
                raise NotRun(f"block '{name}' includes itself: {' > '.join(chain + (name,))}")
            block = load_json(block_path(root, settings, name), "block")
            steps += [(f"[{' > '.join(chain + (name,))}] ", t, p)
                      for _, t, p in expand(block.get("steps") or [], root, settings, chain + (name,))]
            continue
        text = substitute(text, settings)
        steps.append(("", text, parse_step(text, settings)))
    return steps


def recipe_path(root, settings, name):
    if name.endswith(".json") or os.sep in name or "/" in name:
        return os.path.abspath(name)
    return os.path.join(root, settings["recipes"], name + ".json")


# --- the check --------------------------------------------------------------------------------------------------

def make_uloop(root, settings):
    env = dict(os.environ)
    for field, value in conditions(settings["uloop-env"]):
        env[field] = value

    def uloop(*args, timeout=60):
        try:
            done = subprocess.run([settings["uloop"], *args, "--project-path", root], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise NotRun(f"uloop {args[0]} did not answer in {timeout} s")
        except OSError as error:
            raise NotRun(f"uloop could not start ({settings['uloop']}): {error}")
        out = done.stdout.strip()
        try:
            return json.loads(out)
        except ValueError:
            raise NotRun(f"uloop {args[0]} answered no JSON: {(out or done.stderr.strip())[:600]}")
    return uloop


def field(answer, name):
    return next((v for k, v in answer.items() if k.lower() == name.lower()), None)


def same(value, want):
    return str(value).lower() == want.lower()


def refused(answer):
    return answer.get("Success") is False


class Check:
    def __init__(self, uloop, root, settings, name, clock=time):
        self.uloop, self.root, self.settings, self.name, self.clock = uloop, root, settings, name, clock
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.folder = os.path.join(root, settings["reports"], stamp + "_" + name)
        self.lines = []
        self.shots = 0
        self.ready = conditions(settings["ready"])
        # The console before the last action and its time: expect-log and expect-file look after them.
        self.mark_logs = 0
        self.mark_time = clock.time()
        self.errors_at_start = 0

    # --- the bridge ---

    def state(self):
        answer = self.uloop(self.settings["state-command"])
        if refused(answer):
            raise NotRun(f"{self.settings['state-command']} refused: {answer.get('Message')}")
        return answer

    def count(self, *options):
        return int(self.uloop("get-logs", *options, "--max-count", "1").get("TotalCount") or 0)

    def mark(self):
        self.mark_logs = self.count()
        self.mark_time = self.clock.time()

    def new_logs(self):
        fresh = self.count() - self.mark_logs
        if fresh <= 0:
            return []
        # get-logs lists the newest first.
        return self.uloop("get-logs", "--max-count", str(fresh)).get("Logs") or []

    def size(self):
        s = self.state()
        width, height = float(field(s, "GameWidth") or 0), float(field(s, "GameHeight") or 0)
        if width <= 0 or height <= 0:
            raise StepFailed(f"no game picture size from {self.settings['state-command']}")
        return width, height

    def point(self, text):
        """-> fractions of the game picture from its top left."""
        panel, x, y = parse_point(text)
        if not panel:
            return x, y
        width, height = self.size()
        base = float(self.settings["panel-height"] or 0)
        unit = max(1.0, height / base) if base > 0 else 1.0
        return x * unit / width, y * unit / height

    def act(self, *args):
        answer = self.uloop(*args)
        if refused(answer):
            raise StepFailed(answer.get("Message") or f"{args[0]} refused")
        return answer.get("Message") or "done"

    # --- steps ---

    def step(self, kind, args, within):
        if kind in ACTIONS:
            self.mark()
        if kind == "wait":
            self.clock.sleep(number(args[0], "wait"))
            return f"waited {args[0]} s"
        if kind == "key":
            return self.act("simulate-keyboard", "--action", "Press", "--key", args[0], "--duration",
                            args[1].rstrip("s") if len(args) > 1 else "0")
        if kind in ("click", "drag"):
            command = self.settings["click-command"]
            if not command:
                raise StepFailed("no click-command in the profile; for the Input System's mouse use mouse")
            x, y = self.point(args[0])
            call = [command, "--action", kind, "--x", f"{x:.5f}", "--y", f"{y:.5f}"]
            if kind == "drag":
                tx, ty = self.point(args[1])
                call += ["--to-x", f"{tx:.5f}", "--to-y", f"{ty:.5f}", "--seconds",
                         args[2].rstrip("s") if len(args) > 2 else "0.5"]
            return self.act(*call)
        if kind == "mouse":
            width, height = self.size()
            x, y = self.point(args[1])
            return self.act("simulate-mouse-input", "--action", args[0], "--x", f"{x * width:.1f}",
                            "--y", f"{y * height:.1f}", *args[2:])
        if kind == "call":
            return self.act(*args)
        if kind == "expect-log":
            return self.expect_log(args[0], within)
        if kind == "expect-state":
            return self.expect_state(args, within)
        if kind == "expect-file":
            return self.expect_file(args, within)
        if kind == "expect-no-errors":
            return self.expect_no_errors()
        if kind == "shot":
            return self.shot(args[0] if args else "shot")
        raise StepFailed("unknown step " + kind)

    def until(self, within, test):
        """test() -> (done, evidence); once now and then every POLL until within seconds have passed."""
        end = self.clock.time() + within
        while True:
            done, evidence = test()
            if done or self.clock.time() >= end:
                return done, evidence
            self.clock.sleep(POLL)

    def judged(self, within, test):
        done, evidence = self.until(within, test)
        if not done:
            raise StepFailed(evidence)
        return evidence

    def expect_log(self, pattern, within):
        regex = re.compile(pattern)

        def test():
            for entry in self.new_logs():
                if regex.search(entry.get("Message", "")):
                    return True, entry["Message"][:300]
            return False, "no console line after the last action matches " + pattern
        return self.judged(within, test)

    def expect_state(self, args, within):
        negate = args[0] == "not"
        target = args[-1]
        wanted = self.ready if target == "ready" else conditions(target)

        def test():
            s = self.state()
            seen = ", ".join(f"{name} {field(s, name)}" for name, _ in wanted)
            met = all(same(field(s, name), want) for name, want in wanted)
            return met != negate, seen
        return self.judged(within, test)

    def expect_file(self, args, within):
        pattern = os.path.join(self.root, args[0])

        def test():
            files = [f for f in glob.glob(pattern) if os.path.getmtime(f) >= self.mark_time - 1]
            if not files:
                return False, "no file " + args[0] + " written since the last action"
            newest = max(files, key=os.path.getmtime)
            name = os.path.relpath(newest, self.root)
            if len(args) < 2:
                return True, name
            path, want = args[1].split("=", 1)
            try:
                with open(newest, encoding="utf-8") as file:
                    value = json.load(file)
                for key in path.split("."):
                    if key == "length" and isinstance(value, (list, str)):
                        value = len(value)
                    elif isinstance(value, list):
                        value = value[int(key)]
                    else:
                        value = value[key]
            except (ValueError, KeyError, IndexError, TypeError, OSError) as error:
                return False, f"{name}: {path} unreadable ({error})"
            return same(value, want), f"{name}: {path} = {value}"
        return self.judged(within, test)

    def errors(self, limit):
        answer = self.uloop("get-logs", "--log-type", "Error", "--max-count", str(max(1, limit)))
        fresh = int(answer.get("TotalCount") or 0) - self.errors_at_start
        return fresh, (answer.get("Logs") or [])[:max(0, min(fresh, limit))]

    def expect_no_errors(self):
        fresh, logs = self.errors(3)
        if fresh > 0:
            raise StepFailed(f"{fresh} console errors since the start: " + " | ".join(e.get("Message", "")[:150] for e in logs))
        return "no console errors since the start"

    def shot(self, label):
        self.shots += 1
        temp = os.path.join(self.folder, "_shot")
        answer = self.uloop("screenshot", "--capture-mode", "rendering", "--output-directory", temp)
        images = answer.get("Screenshots") or []
        if refused(answer) or not images:
            raise StepFailed(answer.get("Message") or "no screenshot")
        target = os.path.join(self.folder, f"{self.shots:02d}_{label}.png")
        shutil.move(images[0]["ImagePath"], target)
        shutil.rmtree(temp, ignore_errors=True)
        return os.path.relpath(target, self.root) + f" ({images[0].get('Width')}x{images[0].get('Height')})"

    # --- the run ---

    def write(self, line):
        print(line, flush=True)
        self.lines.append(line)

    def play(self, number_, label, text, parsed):
        try:
            evidence = self.step(*parsed)
            self.write(f"PASS {number_:2d} {label}{text} | {evidence}")
            return True
        except StepFailed as error:
            self.write(f"FAIL {number_:2d} {label}{text} | {error}")
            return False

    def run(self, recipe, steps, on_failure):
        os.makedirs(self.folder, exist_ok=True)
        self.write(f"user check {self.name}: {recipe.get('about', '')}")
        try:
            return self.finish(self.played(steps, on_failure))
        except NotRun as error:
            self.write("not run to the end: " + str(error))
            return self.finish(2)

    def played(self, steps, on_failure):
        s = self.state()
        scene = self.settings["scene"]
        refusal = ("the editor is in Play Mode" if same(field(s, "Playing"), "true")
                   else "the editor is compiling" if same(field(s, "Compiling"), "true")
                   else f"the open scene is {field(s, 'Scene')}, not {scene}" if scene and field(s, "Scene") != scene
                   else None)
        if refusal:
            raise NotRun(refusal)
        answer = self.uloop("control-play-mode", "--action", "Play", "--unsaved-changes", "keep", timeout=240)
        if not answer.get("IsPlaying"):
            raise NotRun("Play Mode did not start: " + str(answer.get("Message")))
        code = 2
        try:
            s = self.state()
            self.write(f"game picture {field(s, 'GameWidth')}x{field(s, 'GameHeight')}")
            self.errors_at_start = self.count("--log-type", "Error")
            self.mark()
            code = 0
            for number_, (label, text, parsed) in enumerate(steps, 1):
                if not self.play(number_, label, text, parsed):
                    code = 1
                    for extra, (label_, text_, parsed_) in enumerate(on_failure, 1):
                        self.play(extra, "on failure: " + label_, text_, parsed_)
                    break
            fresh, logs = self.errors(5)
            self.write(f"console errors since the start {fresh}" + "".join("\n  " + e.get("Message", "")[:200] for e in logs))
        finally:
            try:
                answer = self.uloop("control-play-mode", "--action", "Stop", timeout=120)
                self.write("Play Mode left" if not answer.get("IsPlaying") else "WARNING: Play Mode did not stop")
            except NotRun as error:
                self.write("WARNING: Play Mode may still run: " + str(error))
        return code

    def finish(self, code):
        result = {0: "passed", 1: "FAILED"}.get(code, "not run")
        self.write(f"result: {result} (code {code}); report {os.path.relpath(self.folder, self.root)}")
        with open(os.path.join(self.folder, "report.txt"), "w", encoding="utf-8") as file:
            file.write("\n".join(self.lines) + "\n")
        return code


def prepare(name, project):
    root = find_root(project)
    settings = read_settings(root)
    path = recipe_path(root, settings, name)
    if not os.path.isfile(path):
        raise NotRun(f"no recipe {path}")
    recipe = load_json(path, "recipe")
    steps = expand(recipe.get("steps") or [], root, settings)
    if not steps:
        raise NotRun(f"recipe {path} has no steps")
    on_failure = expand(recipe.get("on-failure", ["shot failure"]), root, settings)
    name = os.path.splitext(os.path.basename(path))[0]
    return root, settings, recipe, name, steps, on_failure


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("recipe", help="a recipe name in the profile's recipes folder, or a path to a .json recipe")
    parser.add_argument("--project", default=".", help="the project folder (default: found from the current folder up)")
    parser.add_argument("--dry-run", action="store_true", help="read the recipe and its blocks and print the steps; no Unity")
    a = parser.parse_args(argv)
    # Recipes and console lines are in any language; a Windows console's code page must not break the report.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        root, settings, recipe, name, steps, on_failure = prepare(a.recipe, a.project)
    except NotRun as error:
        print("ERROR: " + str(error))
        return 2
    if a.dry_run:
        print(f"user check {name}: {recipe.get('about', '')}")
        for number_, (label, text, _) in enumerate(steps, 1):
            print(f"{number_:2d} {label}{text}")
        for label, text, _ in on_failure:
            print(f"on failure: {label}{text}")
        return 0
    return Check(make_uloop(root, settings), root, settings, name).run(recipe, steps, on_failure)


if __name__ == "__main__":
    sys.exit(main())
