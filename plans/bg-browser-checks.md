# Screen checks in background task sessions

Owner's words: none in chat; the owner said «так» on 2026-11-23 to «Запустити нову сесію «C: Перевірки екрана у фонових сесіях»? (зараз перевірку екрана тихо пропускають)».

Source: BACKLOG.md entry «A background task session cannot run check-ui or check-usability» (read it first: the facts, the places in web-kit and project-lead, the cheapest test).

Goal: a C that the project lead starts with `claude --bg` can run the owner-approved check-ui and check-usability of a web screen (web-kit e2e-check and user-walk), or the flow hands them to a place that can, with nothing skipped silently.

Success criterion: in one live test, a background session runs (or correctly hands off) the check-ui of a small web page and the result reaches P; the rules in web-kit and dev-kit project-lead / test-change name that route; the backlog entry is removed.

Notes: pick the route yourself after the cheapest test (headless browser route in web-kit, or a documented hand-off); a choice that changes what the owner sees or does goes to P as a question. Bump plugin versions as the repo rules say.
