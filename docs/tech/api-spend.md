# API spend

Code: `plugins/spend-kit/scripts/api_client.py` (command `spend-kit-api`), `plugins/spend-kit/api-prices.json`.
The rules the user sees: [Log and reconcile API spend](../features/log-and-reconcile-api-spend.md).

## The log

One file, `~/.claude/dev-kit/api-calls.jsonl` (next to the weekly credit-check log `credits.md`), or the
path in env `DEV_KIT_API_LOG`. One JSON object per line, UTF-8 without BOM, `\n` at the end, appended (never
rewritten) by one write of the whole line.

## The spend line

The format and every field: the module docstring of `plugins/spend-kit/scripts/api_client.py` (its one home: the
docstring ships with the installed plugin, so agents in other projects can read it).

A missing token field counts as 0. Readers skip a line that is not valid JSON or has no valid `ts`, and say how
many they skipped. Other programs that call the API from their own single call point (Zhratva's
`AiProviderClient`, `tools/ai-api`) append the same line themselves.

## Cost

The API returns tokens, not dollars. `plugins/spend-kit/api-prices.json` holds the USD per million tokens of each
model; the cost rule is in the same docstring. `spend-kit-api prices` prints the table.

The table comes from the claude-api skill's model table (cached 2026-11-03). Haiku 5.5's cache read price
(0.1 times its input price) is assumed: the model table does not list it. Not priced: fast mode (Opus 5.5
`speed: fast`, 2 times) and server tools (web search fees); nobody uses them now. The client sends the API
version `2026-10-21`, retries on 408, 409, 429 and 5xx, takes the key from env `DEV_KIT_API_KEY` and the key's
Console name from `--key-name` or env `DEV_KIT_API_KEY_NAME`; the project name defaults to the repository folder
(the main repository for a worktree).

## What writes a line

`spend-kit-api call` writes one line per response that carries `usage` (a refusal included) and only for the
Messages API: it has no Message Batches call. A line with `batch: true` comes from another program that
appends it itself; `report` and `reconcile` price it at the batch rate.
