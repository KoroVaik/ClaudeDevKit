import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "plugins" / "dev-kit"
SCRIPT = PLUGIN / "hooks" / "lead-reply-form.py"

PEER = {"type": "user", "isMeta": True, "turnOrigin": "peer",
        "origin": {"kind": "peer", "name": "M: Пошук"},
        "message": {"role": "user", "content": "Another Claude session sent a message:\nГОТОВО - ..."}}
OWNER = {"type": "user", "turnOrigin": "human", "origin": {"kind": "human"},
         "message": {"role": "user", "content": "Так"}}
TASK = {"type": "user", "turnOrigin": "task_notification", "origin": {"kind": "task-notification"},
        "message": {"role": "user", "content": "<task-notification>..."}}
TIMER = {"type": "user", "isMeta": True, "turnOrigin": "scheduled",
         "message": {"role": "user", "content": "Reminder for the owner: ..."}}

STATUS = """**Питання без відповіді**

- від сесій: 2
- від мене: 1

**Статуси сесій**

- чекає на тебе - «M: Нова сторінка налаштувань» (вибір кольору кнопки)
- ще працюють: «M: Пошук у журналі», «M: Нові іконки»

Показати всі питання?"""

CRITICAL = """**Статуси сесій**

- чекає на тебе - «M: Тести хуків» (дозвіл на запис у main)

**Питання без відповіді**

- ❗ термінові: 1
- від сесій: 2

«M: Тести хуків» питає: дозволити запис у main? (інакше тести стоять)
Рекомендую: так - запис лише у тестову гілку."""

PROJECT_STATE = """**Статуси сесій**

- готово - «M: Відкриті пункти каталогу продуктів»

**Стан проєкту**

Каталог продуктів закінчено: пошук і фільтри працюють. Далі за планом - кошик.

Запустити нову сесію «M: Кошик»? (з'явиться кошик у застосунку)
   Рекомендую: так - від тебе нічого не треба."""

FULL_LIST = """**Статуси сесій**

- ще працюють: «M: Нові іконки»

**Питання сесій**

1. ❗ «M: Тести хуків» питає: дозволити запис у main? (інакше тести стоять)
   Рекомендую: так - запис лише у тестову гілку.

**Питання від мене**

2. Запустити нову сесію «M: Меню налаштувань»? (з'явиться екран налаштувань)
   Рекомендую: так - від тебе нічого не треба.
ще 2 питання

Приймаєш усі мої рекомендації?"""

EXCEPTIONS = [
    "",
    "Зараз нічого не працює і нічого не чекає на тебе.",
    "Відкрий сесію «Discuss: Нова тема» і говори там.",
    "Відкрий сесію «Обговорення: Нова тема» і говори там.",  # Edge: the old title, a lead that has not restarted yet
    "Тест пушу: напиши + і одразу закрий застосунок. Через 5 секунд прийде пуш «Тест 3 · 21:40».",
    "Пуш «Тест 3» надіслано. Прийшов? + або -",
    "⚠ ЧЕРЕЗ 30 СЕК БУДЕ ПЕРЕЗАВАНТАЖЕННЯ (СВІЖИЙ КОНТЕКСТ)",
    "⚠ ЧЕРЕЗ 30 СЕК БУДЕ ПЕРЕЗАВАНТАЖЕННЯ (ОНОВЛЕННЯ ІНСТРУМЕНТІВ)",
    STATUS, CRITICAL, PROJECT_STATE, FULL_LIST,
    CRITICAL.split("\n\n«M:")[0] + "\n\nГлянь у сповіщення Claude на телефоні: є пуш о 17:27? + або -",
]

BAD = [
    "Прийняв. Чекаю на відповідь сесії.",
    "Прийняв.\n\n" + STATUS,
    STATUS + "\n\nПеревірю ще раз за 10 хвилин.",
    STATUS.replace("Показати всі питання?", "Сесія «M: Пошук» застрягла, я її перезапущу.\n\nПоказати всі питання?")
    .replace("\n\nПоказати", "\n\nЩе одна примітка.\n\nПоказати"),
    """**Питання без відповіді**

- від сесій: 2

Злиття не вдалося через конфлікт, розберу сам.

**Статуси сесій**

- ще працюють: «M: Нові іконки»""",
]


