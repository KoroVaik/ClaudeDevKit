"""The shared Claude API client: call the Messages API, write one spend line per call, report and reconcile spend.

    spend-kit-api call --model <id> --key-name <console key name> [--project <name>] [--max-tokens N] [--effort L]
                       [--system TEXT] [--prompt TEXT | --prompt-file FILE | --request FILE] [--json]
    spend-kit-api report [--days N | --since YYYY-MM-DD] [--by key|project|model|day]
    spend-kit-api reconcile [--days N] --console "<key name>=<USD>" [--console ...]
    spend-kit-api prices

Agents call the Claude API only through this client (rule: `dev-kit:manager`, "Claude API calls"), so every paid
call leaves a line in one local log. Other programs that call the API from their own single call point (Zhratva's
AiProviderClient and tools/ai-api) append the same line themselves; the format is below (the one home of the format and the cost rule;
`docs/tech/api-spend.md` of the plugin repo links here). `call` uses only the Messages API: it writes no line for
Message Batches.

The log: one file, `~/.claude/spend-kit/api-calls.jsonl` (next to the weekly credit-check log `credits.md`), or the
path in env `DEV_KIT_API_LOG`. Both files used to live in `~/.claude/dev-kit/`: the first run copies them to the new
folder once. Programs of other projects still append to the OLD path `~/.claude/dev-kit/api-calls.jsonl` (they name
it in their own code), so `report` and `reconcile` read both files and count a line copied to the new one once; the
old path stays valid for those writers and for no one else (this client writes only the new file; with env
`DEV_KIT_API_LOG` only that file is read). One JSON object per line, UTF-8 without BOM, `\\n` at the end, appended
(never rewritten) by one write of the whole line:

    {"v": 1, "ts": "2026-11-21T14:03:05Z", "project": "Zhratva", "key": "Zhratva test",
     "model": "claude-sonnet-5-5", "batch": false, "input": 1234, "output": 567, "cache_write_5m": 0,
     "cache_write_1h": 0, "cache_read": 0, "cost_usd": 0.008137, "source": "spend-kit-api", "request_id": "msg_..."}

- `ts` UTC time of the call, `YYYY-MM-DDTHH:MM:SSZ` (readers also take fractional seconds or an offset) (for a batch: when its results were collected). `project` the repository name.
  `key` the API key's name as the Console shows it (Settings, API keys), the unit the weekly check reconciles by.
- `model` the `model` field of the response (the model that ran). `batch` true for Message Batches results.
- The token fields come from the response `usage`: `input` = `input_tokens`, `output` = `output_tokens`,
  `cache_read` = `cache_read_input_tokens`, `cache_write_5m` / `cache_write_1h` = `usage.cache_creation`
  `ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens` (when that breakdown is missing, all of
  `cache_creation_input_tokens` counts as 5m). A missing field is 0.
- `cost_usd` the cost from the shared price table `api-prices.json`, or null when the writer computes no dollars;
  `report` and `reconcile` compute every line's cost from the table and its tokens, so a null is fine.
- `source` the caller (program or command), `request_id` the message id or the batch request's custom id; optional.

Cost: tokens times the model's USD per million tokens; cache writes at `cache_write_5m` / `cache_write_1h` times the
input price, cache reads at the model's own `cache_read` price; the long-prompt prices of a model (`long`) apply when
input plus cache tokens exceed `above_prompt_tokens`; a batch line costs `batch` times that. A model missing from the
table has no cost: `report` counts its lines apart and names it.

Exit codes: 0 ok, 1 the API refused or failed, or reconcile found a gap, 2 usage error, 3 the model refused
(`stop_reason` refusal; the line is still written).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the launcher runs this file with runpy, which adds nothing
import spend_dir  # noqa: E402  the data folder and the one-time move from dev-kit

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2026-10-21"
PRICES = Path(__file__).resolve().parent.parent / "api-prices.json"
RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
RETRIES = 2
TIMEOUT = 600
KEY_ENV = "DEV_KIT_API_KEY"  # not ANTHROPIC_API_KEY (plugins/dev-kit/claude-facts.md, "A headless `claude -p` bills `ANTHROPIC_API_KEY` if it is set")
TOKEN_FIELDS = ("input", "output", "cache_write_5m", "cache_write_1h", "cache_read")
GAP_USD = 0.5
GAP_SHARE = 0.10


class UsageError(Exception):
    """Bad arguments or environment (exit 2)."""


class ApiError(Exception):
    """The API call failed (exit 1)."""


def log_path():
    """The log this client writes: env DEV_KIT_API_LOG, else `api-calls.jsonl` in the spend-kit data folder (the old
    files are copied there first, once)."""
    env = os.environ.get("DEV_KIT_API_LOG")
    if env:
        return Path(env)
    spend_dir.migrate_api_files()
    return spend_dir.data_dir() / spend_dir.API_LOG


def old_log_path():
    """The old log that other projects' programs still append to, read besides the new one; None when env
    DEV_KIT_API_LOG names the only file or there is no old folder."""
    return None if os.environ.get("DEV_KIT_API_LOG") else spend_dir.old_api_log()


def load_prices(path=PRICES):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def tokens_from_usage(usage):
    """Map a response `usage` object to the line's token fields."""
    usage = usage or {}
    created = usage.get("cache_creation_input_tokens") or 0
    split = usage.get("cache_creation") or {}
    write_1h = split.get("ephemeral_1h_input_tokens") or 0
    write_5m = split.get("ephemeral_5m_input_tokens")
    if write_5m is None:
        write_5m = max(created - write_1h, 0)
    return {
        "input": usage.get("input_tokens") or 0,
        "output": usage.get("output_tokens") or 0,
        "cache_write_5m": write_5m,
        "cache_write_1h": write_1h,
        "cache_read": usage.get("cache_read_input_tokens") or 0,
    }


