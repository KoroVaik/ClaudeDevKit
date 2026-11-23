# Move long sessions to a fresh one at a third

Owner's words (2026-11-23): «так» to «переносити довгу сесію в нову вже при заповненні на третину, а не наполовину? (менше витрат на довгі сесії)», from the retro item fill-limit-above-bloat (local file C:/Users/korov/.claude/dev-kit/retro/claudedevkit-ff941a2990/items/fill-limit-above-bloat.md: places sessions.py:1493, :1515, project-lead/SKILL.md:777, :847).

Goal: the fill limit for refreshing a C and for P moving itself is about one third of the context window instead of half, in code, rules and docs.

Success criterion: `dev-kit-sessions fill` marks OVER at the new limit (tests cover it); project-lead SKILL.md and the feature doc say the new limit; the retro item file's status line is set to fixed; dev-kit version bumped once.

Spend: <0.1% of the weekly limit, estimate; API: 0 USD

Done: limit 0.33 (FILL_LIMIT in sessions.py), test test_fill_default_limit_is_a_third, project-lead SKILL.md, feature docs, pult README/hub/watcher comment; retro item status fixed; dev-kit 0.1.103. Pult version not bumped: wording only.