def assistant(text, msg_id="m1"):
    return {"type": "assistant", "message": {"id": msg_id, "role": "assistant", "stop_reason": "end_turn",
                                             "content": [{"type": "text", "text": text}]}}


class LeadReplyFormTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def test_reply_to_a_waiting_owner_question_is_not_checked(self):
        """The owner asked, the Lead waited on a subagent with no reply yet: the subagent's turn answers the owner."""
        self.assertIsNone(self.run_hook("L: Zhratva", TASK, "### Чому картка зверху\n\nТак задумано.", answered=False))
        self.assertIsNotNone(self.run_hook("L: Zhratva", TASK, "### Чому картка зверху\n\nТак задумано."))

    def run_hook(self, title, trigger, text, active=False, raw=None, answered=True):
        path = self.tmp / "t.jsonl"
        earlier = assistant("old", "m0") if answered else {"type": "assistant", "message": {
            "id": "m0", "role": "assistant", "stop_reason": "end_turn", "content": [{"type": "thinking"}]}}
        entries = [{"type": "custom-title", "customTitle": title}, OWNER, earlier, trigger,
                   {"type": "assistant", "message": {"id": "m1", "role": "assistant",
                                                     "content": [{"type": "thinking", "thinking": "x"}]}}]
        if text:
            entries.append(assistant(text))
        path.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in entries), encoding="utf-8")
        call = raw if raw is not None else json.dumps({"session_id": "s", "transcript_path": str(path),
                                                       "stop_hook_active": active, "hook_event_name": "Stop"})
        done = subprocess.run([sys.executable, "-X", "utf8", str(SCRIPT)], input=call.encode("utf-8"),
                              capture_output=True, timeout=30)
        self.assertEqual(done.returncode, 0, done.stderr)
        out = done.stdout.decode("utf-8").strip()
        return json.loads(out) if out else None

    def test_every_named_exception_passes(self):
        for text in EXCEPTIONS:
            for trigger in (PEER, TASK, TIMER):
                with self.subTest(text=text[:40], trigger=trigger["turnOrigin"]):
                    self.assertIsNone(self.run_hook("L: Zhratva", trigger, text))

    def test_free_text_beside_blocks_is_flagged(self):
        for text in BAD:
            with self.subTest(text=text[:40]):
                out = self.run_hook("L: Zhratva", PEER, text)
                self.assertIsNotNone(out)
                self.assertEqual(out["decision"], "block")
                self.assertIn("не надсилай її знову", out["reason"])

    def test_owner_turn_is_not_checked(self):
        self.assertIsNone(self.run_hook("L: Zhratva", OWNER, BAD[0]))

    def test_other_sessions_are_not_checked(self):
        for title in ("M: Пошук", "C: Пошук", "Discuss: Тема", "Обговорення: Тема", ""):
            with self.subTest(title=title):
                self.assertIsNone(self.run_hook(title, PEER, BAD[0]))

    def test_old_lead_title_is_still_checked(self):
        """Edge: a lead that runs under «P: » (not yet restarted as «L: ») keeps its message form checked."""
        out = self.run_hook("P: Zhratva", PEER, BAD[0])
        self.assertIsNotNone(out)
        self.assertEqual(out["decision"], "block")
        self.assertIn("Lead", out["reason"])
        self.assertNotIn("керівник", out["reason"])

    def test_no_second_block_in_a_row(self):
        self.assertIsNone(self.run_hook("L: Zhratva", PEER, BAD[0], active=True))

    def test_broken_input_never_blocks(self):
        self.assertIsNone(self.run_hook("L: Zhratva", PEER, BAD[0], raw="not json"))
        self.assertIsNone(self.run_hook("L: Zhratva", PEER, BAD[0],
                                        raw=json.dumps({"transcript_path": str(self.tmp / "missing.jsonl")})))


if __name__ == "__main__":
    unittest.main()
