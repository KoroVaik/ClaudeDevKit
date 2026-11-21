# Shared Claude API client with spend logging

Owner's words (2026-11-20): «Клієнт має буть спільний для всього», «Запускай імплементацію клієнта для апі. Сесія має синхронізуватись із жратвой стосовно апдейтів там, щоб все було враховано. Давай обговорення краще».

## Starting point
- BACKLOG.md entry «A shared Claude API client with spend logging» (what, why, cheapest test).
- Facts from the Console (P, 2026-11-20): the API credit is the monthly Max credit ($100, about $89.95 left, expires 2026-12-05); almost all spend in 30 days ($81.63) came from the Zhratva keys «Zhratva test» and «Zhratva test Expired» (about $43 on Nov 4, about $7 on Nov 20). The API has no endpoint for the remaining balance; P checks the Console weekly (project-lead «API credit check», local log C:/Users/korov/.claude/dev-kit/credits.md).
- Zhratva is a separate repository (C:/Users/korov/MyRepositories/Zhratva) with its own lead «P: Zhratva». Learn how Zhratva calls the API, and its recent and planned changes there, by asking «P: Zhratva» with SendMessage; do not edit Zhratva. Any change Zhratva must make is agreed with the owner here and handed to «P: Zhratva» as its task after the owner's yes.
- Zhratva's answer («P: Zhratva», 2026-11-21, read-only check): .NET 10, raw HTTP to /v1/messages, no SDK. Every runtime call goes through its AiProviderClient (backend/Zhratva.Core/Ai/), which already saves request and raw response per job attempt and reports cost with cache usage (Zhratva docs/standards/ai.md). Models: sonnet-5-5, haiku-5-5, opus-5-5 (arbiter). Key only on the worker (user-secrets locally, env var in prod; worker in home Docker, API on Render). Offline: tools/ai-api, a C# CLI (prepare/run/batch-submit/batch-collect); Python recipe tools only shell out to it. Catalogue and reuse-court run headless `claude -p` on the subscription, no API. Most spend: recipe-analysis batch runs after the owner's yes (2026-11-20: 30 recipes 6.70 USD, plus a 102-recipe run 23.15 USD; 2026-11-04 about 43 USD by estimate). Nothing in flight on batching, caching or key change.

## Goal
Agree with the owner where the client lives, what it logs, how every project uses it, and how it relates to the weekly Console check. Write it in «Owner's approval» here.

## Owner's approval
- 2026-11-21, «так»: every API call writes one line to one local log next to the weekly credit-check log (date, project, key name, model, tokens, cost).
- 2026-11-21, «так»: the weekly Console check stays, now as a reconciliation of the Console figure against the log (the API gives no remaining balance).
- 2026-11-21, «так»: agents may not call the Claude API directly, only through the client (a rule plus a deny rule).
- 2026-11-21, «так»: the Zhratva prod worker (home Docker on this PC, stopped for two weeks) is not joined to the shared log for now; it keeps its per-call records in its own database; join it when it runs again.
- 2026-11-21, «так»: the shared part is the log line format and the one log file, not a shared code library; Zhratva appends the line from its own single call point (AiProviderClient and the tools/ai-api CLI), no switch to another client.
- 2026-11-21, «так»: for other projects and scripts dev-kit ships a small ready client that calls the API and writes the line itself.
- 2026-11-21, «так»: cost per call is computed from tokens by one shared model price table in dev-kit (the API returns only tokens; Zhratva computes no dollars).
- 2026-11-21, «так»: the dev-kit client is Python, like the other dev-kit tools.
- 2026-11-21, «так»: each project has its own API key, and the log line carries the key's Console name, so the weekly check reconciles per key.