def cost_usd(line, prices):
    """The line's cost from the price table, or None when its model has no price."""
    model = prices["models"].get(line.get("model"))
    if model is None:
        return None
    t = {k: int(line.get(k) or 0) for k in TOKEN_FIELDS}
    rates = model
    long_rates = model.get("long")
    prompt = t["input"] + t["cache_write_5m"] + t["cache_write_1h"] + t["cache_read"]
    if long_rates and prompt > long_rates["above_prompt_tokens"]:
        rates = long_rates
    usd = (
        t["input"] * rates["input"]
        + t["output"] * rates["output"]
        + t["cache_write_5m"] * rates["input"] * prices["cache_write_5m"]
        + t["cache_write_1h"] * rates["input"] * prices["cache_write_1h"]
        + t["cache_read"] * rates["cache_read"]
    ) / 1_000_000
    if line.get("batch"):
        usd *= prices["batch"]
    return round(usd, 6)


def make_line(project, key, model, usage, batch=False, source=None, request_id=None, prices=None, ts=None):
    line = {
        "v": 1,
        "ts": (ts or now_utc()).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": project,
        "key": key,
        "model": model,
        "batch": bool(batch),
        **tokens_from_usage(usage),
    }
    line["cost_usd"] = cost_usd(line, prices or load_prices())
    if source:
        line["source"] = source
    if request_id:
        line["request_id"] = request_id
    return line


def append_line(line, path=None):
    """Append one line to the log by a single write; the folder is created when missing."""
    path = Path(path) if path else log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(line, ensure_ascii=False, separators=(", ", ": ")) + "\n").encode("utf-8")
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o644)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def read_lines(path=None):
    """The log's lines as dicts; a broken line is skipped and counted."""
    path = Path(path) if path else log_path()
    lines, broken = [], 0
    if not path.exists():
        return lines, broken
    with open(path, encoding="utf-8-sig") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                item = json.loads(raw)
                parse_ts(item["ts"])
            except (ValueError, KeyError, TypeError):
                broken += 1
                continue
            lines.append(item)
    return lines, broken


