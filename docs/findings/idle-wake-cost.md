# Idle wakes of Pult and the leads

Measured 2026-11-15..20 from the session transcripts and `servers.log`. The design that followed is in
[Start leads at logon and heal them](../features/start-leads-at-logon-and-heal-them.md) and
[Hand work to the project lead](../features/hand-work-to-the-project-lead.md) ("P wakes only when needed").

## A model that re-arms a watcher burns tokens for nothing

- Claim: an idle session costs nothing; the cost was waking it every 2 hours to re-arm a watcher the host kills.
  Evidence (the Pult hub, 2026-11-19..20): about 13 wakes a day, 22 of 22 pushed nothing, 21 of 22 found the prompt
  cache cold (each rewrote about 110k tokens and read about 230k), about 4.4M tokens a day for nothing. The
  Zhratva lead spent about 18M tokens a day (contexts 340k-540k) with 1 push in 33 wakes.
- Total of idle wakes 2026-11-15..20: 23.6M units, about 3.4% of a weekly limit; the hub 87% of its own usage, the
  Zhratva lead 20%, the Prishch lead 11%; about 85% of it cache writes.
- The 2 hours are the host's cap on a background Bash run (a 125-minute run was killed at 120); the Monitor tool
  caps at 30 minutes. So no watcher inside a session avoids the wakes.
- Consequence: no model keeps a watcher; the Pult watcher script (no model) does all watching and wakes a session
  by message only on an event.

## Few real events, many reports

- Claim: real watcher events are about 2 a day across all leads; reports from task sessions wake a lead far
  more often (ClaudeDevKit about 10 a day, Zhratva about 11, peaks 22 and 27). Evidence: 80 lead watcher exits
  (other than the time limit) in 2026-11-15..20, only 10 did work (3 gone, 7 stale); 70 were waste (40 "already
  watching", 12 "nothing to watch", 8 time-limit exits, 10 other).
- Consequence: a wake by message per event is cheap, and a keep-warm ping matters more: a warm cache read costs
  about 1/20 of a cold rewrite, so the ping pays while a task session's report comes within about 16 hours (leads
  write a 1-hour cache).

## Sending a wake from a script

- A one-shot `claude -p --no-session-persistence --model haiku --safe-mode` with only SendMessage delivers a
  message into a running session in 1-3 seconds and costs about 0.0008 USD (about 0.016 with plugins loaded). It
  needs no approval, delivers to a busy target, and answers `failed: ...` with exit 0 when the target is missing.
  Delivery across permission modes works from manual and acceptEdits to auto; between sessions in
  `bypassPermissions` (2026-11-21) it also works, a held message was the earlier trouble of mixed modes.
- A session with a background shell shows as busy, one with none as idle: a lead with no watcher of its own shows idle.
- A push from a fresh session (a `-p` one-shot, a background session, one with Remote Control) is refused with
  "Not sent - this terminal is active"; a push from a session the owner is attached to (Pult, or a live lead) goes
  through. While the Claude app is open on the phone, no push shows: a test push arrived only after the app was closed.
- Consequence: the watcher script wakes sessions by message and asks a relay session to push; it never pushes itself.

## Token thresholds on 5 days of scans

- Claim: with the thresholds of the critical token problem (a session over 2% of the weekly limit in a day, or
  waste over 0.5%), the scans of 2026-11-16..20 gave 2, 2, 1, 5 and 6 lines a day. Spend over 2% fires on long
  Zhratva catalogue sessions most days; waste over 0.5% fires on the hub's idle wakes (0.56-0.60% a day before the fix)
  and on the Zhratva lead.
- Consequence: the thresholds stay as the owner set them; Pult shows each problem once and again only after it
  grew 1.25 times.
