# Spend the 5-hour limit slower

Status: discussion started 2026-11-27 by L: ClaudeDevKit.

## Owner's words

2026-11-27: «Проаналізуй витрати лімітів за останній 5 годинний ліміт. Надто бистро витратився». After the Lead's answer,
to «запустити обговорення, як зменшити витрати? (наприклад, менше одночасних сесій на Opus)»: «Давай обговорення.»

## What the Lead found (estimate, token prices assumed)

Window 2026-11-27 06:40-11:40 UTC; 95% by 09:30 UTC. About 85% of the weighted cost was Opus. About ten Opus sessions
lived at once (leads, Managers, a review session, Pult); each turn re-reads a large cached context, and sessions that
woke after a pause wrote their whole context to the cache again. Top: Prishch pain-feedback Manager with Opus
subagents (~23%), Zhratva catalogue-next with a Sonnet judge loop (~19%), L: Prishch (~10%), Pult (~9%). Fastest rise:
09:19-09:30, 78% to 95%, four sessions at once. Full tables: C:/Users/korov/.claude/handoffs/ClaudeDevKit/spend-5h-2026-11-27.md
(local file).

## Goal of the talk

Agree with the owner what changes so the 5-hour limit lasts (for example a cap on parallel Opus sessions, cheaper
models for some roles, smaller contexts, a per-window budget). The outcome goes into «Owner's approval» below.