## Built (dev-kit side, 2026-11-21)
- `dev-kit-api` (`plugins/dev-kit/scripts/api_client.py`, stdlib only, raw HTTP to /v1/messages with `anthropic-version: 2026-10-21`, retries on 408/409/429/5xx): `call` (sends, writes the line, prints the answer), `report` (sums by key, project, model or day), `reconcile` (Console sums per key against the log), `prices`.
- Log: `C:/Users/korov/.claude/dev-kit/api-calls.jsonl` (env `DEV_KIT_API_LOG` overrides). Line format and cost rules: `docs/features/log-and-reconcile-api-spend.md` (the one home; the handoff below repeats only what Zhratva needs).
- Price table: `plugins/dev-kit/api-prices.json`, from the claude-api skill's model table (cached 2026-11-03). Assumed, not on that table: Haiku 5.5 cache read at 0.1x input (0.01 / 0.05 USD). Not priced: fast mode (Opus 5.5 `speed: fast`, 2x), server tools (web search fees); nobody uses them now.
- Keys: the client reads the key from env `DEV_KIT_API_KEY` (not `ANTHROPIC_API_KEY`, which a headless `claude -p` would bill unlogged; reviewer, 2026-11-21) and its Console name from `--key-name` or env `DEV_KIT_API_KEY_NAME`; the project name defaults to the repository folder (the main repo for a worktree).
- Rules: `dev-kit:manager` "Claude API calls" (agents only through `dev-kit-api call`); `dev-kit:project-lead` "API credit check" now runs `dev-kit-api reconcile` per key and adds its `line:` text to `credits.md`.
- Not tested: a live paid call (no API key on this machine for ClaudeDevKit); the HTTP path is tested with a fake opener. Paid spend stays 0 USD.

## Deny lines for P (not written by this C)
Exact lines, for the owner's user-level `C:/Users/korov/.claude/settings.json` `permissions.deny` (all projects at once, Zhratva included; per-project `.claude/hard-bans.json` works too but needs every project):

```json
"Bash(*api.anthropic.com*)",
"PowerShell(*api.anthropic.com*)",
"WebFetch(domain:api.anthropic.com)"
```

They stop an agent's direct `curl`/`Invoke-RestMethod`/fetch to the API; `dev-kit-api call` and Zhratva's `tools/ai-api` commands do not name the host, so they still run. Best-effort: a script file that calls the API is not caught (the rule covers that). Not checked: a leading `*` in Bash and PowerShell rules (the existing hard bans use a middle `*`, `Bash(git push*main*)`).

## Handoff to «P: Zhratva» (after the merge)
Task: append one spend line per paid API call to the shared log, from Zhratva's own call points (AiProviderClient for runtime calls, tools/ai-api for `run` and `batch-collect`); no switch to another client, no dollars computed in Zhratva. The prod worker (home Docker) stays out for now (owner, 2026-11-21).
- File: `%USERPROFILE%/.claude/dev-kit/api-calls.jsonl`, or the path in env `DEV_KIT_API_LOG` when set. Create the folder when missing.
- Write: open for append, write the whole line plus `\n` in one write (UTF-8, no BOM), close. Never rewrite or truncate the file. A failed write is logged as a warning and never fails the job (the money is spent).
- One line per response that has `usage`; for `batch-collect`, one line per succeeded request, `batch: true`, `ts` = collection time, `request_id` = the custom id.
- Line (keys in this order is nice, not required; compact JSON is fine):
  `{"v": 1, "ts": "2026-11-21T14:03:05Z", "project": "Zhratva", "key": "<the key's Console name>", "model": "<response model>", "batch": false, "input": <usage.input_tokens>, "output": <usage.output_tokens>, "cache_write_5m": <usage.cache_creation.ephemeral_5m_input_tokens>, "cache_write_1h": <usage.cache_creation.ephemeral_1h_input_tokens>, "cache_read": <usage.cache_read_input_tokens>, "cost_usd": null, "source": "AiProviderClient" or "ai-api <command>", "request_id": "<message id or custom id>"}`
- `ts` UTC `yyyy-MM-ddTHH:mm:ssZ`. With no `usage.cache_creation` breakdown, all of `cache_creation_input_tokens` goes to `cache_write_5m`. A missing number is 0.
- Key name: from config next to the key (user-secrets locally), e.g. `Ai:KeyName`; the value is the key's name in the Console. The owner's choice: each project has its own key, so the Zhratva keys stay Zhratva's.
- Keep the API key out of `ANTHROPIC_API_KEY` in any shell where `claude -p` runs (catalogue, reuse-court): `claude -p` bills a set `ANTHROPIC_API_KEY` with no log line.
- Check: one cheap call (Haiku, a few tokens) writes one line; `dev-kit-api report --days 1 --by project` shows Zhratva with that call.

## Paid spend
Total so far: 0 USD.
