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
blocked, not broken.

### A lead on an old version is restarted when idle
A lead that runs on an older dev-kit version than the installed one, or whose extension plugin (web-kit,
unity-kit) changed version, is restarted when it is idle. A busy lead is not interrupted: it is restarted
at a safe point it marks itself.

### A lead past a third of its context moves to a fresh session
A lead that saved its notes at a third of its context is stopped and started fresh under the same name, once it
has been idle and quiet for 5 minutes, or at once after your «так» or «перезапускай». A failed move is
shown in Pult and pushed to your phone; the old lead comes back.

### Your own sessions are never touched
The watcher never touches your own sessions, taken-over ones included.

### A stop on purpose stays stopped
After you stop the servers on purpose (`stop-servers.ps1`), the watcher brings nothing back until the next
full start. Restarting the leads (`restart-leads.ps1`) pauses the watcher only while the restart runs: the
restart's own start run brings the leads back and lifts the pause. The watcher also restarts nothing while
a full start runs. A lead stopped only with `claude stop` is not a stop on purpose: it comes back; to retire
one project, remove its row from the project list.

## Acceptance criteria
- Windows starts: each project's lead and the Pult server are running without you starting them.
- A lead is killed: after about two checks it is back.
- dev-kit is updated: an idle lead restarts and runs on the new version; a busy one waits for a safe point.
- You stop the servers on purpose: nothing is brought back until the next full start.
- You restart the leads on purpose: they come back through the restart itself, and the watcher goes on as usual.

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
- `tools/tests/test_start_servers_handoff.py`

## Open
- [ ] Defect: a HEAL has no timeout, so a hung `claude --bg` stalls the watcher loop; `plugins/pult/scripts/watch-servers.ps1`
- [ ] Defect: a hold file left by a crashed `restart-leads.ps1` stays until the next full `start-servers.ps1`; `plugins/pult/scripts/restart-leads.ps1`
- [ ] Check from the watcher's logs and the transcripts that Pult and a lead with no events show no wakes for a day, that one forced GIVEUP gives one push and the fix line in Pult, and that a push relayed by a live lead (Pult down) reaches the phone; the lead relay is untested
- [ ] Check whether you can still attach to a P from a terminal with `claude attach <id>`, and the exact wording of the session list in the phone app
