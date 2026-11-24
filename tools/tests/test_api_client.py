import datetime
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "plugins" / "spend-kit" / "scripts"))
import api_client  # noqa: E402

PRICES = api_client.load_prices()
UTC = datetime.timezone.utc


class FakeResponse:
    def __init__(self, body):
        self.body = json.dumps(body).encode("utf-8")

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def response(model="claude-sonnet-5-5", usage=None, stop="end_turn"):
    return {
        "id": "msg_1", "model": model, "stop_reason": stop,
        "content": [{"type": "text", "text": "hi"}],
        "usage": usage or {"input_tokens": 1000, "output_tokens": 500},
    }


class LogTestCase(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.log = self.dir / "sub" / "api-calls.jsonl"
        patcher = mock.patch.dict(os.environ, {"DEV_KIT_API_LOG": str(self.log), "DEV_KIT_API_KEY": "k"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def lines(self):
        return [json.loads(x) for x in self.log.read_text(encoding="utf-8").splitlines()]


class CostTest(unittest.TestCase):
    def line(self, **kw):
        base = {"model": "claude-sonnet-5-5", "batch": False, "input": 0, "output": 0,
                "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0}
        base.update(kw)
        return base

    def test_plain_tokens(self):
        # 1M input at $2 + 1M output at $10
        self.assertAlmostEqual(api_client.cost_usd(self.line(input=10**6, output=10**6), PRICES), 12.0)

    def test_cache_writes_and_reads(self):
        line = self.line(cache_write_5m=10**6, cache_write_1h=10**6, cache_read=10**6)
        # 1.25 * 2 + 2.0 * 2 + 0.10
        self.assertAlmostEqual(api_client.cost_usd(line, PRICES), 6.6)

    def test_batch_is_half(self):
        self.assertAlmostEqual(api_client.cost_usd(self.line(input=10**6, batch=True), PRICES), 1.0)

    def test_haiku_long_prompt_prices(self):
        short = self.line(model="claude-haiku-5-5", input=100000, output=10**6)
        long = self.line(model="claude-haiku-5-5", input=100001, output=10**6)
        self.assertAlmostEqual(api_client.cost_usd(short, PRICES), 0.01 + 0.5)
        self.assertAlmostEqual(api_client.cost_usd(long, PRICES), round(100001 * 0.5 / 10**6 + 2.5, 6))

    def test_unknown_model_has_no_cost(self):
        self.assertIsNone(api_client.cost_usd(self.line(model="claude-new-9"), PRICES))


class UsageMapTest(unittest.TestCase):
    def test_split_by_ttl(self):
        usage = {"input_tokens": 5, "output_tokens": 6, "cache_read_input_tokens": 7,
                 "cache_creation_input_tokens": 30,
                 "cache_creation": {"ephemeral_5m_input_tokens": 10, "ephemeral_1h_input_tokens": 20}}
        self.assertEqual(api_client.tokens_from_usage(usage), {
            "input": 5, "output": 6, "cache_write_5m": 10, "cache_write_1h": 20, "cache_read": 7})

    def test_no_split_counts_as_5m(self):
        t = api_client.tokens_from_usage({"input_tokens": 1, "cache_creation_input_tokens": 9})
        self.assertEqual((t["cache_write_5m"], t["cache_write_1h"], t["output"]), (9, 0, 0))


class CallTest(LogTestCase):
    def test_call_writes_one_line_with_cost(self):
        sent = []

        def opener(request, timeout):
            sent.append(request)
            return FakeResponse(response())

        result = api_client.call({"model": "claude-sonnet-5-5", "max_tokens": 10, "messages": []},
                                 "Proj", "Proj key", opener=opener)
        self.assertEqual(result["id"], "msg_1")
        self.assertEqual(sent[0].get_header("X-api-key"), "k")
        [line] = self.lines()
        self.assertEqual((line["project"], line["key"], line["model"], line["batch"]),
                         ("Proj", "Proj key", "claude-sonnet-5-5", False))
        self.assertAlmostEqual(line["cost_usd"], (1000 * 2 + 500 * 10) / 10**6)
        self.assertEqual(line["request_id"], "msg_1")
        api_client.parse_ts(line["ts"])

    def test_retry_then_success_writes_one_line(self):
        calls = []

        def opener(request, timeout):
            calls.append(1)
            if len(calls) == 1:
                raise urllib.error.HTTPError(request.full_url, 529, "overloaded", {}, io.BytesIO(b"{}"))
            return FakeResponse(response())

        api_client.call({"model": "m", "messages": []}, "P", "K", opener=opener, sleep=lambda s: None)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(self.lines()), 1)

    def test_bad_request_writes_nothing(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(request.full_url, 400, "bad", {}, io.BytesIO(b"{\"error\":1}"))

        with self.assertRaises(api_client.ApiError):
            api_client.call({"model": "m", "messages": []}, "P", "K", opener=opener)
        self.assertFalse(self.log.exists())

    def test_key_name_required(self):
        with self.assertRaises(api_client.UsageError):
            api_client.call({"model": "m"}, "P", "", opener=lambda r, timeout: FakeResponse(response()))

    def test_refusal_exit_3_and_line_written(self):
        with mock.patch.object(api_client, "post", return_value=response(stop="refusal")), \
                redirect_stderr(io.StringIO()):
            code = api_client.main(["call", "--model", "claude-sonnet-5-5", "--key-name", "K", "--project", "P",
                                    "--prompt", "x"], out=io.StringIO())
        self.assertEqual(code, 3)
        self.assertEqual(len(self.lines()), 1)

    def test_cli_prints_text(self):
        out = io.StringIO()
        with mock.patch.object(api_client, "post", return_value=response()):
            code = api_client.main(["call", "--model", "claude-sonnet-5-5", "--key-name", "K", "--project", "P",
                                    "--prompt", "x"], out=out)
        self.assertEqual((code, out.getvalue().strip()), (0, "hi"))


class ReportTest(LogTestCase):
    def write(self, key, model, inp, days_ago, batch=False, cost=None):
        ts = datetime.datetime.now(UTC) - datetime.timedelta(days=days_ago)
        line = api_client.make_line("P", key, model, {"input_tokens": inp}, batch=batch, prices=PRICES, ts=ts)
        line["cost_usd"] = cost  # a writer that computes no dollars; report computes it from tokens
        api_client.append_line(line)

    def test_report_sums_per_key_in_window(self):
        self.write("A", "claude-sonnet-5-5", 10**6, 1)
        self.write("A", "claude-sonnet-5-5", 10**6, 40)  # outside 30 days
        self.write("B", "claude-opus-5-5", 10**6, 2, batch=True)
        self.write("B", "claude-new-9", 10**6, 2)
        with open(self.log, "a", encoding="utf-8") as f:
            f.write("not json\n")
        out = io.StringIO()
        self.assertEqual(api_client.main(["report"], out=out), 0)
        text = out.getvalue()
        self.assertRegex(text, r"A\s+2\.00 USD  1 calls")
        self.assertRegex(text, r"B\s+2\.00 USD  2 calls")
        self.assertIn("no price for model claude-new-9: 1 lines", text)
        self.assertIn("1 broken lines skipped", text)

    def test_reconcile(self):
        self.write("A", "claude-sonnet-5-5", 10**6, 1)  # $2.00
        self.write("C", "claude-sonnet-5-5", 10**6, 1)  # $2.00, not in Console
        out = io.StringIO()
        code = api_client.main(["reconcile", "--console", "A=$2.30", "--console", "Zhratva test=5"], out=out)
        text = out.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("A: Console $2.30, log $2.00: ok", text)
        self.assertIn("C: Console -, log $2.00: not in Console", text)
        self.assertIn("Zhratva test: Console $5.00, log -: not logged", text)
        self.assertIn("line: reconciled 30d Console/log:", text)

    def test_reconcile_gap(self):
        rows, gap = api_client.reconcile({"A": 10.0}, {"A": 8.0})
        self.assertEqual((rows[0][3], gap), ("gap", True))
        rows, gap = api_client.reconcile({"A": 10.0}, {"A": 9.1})
        self.assertEqual((rows[0][3], gap), ("ok", False))

    def test_bad_console_arg(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(api_client.main(["reconcile", "--console", "A"], out=io.StringIO()), 2)


class RobustnessTest(LogTestCase):
    def test_bad_since_is_usage_error(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(api_client.main(["report", "--since", "2026/11/01"], out=io.StringIO()), 2)

    def test_stream_refused(self):
        with self.assertRaises(api_client.UsageError):
            api_client.call({"model": "m", "stream": True}, "P", "K", opener=lambda r, timeout: None)

    def test_non_json_answer_is_api_error(self):
        class Raw(FakeResponse):
            def __init__(self):
                self.body = b"event: message_start"

        with self.assertRaises(api_client.ApiError):
            api_client.call({"model": "m"}, "P", "K", opener=lambda r, timeout: Raw())

    def test_retry_after_not_a_number(self):
        self.assertEqual(api_client.retry_delay("soon", 1), 2.0)
        self.assertEqual(api_client.retry_delay("3", 0), 3.0)

    def test_ts_with_fraction_and_offset(self):
        a = api_client.parse_ts("2026-11-21T14:03:05.1234567Z"[:26] + "Z")
        b = api_client.parse_ts("2026-11-21T16:03:05+02:00")
        self.assertEqual((a.hour, b.hour), (14, 14))
        with self.assertRaises(ValueError):
            api_client.parse_ts("2026-11-21T14:03:05")


class ProjectNameTest(unittest.TestCase):
    def test_worktree_gives_main_repo_name(self):
        here = Path(__file__).resolve().parent
        name = api_client.default_project(here)
        self.assertNotEqual(name, "tests")
        self.assertNotEqual(name, ".git")


if __name__ == "__main__":
    unittest.main()
