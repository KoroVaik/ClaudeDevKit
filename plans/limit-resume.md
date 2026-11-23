# Sessions resume by themselves after the usage limit resets

Status: build (C: Сесії самі продовжують після ліміту).

Owner's words (2026-11-23, P: ClaudeDevKit chat): «Також Потрібно попрацювать над відновлення роботи після поновлення лімітів, бо зараз сесії чекають поки я щось напишу».

Known: the Pult watcher logs `LIMIT <name> <id> (resets <time>)` and sends the lead a `limited:` event (`plugins/pult/scripts/watch-servers.ps1` ~:543-554); project-lead SKILL.md says a limited C «is alive and goes on after the reset», but nothing wakes it, so it stands until someone writes to it. Applies to every session P or Pult manages (C, discussions, leads); check how the limit stop looks in `plugins/dev-kit/claude-facts.md` and add what you learn through the facts-keeper agent.

Success criterion: after the reset time, a session stopped by the limit is woken with a short «continue» message (once, logged), carries on its task with no owner message, and a lead gets no extra noise; tested on a throwaway session where possible; the skill line made true.

## Done

- Pult watcher (`plugins/pult/scripts/watch-servers.ps1`, `Invoke-LimitResume`): for each live lead and task
  session whose transcript ends with the limit notice, once the reset time (cut to the minute) plus 180 s has
  passed, or at once when unknown, it sends one `[EVT-<id>] ... the usage limit that stopped you has reset. Go on
  with your task ...` by `Send-Wake`. Logs LIMIT-RESUME, LIMIT-RESUME-TAKEN. Not taken: resent after
  $WakeConfirmSec, at most 3 sends, then LIMIT-RESUME-GIVEUP. A send the sender cannot make (account still
  limited) counts no try, retried every 900 s, logged once per reason (LIMIT-RESUME-FAILED). A name shared by two
  live sessions is skipped. Not with -Once, on hold or during a full start. After review: the 3 sends count
  per session across a new stop with no LIMIT-END between (a resume turn that hits the limit again), a sender
  that keeps failing gives up 12 h after the reset, a lead marked ready is not messaged, the send sets LastWake.
- Lead noise: the `limited:` event line of a stop being resumed is held back in the wake pass; the lead gets it
  only after a give-up. The skill line (project-lead, event lines) now says that.
- Scope kept: leads and registered non-owner task sessions (C, discussions, retro). Owner sessions and the Pult
  hub are not woken (the watcher header: never an owner session).
- Docs: `plugins/pult/README.md`, feature `start-leads-at-logon-and-heal-them.md` (new rule section), facts via
  facts-keeper (resetsAt in the notice; a limited session does not go on by itself).
- Tests: 4 new in `tools/tests/test_watch_servers_wake.py` (resume after reset, none before, give-up then the
  lead hears, refused send counts no try); the limit test filters out the resume lines.
- Not tested live: a real limit stop cannot be made on purpose; message delivery to a live session is the same
  path as the other wakes (claude-facts, "A one-shot `claude -p` delivers a message into a running session").
- Versions: pult 0.1.28, dev-kit 0.1.108 (routine).

Spend: ~0.3% of the weekly limit, estimate; API: 0 USD
