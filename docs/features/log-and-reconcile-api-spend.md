# Log and reconcile API spend

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
Every paid Claude API call, from any project, leaves one line in one local log, so the owner knows what each
project and key spent without opening the Console, and the weekly Console check finds spend the log missed.

## Rules
### One log, one line per call
The log is one file, `api-calls.jsonl` in the dev-kit folder of the user's `.claude` folder, next to the weekly
credit-check log `credits.md` (env `DEV_KIT_API_LOG` points elsewhere, for tests or a container). Each call
appends one JSON object on one line, written by one append of the whole line; the file is never rewritten. A
line holds the time, the project, the API key's Console name, the model, the token counts and the cost. The
format and every field: [API spend](../tech/api-spend.md). Readers skip a line that is not valid JSON or has no
valid time, and say how many they skipped.

Known limits: `dev-kit-api call` uses only the Messages API, so it writes no line for Message Batches; a
program that runs Batches from its own call point appends one line per succeeded request itself.

### Agents call the API only through the client
An agent calls the API only with `dev-kit-api call`, which sends the request, writes the line and prints the
answer (rule: `dev-kit:manager`, "Claude API calls"). A project's own program that calls the API from its single
call point appends the same line itself instead of switching to the client; a failed write is a warning and
never fails the call, since the money is spent. Deny rules on the API host back the rule where the owner added them.
Why: owner, 2026-11-21: the API credit was spent unseen on the keys of one project; every call is to be logged
and reconciled weekly. The shared part is the line format and the one file, not a code library, so a project
keeps its own client where it has one.

Known limits: a project's worker that is not running (Zhratva's home Docker worker, stopped for two weeks on
2026-11-21) is not joined to the log yet; it keeps its per-call records in its own database until it runs again.

### Cost from one price table
The API returns tokens, not dollars. `plugins/dev-kit/api-prices.json` holds the USD per million tokens of each
model, and `dev-kit-api report` and `reconcile` compute every line's cost from this table, so a line with
`cost_usd: null` still counts; a model missing from the table is named, never counted silently as free. How a
line is priced (cache, batch and long-prompt rates): [API spend](../tech/api-spend.md).

### Each project its own key
Each project calls with its own API key, named in the Console, and the line carries that name, so spend is
known per key and per project. The client reads the key from env `DEV_KIT_API_KEY`, never `ANTHROPIC_API_KEY` ([Claude facts](../../plugins/dev-kit/claude-facts.md), "A headless `claude -p` bills `ANTHROPIC_API_KEY` if it is set").

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
- `docs/tech/api-spend.md`
- `plugins/dev-kit/skills/manager/SKILL.md`
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `tools/tests/test_api_client.py`

## Open
- [ ] Zhratva appends one line per paid call from its own call points (`AiProviderClient` for runtime calls, `tools/ai-api` for `run` and, one line per succeeded request with `batch: true`, `batch-collect`), with no switch of client and no dollars computed there; the key name comes from its config next to the key; handed to `P: Zhratva` as its task; `dev-kit-api report --days 1 --by project` shows it after one cheap call
- [ ] The owner adds the deny lines `Bash(*api.anthropic.com*)`, `PowerShell(*api.anthropic.com*)` and `WebFetch(domain:api.anthropic.com)` to the user-level `permissions.deny` (all projects at once); whether a leading `*` works in Bash and PowerShell rules is not checked (the hard bans use a middle `*`)
