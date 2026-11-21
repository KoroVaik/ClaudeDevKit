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

## Paid spend
Total so far: 0 USD.
