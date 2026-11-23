# Start leads at logon and heal them

Epic: [Run all projects from the phone](../epics/run-all-projects-from-the-phone.md)

## Purpose
The project leads and the Remote Control server are up whenever you sit down or pick up the phone, and a
dead one comes back without you. The mechanics (the start shortcut, the project list, the watcher's
checks, log lines and files): [the plugin README](../../plugins/pult/README.md).

## Rules
### Leads are up at Windows logon
At Windows logon each project's lead and the Remote Control server are started; you do not start them.

### A dead lead comes back
A lead or server that is down for two checks of the watcher is brought back, at most 3 tries an hour, then
the watcher gives up until that lead or server is seen up again. A task session a project lead registered,
closed by Claude Code and not stopped on purpose, comes back too, after two checks and with the same
limit of 3 tries an hour. A lead whose project has no hard-ban lines on main is not brought back: it is
blocked, not broken. A try that hangs is cut after 5 minutes and counts as a failed try; then the watcher goes
on with its other checks.

### A session stopped by the usage limit goes on after the reset
A lead or task session that stopped on the 5-hour or weekly limit gets one short «go on» message from the
watcher a few minutes after the limit resets, and carries on its task with no message from you. Its lead
hears of the stop only when that message was not taken after 3 tries; then the lead's status shows
`стоїть, скінчився ліміт`. Why: owner, 2026-11-23 (`plans/limit-resume.md`): sessions waited after the reset
until he wrote to them.

### A lead on an old version is restarted when the update allows
Each dev-kit update is marked critical (agents cannot cope without it) or routine by the agent that makes
it. A routine update reaches a lead once, on a later day, at its first quiet moment: the lead is idle, its
last message to you is not an open question and you wrote nothing to it for 5 minutes. A critical update
restarts a quiet lead the same day with no warning; a lead in a talk with you first finishes its step,
writes «⚠ ЧЕРЕЗ 30 СЕК БУДЕ ПЕРЕЗАВАНТАЖЕННЯ (ОНОВЛЕННЯ ІНСТРУМЕНТІВ)» and restarts 30 seconds later; a
message you send in those 30 seconds is answered after the restart. Any restart takes every waiting
update with it. A lead whose extension plugin (web-kit, unity-kit) changed version is restarted when it is
idle. Why: owner, 2026-11-23 (`plans/update-timing.md`): updates restarted the leads several times an hour,
in the middle of talks.

### A lead past a third of its context moves to a fresh session
A lead that saved its notes at a third of its context is stopped and resumed with an empty context in the same
session (no phone push), when it is quiet as for a release restart, or 30 seconds after its warning in a talk, or
after your «перезапускай». If that resume fails, a fresh session of the same name loads the notes (one push). A
failed move, or one that hangs and is cut after 10 minutes, is shown in Pult and pushed to your phone; the old
lead comes back.

### Your own sessions are never touched
The watcher never touches your own sessions, taken-over ones included.

### A stop on purpose stays stopped
After you stop the servers on purpose (`stop-servers.ps1`), the watcher brings nothing back until the next
full start. Restarting the leads (`restart-leads.ps1`) pauses the watcher only while the restart runs: the
restart's own start run brings the leads back and lifts the pause; a restart that crashed before that run
lifts no pause, so the watcher lifts it itself at its next check. A lead restart that hangs is cut after 10
minutes, logged, and its pause lifted at once; a lead it had stopped comes back as after a crash. The watcher also restarts nothing while
a full start runs. A lead stopped only with `claude stop` is not a stop on purpose: it comes back; to retire
one project, remove its row from the project list.

## Acceptance criteria
- Windows starts: each project's lead and the Pult server are running without you starting them.
- A lead is killed: after about two checks it is back.
- dev-kit gets a routine update: the leads keep running on the old version that day and restart once on a later day.
- dev-kit gets a critical update: a quiet lead restarts the same day; a lead in a talk writes the 30-second warning first.
- You stop the servers on purpose: nothing is brought back until the next full start.
- You restart the leads on purpose: they come back through the restart itself, and the watcher goes on as usual.
- A lead's start hangs: after 5 minutes it is cut, logged, and the watcher goes on; the next try follows as usual.
- A lead restart crashes halfway: at the watcher's next check the pause is lifted and the stopped leads come back.
- A lead restart hangs: after 10 minutes it is cut, logged, the pause is lifted, and the watcher goes on.
- A lead's move to a fresh context hangs: after 10 minutes it is cut, logged, the old lead comes back, and the watcher goes on.

## Built in
- `plugins/pult/scripts/start-servers.ps1`
- `plugins/pult/scripts/stop-servers.ps1`
- `plugins/pult/scripts/restart-leads.ps1`
- `plugins/pult/scripts/watch-servers.ps1`
- `plugins/pult/scripts/servers.psd1`
- `plugins/pult/scripts/resume-lib.ps1`
- `tools/tests/test_watch_servers_restart.py`
- `tools/tests/test_watch_servers_limit.py`
- `tools/tests/test_watch_servers_handoff.py`
- `tools/tests/test_watch_servers_heal.py`
- `tools/tests/test_start_servers_handoff.py`

## Open
- [ ] Check from the watcher's logs and the transcripts that Pult and a lead with no events show no wakes for a day, that one forced GIVEUP gives one push and the fix line in Pult, and that a push relayed by a live lead (Pult down) reaches the phone; the lead relay is untested
- [ ] Check whether you can still attach to a P from a terminal with `claude attach <id>`, and the exact wording of the session list in the phone app
