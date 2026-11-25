import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
from test_retro import RetroFixture  # noqa: E402

PLUGIN = TESTS.parent.parent / "plugins" / "rules-kit"
sys.path.insert(0, str(PLUGIN / "scripts"))
import packets  # noqa: E402
import parts  # noqa: E402
import retro  # noqa: E402
import subscriptions  # noqa: E402
import talk  # noqa: E402

STAMP = "2026-11-24T10:00:00Z"
DEMO_SUBSCRIPTION = """| Setting | Value |
|---|---|
| set | demo |
| reviewed by | repo |
| lands by | merged |

## Files

| Path | Type | Part kinds |
|---|---|---|
| skills/lead/SKILL.md | process | skill demo:lead |
| skills/build/SKILL.md | process | skill demo:build |
| agents/coder.md | process | agent demo:coder |
| hooks/*.py | technical | hook demo |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| deploy asked | process | the owner is asked to deploy: «deploy now\\?» |
| talk sign | talk | «зараз» |
"""
GLOBAL_RULES = """# Global

## Check before you act or agree

- A yes/no question gets "так" or "ні" as the first word.

## Chat replies

- Ordinary reply: 2-5 short, plain sentences.
- Report: one list, at most 5 items, each one sentence of at most 15 words.

## Reply language

- Reply in Ukrainian whenever any paragraph of the reply has more than two sentences.

## No em dash

Never use the em dash anywhere.

## Process

Always run the build before you deploy the build.
"""


def line(kind, **fields):
    return {"type": kind, "timestamp": STAMP, **fields}


def owner(text, origin="human"):
    return line("user", origin={"kind": origin}, message={"role": "user", "content": text})


def command(name):
    return line("user", origin={"kind": "human"},
                message={"content": f"<command-message>{name}</command-message>\n<command-name>/{name}</command-name>"})


def said(text):
    return line("assistant", message={"content": [{"type": "text", "text": text}]})


def use(tool_id, name, tool_input):
    return line("assistant", message={"content": [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]})


def done(tool_id, text="ok", error=False):
    return line("user", message={"content": [{"type": "tool_result", "tool_use_id": tool_id, "content": text,
                                              "is_error": error}]})


def numbered(entries):
    return [(number, entry) for number, entry in enumerate(entries, 1)]


def plugins_with_demo(folder):
    """A plugins folder with the plugin `demo`: its subscription and a hook whose refusal text is known."""
    (folder / "demo" / "hooks").mkdir(parents=True)
    (folder / "demo" / "skills" / "lead").mkdir(parents=True)
    (folder / "demo" / "skills" / "build").mkdir(parents=True)
    (folder / "demo" / "rules-subscription.md").write_text(DEMO_SUBSCRIPTION, encoding="utf-8")
    (folder / "demo" / "hooks" / "guard.py").write_text(
        "REASON = 'Deploy guard (docs/deploy.md): ' + fix  # the reason of a refusal\n", encoding="utf-8")
    (folder / "demo" / "skills" / "lead" / "SKILL.md").write_text(
        "# Lead\n\n## Deploy\n\nAsk the owner before a deploy of the build.\n", encoding="utf-8")
    (folder / "demo" / "skills" / "build" / "SKILL.md").write_text(
        "# Build\n\n## Steps\n\nRun the build and check the deploy target.\n", encoding="utf-8")


class SplitTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        plugins_with_demo(self.tmp / "plugins")
        self.hooks = parts.HookIndex(self.tmp / "plugins")

    # protects: Flow
    def test_a_session_splits_by_slash_command_skill_call_agent_call_and_hook_refusal(self):
        entries = numbered([
            command("demo:lead"),                                            # 1: a skill by slash command
            said("starting"),                                                # 2
            use("s", "Skill", {"skill": "demo:build"}),                      # 3: a skill inside the lead's
            use("a", "Agent", {"subagent_type": "demo:coder"}),              # 4
            done("a", "launched"),                                           # 5
            use("b", "Bash", {"command": "deploy"}),                         # 6
            done("b", "PreToolUse:Bash hook error: Deploy guard (docs/deploy.md): ask first", True),  # 7
            command("clear"),                                                # 8: ends the skills
            said("fresh"),                                                   # 9
        ])
        found = parts.split(entries, hooks=self.hooks)
        self.assertEqual([(p.label(), p.start, p.end) for p in found],
                         [("session", 1, 9), ("skill demo:lead", 1, 7), ("skill demo:build", 3, 7),
                          ("agent demo:coder", 4, 5), ("hook PreToolUse:Bash (demo)", 7, 7)])
        self.assertEqual(parts.innermost(found, 6).label(), "skill demo:build")
        self.assertEqual(parts.innermost(found, 7).plugin, "demo")
        self.assertEqual(parts.innermost(found, 9).label(), "session")
        self.assertEqual(parts.body(parts.innermost(found, 7)).label(), "skill demo:build")

    # protects: Rule
    def test_a_hooks_plugin_comes_from_its_command_path_else_from_the_words_only_one_plugin_holds(self):
        self.assertEqual(self.hooks.plugin("x", "python C:/a/.claude/plugins/cache/mkt/web-kit/1.0/hooks/h.py"), "web-kit")
        self.assertEqual(self.hooks.plugin("x", "python C:/repo/plugins/pult/hooks/hub.py"), "pult")
        self.assertEqual(self.hooks.plugin("Deploy guard (docs/deploy.md): ask first", "command hook"), "demo")
        self.assertIsNone(self.hooks.plugin("Something no plugin says at all", "command hook"))
        self.assertEqual(parts.hook_refusal("PreToolUse:Bash hook error: [powershell -File C:/u/.claude/hooks/f.ps1]: "
                                            "BLOCKED: find /"),
                         ("PreToolUse:Bash", "BLOCKED: find /", "powershell -File C:/u/.claude/hooks/f.ps1"))

    # protects: Rule
    def test_candidates_are_the_parts_own_sets_then_its_parents_then_global_and_the_project(self):
        (self.tmp / "global").mkdir()
        (self.tmp / "global" / "rules-subscription.md").write_text(
            DEMO_SUBSCRIPTION.replace("| set | demo |", "| set | global |"), encoding="utf-8")
        with mock.patch.dict(os.environ, {subscriptions.GLOBAL_ENV: str(self.tmp / "global")}):
            registry = subscriptions.discover(plugins=self.tmp / "plugins", global_folder=self.tmp / "global")
            entries = numbered([use("s", "Skill", {"skill": "other:x"}), use("b", "Bash", {}),
                                done("b", "PreToolUse:Bash hook error: Deploy guard (docs/deploy.md): no", True)])
            found = parts.split(entries, hooks=self.hooks)
            hook = parts.innermost(found, 3)
            self.assertEqual(parts.candidates(hook, registry, "repo"), ["demo", "global", "repo"])
            self.assertEqual(parts.target(hook, registry, "repo"), "demo")
            self.assertEqual(parts.target(parts.innermost(found, 2), registry, "repo"), "repo")  # no set names other:x


