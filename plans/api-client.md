# Shared Claude API client with spend logging

Owner's words (2026-11-20): «Клієнт має буть спільний для всього», «Запускай імплементацію клієнта для апі. Сесія має синхронізуватись із жратвой стосовно апдейтів там, щоб все було враховано. Давай обговорення краще».

## Starting point
- BACKLOG.md entry «A shared Claude API client with spend logging» (what, why, cheapest test).
- Facts from the Console (P, 2026-11-20): the API credit is the monthly Max credit ($100, about $89.95 left, expires 2026-12-05); almost all spend in 30 days ($81.63) came from the Zhratva keys «Zhratva test» and «Zhratva test Expired» (about $43 on Nov 4, about $7 on Nov 20). The API has no endpoint for the remaining balance; P checks the Console weekly (project-lead «API credit check», local log C:/Users/korov/.claude/dev-kit/credits.md).
- Zhratva is a separate repository (C:/Users/korov/MyRepositories/Zhratva) with its own lead «P: Zhratva». Learn how Zhratva calls the API, and its recent and planned changes there, by asking «P: Zhratva» with SendMessage; do not edit Zhratva. Any change Zhratva must make is agreed with the owner here and handed to «P: Zhratva» as its task after the owner's yes.

## Goal
Agree with the owner where the client lives, what it logs, how every project uses it, and how it relates to the weekly Console check. Write it in «Owner's approval» here.
