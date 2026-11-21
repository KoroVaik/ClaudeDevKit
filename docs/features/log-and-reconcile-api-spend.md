# Log and reconcile API spend

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
Every paid Claude API call, from any project, leaves one line in one local log, so the owner knows what each
project and key spent without opening the Console, and the weekly Console check finds spend the log missed.

## Rules
### One log, one line per call
The log is one file, `api-calls.jsonl` in the dev-kit folder of the user's `.claude` folder, next to the weekly
credit-check log `credits.md` (env `DEV_KIT_API_LOG` points elsewhere, for tests or a container). Each call
appends one JSON object on one line, UTF-8 without BOM, ending in `\n`, written by one append of the whole
line; the file is never rewritten. A Message Batches run writes one line per succeeded request.

```json
{"v": 1, "ts": "2026-11-21T14:03:05Z", "project": "Zhratva", "key": "Zhratva test", "model": "claude-sonnet-5-5", "batch": false, "input": 1234, "output": 567, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0, "cost_usd": null, "source": "AiProviderClient", "request_id": "msg_01..."}
```

| Field | Value |
|---|---|
| `v` | 1 (the format version) |
| `ts` | UTC time, `YYYY-MM-DDTHH:MM:SSZ` (readers also take fractional seconds or an offset, never a time with no zone); for a batch, when its results were collected |
| `project` | the repository name (`Zhratva`, `ClaudeDevKit`) |
| `key` | the API key's name as the Console shows it (Settings, API keys); the weekly check reconciles by it |
| `model` | the response's `model` field (the model that ran) |
| `batch` | true for a Message Batches result |
| `input`, `output` | `usage.input_tokens`, `usage.output_tokens` |
| `cache_write_5m`, `cache_write_1h` | `usage.cache_creation.ephemeral_5m_input_tokens` / `ephemeral_1h_input_tokens`; with no breakdown, all of `usage.cache_creation_input_tokens` goes to 5m |
| `cache_read` | `usage.cache_read_input_tokens` |
| `cost_usd` | dollars from the shared price table, or `null` when the writer computes none |
| `source` | optional: the program or command that called |
| `request_id` | optional: the message id or the batch request's custom id |

A missing token field counts as 0. Readers skip a line that is not valid JSON or has no valid `ts`, and say how many they skipped.

### Agents call the API only through the client
An agent calls the API only with `dev-kit-api call`, which sends the request, writes the line and prints the
answer (rule: `dev-kit:manager`, "Claude API calls"). A project's own program that calls the API from its single
call point appends the same line itself instead of switching to the client.

### Cost from one price table
The API returns tokens, not dollars. `plugins/dev-kit/api-prices.json` holds the USD per million tokens of each
model; cache writes cost 1.25 (5 minutes) or 2 (1 hour) times the input price, cache reads the model's own
price, a batch half of all that, and a model's long-prompt prices apply above its threshold. `dev-kit-api report`
and `reconcile` compute every line's cost from this table, so a line with `cost_usd: null` still counts; a
model missing from the table is named, never counted silently as free.

### Each project its own key
Each project calls with its own API key, named in the Console, and the line carries that name, so spend is
known per key and per project. The client reads the key from env `DEV_KIT_API_KEY`, never `ANTHROPIC_API_KEY`: a headless `claude -p` bills that one with no line.

### The weekly check reconciles per key
The project lead of the plugin repo reads the Console's spend per key for 30 days once a week and runs
`dev-kit-api reconcile`; a key whose Console sum and log sum differ by more than 0.50 USD and 10%, a key with
spend and no lines, or lines under a key the Console does not list, is named to the owner as spend the log
missed (rule: `dev-kit:project-lead`, "API credit check").

## Acceptance criteria
- `dev-kit-api call` gets an answer: the log gains one line with the project, the key name, the model, the tokens and the cost.
- A call that fails with a 400 writes no line; a 529 is retried and writes one line.
- A line with `cost_usd: null` from another program is counted in `dev-kit-api report` at its table price.
- `dev-kit-api reconcile --console "Zhratva test=5"` with no Zhratva lines marks the key `not logged` and exits 1.
- A model missing from the price table is named by `report` and `reconcile`.

## Built in
- `plugins/dev-kit/bin/dev-kit-api`
- `plugins/dev-kit/scripts/api_client.py`
- `plugins/dev-kit/api-prices.json`
- `plugins/dev-kit/skills/manager/SKILL.md`
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `tools/tests/test_api_client.py`