def read_all_lines():
    """The lines of the log and of the old log (see `old_log_path`) and the broken count. A line copied to the new log
    is in both files: each line of the old file that has a twin in the new one (the same content, once per twin)
    is not counted again."""
    lines, broken = read_lines(log_path())
    old = old_log_path()
    if old is None or not old.exists():
        return lines, broken
    twins = Counter(json.dumps(item, sort_keys=True) for item in lines)
    old_lines, old_broken = read_lines(old)
    for item in old_lines:
        key = json.dumps(item, sort_keys=True)
        if twins[key] > 0:
            twins[key] -= 1
        else:
            lines.append(item)
    return lines, max(broken, old_broken)  # a broken line copied over is in both counts


def parse_ts(text):
    """An ISO 8601 time with `Z` or an offset (fractional seconds allowed), as UTC; a time with no zone is refused."""
    value = datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError(f"no time zone in {text!r}")
    return value.astimezone(datetime.timezone.utc)


def default_project(cwd=None):
    """The repository name: the folder holding the git common dir (a worktree gives its main repo), else cwd's name."""
    cwd = Path(cwd or os.getcwd())
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=cwd, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(out).parent.name
    except (OSError, subprocess.CalledProcessError):
        return cwd.name


def retry_delay(header, attempt):
    try:
        return max(float(header), 0.0)
    except (TypeError, ValueError):
        return float(2 ** attempt)


def post(body, api_key, opener=urllib.request.urlopen, sleep=time.sleep):
    """POST the body to the Messages API with retries on 408/409/429/5xx and network errors."""
    data = json.dumps(body).encode("utf-8")
    headers = {"content-type": "application/json", "x-api-key": api_key, "anthropic-version": API_VERSION}
    for attempt in range(RETRIES + 1):
        request = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
        try:
            with opener(request, timeout=TIMEOUT) as response:
                raw = response.read()
            try:
                return json.loads(raw.decode("utf-8"))
            except ValueError:
                raise ApiError(f"the answer is not JSON (no spend line written): {raw[:200]!r}")
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            if e.code in RETRY_STATUS and attempt < RETRIES and e.headers.get("x-should-retry") != "false":
                sleep(retry_delay(e.headers.get("retry-after"), attempt))
                continue
            raise ApiError(f"HTTP {e.code}: {text[:500]}")
        except (urllib.error.URLError, OSError) as e:
            if attempt < RETRIES:
                sleep(2 ** attempt)
                continue
            raise ApiError(f"network error: {getattr(e, 'reason', e)}")
    raise ApiError("no response")


def call(body, project, key_name, api_key=None, opener=urllib.request.urlopen, sleep=time.sleep, log=None):
    """Call the Messages API with the request body and write the spend line; returns the response dict.

    The line is written for every response that carries `usage` (a refusal included); a failed log write is told
    on stderr and does not lose the response, since the money is already spent."""
    if not key_name:
        raise UsageError("the API key's Console name is required (--key-name or env DEV_KIT_API_KEY_NAME)")
    if body.get("stream"):
        raise UsageError("streaming is not supported; leave out \"stream\"")
    api_key = api_key or os.environ.get(KEY_ENV)
    if not api_key:
        raise UsageError(f"env {KEY_ENV} is not set")
    response = post(body, api_key, opener=opener, sleep=sleep)
    if "usage" in response:
        line = make_line(project, key_name, response.get("model") or body.get("model"), response["usage"],
                         source="spend-kit-api", request_id=response.get("id"))
        try:
            append_line(line, log)
        except OSError as e:
            print(f"spend-kit-api: spend line not written ({e}); line: {json.dumps(line)}", file=sys.stderr)
    return response


