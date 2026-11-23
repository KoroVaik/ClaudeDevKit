# Tell child sessions when their lead restarts

Owner's words (2026-11-23, P: ClaudeDevKit chat): «Чи можна сповістити чайлд сесії що парент не приймає поввдомення наступні 30сек? І як це краще зробить? Давай обговорення»

Context:
- A lead (P) restarts for a plugin release (plans/update-timing.md: routine at a quiet moment, critical with a 30 s CAPS warning) and when it moves itself to a fresh chat at a third of its context.
- A message a C sends to a stopped session fails at the sender with «No agent named ... is reachable» and is not queued (checked live 2026-11-16); today P asks each active C after a restart to resend a failed report (project-lead «Restart for a plugin update»).
- Not checked: what happens to the owner's own message typed during a lead restart.
- Agreed today and not built yet (PROGRESS.md In flight «P moves itself like a release»): P moves itself like a release - quiet -> silent move; otherwise the CAPS warning, then the move 30 s later. This talk may fold that build in.

Topics: whether and how child sessions learn that their lead is away (and for how long); what they do with a report meanwhile (wait and resend, queue, other); whether the owner's own messages need the same; anything the owner raises.

Result: the «Owner's approval» section in this file with every agreed point in builder detail.

Spend: <0.1% of the weekly limit, estimate; API: 0 USD

## Owner's approval

Owner «все так» (2026-11-23, «Обговорення» session) to the points below (a third point, a live check of the owner's message typed during a restart, left the plan: checks run in the discussion, not in the build). The owner's own message typed into a lead's chat during a restart is not lost: the owner checked it himself (2026-11-23, «не губиться, я перевіряв»); nothing to build for it. No warning is sent to child sessions before a lead restart: the C retries on its own instead. Why: a warning is possible only on the warned (CAPS, 30 s) paths, costs P and every C a turn, and misses the silent restart; P is unreachable about 10 s in practice (Pult log `RESTART-LEAD` -> `HOLD off`).

Checked live 2026-11-23 (throwaway background session, real sessions untouched): a send to a stopped session fails («No agent named ... is reachable», or via Remote Control «HTTP 409 ... Session ... is not active»); after a resume a send to it is delivered and answered. Side fact: a resume without `-n` renamed the session after its first prompt, so a resume must keep the name (Pult's resume of P does: P kept its name today).

1. A C retries a failed send to its P by itself. When a send to P fails with any error (the text varies, see above), the C keeps the message and sends it again about a minute later, up to three retries. The wait never blocks the C's conversation or work (a background timer, not a foreground sleep). After the third failed retry the C stops retrying, keeps the message and sends it with its next message to P or when P next writes to it. Applies to every kind a C sends P (`ГОТОВО`, `ПИТАННЯ`, `ЗАСТРЯГ`, `ВІДПОВІДЬ`). Where: `plugins/dev-kit/skills/manager/SKILL.md` (the «not reachable» rule, today «keeps the report and sends it again when P asks»). Success: a C whose send fails while P restarts delivers it within about a minute with no message from P.
2. P no longer asks its sessions to resend after a restart. Remove the `ВКАЗІВКА` «P перезапущено... Якщо твій звіт не дійшов, надішли його ще раз» from `plugins/dev-kit/skills/project-lead/SKILL.md` (restart for a plugin update and the handoff first prompt) and that purpose from the `ВКАЗІВКА` row in `plugins/dev-kit/messages.md`. Fix any other place that still says P asks for a resend (Pult first prompts, docs/features).

Not in scope: «P moves itself like a release» (PROGRESS.md) stays its own build.
