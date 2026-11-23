# P moves itself like a release

Status: built (C: Переїзд керівника без пушів), together with `plans/push-noise.md` (spend line there).

Built: no restart question; quiet -> silent move; not quiet -> event `handoff requested: <file>`, P's CAPS line,
`handoff go`, move 30 s after `go` (`handoff.json` `go_at`). Skill: "Restart P"; docs: the two feature docs.

## Owner's approval

Owner «так», 2026-11-23, P: ClaudeDevKit chat (from PROGRESS.md «Top priorities»):
P moves itself to a fresh context like a release restart: no «Перезапустити мене зараз?» question and no push; quiet (owner silent 5 min, no open question) -> silent move; otherwise the CAPS warning, then the move 30 s later, as in «Restart for a plugin update». Weak spot accepted: while the owner keeps writing, the move waits.

With `plans/push-noise.md` point 1, the move itself is a resume of the same session with `/clear` and then the handoff prompt (fallback: a fresh session).

## Where

- `plugins/dev-kit/skills/project-lead/SKILL.md`, «Restart P» and the «Owner queue and critical items» mention of «Перезапустити мене зараз?»; `docs/features/hand-work-to-the-project-lead.md`, «P moves itself to a fresh session».
- The Pult watcher (`plugins/pult/scripts`, handoff / self-move code).

## Success criterion

When P's own fill passes the limit, the owner gets no question and no push; a quiet P is moved silently; a P in a talk shows the CAPS warning and is moved 30 s later; the handoff loads after the move.
