# Take over a session I started

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
A session you started yourself can become one of the project lead's: the lead watches its work and its
end, and you keep talking to the session directly.

## Rules
### The Lead takes it over after the first reply
A session you started yourself can be taken over: the Lead registers it after its first reply
(`dev-kit-sessions add --owner`) and it keeps talking with you.

### The session knows it is watched
At each of your messages to a session the lead took over, the session gets a short note: the lead only
reads it, and the session ends its work with the line "Роботу завершено". Other sessions get nothing.
How the note is added: [hooks](../tech/hooks.md).

## Acceptance criteria
- You start a session yourself and it answers: the Lead can register it and it shows up among the sessions the Lead watches.
- You write to a taken-over session: it gets the note about the lead and the closing line.
- You write to a session the Lead does not watch: it gets nothing extra.
- A taken-over session writes "Роботу завершено": the Lead sees it as finished.

## Built in
- `plugins/dev-kit/hooks/owner-session-note.py`
- `plugins/dev-kit/scripts/sessions.py`
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `tools/tests/test_owner_session_note.py`
