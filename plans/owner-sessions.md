# Owner-started sessions under the lead (discussion, then build)

Started 2026-11-15 from the P: ClaudeDevKit chat. Discuss with the owner first; build after the owner's
yes on a written proposal.

## Owner's words (verbatim)

1. «Так» to: «Запустити нову сесію «C: Прибирання завершених сесій»? (керівник закриватиме твої сесії,
   що закінчили роботу)».
2. «І ще треба обговорить флоу, щоб керівник підхоплював відкриті мною сесії і моніторив їх, читав
   статус і тд. Я знаю що назву сесії він змінить не зможе, але фактично вона має ставать однією з його
   підопічних. Звісно після мого апруву»

## Context

- Already built (dev-kit 0.1.34-0.1.35, plugins/dev-kit/skills/project-lead/SKILL.md): section «Take over a
  session the owner started»; status group «Сесії, які ти запустив сам»; `dev-kit-sessions others` lists
  them; the watcher `dev-kit-sessions watch` follows only registered C sessions; the owner queue.
- Open point from plans/lead-authority.md: a session the owner started that finished its task just hangs
  idle; P can neither reach it (messages held, permission mode mismatch) nor close it. Seen in Zhratva
  2026-11-15 («Неоднозначні факти арбітра»).
- Since 2026-11-15 Pult set `remoteControlAtStartup: true`, so new PC sessions show on the phone.
- Known blocker: P's SendMessage to an interactive session in another permission mode is held for the
  owner's approval and may expire.

## Checked facts (2026-11-15)

- `claude agents --json` gives each session's `kind` (interactive / background), `status`
  (idle / busy / waiting + `waitingFor`) and `name` without messaging it; `others` already reads the
  first owner messages from the transcript (`sessions.py` `first_tasks`, `find_transcript`).
- `dev-kit-sessions add` accepts a session P did not start (only a duplicate id is rejected).
- `watch` fires only when the process is gone; an idle session that finished its task never fires.
- `claude stop <id>` is documented for background sessions only; on an interactive one: unchecked.
- `others` runs only at P start and at task start; nothing notices a new owner session mid-run.

## Decisions (owner, 2026-11-15, «Так всім»)

1. P watches a taken-over owner session without messaging it: it reads the session's status and its
   last reply (e.g. «чекає на тебе: питання про арбітра») and shows that in the status.
2. P notices a new owner session at every status, not only at its start, and offers the takeover as
   one owner-queue item («Взяти «X» під керування?»).
3. When a taken-over session finished its work, P stops it itself with no question: the owner's
   takeover yes covers it.

## Decisions, round 2 (owner, 2026-11-15)

4. After the takeover P sends nothing to the session; the owner keeps talking to it directly.
5. The plugin itself adds a note to the session at each owner message to it (e.g. a hook that checks
   the registry): «тебе веде керівник; коли закінчиш, напиши «Роботу завершено»». P sends nothing.
   The line «Роботу завершено» is how P knows the session finished. Owner's counter-proposal: the
   session must know it is watched and say clearly that it is done.
6. Fallback: if P cannot stop a session open in the app window, it asks the owner to close it with
   one queue item (until stopping such sessions is checked).
- Owner's priority: the main point is watching the session's work so it does not get in the way of
  other sessions; closing it is secondary and matters only so P stops counting it as active.

7. Replaces 6 (owner «Так», 2026-11-15): after «Роботу завершено» P marks the session finished
   and stops counting it as active (gone from «Сесії в роботі»), tries to stop it, and asks the
   owner nothing even if the window stays open.

## Proposal (for the owner's one yes)

- Skill rule (project-lead): at every status P runs `others`; each new owner session becomes one
  queue item «Взяти «X» під керування?». On yes: `dev-kit-sessions add`, no message to it.
- Status: a taken-over session shows under «Сесії в роботі» with its state and the gist of its last
  reply (working / чекає на тебе: ... / завершила); P keeps new tasks off its changed files.
- Script: a command that reads a registered session's status and last reply from the transcript and
  reports «finished» when the last reply has the line «Роботу завершено»; `watch` fires on it too.
- Plugin hook (UserPromptSubmit): if the session is in the project's registry, it adds the note
  «тебе веде керівник; коли закінчиш, напиши окремим рядком «Роботу завершено»».
- On finished: `dev-kit-sessions end`, try `claude stop`; on failure nothing is asked.
- Checks: script tests on a sample transcript; hook test on a registered and an unregistered id;
  independent review of the diff.

## Open points

- When P notices a new owner session: how it offers the takeover (one queue item, the owner's yes).
- After the yes: how P reaches it reliably despite the mode mismatch, registers it, watches it, reads
  its state and shows it in the status.
- When it finishes: how P closes it or turns its open question into a new C.

## Status

Built in dev-kit 0.1.36 (2026-11-15): `add --owner`, `state`, `watch` finished exit (owner records
only), the UserPromptSubmit hook note, project-lead and manager rules. Reviewed; tests and lint pass.
Not checked: `claude stop` on a session open in the app window (P then just stops counting it);
a session already idle at takeover learns about the marker only at the owner's next message.
