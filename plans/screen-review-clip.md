# Plan: a built screen is judged against real references and shown with a clip

Status: built (2026-11-26).

Owner's words: «так» to «Запустити сесію «M: Перевірка зібраного екрана з відео»? (сесія сама звірить вигляд із реальними фото і покаже відео змін)» (L: ClaudeDevKit, 2026-11-26).

Source: BACKLOG.md entry «Built-screen review: judge the look against real references and show a clip for every change over time» (points 1-6); removed when built.

Success criterion: points 1-6 of the entry are in `plugins/dev-kit/skills/project-lead/SKILL.md` "Build a designed screen" (and the review session's first prompt there) and in `unity-kit:game-clip`; lint and tests pass; versions bumped with release marks.

## Done
- project-lead "Build a designed screen": step 1 adds the reference check (1), clips per moving state with resolution (2), mockup «так» covers the clip run (4); step 2's review prompt judges against references and shows clips (3); step 3 replies with shots and clips.
- test-change consent paragraph: the mockup «так» also covers the clips' Play Mode runs (4).
- game-clip: no verdict only in the owner caption (5); scenario or recipe reaches the state; detail clips tight, real density or higher, 600-800 px, limits lifted, caption names resolution (6); a built screen's clip goes to the review session.
- game-view-check, unity-editor, user-check: "agent does not judge the look" narrowed to the owner verdict, pointing to the Manager's reference check.
- Docs: `docs/features/show-a-gif-of-play.md`, `docs/features/hand-work-to-the-project-lead.md`.
- Versions: dev-kit 0.1.141, unity-kit 0.2.6, routine marks.
- Script defaults (480 px, 5 MB) kept: the rule lifts them per clip by flags.
- Review doubts recorded, not fixed: unity-editor permission table does not itself say the mockup «так» counts (game-clip and test-change do); `hand-work-to-the-project-lead.md` line about shots of a look question names no clip.
- Cheapest test (replay the Prishch review prompt) not run here: needs Prishch's Unity run.

Spend: ~0.2% of the weekly limit, estimate; API: 0 USD
