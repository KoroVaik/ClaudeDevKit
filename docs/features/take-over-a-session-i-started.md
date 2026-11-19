# Take over a session I started

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
A session you started yourself can become one of the project lead's: the lead watches its work and its
end, and you keep talking to the session directly.

## Rules
### P takes it over after the first reply
A session you started yourself can be taken over: P registers it after its first reply
(`dev-kit-sessions add --owner`) and it keeps talking with you.

### The session knows it is watched
At each of your messages to a session the lead took over, the session gets a short note: the lead only
reads it, and the session ends its work with the line "Роботу завершено". Other sessions get nothing.
How the note is added: [hooks](../tech/hooks.md).

## Acceptance criteria
- You start a session yourself and it answers: P can register it and it shows up among the sessions P watches.
- You write to a taken-over session: it gets the note about the lead and the closing line.
- You write to a session P does not watch: it gets nothing extra.
- A taken-over session writes "Роботу завершено": P sees it as finished.

## Built in
- `plugins/dev-kit/hooks/owner-session-note.py`
- `plugins/dev-kit/scripts/sessions.py`
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `tools/tests/test_owner_session_note.py`

## Open
- [ ] Check `claude stop` on a taken-over session open in the app window (P then only stops counting it), and the case of a session already idle at takeover, which learns about the "Роботу завершено" marker only at your next message.