class TalkTestCase(unittest.TestCase):
    def hits(self, owner_text, reply):
        return [check for check, _ in talk.check_reply(owner_text, reply)]

    # protects: Rule
    def test_each_talk_check_catches_its_breach(self):
        self.assertEqual(self.hits("ok", "Done — all green."), ["dash"])
        self.assertEqual(self.hits("ok", "One. Two. Three. Four. Five. Six."), ["long reply"])
        self.assertEqual(self.hits("ok", "- a\n- b\n- c\n- d\n- e\n- f"), ["long list"])
        self.assertEqual(self.hits("ok", "- " + " ".join(["word"] * 16)), ["long item"])
        self.assertEqual(self.hits("Що там із тестами?", "The tests pass now. The lint is green. Nothing is left."),
                         ["not ukrainian"])
        self.assertEqual(self.hits("Тести зелені?", "Усі тести пройшли."), ["yes-no first"])
        self.assertEqual(self.hits("Тести зелені?", "**Так**, усі тести пройшли."), [])

    # protects: Edge
    def test_text_that_is_not_the_agents_own_prose_and_the_allowed_extras_raise_nothing(self):
        cases = [
            ("ok", "Code:\n```\na — b\n```\nQuote: «a — b». Also “c – d”."),  # code and quotes keep their dashes
            ("ok", "> owner wrote — this\n| a | b — c |\nFine."),  # a quote line and a table row
            ("ok", "One. Two. Three. Four. Five.\n\nЗакриваємо?\nРекомендую: так - готово."),  # closing question, advice
            ("ok", "1. Лишаємо всі шістнадцять правил як є, без змін у жодному файлі? (бо всі вони вже перевірені)"
                   " Рекомендую: так - нічого не ламається і не треба переписувати нічого."),  # a batch item
            ("Тести зелені?", "Ні, один падає."),
            ("<!-- reply 1 -->\n> Лишаємо як є?\n\nЧОМУ?!", "Бо так простіше."),  # the app's quote of a reply
            ("Чому тести червоні?", "Бо лінт падає."),  # a question word first: no yes/no question
            ("Робимо A чи B?", "B, бо дешевше."),  # either-or
            ("What now?", "Run the tests. Then the lint. Then report. Then wait."),  # an English owner: no language check
            # launch lines (new «помічник:», «сесія:», English and the old «агент:») are not prose
            ("ok", "One. Two. Three. Four. Five.\nпомічник: Coder. Sonnet. Medium."),
            ("ok", "One. Two. Three. Four. Five.\nhelper: Coder. Sonnet. Medium."),
            ("ok", "One. Two. Three. Four. Five.\nсесія: Coder. Sonnet. Medium."),
            ("ok", "One. Two. Three. Four. Five.\nsession: Coder. Sonnet. Medium."),
            ("ok", "One. Two. Three. Four. Five.\nагент: Coder. Sonnet. Medium."),
        ]
        for owner_text, reply in cases:
            with self.subTest(reply=reply):
                self.assertEqual(self.hits(owner_text, reply), [])

    # protects: Rule
    def test_only_turns_the_owner_opened_are_checked_on_their_last_reply(self):
        entries = numbered([
            owner("Brief from the lead: build it."),             # 1: the first prompt (a Manager gets it from the Lead)
            said("Working — first note."), said("Done — built."),  # 2, 3: the reply is the last text
            owner("Status from M", origin="peer"),               # 4: another session's message
            said("Noted — fine."),                               # 5: not a reply to the owner
            line("user", isMeta=True, message={"content": "Base directory for this skill: x"}),
            owner("Ну як?"),                                     # 7
            said("[SYSTEM NOTIFICATION - NOT USER INPUT]\nThis is an automated event — not a reply."),  # an echo
        ])
        self.assertEqual([(hit["check"], hit["line"], hit["first_prompt"]) for hit in talk.check_entries(entries)],
                         [("dash", 3, True)])
        self.assertEqual([hit["first_prompt"] for hit in talk.check_entries(entries, at_start=False)], [False])

    # protects: Rule
    def test_the_rule_line_of_a_check_is_found_in_the_talk_sections_then_the_whole_file_else_the_fallback(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "CLAUDE.md").write_text(GLOBAL_RULES, encoding="utf-8")
        shutil.copy(PLUGIN / "templates" / "global-rules-subscription.md", tmp / "rules-subscription.md")
        with mock.patch.dict(os.environ, {subscriptions.GLOBAL_ENV: str(tmp)}):
            registry = subscriptions.discover(plugins=tmp / "none", global_folder=tmp)
            refs = talk.rule_refs(registry)
        self.assertEqual((refs["long reply"].set, refs["long reply"].line, refs["long reply"].section),
                         ("global", 9, "Chat replies"))
        self.assertEqual((refs["dash"].line, refs["dash"].section), (16, "No em dash"))
        self.assertEqual((refs["yes-no first"].line, refs["yes-no first"].section), (5, "Check before you act or agree"))
        (tmp / "CLAUDE.md").write_text("# Empty\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {subscriptions.GLOBAL_ENV: str(tmp)}):
            fallback = talk.rule_refs(subscriptions.discover(plugins=tmp / "none", global_folder=tmp))["long list"]
        self.assertEqual((fallback.set, fallback.rel, fallback.line, fallback.section), ("global", "CLAUDE.md", 0, "Chat replies"))


class PacketTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        plugins_with_demo(self.tmp / "plugins")
        (self.tmp / "global").mkdir()
        (self.tmp / "global" / "CLAUDE.md").write_text(GLOBAL_RULES, encoding="utf-8")
        shutil.copy(PLUGIN / "templates" / "global-rules-subscription.md", self.tmp / "global" / "rules-subscription.md")
        patcher = mock.patch.dict(os.environ, {subscriptions.GLOBAL_ENV: str(self.tmp / "global")})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.registry = subscriptions.discover(plugins=self.tmp / "plugins", global_folder=self.tmp / "global")
        self.hooks = parts.HookIndex(self.tmp / "plugins")

    def session(self):
        return numbered([
            command("demo:lead"),                                                      # 1
            owner("Збери і задеплой."),                                                # 2
            said("Ready to deploy now? Рекомендую: так."),                             # 3: the set's own sign
            owner("не так, я ж казав спершу build"),                                   # 4: an owner correction
            use("b1", "Bash", {"command": "make build"}), done("b1", "make: build failed", True),  # 5, 6
            use("b2", "Bash", {"command": "make build"}), done("b2", "make: build failed", True),  # 7, 8
            use("b3", "Bash", {"command": "make build"}), done("b3", "make: build failed", True),  # 9, 10
        ])

    # protects: Flow
    def test_a_part_with_a_sign_gets_a_packet_with_its_excerpt_and_only_the_matching_process_rule_lines(self):
        entries = self.session()
        found = parts.split(entries, hooks=self.hooks)
        marked = packets.mark(entries, found, self.registry, "repo")
        self.assertEqual([(m.part.label(), sorted(m.general), m.own) for m in marked],
                         [("skill demo:lead", ["failed calls", "owner correction", "repeated call"],
                           {"demo": ["deploy asked"]})])  # the talk sign «зараз» is the talk check's, not a mark
        path, data = packets.write(self.tmp / "packets", self.tmp / "abcdef12-x.jsonl", "S (abcdef12)", entries,
                                   marked[0], self.registry, "repo")
        text = path.read_text(encoding="utf-8")
        self.assertEqual(path.name, "abcdef12-L1.md")
        self.assertEqual(data["candidates"], ["demo", "global", "repo"])
        self.assertIn("L4 owner: не так, я ж казав спершу build", text)
        self.assertIn("### demo | skills/lead/SKILL.md", text)
        self.assertIn("5: Ask the owner before a deploy of the build.", text)
        self.assertNotIn("skills/build/SKILL.md", text)  # a row of another skill of the set
        self.assertIn("22: Always run the build before you deploy the build.", text)  # the global set's process part
        self.assertNotIn("Ordinary reply", text)  # a talk-typed section is not a process rule

    # protects: Rule
    def test_failed_calls_mark_a_main_session_but_a_subagent_only_for_one_error_repeated(self):
        # A coder's tests failing while it works are normal: three different errors in a subagent are no sign.
        def errors(*texts):
            return numbered([entry for n, text in enumerate(texts) for entry in (
                use(f"t{n}", "Bash", {"command": f"pytest {n}"}), done(f"t{n}", text, True))])

        def signs(entries, kind):
            found = parts.split(entries, kind, "dev-kit:coder" if kind == "agent" else "")
            return [sorted(marks.general) for marks in packets.mark(entries, found)]

        different = errors("1 failed: test_a", "2 failed: test_b", "1 failed: test_c")
        self.assertEqual(signs(different, "session"), [["failed calls"]])
        self.assertEqual(signs(different, "agent"), [])
        same = errors("ImportError: no module x", "ImportError: no module x", "ImportError: no module x")
        self.assertEqual(signs(same, "agent"), [["failed calls"]])

    # protects: Edge
    def test_an_excerpt_over_its_cap_keeps_the_lines_around_the_signs(self):
        filler = [said(f"step {n} " + "x" * 300) for n in range(80)]
        entries = numbered(filler + [owner("я ж казав інакше")] + filler)
        part = parts.split(entries)[0]
        with mock.patch.object(packets, "EXCERPT_CHARS", 3000):
            text = packets.excerpt(entries, part, {81})
        self.assertLessEqual(len(text), 3000 + 400)
        self.assertIn("L81 owner: я ж казав інакше", text)
        self.assertIn("...", text)

    # protects: Rule
    def test_a_sign_gap_is_written_only_for_a_set_whose_own_signs_did_not_fire(self):
        data = {"part": "skill demo:lead", "session": "S (abcdef12)", "lines": [1, 10], "own_signs": {"demo": ["x"]},
                "general": [{"sign": "failed calls", "kind": "technical", "pattern": "make: build failed",
                             "evidence": "3 errors"}]}
        self.assertIsNone(packets.gap_line(data, "demo", "2026-11-24"))
        gap = packets.gap_line(data, "global", "2026-11-24")
        self.assertTrue(gap.startswith("- 2026-11-24 | from rules-kit | sign-gap | global: the part skill demo:lead"))
        self.assertIn("failed calls: «make: build failed»", gap)


class ScanPartsTestCase(RetroFixture):
    """The scan lays technical and talk findings to the sets of their parts; `parts` and `add --packet`."""

    def setUp(self):
        super().setUp()
        plugins_with_demo(self.tmp / "plugins")
        (self.tmp / "global").mkdir()
        (self.tmp / "global" / "CLAUDE.md").write_text(GLOBAL_RULES, encoding="utf-8")

    def new_lines(self, set_name):
        folder = self.set_folder(set_name) / "new"
        return [text for path in sorted(folder.glob("*.md")) for text in retro.read_lines(path)] if folder.is_dir() else []

    # protects: Flow
    def test_a_repeated_call_in_a_skill_goes_to_the_skills_set_and_a_hook_refusal_to_the_hooks_plugin_from_any_project(self):
        refusal = "PreToolUse:Bash hook error: Deploy guard (docs/deploy.md): ask the owner first"
        self.write("proj/s1.jsonl", [command("demo:build")] + [use(f"r{n}", "Read", {"file_path": "a.md"}) for n in range(3)])
        other = self.tmp / "other"
        other.mkdir()
        self.write("proj/s2.jsonl", [use("b1", "Bash", {"command": "deploy"}), done("b1", refusal, True),
                                     use("b2", "Bash", {"command": "deploy -f"}), done("b2", refusal, True)], cwd=other)
        self.run_cmd("scan", "--force")
        demo = self.new_lines("demo")
        self.assertTrue(any("| repeated call | Read x3" in text and "| part: skill demo:build | sets: demo, global, repo"
                            in text for text in demo), demo)
        self.assertTrue(any("| hook refusal | PreToolUse:Bash x2: Deploy guard" in text for text in demo), demo)
        self.assertFalse(any("repeated call" in text for text in self.new_lines("repo")))

    # protects: Flow
    def test_a_talk_breach_in_a_reply_to_the_owner_goes_to_the_global_set_with_its_rule_line_and_a_managers_brief_does_not(self):
        self.write("proj/s1.jsonl", [owner("Як справи?"), said("Готово — все зелене.")])
        self.write("proj/s2.jsonl", [line("custom-title", customTitle="M: Build"), owner("Brief: build."),
                                     said("Built — done.")])
        for name, title in (("s3", "C: Old build"), ("s4", "Discuss: Topic"), ("s5", "Обговорення: Topic")):
            # Edge: the old «C:» and «Обговорення:» titles are briefed by the lead too, like «M:» and «Discuss:»
            self.write(f"proj/{name}.jsonl", [line("custom-title", customTitle=title), owner("Brief: build."),
                                              said("Built — done.")])
        self.write("proj/s1/subagents/agent-a1.jsonl", [owner("Do it."), said("Done — ok.")])
        self.run_cmd("scan", "--force")
        talk_lines = [text for text in self.new_lines("global") if "| talk " in text]
        self.assertEqual(len(talk_lines), 1, talk_lines)
        self.assertIn("| s1 | talk dash | global: CLAUDE.md:16 (No em dash): x1; L2:", talk_lines[0])

    # protects: Bug
    def test_line_numbers_go_on_across_scans_of_one_growing_transcript(self):
        self.write("proj/s1.jsonl", [said("a"), said("b")])
        self.run_cmd("scan", "--force")
        self.write("proj/s1.jsonl", [owner("Як?"), said("Добре — так.")], mode="a")
        self.run_cmd("scan", "--force")
        self.assertTrue(any("L4:" in text for text in self.new_lines("global") if "talk dash" in text))

    # protects: Flow
    def test_parts_writes_a_packet_per_part_with_a_sign_and_add_with_the_packet_records_a_sign_gap(self):
        self.write("proj/abcdef12-0000.jsonl", [
            command("demo:lead"), owner("я ж казав не так"), said("Виправляю.")])
        out = self.run_cmd("parts", "--since", "2000-01-01")
        packet = out.splitlines()[0].split(" | ")[0]
        self.assertIn("skill demo:lead lines 1-3 | signs: owner correction | sets: demo, global, repo", out)
        self.assertIn("parts: session 1, skill 1; packets: 1", out)
        added = self.run_cmd("add", "--set", "global", "--text", "part reader: CLAUDE.md:5 | asked twice", "--packet", packet)
        self.assertIn("sign gap recorded for global", added)
        self.assertTrue(any("| sign-gap | global: the part skill demo:lead" in text for text in self.new_lines("global")))


if __name__ == "__main__":
    unittest.main()
