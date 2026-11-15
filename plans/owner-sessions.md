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

## Open points

- When P notices a new owner session: how it offers the takeover (one queue item, the owner's yes).
- After the yes: how P reaches it reliably despite the mode mismatch, registers it, watches it, reads
  its state and shows it in the status.
- When it finishes: how P closes it or turns its open question into a new C.
