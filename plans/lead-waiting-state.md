# Project lead: a session that waits on something shows as «чекає» with the reason

Status: build (C: Стан «чекає» у статусах керівника).

Source: BACKLOG.md entry of the same name (owner yes, 2026-11-23, Zhratva); its What, Why and Cheapest test are the scope. Remove the entry in the same branch.

Success criterion: the entry's cheapest test holds: a C that hits a 30-min retry wait sends P a report; P's next message has `чекає - «C: ...» (<reason>, повтор о HH:MM)`, not `працює`.
