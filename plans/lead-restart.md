# Lead restart for a plugin update

## Owner's words (2026-11-15/16)

«Яким чином моюна перезапускати керівників щоб вони підхоплювали нові правила? Треба подумати про якийсь скриптовий шлях»
«Запитай в сесії пульт чи може краще щоб це робила вона?» - Pult answered yes, it should do it.
Owner's yes to the task: «так» (2026-11-16).

## What is known

- Pult (now plugins/pult in this repo) restarts leads: `claude stop <id>`, then `scripts/start-servers.ps1`,
  which writes respawnFlags `--model opus --effort medium` into `~/.claude/jobs/<short id>/state.json`,
  runs `claude --bg --resume <sessionId> -- '/dev-kit:project-lead'` (no other flags: any extra flag makes
  a copy) and pins the short id in `~/.claude/jobs/pins.json`. `scripts/restart-leads.ps1` restarts only
  idle leads; a lead with a running watcher always looks busy, so it is skipped.
- A resumed lead runs the project-lead skill again on its first prompt, so it gets the current rules.
- Pult's request (verbatim, translated parts kept): when Pult writes the lead «є оновлення плагіна, дійди
  до безпечного місця і відпиши "готовий"», the lead starts no new steps, brings the current one to a
  point where a restart breaks nothing (C sessions keep working on their own), and answers Pult by
  SendMessage with one word «готовий». After the restart (same conversation resumed) the first prompt is
  '/dev-kit:project-lead' with a note that it was restarted for an update; the lead continues where it
  stopped and re-arms its watcher if it has C sessions. Pult will add the note to the first prompt - this
  task defines how the note looks.
- Agreed by the owner in P: ClaudeDevKit: after each dev-kit version bump that P: ClaudeDevKit merges, it
  messages Pult so Pult restarts the leads (the trigger was missing).
- Unchecked risk: a C report sent by SendMessage while its lead is stopped may be lost. Check how a
  message to a stopped session behaves (cheapest test with throwaway sessions) and cover it in the rules
  (for example the lead runs `dev-kit-sessions state` for its C sessions after a restart).

## Success criterion

- project-lead SKILL.md: the «готовий» handshake, the restart note handling, re-arming the watcher,
  catching up on C reports missed during the stop, and P: ClaudeDevKit telling Pult after a version bump.
- Pult side (plugins/pult): restart-leads.ps1 asks busy leads first and restarts them after «готовий»
  (with a time limit), with the agreed note in the first prompt.
- One live check with a throwaway lead-like session, or a stated reason why not.

## Result (C: lead-restart, 2026-11-16)

- Live check with a throwaway haiku session (removed after): a SendMessage to a stopped session fails at
  the sender ("No agent named ... is reachable"), nothing is queued; after `claude --bg --resume <id> --
  '<prompt with spaces>'` the session keeps its name, gets the prompt intact and answers SendMessage
  («готовий» came back). `claude` has no command to send a message, so the asking is done by Pult
  (hub rules), and the script only restarts the leads Pult names in `-Ready`.
- project-lead: section "Restart for a plugin update" (handshake, `restart: plugin update` note,
  watcher re-arm, resend request to active C sessions); P: ClaudeDevKit messages Pult after a version
  bump. manager: a C whose report fails with "not reachable" keeps it and resends on P's request.
- Pult: hub.md section "Restart leads for a plugin update" (20-minute limit; a lead that does not
  answer is left running and reported). P's yes for the narrow exception to "never start or stop
  sessions" (2026-11-16). restart-leads.ps1 `-Ready`, start-servers.ps1 `-Restarted`, note in
  resume-lib.ps1. Script checks: parse, Get-LeadStartArgs with and without the note, `-File`
  passing of a comma-joined list. Not run against real leads (needs P's yes; first real run is the
  next version bump).
- Versions: dev-kit 0.1.40, pult 0.1.2.
- Paid spend: about $0.01 (two haiku turns).
- Review (dev-kit:reviewer, sonnet) fixes applied: «Відбій» release and a 30-minute self-release for a
  lead on hold, early end of Pult's round, waiting for the stopped process before the resume,
  a watcher that outlived the stop, `from-name` check, `-Ready` given as one comma-joined string.
- Not checked: whether a restarted lead loads the new version. `installed_plugins.json` lists project
  installs of dev-kit from the plugin cache (Zhratva and Prishch at 0.1.10), while the marketplace
  is this repo's folder. If a lead loads the cache copy, a restart alone does not bring the new rules;
  the cheapest check is the version a lead's skill base directory shows after the next restart.
