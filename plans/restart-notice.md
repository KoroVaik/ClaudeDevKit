# Tell child sessions when their lead restarts

Owner's words (2026-11-23, P: ClaudeDevKit chat): «Чи можна сповістити чайлд сесії що парент не приймає поввдомення наступні 30сек? І як це краще зробить? Давай обговорення»

Context:
- A lead (P) restarts for a plugin release (plans/update-timing.md: routine at a quiet moment, critical with a 30 s CAPS warning) and when it moves itself to a fresh chat at a third of its context.
- A message a C sends to a stopped session fails at the sender with «No agent named ... is reachable» and is not queued (checked live 2026-11-16); today P asks each active C after a restart to resend a failed report (project-lead «Restart for a plugin update»).
- Not checked: what happens to the owner's own message typed during a lead restart.
- Agreed today and not built yet (PROGRESS.md In flight «P moves itself like a release»): P moves itself like a release - quiet -> silent move; otherwise the CAPS warning, then the move 30 s later. This talk may fold that build in.

Topics: whether and how child sessions learn that their lead is away (and for how long); what they do with a report meanwhile (wait and resend, queue, other); whether the owner's own messages need the same; anything the owner raises.

Result: the «Owner's approval» section in this file with every agreed point in builder detail.