def window(days=None, since=None, today=None):
    """The [start, end) of a report window in UTC."""
    end = now_utc() if today is None else today
    if since:
        try:
            start = datetime.datetime.strptime(since, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            raise UsageError(f"--since needs YYYY-MM-DD, got {since!r}")
    else:
        start = end - datetime.timedelta(days=days if days is not None else 30)
    return start, end


def summarize(lines, prices, start, end, by="key"):
    """Sums per group over the window: {group: [usd, calls]}, plus the models with no price and their line count."""
    groups = defaultdict(lambda: [0.0, 0])
    unpriced = defaultdict(int)
    for line in lines:
        ts = parse_ts(line["ts"])
        if not start <= ts < end:
            continue
        usd = cost_usd(line, prices)
        if usd is None:
            unpriced[line.get("model")] += 1
            usd = 0.0
        name = ts.strftime("%Y-%m-%d") if by == "day" else str(line.get(by) or "?")
        groups[name][0] += usd
        groups[name][1] += 1
    return dict(groups), dict(unpriced)


def cmd_report(args, out):
    prices = load_prices()
    lines, broken = read_all_lines()
    start, end = window(args.days, args.since)
    groups, unpriced = summarize(lines, prices, start, end, args.by)
    old = old_log_path()
    also = f" and the old log {old}" if old is not None and old.exists() else ""
    print(f"API spend from the log {log_path()}{also}, {start:%Y-%m-%d}..{end:%Y-%m-%d} by {args.by}, "
          f"prices as of {prices['as_of']}", file=out)
    width = max([len(k) for k in groups] + [5])
    for name in sorted(groups):
        usd, calls = groups[name]
        print(f"  {name:<{width}}  {usd:9.2f} USD  {calls} calls", file=out)
    total = sum(g[0] for g in groups.values())
    print(f"  {'total':<{width}}  {total:9.2f} USD  {sum(g[1] for g in groups.values())} calls", file=out)
    for model, count in sorted(unpriced.items(), key=lambda x: str(x[0])):
        print(f"  no price for model {model}: {count} lines counted as 0 (add it to api-prices.json)", file=out)
    if broken:
        print(f"  {broken} broken lines skipped", file=out)
    return 0


def parse_console(items):
    result = {}
    for item in items or []:
        name, sep, usd = item.rpartition("=")
        if not sep or not name.strip():
            raise UsageError(f"--console needs '<key name>=<USD>', got {item!r}")
        try:
            result[name.strip()] = float(usd.strip().lstrip("$"))
        except ValueError:
            raise UsageError(f"--console amount is not a number: {item!r}")
    return result


def reconcile(console, logged, unpriced=None):
    """Rows (key, console, log, verdict) and whether any key has a gap."""
    rows, gap = [], False
    for key in sorted(set(console) | set(logged)):
        c, lg = console.get(key), logged.get(key)
        if c is None:
            verdict = "not in Console" if lg >= 0.005 else "ok"
        elif lg is None:
            verdict = "not logged" if c >= 0.005 else "ok"
        else:
            verdict = "ok" if abs(c - lg) <= max(GAP_USD, GAP_SHARE * c) else "gap"
        if verdict != "ok":
            gap = True
        rows.append((key, c, lg, verdict))
    if unpriced:
        gap = True
    return rows, gap


def cmd_reconcile(args, out):
    console = parse_console(args.console)
    prices = load_prices()
    lines, broken = read_all_lines()
    start, end = window(args.days)
    groups, unpriced = summarize(lines, prices, start, end, "key")
    logged = {k: v[0] for k, v in groups.items()}
    rows, gap = reconcile(console, logged, unpriced)
    print(f"Console against the log, {start:%Y-%m-%d}..{end:%Y-%m-%d}", file=out)
    parts = []
    for key, c, lg, verdict in rows:
        cs = "-" if c is None else f"${c:.2f}"
        ls = "-" if lg is None else f"${lg:.2f}"
        print(f"  {key}: Console {cs}, log {ls}: {verdict}", file=out)
        parts.append(f"{key} {cs}/{ls} {verdict}")
    for model, count in sorted(unpriced.items(), key=lambda x: str(x[0])):
        print(f"  no price for model {model}: {count} lines (add it to api-prices.json)", file=out)
        parts.append(f"no price {model}")
    if broken:
        print(f"  {broken} broken lines skipped", file=out)
    print(f"line: reconciled {args.days}d Console/log: " + ("; ".join(parts) or "no spend"), file=out)
    return 1 if gap else 0


def cmd_prices(args, out):
    prices = load_prices()
    print(f"USD per million tokens, as of {prices['as_of']}; cache writes x{prices['cache_write_5m']} (5m) / "
          f"x{prices['cache_write_1h']} (1h) of input; batch x{prices['batch']}", file=out)
    for name, p in prices["models"].items():
        text = f"  {name}: input {p['input']}, output {p['output']}, cache read {p['cache_read']}"
        if "long" in p:
            lg = p["long"]
            text += (f"; above {lg['above_prompt_tokens']} prompt tokens: input {lg['input']}, output {lg['output']}, "
                     f"cache read {lg['cache_read']}")
        print(text, file=out)
    return 0


def build_body(args):
    if args.request:
        with open(args.request, encoding="utf-8-sig") as f:
            body = json.load(f)
        if args.model:
            body["model"] = args.model
        if "model" not in body:
            raise UsageError("the request has no model (set it in the file or with --model)")
        body.setdefault("max_tokens", args.max_tokens)
        if args.system or args.effort:
            raise UsageError("--system and --effort go inside the --request file")
        return body
    if not args.model:
        raise UsageError("--model is required")
    if args.prompt is not None:
        prompt = args.prompt
    elif args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8-sig")
    else:
        prompt = sys.stdin.read()
    if not prompt.strip():
        raise UsageError("empty prompt (--prompt, --prompt-file or stdin)")
    body = {"model": args.model, "max_tokens": args.max_tokens, "messages": [{"role": "user", "content": prompt}]}
    if args.system:
        body["system"] = args.system
    if args.effort:
        body["output_config"] = {"effort": args.effort}
    return body


def cmd_call(args, out):
    body = build_body(args)
    project = args.project or default_project()
    key_name = args.key_name or os.environ.get("DEV_KIT_API_KEY_NAME")
    response = call(body, project, key_name)
    if args.json:
        print(json.dumps(response, ensure_ascii=False, indent=2), file=out)
    else:
        text = "".join(b.get("text", "") for b in response.get("content", []) if b.get("type") == "text")
        print(text, file=out)
    if response.get("stop_reason") == "refusal":
        print(f"spend-kit-api: the model refused ({response.get('stop_details')})", file=sys.stderr)
        return 3
    if response.get("stop_reason") == "max_tokens":
        print("spend-kit-api: the answer was cut at max_tokens", file=sys.stderr)
    return 0


def parser():
    p = argparse.ArgumentParser(prog="spend-kit-api", description="Shared Claude API client with spend logging.")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("call", help="call the Messages API and write the spend line")
    c.add_argument("--model")
    c.add_argument("--key-name", help="the API key's name in the Console (default: env DEV_KIT_API_KEY_NAME)")
    c.add_argument("--project", help="default: the repository name")
    c.add_argument("--max-tokens", type=int, default=16000)
    c.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"])
    c.add_argument("--system")
    src = c.add_mutually_exclusive_group()
    src.add_argument("--prompt")
    src.add_argument("--prompt-file")
    src.add_argument("--request", help="a JSON file with the whole request body")
    c.add_argument("--json", action="store_true", help="print the whole response")
    r = sub.add_parser("report", help="sum the logged spend")
    r.add_argument("--days", type=int, default=30)
    r.add_argument("--since")
    r.add_argument("--by", choices=["key", "project", "model", "day"], default="key")
    rc = sub.add_parser("reconcile", help="compare the Console's per-key spend with the log")
    rc.add_argument("--days", type=int, default=30)
    rc.add_argument("--console", action="append", help="'<key name>=<USD>' as the Console shows it; repeat per key")
    sub.add_parser("prices", help="print the shared price table")
    return p


def main(argv=None, out=None):
    out = out or sys.stdout
    try:
        args = parser().parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    handlers = {"call": cmd_call, "report": cmd_report, "reconcile": cmd_reconcile, "prices": cmd_prices}
    try:
        return handlers[args.cmd](args, out)
    except UsageError as e:
        print(f"spend-kit-api: {e}", file=sys.stderr)
        return 2
    except ApiError as e:
        print(f"spend-kit-api: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
