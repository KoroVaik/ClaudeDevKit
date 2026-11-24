# Watches the servers from servers.psd1 and writes every change to ~\.claude\pult\logs\servers.log
# (the health log the Pult hub reads): STATE (first look), DOWN (with what is known about why), UP.
# It fixes four mechanical problems itself:
# - A lead or server of the list that is down for two rounds in a row is brought back by
#   start-servers.ps1 -Only <name> (the same resume as at logon): HEAL. At most $MaxHeals tries per
#   hour per entry, then GIVEUP until it is seen up again. A hold file (~\.claude\pult\hold, left by
#   stop-servers.ps1 and restart-leads.ps1, removed by a full start-servers.ps1 run) pauses this: HOLD.
#   A HEAL run still going after $HealWaitSec s (a hung `claude --bg`) is stopped (Invoke-Bounded) and logged as
#   HEAL-TIMEOUT <name>; it counts as a failed try and the round goes on. The same bound holds for the
#   `claude respawn` of a HEAL-TASK (HEAL-TASK-TIMEOUT <name> <id>). A restart-leads.ps1 run (RESTART-LEAD below) still
#   going after $LeadRestartWaitSec s is stopped the same way and logged as RESTART-LEAD-TIMEOUT <name> (a failed restart:
#   no new try on the same versions); the hold it left is removed at once (HOLD-STALE) and the round goes on, so a
#   lead it had stopped comes back by HEAL. A handoff move (below) is bounded the same way: HANDOFF-TIMEOUT.
#   A hold file restart-leads.ps1 left (its text names its pid) whose process is gone, or is another process now
#   (started after the hold was written), is stale: the script crashed before its full start-servers.ps1 run. The
#   watcher removes it at the start of a round (not with -Once, not while a full start runs) and logs HOLD-STALE
#   (<its text>). A hold file of stop-servers.ps1, or one with no pid, stays until a full start as before.
#   Other sessions it touches only as the next item says; never an owner session.
#   A lead whose project has no hard-ban lines on main is never started (start-servers.ps1 prints NO-BANS): no
#   HEAL try is counted, no HEAL-FAILED or GIVEUP; the watcher logs NO-BANS <name> (<reason>) once and sends it to
#   Pult (the hub prepares .claude/hard-bans.json on the owner's yes; then runs `dev-kit-bans add-approved`), looks again every $NoBansRetryMin minutes, and starts the
#   lead once the bans are on main. A version restart of a running lead (restart-leads.ps1) is skipped the same
#   way and the lead keeps running.
# - A task session that a project lead registered as active (<DevKitStateDir>\<repo>-<hash>\sessions.json,
#   not a lead) and that Claude Code closed is brought back by `claude respawn <id>`. It is closed when
#   it is in `claude agents --json --all` with no pid and its state is not stopped (plugins/dev-kit/claude-facts.md,
#   "Other sessions listed as `blocked` or `done` in `claude agents --json`"), or its state is stopped and
#   ~\.claude\daemon.log (last 2000 lines) has a `bg retire <id>` line after the last `bg spawned <id>`
#   line (plugins/dev-kit/claude-facts.md, "Claude closes an idle background session after 8 h of waiting, 1 h
#   without Remote Control": a plain `claude stop` writes no retire line, so it is left alone). Two rounds in a row:
#   HEAL-TASK (the same hold file pauses it; HEAL-TASK-FAILED when the command exits with an error). At
#   most $MaxHeals respawns per hour per session, then GIVEUP-TASK (once, until it is seen alive again).
#   The lead's own watcher (dev-kit-sessions watch) waits 300 s before it calls such a session gone,
#   so this watcher gets its chance first.
# - A live lead of the list or active task session that stopped on the usage limit (5-hour or weekly) keeps
#   its process and shows as blocked (plugins/dev-kit/claude-facts.md, "Other sessions listed as `blocked` or `done` in `claude agents --json`"), so it looks alive: LIMIT <name> <session id> (resets <time>) once per
#   stop, LIMIT-END when it goes on or is no longer live (a new watcher run logs a stop again). Its transcript tells (`sessions.py limited`, one call per round).
#   A respawn or restart would hit the same limit, and the session would wait for a message until the owner writes.
#   So once the reset time has passed by $LimitGraceSec s (at once when it is unknown), the watcher sends it one
#   message by the one-shot sender of the wakes below: `[EVT-<id>] Pult server watcher: the usage limit that stopped
#   you has reset. ...` (go on with the task). Logged: LIMIT-RESUME <name> <session id> <event id> (try N),
#   LIMIT-RESUME-TAKEN when the id shows in its transcript at once (else the LIMIT-END of a later round tells it went
#   on). Not seen within $WakeConfirmSec s: sent again, at most $WakeMaxTries sends per session, counted on over
#   a new stop that comes with no LIMIT-END between (the resume turn hit the limit again; an unknown reset time
#   then waits $LimitRetrySec s), then LIMIT-RESUME-GIVEUP. A send the sender could not make (the account
#   still limited, no answer) counts no try: LIMIT-RESUME-FAILED <reason> (logged again only when the reason
#   changes), tried again after $LimitRetrySec s; still stopped $LimitFailHours h after the reset: GIVEUP. A name
#   that more than one live session has is not sent to: LIMIT-RESUME-SKIPPED. Like a wake, it sets the target's last
#   wake time and waits while a lead is marked ready. Not with -Once, while on hold or during a full start; the
#   sends of a round stop after $WakeSendBudgetSec s. While a stop is being resumed (not given up), its `limited` event line is not sent to the
#   lead (Invoke-WakePass): the lead hears of it only when the resume gave up. The resume marks live in memory: a
#   new watcher run sends the message again.
# - A dev-kit lock file whose owner is gone is removed: UNLOCK (see Clear-StaleLocks).
# - A lead that runs on an older dev-kit version than the one installed (<DevKitDir>\.claude-plugin\plugin.json)
#   is restarted so it loads the new skills. The same for the other plugins the lead loads (plugin-versions.ps1: the
#   user-scope plugins rules-kit and spend-kit, and the <name>@korov-dev keys, except dev-kit and pult, that are true
#   in <project Path>\.claude\settings.json enabledPlugins; version from plugins\<name>\.claude-plugin\plugin.json
#   next to dev-kit): web-kit, unity-kit. Below "extension" means any of them. The versions each lead process
#   started on are kept by pid and
#   process start time in <StateDir>\lead-versions.json: "version" is the dev-kit one, "ext" holds name ->
#   version of the extensions (LEAD-VERSION on a new entry; a process that started after a plugin.json was
#   last written gets the installed version, else "older"). An old entry with no "ext" adopts the installed
#   extension versions (no restart on upgrade), and so does an extension that has no stored version yet.
#   A lead that started on dev-kit $WakeMinDevKit or later keeps no session watcher (see the wakes below); for it
#   "idle" below also needs no task session of its registry live and busy (a restart would lose that session's
#   reports; Get-BusyTask). Restarts go through restart-leads.ps1 (-Name, or -Ready for a ready mark): RESTART-LEAD
#   <name> (<changed plugins>, <how>).
#   An extension is never asked of a lead (the skill knows only dev-kit versions, a wake-up is a paid turn, and -Ask
#   writes no request for it): a lead stale only in extensions is restarted by the release rules below, a busy one
#   also when `restart status` says `ready V <seconds>` with V the installed dev-kit and
#   less than 10 minutes (how: ready; a ready mark older or for another version is cleared: READY-EXPIRED).
#   Stale in any plugin (owner's rules, plans/update-timing.md): each release is marked critical or routine in the
#   plugin's own releases.json (<DevKitDir>\releases.json, plugins\<name>\releases.json; the agent that bumps the
#   version adds it; missing counts as routine). Per lead, pid and installed versions the watcher asks, for each
#   changed plugin, `sessions.py release --from <started version> --to <installed> --file <its releases.json>
#   --started <process start>` once (RELEASE-KIND <name> (dev-kit X -> V; web-kit X -> Y): critical <version>:
#   <reason> | routine); one critical mark makes the change critical. The entry keeps
#   "staleSince", the local date this watcher first saw that pid stale in any plugin (a new pid starts fresh).
#   - A `ready V <seconds>` mark for the installed V (the lead itself, or restart-leads.ps1 -Ask) is honoured
#     whatever the kind, with less than 10 minutes: the lead wrote its 30-second warning into its chat just before
#     it marked itself ready, so a mark younger than $ReadyWarnSec s is waited out inside the round first; then
#     -Ready (how: ready). An older mark or one for another version: cleared, READY-EXPIRED (a stale mark for V is
#     asked again with `restart request`).
#   - Quiet means: status idle, no busy task session (as above) and `sessions.py quiet --id <session id>` says
#     quiet (the owner wrote nothing to the lead for 5 minutes and its last text to the owner is no open question).
#   - Routine: no restart and no request on the staleSince day (RESTART-DEFERRED <name> (dev-kit X -> V, routine,
#     until a later day), once per lead and V). On a later day it is restarted at its first quiet round (how: quiet),
#     onto the newest version; until then it waits in silence. A routine release is never asked for.
#   - Critical: quiet: restarted at once, silently (how: critical, quiet). Not quiet: a lead woken by message with
#     no open request for V gets `restart request --version V` (RESTART-ASKED <name> (dev-kit X -> V, critical,
#     <busy | idle, <task> working | owner active | open question | no transcript>), once; the `restart` event of the
#     wakes then reaches it): it finishes its step, writes the 30-second warning into its chat and marks itself
#     ready, which the ready mark above handles. An older lead (below $WakeMinDevKit; its own session watcher
#     exits 7 on a request of -Ask) is restarted only when quiet.
#   - A critical release with an extension changed too, or in an extension only (never asked): a lead that is not
#     quiet but idle is restarted at once (how: idle); any restart takes the pending versions of every plugin with it.
#   restart.json is cleared after a restart and after a failure, and a lead already on the installed versions has a
#   left-over one cleared (RESTART-CLEARED; checked once per pid). One try per lead per combined version (dev-kit
#   plus extensions); a failure is logged as RESTART-LEAD-FAILED (RESTART-LEAD-TIMEOUT for a run cut at its bound, see
#   HEAL above). The hold file and a running full start pause it,
#   as for HEAL (staleSince is still recorded).
# - Wakes: no Claude session keeps a watcher of its own (plugins/dev-kit/claude-facts.md, "The host kills a
#   background Bash run after 2 hours"); this watcher wakes Pult and the leads by a cross-session message only when
#   something needs them. A pass after the heal work each round (not with -Once):
#   - Lead events: for each lead of the list with a Path that is live and whose process started on dev-kit
#     $WakeMinDevKit or later (lead-versions.json; "older" counts as below), `sessions.py --project <Path> check`
#     (the round's session list passed in env DEV_KIT_AGENTS_JSON) prints the events not delivered yet (gone,
#     finished, limited, stale, fill, restart, handoff); each becomes a line for that lead (as the old watcher printed
#     it, `<kind>: <name> | <id> | <detail>`, or `restart requested: <V>`, or `handoff requested: <file>`) with a
#     `sessions.py mark` call run after delivery. A lead below that version keeps its own watcher and is skipped.
#   - Pult events: each GIVEUP, GIVEUP-TASK, RESTART-LEAD-FAILED, RESTART-LEAD-TIMEOUT, HANDOFF-FAILED and HANDOFF-TIMEOUT line also goes to Pult (the session list entry
#     named exactly Pult, kind interactive). Once ever (wake-state.json), when Pult is live, it is told that its
#     log watcher (watch-log.py) is retired and must not be armed again.
#   - Keep-warm ping: a lead (version as above) that is live and idle, has a non-owner task session of its registry
#     that is live and busy (status busy or state working), whose transcript was last written $PingQuietMin or
#     more minutes ago and that got no wake for as long, gets `$PingLine`. Not when a wake for it is pending: an
#     event message wakes it anyway.
#   - Size: each round one `sessions.py size` call for the live leads, live task sessions and Pult. A session at
#     $SizePushShare of its window or more gets one phone push (once per session id, wake-state.json):
#     PUSH-SIZE; all the sessions that pass it in one round share one push. Every $SizeLogMin minutes the call takes `--wakes <StateDir>\size-state.json` and each session
#     is logged: SIZE <name> <session id> <tokens> owner=N peer=N notify=N units=U.
#   - Weekly limit forecast (plans/limit-tracking.md): when the usage log of the status line (usage-log.jsonl in the
#     folder of env DEV_KIT_USAGE_LOG, else ~\.claude\spend-kit) changed since the last look, or task sessions opened or
#     all closed (first look at start; the last look is kept in memory only, the mark stops a second push), one
#     `<SpendKitDir>\scripts\usage_forecast.py check --open <live task sessions of the leads' registries> --mark <StateDir>\limit-forecast.json`
#     call (the forecast, the "open tasks" test and the once-per-weekly-window mark are its own; see its doc). On `push`
#     it logs LIMIT-FORECAST runout=<local time> resets=<local time> pct=<last %> pace=<%/h> and queues one phone push
#     (cause limit) with its text, delivered like a size push. After it nothing is paused or asked.
#   The lines of one target are merged into one message (`[EVT-<id>] Pult server watcher:`, the lines, one fixed
#   instruction line; control characters removed, each line cut at 300 characters, at most about 1500 per
#   message, more lines wait for the next one), kept in <StateDir>\wake-pending.json until delivered. At most
#   one message per target per round and one in flight per target, none within $WakeCooldownSec s of the last
#   send to it, none while on hold or during a full start (the hold file is looked at again before each send),
#   none to a lead whose `restart status` says ready (its -Ready restart would cut the turn handling the message;
#   it waits until after the restart). The sends of a round stop after $WakeSendBudgetSec s; the rest wait for
#   the next round. The output of every python call is read as UTF-8 (Cyrillic names). Send-Wake runs one
#   hidden one-shot `claude -p` (haiku, safe mode, only the SendMessage tool, permission mode bypassPermissions, the
#   one mode of every session of the plugin; plugins/dev-kit/claude-facts.md, "A one-shot `claude -p` delivers a
#   message into a running session") in <StateDir>\wake, the
#   prompt by stdin; it is stopped after $WakeWaitSec s; its json `result` says sent or failed. Logged: WAKE
#   <target> <id> cause=event|ping|note kinds=<kinds> (first send), WAKE-SENT, WAKE-FAILED <reason>. A message
#   is delivered when `[EVT-<id>]` shows in the tail of the target's transcript (Find-Transcript: the linkScanPath of
#   the session's job in <jobs>\*\state.json whose sessionId or resumeSessionId is the id, env DEV_KIT_JOBS_DIR or
#   ~\.claude\jobs: a /clear keeps the job but writes a new file, whose id the session list then shows; else <projects>\*\<session id>.jsonl, env DEV_KIT_PROJECTS_DIR or ~\.claude\projects;
#   sessions.py finds transcripts the same way): WAKE-TAKEN <target> <id> (<s> s), then the marks run. Not
#   seen within $WakeConfirmSec s: sent again, at most $WakeMaxTries times; a target not live sends nothing.
#   After that, or after $WakeDownSec s not live: WAKE-FALLBACK, and the event lines go to the phone (a lead's:
#   «<lead> не взяв повідомлення» or «<lead> не на зв'язку»; Pult's: «Pult не піднявся - запусти його на
#   комп'ютері»; and the events; under 200 characters). A phone push is never a one-shot's own PushNotification:
#   a fresh session's push is refused (plugins/dev-kit/claude-facts.md, "A push from a fresh session is
#   refused"). So it is a message (`[EVT-<id>] Pult server watcher: phone push
#   request.`, then the instruction to call PushNotification once with the next line and write nothing else,
#   then the text) to a relay: Pult when it is live, else a live lead (an idle one first, any version, its MODE
#   line for the mode, not one marked ready), never the session that did not take the original message (so a
#   lead's fallback goes to Pult first). Logged: WAKE-SENT / WAKE-FAILED phone <id> via <relay>, WAKE-TAKEN phone
#   <id> via <relay> (delivery as above; then the marks run). No relay live: WAKE-FALLBACK-NONE, tried again
#   after $PhoneRetrySec s. Not taken: sent again after $WakeConfirmSec s, after $WakeMaxTries sends every
#   $PhoneRetrySec s (a size push too); events are never dropped. A ping or the Pult note that is not taken is
#   dropped (WAKE-FAILED).
#   The keep-warm ping is not sent to a lead that has a handoff marker (see the next item); events still are.
# - A lead whose context is a third full saves a handoff file and a marker (`sessions.py handoff save --file <name.md>
#   [--go]`, handoff.json next to its registry; the project-lead skill's "Restart P"). A pass after its version check
#   each round (Invoke-HandoffCheck; not with -Once, not while the hold file or a full start runs, not while NO-BANS
#   blocks that lead) reads `handoff status` for each live lead: none (the in-memory marks of that lead are dropped) or
#   `saved <file> <s>` (seconds since the save) / `go <file> <s>` (seconds since `handoff go`). The move works like a
#   release restart, with no question to the owner (plans/lead-self-move.md; Get-HandoffWhy):
#   - `saved`: moved silently when the lead is quiet as for a release restart (status idle, no busy task session,
#     `sessions.py quiet` says quiet; Get-LeadActivity) and no message was sent to it for $HandoffWakeQuietSec s
#     (wake-state.json LastWake: a just-sent message is not handled yet). Busy or just woken: it waits. Not quiet for
#     another reason (a task working, owner active, open question, no transcript): a lead woken by message is asked
#     once (`sessions.py handoff request`; HANDOFF-ASKED <name> <file> (<reason>) when newly asked; the `handoff` event
#     of the wakes then reaches it as `handoff requested: <file>`): it brings its step to a safe point, writes its
#     30-second warning into its chat and runs `handoff go`. While the owner keeps writing, the move waits.
#   - `go` (the lead after its warning, or on the owner's word): moved once the lead is idle and $ReadyWarnSec s have
#     passed since the go (the rest is waited out inside the round); the message quiet does not apply and a go never
#     expires.
#   Not moved yet: HANDOFF-WAIT <name> <file> once per marker. To move: the hard-ban gate is checked first (resume-lib.ps1
#   Get-LeadPermissionMode; a lead that could not be started again is not stopped: NO-BANS as for a restart), then the
#   session list is read again right before the stop (a local copy; the lead must still be live with the same short id,
#   the job's, which stays while the sessionId the list shows changes with each move, and pass the same check), then
#   `claude stop <short id>` and a wait up to $HandoffStopWaitSec s until no background
#   entry of that name has a pid and no claude.exe process holds one of its ids (Get-SessionProcessIds,
#   Get-JobSessionIds). Then `start-servers.ps1 -Only <name> -Handoff <file> -HandoffSessionId <session id>` (the id the
#   list shows; start-servers.ps1 resumes by the job's own id) moves it
#   without a new session, so no phone push (plans/push-noise.md): /clear, then a resume with the handoff prompt; on
#   any failure it logs HANDOFF-FALLBACK <name> <reason> and starts a fresh lead (one push; see start-servers.ps1). No
#   session id: HANDOFF-FALLBACK <name> no session id, and the fresh start at once. `Resumed lead: <name>` (moved) or
#   `Started lead: <name>` (fresh): `handoff clear`, LastWake of the lead set to now, the `handoff requested` lines of
#   its pending messages dropped, sent but not seen ones too (Remove-HandoffLines), then HANDOFF-CLEAR <name> <session id before the move> <file> (moved; the
#   size push mark of that id is dropped, the list shows a new id from now on) or HANDOFF <name> <old session id> <file>
#   (fresh). Lookups by the list's sessionId (transcripts, size, quiet, limits) follow the new id through the job state.
#   `NO-BANS <name> `: Register-NoBans. Any other output: Write-Critical HANDOFF-FAILED <name>: <output> (Pult gets it);
#   a stop that did not finish in time: HANDOFF-FAILED <name>: still running after the stop. A start-servers.ps1 run
#   still going after $HandoffMoveWaitSec s (a hung /clear, resume or fresh start) is stopped with its child processes
#   (Invoke-Bounded) and logged by Write-Critical as HANDOFF-TIMEOUT <name> (Pult gets it); it is a failed move. A failed move keeps the marker and is
#   not tried again for that marker until the watcher restarts (in memory, key name and file; a new file name, or a
#   marker that was cleared and saved again, is a new try); the next round's HEAL brings an old lead that is down
#   back as for any dead lead. After the stop the round's session list is read again, so the rest of the round sees
#   the new lead.
# - Its own code: it takes a fingerprint (SHA-256) of this script and the scripts it dot-sources
#   (plugin-versions.ps1, resume-lib.ps1) at start. When the fingerprint differs and was the same in the previous round
#   (the file is stable, not in the middle of a git merge), the new files are parse-checked: with a parse
#   error WATCH-RESTART-SKIPPED <reason> is logged once (it tries again only when the fingerprint changes
#   again); otherwise WATCH-RESTART <old pult version> -> <new> (pult plugin.json; version+short hash when
#   the versions are equal) is logged, a fresh copy is started the way start-servers.ps1 starts it (hidden,
#   the same parameters) and this one exits, but only after the new copy wrote its own "WATCH started" line
#   (waits up to 20 s; WATCH-RESTART is logged then, after that line). A copy that exits or stays silent is
#   stopped if it still runs and WATCH-RESTART-SKIPPED <reason> is logged: this copy keeps running the old
#   code and tries again only when the fingerprint changes. Checked at the end of a round, never while a full start-servers.ps1
#   run is going on; a hold file does not stop it. The watcher has no single-instance guard of its own
#   (start-servers.ps1 only looks for a running one), so nothing is released. State kept in memory only is
#   lost: HEAL/HEAL-TASK try counts and GIVEUP marks (a still-down entry gets up to $MaxHeals more tries), the
#   one-try-per-version marks of leads (a failed lead restart is tried once more), the usage-limit marks (LIMIT
#   is logged again) and the "seen" lists (STATE lines again, as at any start). The wake files stay on disk and
#   the new copy goes on with them: wake-pending.json (undelivered messages and their marks), wake-state.json
#   (the Pult note, the size pushes, the last send per target), size-state.json (the `size --wakes` offsets) and
#   limit-forecast.json (the weekly window already pushed);
#   only the time of the last SIZE lines is lost (they are logged again at once).
# start-servers.ps1 starts it at logon in a hidden window. -Once: one check, then exit; -Rounds N:
# N checks, then exit (both for tests; -Once never restarts anything, touches restart.json or wakes anyone).
# -RestartExe: the program that starts the new copy (default powershell.exe; for tests).
# -WakeExe: the program of the one-shot sender (default: claude from PATH); -SessionsPy: the sessions.py it calls
# (default: <DevKitDir>\scripts\sessions.py); -WakeConfirmSec, -WakeCooldownSec, -WakeDownSec: the waits of the
# wakes; -HandoffStopWaitSec: the wait for a stopped lead to be gone; -HandoffClearWaitSec: the wait for the /clear turn
# of a handoff move to end (default 120; both passed on to start-servers.ps1); -ReadyWarnSec: the age a ready mark or a
# handoff go must reach before its restart or move (default 30, the lead's warning; all for tests). -HealWaitSec: the
# longest a HEAL or HEAL-TASK run may take (default 300; for tests). -LeadRestartWaitSec: the longest a restart-leads.ps1 run
# may take (default 600: its wait for the stopped lead, up to 60 s, plus a full start; for tests). -HandoffMoveWaitSec:
# the longest the start-servers.ps1 -Handoff run of a handoff move may take (default 600: the /clear wait, up to 120 s,
# two stop waits, up to 60 s each, and the fallback's fresh start; for tests).
# -ConfigFile / -StateDir / -DevKitStateDir / -DaemonLog: another server list, Pult state folder,
# dev-kit state folder and Claude Code daemon log (for tests with a throwaway lead).
# -LimitGraceSec: the wait after a usage-limit reset before the resume message (default 180; the reset time is cut to
# the minute); -LimitRetrySec: the wait after a resume send the sender could not make (default 900; both for tests).
# -DevKitDir: the dev-kit plugin folder (default: ..\..\dev-kit next to this plugin); it holds
# .claude-plugin\plugin.json (the installed version) and scripts\sessions.py.
# -SpendKitDir: the spend-kit plugin folder (default: ..\..\spend-kit next to this plugin); it holds
# scripts\usage_forecast.py, which the weekly limit forecast runs.
# Keep this file saved as UTF-8 with BOM (plugins/dev-kit/claude-facts.md, "Windows PowerShell 5.1 misreads
# Cyrillic in a script saved without a BOM").
param([int]$IntervalSec = 60, [switch]$Once, [int]$Rounds = 0, [int]$MaxHeals = 3,
    [string]$ConfigFile, [string]$StateDir, [string]$DevKitStateDir, [string]$DaemonLog, [string]$DevKitDir,
    [string]$SpendKitDir, [string]$RestartExe = 'powershell.exe', [string]$WakeExe, [string]$SessionsPy,
    [int]$WakeConfirmSec = 120, [int]$WakeCooldownSec = 120, [int]$WakeDownSec = 600, [int]$HandoffStopWaitSec = 60,
    [int]$ReadyWarnSec = 30, [int]$HandoffClearWaitSec = 120, [int]$HealWaitSec = 300, [int]$LeadRestartWaitSec = 600,
    [int]$HandoffMoveWaitSec = 600, [int]$LimitGraceSec = 180, [int]$LimitRetrySec = 900)

. (Join-Path $PSScriptRoot 'plugin-versions.ps1')
. (Join-Path $PSScriptRoot 'resume-lib.ps1')  # Get-SessionProcessIds, Get-JobState, Get-LeadPermissionMode, $HandoffNamePattern
$scriptParams = @{} + $PSBoundParameters  # what the new copy gets on a WATCH-RESTART
$CodeFiles = @($PSCommandPath, (Join-Path $PSScriptRoot 'plugin-versions.ps1'), (Join-Path $PSScriptRoot 'resume-lib.ps1'))  # this script and what it dot-sources

if (-not $DaemonLog) { $DaemonLog = Join-Path $env:USERPROFILE '.claude\daemon.log' }
if (-not $DevKitDir) { $DevKitDir = Join-Path $PSScriptRoot '..\..\dev-kit' }
$DevKitDir = [IO.Path]::GetFullPath($DevKitDir)
if (-not $SpendKitDir) { $SpendKitDir = Join-Path $PSScriptRoot '..\..\spend-kit' }
$SpendKitDir = [IO.Path]::GetFullPath($SpendKitDir)
if (-not $SessionsPy) { $SessionsPy = Join-Path $DevKitDir 'scripts\sessions.py' }
if (-not $WakeExe) {  # an Application: claude.exe or claude.cmd, never the npm claude.ps1 that Start-Process cannot run
    $WakeExe = [string](Get-Command claude -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
}
# The claude program for `claude respawn` (Invoke-Bounded needs a file, not the PowerShell command lookup).
$ClaudeExe = [string](Get-Command claude -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if (-not $ClaudeExe) { $ClaudeExe = 'claude' }
$WakeMinDevKit = '0.1.78'  # a lead that started on this dev-kit or later keeps no session watcher: it is woken by message
$NoBansRetryMin = 10       # a lead blocked by missing hard bans is looked at again after this
$WakeMode = 'bypassPermissions' # the one permission mode of every session of the plugin (the sender's too)
# The Pult hub's own session runs in auto mode, whatever the server's --permission-mode, and holds (never takes) a
# message from a bypassPermissions sender; one from a default-mode sender it takes (seen 2026-11-23, plans/wake-check.md).
$PultWakeMode = 'default'
$WakeMaxTries = 3         # sends of one message before the phone fallback
$WakeWaitSec = 60          # a one-shot sender still running after this is stopped
$PhoneRetrySec = 600       # a failed phone push is tried again after this
$WakeSendBudgetSec = 180   # the sends of one round stop after this; the rest wait for the next round
$LimitFailHours = 12       # a usage-limit resume whose sender made no send this long after the reset gives up
$PingQuietMin = 50         # a lead with a busy task session silent this long gets the keep-warm ping
$HandoffWakeQuietSec = 120 # a lead that saved a handoff (not go) is moved only when it was last sent a message at least this long ago (a just-sent one is not handled yet)
$SizePushShare = 0.7       # a conversation at this share of its window gets one phone push
$SizeLogMin = 10           # minutes between the SIZE lines
$PingLine = 'PING keep-warm: run dev-kit-sessions fill for your C sessions and dev-kit-sessions fill --self for yourself, then answer with your standard status only.'
$NoteLine = 'Note: your log watcher (watch-log.py) is retired. Events now arrive as messages from the server watcher, like this one, so do not arm it again.'

if (-not $ConfigFile) { $ConfigFile = Join-Path $PSScriptRoot 'servers.psd1' }
if (-not $StateDir) { $StateDir = Join-Path $env:USERPROFILE '.claude\pult' }  # outside the plugin folder
if (-not $DevKitStateDir) {
    $DevKitStateDir = if ($env:DEV_KIT_STATE_DIR) { $env:DEV_KIT_STATE_DIR } else { Join-Path $env:USERPROFILE '.claude\dev-kit' }
}
$servers = (Import-PowerShellDataFile $ConfigFile).Servers
$logDir = Join-Path $StateDir 'logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir 'servers.log'
$hold = Join-Path $StateDir 'hold'

function Write-Log($msg) {
    if ((Test-Path $log) -and (Get-Item $log).Length -gt 1MB) {
        Move-Item -Force $log "$log.old"
    }
    Add-Content -LiteralPath $log -Encoding UTF8 -Value ('{0} {1}' -f (Get-Date -Format s), $msg)
}

# The parsed session list, or $null; $script:agentsText keeps the text as read (the wakes pass it to sessions.py).
function Get-Agents([switch]$All) {
    $script:agentsText = $null
    try {
        $out = if ($All) { claude agents --json --all } else { claude agents --json }
        $text = $out | Out-String
        $list = @($text | ConvertFrom-Json)
        $script:agentsText = $text
        return $list
    } catch {
        Write-Log "WARN cannot list background sessions: $_"
        return $null
    }
}

# Logs "WARN <text>" unless the same text was the last one logged for $Key (a failure repeated every round).
function Write-WarnOnce([string]$Key, [string]$Text) {
    if ($warnedOnce[$Key] -cne $Text) { Write-Log "WARN $Text"; $warnedOnce[$Key] = $Text }
}

# Logs a critical line (GIVEUP, GIVEUP-TASK, RESTART-LEAD-FAILED, RESTART-LEAD-TIMEOUT, HANDOFF-FAILED, HANDOFF-TIMEOUT); the wake pass of the round sends it to Pult.
function Write-Critical([string]$Msg) {
    Write-Log $Msg
    [void]$pultEvents.Add($Msg)
}

# A lead blocked because its project has no hard-ban lines on main (start-servers.ps1 and restart-leads.ps1 print
# `NO-BANS <name> (<reason>)`): not an error and not a HEAL failure. No start or restart of it is tried for
# $NoBansRetryMin minutes (then the gate runs again, so bans added meanwhile let it start). The owner is told once
# (Write-Critical: log line and a message to Pult), until the lead is started or restarted again.
function Register-NoBans([string]$Name, [string]$Said) {
    $reason = if ($Said -cmatch ('NO-BANS ' + [regex]::Escape($Name) + ' \(([^)]*)\)')) { $Matches[1] } else { 'no hard-ban lines on main' }
    $noBansUntil[$Name] = (Get-Date).AddMinutes($NoBansRetryMin)
    if (-not $noBansTold[$Name]) {
        $noBansTold[$Name] = $true
        # The hub prepares the set and shows it; on the owner's yes it writes .claude/hard-bans.json in the project's
        # main checkout and runs this command itself.
        $path = [string](@($servers | Where-Object { $_.Session -ceq $Name } | Select-Object -First 1).Path)
        $bin = ($DevKitDir -replace '\\', '/') + '/bin/dev-kit-bans'
        $cmd = if ($path) { "python `"$bin`" add-approved `"$($path -replace '\\', '/')`"" } else { "python `"$bin`" add-approved <project path>" }
        Write-Critical "NO-BANS $Name ($reason): not started. Hub: show the owner the exact lines, on his yes write .claude/hard-bans.json in the project's main checkout and run: $cmd"
    }
}

# Runs python with $PyArgs and returns @{ Code; Out } (stdout, and stderr unless -NoStderr). The output is read as
# UTF-8 (env PYTHONIOENCODING and [Console]::OutputEncoding, both restored after; plugins/dev-kit/claude-facts.md,
# "Windows PowerShell decodes a native program's output with the console code page").
function Invoke-Python([string[]]$PyArgs, [switch]$NoStderr) {
    $oldEnc = $null; $oldIo = $env:PYTHONIOENCODING
    $env:PYTHONIOENCODING = 'utf-8'
    try { $oldEnc = [Console]::OutputEncoding; [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false } catch { }
    try {
        if ($NoStderr) { $out = & python @PyArgs 2>$null | Out-String } else { $out = & python @PyArgs 2>&1 | Out-String }
        $code = $LASTEXITCODE
    } catch { $out = "$_"; $code = -1 } finally {
        if ($oldEnc) { try { [Console]::OutputEncoding = $oldEnc } catch { } }
        $env:PYTHONIOENCODING = $oldIo
    }
    return @{ Code = $code; Out = [string]$out }
}

# Runs sessions.py (-SessionsPy) with env DEV_KIT_STATE_DIR = the dev-kit state folder of this watcher and, when
# given, DEV_KIT_AGENTS_JSON = a file with the session list. Returns @{ Code; Out } (stdout and stderr, trimmed).
function Invoke-Sessions([string[]]$Words, [string]$AgentsFile) {
    $oldState = $env:DEV_KIT_STATE_DIR; $oldAgents = $env:DEV_KIT_AGENTS_JSON
    $env:DEV_KIT_STATE_DIR = $DevKitStateDir
    if ($AgentsFile) { $env:DEV_KIT_AGENTS_JSON = $AgentsFile }
    try { $r = Invoke-Python (@($SessionsPy) + $Words) }
    finally { $env:DEV_KIT_STATE_DIR = $oldState; $env:DEV_KIT_AGENTS_JSON = $oldAgents }
    return @{ Code = $r.Code; Out = $r.Out.Trim() }
}

function Test-PidAlive([int]$Id, [string]$NameLike = '*') {
    $p = Get-Process -Id $Id -ErrorAction SilentlyContinue
    return [bool]($p -and $p.ProcessName -like $NameLike)
}

# One argument for a Windows command line (the quoting CommandLineToArgvW reads back).
function ConvertTo-ArgText([string]$Text) {
    if ($Text -and $Text -notmatch '[\s"]') { return $Text }
    $q = $Text -replace '(\\*)"', '$1$1\"'
    $q = $q -replace '(\\+)$', '$1$1'
    return '"' + $q + '"'
}

# Stops process $RootId and its child processes, except a long-lived one that a run may start and must keep: a
# Remote Control server (its window), Claude's background service (`claude daemon run`, which a `claude --bg` starts
# when none runs) and a background session's host. Their own children are left too.
function Stop-ProcessTree([int]$RootId) {
    $all = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
    $seen = @{}; $kill = @(); $queue = @($RootId)
    while ($queue.Count) {
        $next = @()
        foreach ($id in $queue) {
            if ($seen[$id]) { continue }
            $seen[$id] = $true; $kill += $id
            foreach ($c in @($all | Where-Object { $_.ParentProcessId -eq $id -and $_.ProcessId -ne $id })) {
                if ([string]$c.CommandLine -match '\sremote-control\s|\sdaemon\s+run\b|--bg-pty-host') { continue }
                $next += [int]$c.ProcessId
            }
        }
        $queue = $next
    }
    foreach ($id in $kill) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
}

# Runs $File with $ArgList and waits up to $WaitSec s: @{ Out; Code; TimedOut } (Out: stdout and stderr). A run
# still going then is stopped (Stop-ProcessTree). The output goes to temp files, not a pipe: a child process that
# outlives the run and keeps the handle cannot hold the call open.
function Invoke-Bounded([string]$File, [string[]]$ArgList, [int]$WaitSec) {
    $outFile = [IO.Path]::GetTempFileName(); $errFile = [IO.Path]::GetTempFileName()
    try {
        $line = (@($ArgList | ForEach-Object { ConvertTo-ArgText $_ }) -join ' ')
        $p = Start-Process -FilePath $File -ArgumentList $line -NoNewWindow -PassThru `
            -RedirectStandardOutput $outFile -RedirectStandardError $errFile
        $null = $p.Handle  # Windows PowerShell 5.1 leaves ExitCode empty unless the handle was taken
        $timedOut = -not $p.WaitForExit([Math]::Max(1, $WaitSec) * 1000)
        if ($timedOut) { Stop-ProcessTree $p.Id; $null = $p.WaitForExit(5000) }  # gone before the caller looks at it
        # Shared read: a child that outlives the run may still hold the file open. The child writes in the console's
        # code page, as the old pipe read it.
        $out = (@($outFile, $errFile | ForEach-Object {
            try {
                $fs = [IO.File]::Open($_, 'Open', 'Read', 'ReadWrite')
                try { (New-Object IO.StreamReader($fs, [Console]::OutputEncoding)).ReadToEnd() } finally { $fs.Dispose() }
            } catch { '' } }) -join "`n")
        return @{ Out = $out; Code = $(if ($timedOut) { -1 } else { [int]$p.ExitCode }); TimedOut = $timedOut }
    } finally { Remove-Item -LiteralPath $outFile, $errFile -Force -ErrorAction SilentlyContinue }
}

# Removes the hold file when restart-leads.ps1 left it and its process is gone (see the header: HOLD-STALE).
function Clear-StaleHold {
    if (-not (Test-Path -LiteralPath $hold)) { return }
    $text = ''
    try { $text = (Get-Content -Raw -LiteralPath $hold -ErrorAction Stop).Trim() } catch { return }
    if ($text -cnotmatch '^restart-leads\.ps1 (\S+) pid (\d+)$') { return }
    $at = [datetime]::MinValue
    if (-not [datetime]::TryParseExact($Matches[1], 's', [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::None, [ref]$at)) { return }
    $proc = Get-Process -Id ([int]$Matches[2]) -ErrorAction SilentlyContinue
    if ($proc) {
        $started = $null
        try { $started = $proc.StartTime } catch { return }  # cannot tell: leave it
        if ($started -le $at.AddSeconds(1)) { return }  # the script still runs
    }
    Remove-Item -LiteralPath $hold -Force -ErrorAction SilentlyContinue
    if (-not (Test-Path -LiteralPath $hold)) { Write-Log "HOLD-STALE ($text): removed, its restart-leads.ps1 run is gone" }
}

# Lock files dev-kit leaves in <DevKitStateDir>\<repo>-<hash>\ (dev_kit_state.py). Each is removed
# only when its owner is surely gone; the dev-kit code itself takes most of them over later anyway.
# - watch.lock {"pid", "beat"} (sessions.py watch): its python process is gone and the beat is older
#   than 180 s (the code's own stale age for the default interval).
# - app.lock {"worktree", ...} (run_app.py): its worktree folder no longer exists. The pid in it is
#   the short-lived `dev-kit-app start` process, so it says nothing; a lock of a live worktree is
#   left to the code's own age limit.
# - app.lock.takeover: older than 60 s (the code's own limit).
# - *.<pid>.tmp (half-written app.lock or sessions.json): the pid is gone and the file is older
#   than 5 minutes.
function Clear-StaleLocks {
    if (-not (Test-Path $DevKitStateDir)) { return }
    $now = Get-Date
    foreach ($dir in Get-ChildItem -LiteralPath $DevKitStateDir -Directory -ErrorAction SilentlyContinue) {
        $f = Join-Path $dir.FullName 'watch.lock'
        if (Test-Path -LiteralPath $f) {
            try {
                $j = Get-Content -Raw -LiteralPath $f | ConvertFrom-Json
                $age = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000 - [double]$j.beat
                if ($age -gt 180 -and -not (Test-PidAlive ([int]$j.pid) 'python*')) {
                    Remove-Item -LiteralPath $f -Force
                    Write-Log ("UNLOCK {0}\watch.lock (pid {1} gone, beat {2:N0} s old)" -f $dir.Name, $j.pid, $age)
                }
            } catch { Write-Log "WARN cannot read $f : $_" }
        }
        $f = Join-Path $dir.FullName 'app.lock'
        if (Test-Path -LiteralPath $f) {
            try {
                $j = Get-Content -Raw -LiteralPath $f | ConvertFrom-Json
                if ($j.worktree -and -not (Test-Path -LiteralPath $j.worktree)) {
                    Remove-Item -LiteralPath $f -Force
                    Write-Log "UNLOCK $($dir.Name)\app.lock (worktree $($j.worktree) is gone)"
                }
            } catch { Write-Log "WARN cannot read $f : $_" }
        }
        $f = Get-Item -LiteralPath (Join-Path $dir.FullName 'app.lock.takeover') -ErrorAction SilentlyContinue
        if ($f -and ($now - $f.LastWriteTime).TotalSeconds -gt 60) {
            Remove-Item -LiteralPath $f.FullName -Force
            Write-Log "UNLOCK $($dir.Name)\app.lock.takeover (older than 60 s)"
        }
        foreach ($t in Get-ChildItem -LiteralPath $dir.FullName -Filter '*.tmp' -File -ErrorAction SilentlyContinue) {
            if ($t.Name -notmatch '^(app\.lock|sessions\.json)\.(\d+)\.tmp$') { continue }
            if (($now - $t.LastWriteTime).TotalMinutes -gt 5 -and -not (Test-PidAlive ([int]$Matches[2]))) {
                Remove-Item -LiteralPath $t.FullName -Force
                Write-Log "UNLOCK $($dir.Name)\$($t.Name) (pid gone, older than 5 min)"
            }
        }
    }
}

function Test-IdMatch([string]$AgentId, [string]$Wanted) {  # as sessions.py `matches`
    return ($AgentId -ceq $Wanted) -or ($Wanted.Length -ge 8 -and $AgentId.StartsWith($Wanted, [StringComparison]::Ordinal))
}

# Respawns the task sessions (see the header) that Claude Code closed. Uses $agents of the round
# (claude agents --json --all); nothing is done when that list is unknown.
function Invoke-TaskHeal {
    if ($null -eq $agents -or -not (Test-Path -LiteralPath $DevKitStateDir)) { return }
    # Line numbers of the last `bg retire <id>` and `bg spawned <id>` in the tail of the daemon log.
    $retired = @{}; $spawned = @{}
    if (Test-Path -LiteralPath $DaemonLog) {
        $n = 0
        try {
            foreach ($line in (Get-Content -LiteralPath $DaemonLog -Tail 2000 -Encoding UTF8)) {
                $n++
                if ($line -match '\[bg\] bg (retire|spawned) ([0-9a-f]{8})\b') {
                    if ($Matches[1] -eq 'retire') { $retired[$Matches[2]] = $n } else { $spawned[$Matches[2]] = $n }
                }
            }
        } catch { Write-Log "WARN cannot read $DaemonLog : $_" }
    }
    $seen = @{}
    foreach ($dir in Get-ChildItem -LiteralPath $DevKitStateDir -Directory -ErrorAction SilentlyContinue) {
        $f = Join-Path $dir.FullName 'sessions.json'
        if (-not (Test-Path -LiteralPath $f)) { continue }
        try {
            $records = @(Get-Content -Raw -Encoding UTF8 -LiteralPath $f | ConvertFrom-Json | ForEach-Object { $_ })
        } catch { Write-Log "WARN cannot read $f : $_"; continue }
        foreach ($r in $records) {
            if ($r.status -cne 'active' -or -not $r.id -or $r.owner -eq $true -or ([string]$r.name).StartsWith('P: ', [StringComparison]::Ordinal)) { continue }
            $wid = ([string]$r.id).Trim()  # an id pasted with a CR would match no session
            $seen[$wid] = $true
            $entries = @($agents | Where-Object {
                $_ -and ((Test-IdMatch ([string]$_.sessionId) $wid) -or (Test-IdMatch ([string]$_.id) $wid)) })
            $states = @($entries | ForEach-Object { if ($_.state) { $_.state } else { $_.status } })
            $live = $entries | Where-Object { $_.pid -and $_.sessionId } | Select-Object -First 1
            if ($live) { $liveSessions[[string]$live.sessionId] = [string]$r.name; $liveTasks[[string]$live.sessionId] = [string]$r.name }
            if ($entries | Where-Object { $_.pid }) {  # alive
                $taskClosed.Remove($wid); $taskGaveUp.Remove($wid); continue
            }
            $shortId = ($entries | Where-Object { $_.id } | Select-Object -First 1).id
            if (-not $shortId -and $wid.Length -ge 8) { $shortId = $wid.Substring(0, 8) }
            $shortId = [string]$shortId
            # Stopped is also what a deliberate `claude stop` leaves: closed only if the daemon log shows a retire.
            $retiredByClaude = $retired.ContainsKey($shortId) -and $retired[$shortId] -gt [int]$spawned[$shortId]
            if ($entries.Count -eq 0 -or ($states -contains 'stopped' -and -not $retiredByClaude)) {
                $taskClosed.Remove($wid); continue  # not in the list, or stopped on purpose: not ours to bring back
            }
            if ($onHold -or $Once) { $taskClosed[$wid] = 0; continue }
            $taskClosed[$wid] = [int]$taskClosed[$wid] + 1
            if ($taskClosed[$wid] -lt 2 -or $taskGaveUp[$wid]) { continue }
            if (Test-Path -LiteralPath $hold) { continue }  # a stop began during this round
            $tries = @($taskHeals[$wid] | Where-Object { $_ -and ((Get-Date) - $_).TotalHours -lt 1 })
            if ($tries.Count -ge $MaxHeals) {
                Write-Critical "GIVEUP-TASK $($r.name) $wid ($MaxHeals respawns in the last hour did not keep it up; respawn it by hand)"
                $taskGaveUp[$wid] = $true
                continue
            }
            $taskHeals[$wid] = $tries + @(Get-Date)
            $rid = if ($entries[0].id) { [string]$entries[0].id } else { $wid }
            Write-Log ("HEAL-TASK {0} {1} (closed for {2} rounds, state {3}, try {4} of {5})" -f $r.name, $rid, $taskClosed[$wid], $states[0], ($tries.Count + 1), $MaxHeals)
            $res = Invoke-Bounded $ClaudeExe @('respawn', $rid) $HealWaitSec
            if ($res.TimedOut) {
                Write-Log ("HEAL-TASK-TIMEOUT {0} {1} (no end in {2} s, stopped): {3}" -f $r.name, $rid, $HealWaitSec, ($res.Out.Trim() -replace '\s+', ' '))
            } elseif ($res.Code -ne 0) {
                Write-Log ("HEAL-TASK-FAILED {0} {1} (exit {2}): {3}" -f $r.name, $rid, $res.Code, ($res.Out.Trim() -replace '\s+', ' '))
            }
            $taskClosed[$wid] = 0  # give the respawn two rounds before the next try
        }
    }
    foreach ($k in @($taskClosed.Keys)) { if (-not $seen[$k]) { $taskClosed.Remove($k) } }  # no longer active
}

# Logs the live sessions in $liveSessions (session id -> name: the leads and task sessions of this round) that
# stopped on the usage limit and wakes them after the reset (see the header). $limitSeen keeps the stop already
# logged per session id, $limitResume its resume state.
function Invoke-LimitCheck {
    $ids = @($liveSessions.Keys)
    $now = @{}
    if ($ids.Count) {
        $words = @('limited') + @($ids | ForEach-Object { '--id', $_ })
        $r = Invoke-Python (@($SessionsPy) + $words)
        $out = $r.Out
        if ($r.Code -ne 0) { Write-Log ("WARN usage-limit check failed (exit {0}): {1}" -f $r.Code, ($out.Trim() -replace '\s+', ' ')); return }
        foreach ($line in ($out -split "`r?`n")) {
            $parts = @($line -split ' \| ')
            if ($parts.Count -eq 3) { $now[$parts[0].Trim()] = @{ Resets = $parts[1].Trim(); Key = $parts[2].Trim() } }
        }
    }
    foreach ($id in $now.Keys) {
        if ($limitSeen[$id] -cne $now[$id].Key) {
            Write-Log ("LIMIT {0} {1} (resets {2})" -f $liveSessions[$id], $id, $now[$id].Resets)
            $limitSeen[$id] = $now[$id].Key
            $old = $limitResume[$id]  # a new stop with no LIMIT-END between: the resume turn hit the limit again
            $limitResume[$id] = @{ Name = $liveSessions[$id]; Due = (Get-LimitDue $now[$id].Resets); NextTry = 0.0
                Tries = 0; EvtIds = @(); Sent = 0.0; Done = $false; GaveUp = $false; LastFail = '' }
            if ($old) {  # the sends count on, so a session that keeps hitting the limit is not messaged forever
                $limitResume[$id].Tries = $old.Tries; $limitResume[$id].GaveUp = $old.GaveUp; $limitResume[$id].Done = $old.GaveUp
                if ($now[$id].Resets -eq 'unknown') { $limitResume[$id].Due = (Get-Now) + $LimitRetrySec }
            }
        }
    }
    foreach ($id in @($limitSeen.Keys)) {
        if ($now.ContainsKey($id)) { continue }
        $how = if ($liveSessions.ContainsKey($id)) { $liveSessions[$id] } else { '(no longer live)' }
        Write-Log ("LIMIT-END {0} {1}" -f $how, $id)
        $limitSeen.Remove($id)
        $limitResume.Remove($id)
    }
    if (-not $Once -and -not $onHold -and -not $starting) { Invoke-LimitResume }
}

# Epoch seconds when a stop whose reset time is $Resets (`sessions.py limited`: local 'yyyy-MM-dd HH:mm' or
# 'unknown') is due for its resume message: a minute after it (the text is cut to the minute) plus $LimitGraceSec;
# now when the time is unknown.
function Get-LimitDue([string]$Resets) {
    $t = [datetime]::MinValue
    if (-not [datetime]::TryParseExact($Resets, 'yyyy-MM-dd HH:mm', [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::AssumeLocal, [ref]$t)) { return Get-Now }
    return ([DateTimeOffset]$t).ToUnixTimeSeconds() + 60 + $LimitGraceSec
}

# The resume messages of a round (see the header): per stop not done yet, the message is seen, sent (again) or given up.
function Invoke-LimitResume {
    $passStart = Get-Now
    foreach ($id in @($limitResume.Keys)) {
        $st = $limitResume[$id]
        if ($st.Done) { continue }
        $taken = @($st.EvtIds | Where-Object { Test-TranscriptHas $id "[EVT-$_]" }) | Select-Object -First 1
        if ($taken) {
            Write-Log ("LIMIT-RESUME-TAKEN {0} {1} {2} ({3:N0} s)" -f $st.Name, $id, $taken, (Get-Age $st.Sent))
            $st.Done = $true
            continue
        }
        $t = Get-Now
        if ($t -lt $st.Due -or $t -lt $st.NextTry) { continue }
        if ($st.Tries -ge $WakeMaxTries) {
            Write-Log ("LIMIT-RESUME-GIVEUP {0} {1} (not taken after {2} sends)" -f $st.Name, $id, $st.Tries)
            $st.Done = $true; $st.GaveUp = $true
            continue
        }
        if ($t - $st.Due -ge $LimitFailHours * 3600) {
            Write-Log ("LIMIT-RESUME-GIVEUP {0} {1} (still stopped {2} h after the reset; last failed send: {3})" -f $st.Name, $id, $LimitFailHours, $st.LastFail)
            $st.Done = $true; $st.GaveUp = $true
            continue
        }
        # A lead that marked itself ready is about to be restarted, which would cut the turn: wait (as Invoke-WakePass).
        $row = $servers | Where-Object { $_.Lead -and $_.Session -ceq $st.Name } | Select-Object -First 1
        if ($row -and $row.Path -and (Invoke-LeadRestartFile $row.Path @('status')) -match '^ready ') { continue }
        if ($t - $passStart -ge $WakeSendBudgetSec -or (Test-Path -LiteralPath $hold)) { break }
        $same = @($agents | Where-Object { $_.pid -and [string]$_.name -ceq $st.Name }).Count
        if ($same -gt 1) {
            Write-Log ("LIMIT-RESUME-SKIPPED {0} {1} ({2} live sessions have this name)" -f $st.Name, $id, $same)
            $st.Done = $true; $st.GaveUp = $true
            continue
        }
        $evt = New-WakeId
        $text = "[EVT-$evt] Pult server watcher: the usage limit that stopped you has reset. Go on with your task " +
            "from where you stopped. If it was already done, answer with your usual status only."
        $wakeState.LastWake[$st.Name] = Get-Now  # the keep-warm ping and the handoff "just woken" check see it
        Save-WakeState
        $res = Send-Wake $st.Name $text $WakeMode
        if (-not $res.Ok) {
            if ($res.Reason -cne $st.LastFail) { Write-Log ("LIMIT-RESUME-FAILED {0} {1} {2}" -f $st.Name, $id, $res.Reason) }
            $st.LastFail = $res.Reason
            $st.NextTry = (Get-Now) + $LimitRetrySec
            continue
        }
        $st.Tries++
        $st.EvtIds += $evt
        $st.Sent = Get-Now
        $st.NextTry = $st.Sent + $WakeConfirmSec
        Write-Log ("LIMIT-RESUME {0} {1} {2} (try {3})" -f $st.Name, $id, $evt, $st.Tries)
        if (Test-TranscriptHas $id "[EVT-$evt]") {
            Write-Log ("LIMIT-RESUME-TAKEN {0} {1} {2} ({3:N0} s)" -f $st.Name, $id, $evt, (Get-Age $st.Sent))
            $st.Done = $true
        }
    }
}

# True when the usage-limit stop of the session $Wanted (a full id or an 8+ character prefix) is being resumed by
# Invoke-LimitResume, not given up: its `limited` event line is then not sent to the lead.
function Test-LimitResuming([string]$Wanted) {
    foreach ($id in $limitResume.Keys) {
        if ((Test-IdMatch $id $Wanted.Trim()) -and -not $limitResume[$id].GaveUp) { return $true }
    }
    return $false
}

# The installed dev-kit version (plugin.json) or $null; sets $script:pluginTime to the file's last write time.
# A read error is logged once per error text.
function Get-DevKitVersion {
    $f = Join-Path $DevKitDir '.claude-plugin\plugin.json'
    try {
        $v = [string](Get-Content -Raw -Encoding UTF8 -LiteralPath $f -ErrorAction Stop | ConvertFrom-Json).version
        if (-not $v) { throw 'no version field' }
        $script:pluginTime = (Get-Item -LiteralPath $f).LastWriteTime
        $script:versionWarned = $null
        return $v
    } catch {
        if ("$_" -ne $script:versionWarned) {
            Write-Log "WARN cannot read the dev-kit version from $f : $_"
            $script:versionWarned = "$_"
        }
        return $null
    }
}

function Save-LeadVersions {
    $o = [ordered]@{}
    foreach ($k in $leadVer.Keys) {
        $o[$k] = [ordered]@{ pid = $leadVer[$k].Pid; started = $leadVer[$k].Started; version = $leadVer[$k].Version }
        if ($leadVer[$k].StaleSince) { $o[$k]['staleSince'] = [string]$leadVer[$k].StaleSince }
        if ($null -ne $leadVer[$k].Ext) {  # no "ext" at all: an old entry that adopts the installed ones
            $x = [ordered]@{}
            foreach ($n in ($leadVer[$k].Ext.Keys | Sort-Object)) { $x[$n] = [string]$leadVer[$k].Ext[$n] }
            $o[$k]['ext'] = $x
        }
    }
    $json = if ($o.Count) { $o | ConvertTo-Json -Depth 3 } else { '{}' }
    $tmp = "$versionFile.$PID.tmp"
    [IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding $false))
    Move-Item -Force -LiteralPath $tmp -Destination $versionFile
}

# Runs `dev-kit-sessions --project <path> restart <args>` against the dev-kit state folder of this watcher;
# returns its trimmed output (stdout and stderr).
function Invoke-LeadRestartFile([string]$LeadPath, [string[]]$Words) {
    return (Invoke-Sessions (@('--project', $LeadPath, 'restart') + $Words)).Out
}

# Restarts one lead with restart-leads.ps1 (-Name, or -Ready when it marked itself ready). Returns 'busy' when
# the script skipped it as busy, 'ok' when it was resumed or started, else 'failed' (logged; RESTART-LEAD-TIMEOUT when
# the run went on past $LeadRestartWaitSec s and was stopped).
function Invoke-LeadRestart([string]$LeadName, [switch]$IsReady) {
    $cmd = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'restart-leads.ps1'))
    $cmd += $(if ($IsReady) { '-Ready' } else { '-Name' })
    $cmd += $LeadName
    $cmd += @('-ConfigFile', $ConfigFile, '-StateDir', $StateDir)
    $res = Invoke-Bounded 'powershell.exe' $cmd $LeadRestartWaitSec
    $said = ($res.Out.Trim() -replace '\s+', ' ')
    if ($res.TimedOut) {
        Write-Critical ("RESTART-LEAD-TIMEOUT {0} (no end in {1} s, stopped): {2}" -f $LeadName, $LeadRestartWaitSec, $said)
        try { Clear-StaleHold } catch { Write-Log "WARN stale hold check failed: $_" }  # its hold names the stopped run
        return 'failed'
    }
    if ($said -match 'Busy, skipped') { return 'busy' }
    # The success line is checked first and every match is scoped to this lead: the output of a run may also hold
    # the NO-BANS line of another lead.
    if ($said -match ('(Resumed|Started) lead: ' + [regex]::Escape($LeadName))) { $noBansTold.Remove($LeadName); return 'ok' }
    if ($said -cmatch ('NO-BANS ' + [regex]::Escape($LeadName) + ' ')) { Register-NoBans $LeadName $said; return 'nobans' }
    Write-Critical ("RESTART-LEAD-FAILED {0}: {1}" -f $LeadName, $said)
    return 'failed'
}

# critical or routine: the kind of the releases a lead process ($St, its lead-versions.json entry) lacks. $Items: one
# @{ Plugin; From; To; File } per changed plugin (dev-kit up to the installed version, an extension up to its own);
# each is asked with `sessions.py release` against that plugin's own releases.json (see the header), and one critical
# one makes the whole change critical. Asked once per lead, pid and $Key (the installed versions): RELEASE-KIND <name>
# (<changes>): <answer>. A failed call counts as routine (WARN once) and is asked again next round.
function Get-ReleaseKind([string]$Name, $St, [string]$Key, $Items) {
    $key = "$Name|$($St.Pid)|$Key"
    if ($releaseKinds.ContainsKey($key)) { return $releaseKinds[$key] }
    $label = (@($Items | ForEach-Object { "$($_.Plugin) $($_.From) -> $($_.To)" })) -join '; '
    $verdict = 'routine'
    $failed = $false
    foreach ($item in @($Items)) {
        $words = @('release', '--from', [string]$item.From, '--to', [string]$item.To, '--file', [string]$item.File)
        if ($St.Started) { $words += @('--started', [string]$St.Started) }  # an empty argument would be dropped
        $r = Invoke-Sessions $words
        $lines = @($r.Out -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
        foreach ($w in @($lines | Where-Object { $_ -clike 'dev-kit-sessions:*' })) { Write-WarnOnce "release $w" $w }
        $one = @($lines | Where-Object { $_ -cmatch '^(critical .+|routine)$' }) | Select-Object -First 1
        if ($r.Code -ne 0 -or -not $one) {
            Write-WarnOnce "release $Name $($item.Plugin)" "cannot read the release kind of $($item.Plugin) for $Name, counted as routine: $($r.Out -replace '\s+', ' ')"
            $failed = $true
            continue
        }
        if ($one -clike 'critical *' -and $verdict -ceq 'routine') { $verdict = $one }
    }
    $kind = if ($verdict -clike 'critical *') { 'critical' } else { 'routine' }
    if ($failed -and $kind -ceq 'routine') { return 'routine' }  # asked again next round
    $releaseKinds[$key] = $kind
    Write-Log "RELEASE-KIND $Name ($label): $verdict"
    return $kind
}

# Why a lead ($Entry: its session list entry) is not quiet enough for a silent restart, '' when it is: 'busy' (status
# not idle), 'idle, <task> working' ($BusyTask: only looked up for a lead woken by message), or what `sessions.py
# quiet` finds in its transcript: 'owner active' (the owner wrote within 5 minutes), 'open question', 'no transcript'.
function Get-LeadActivity($Entry, [string]$BusyTask) {
    if ($Entry.status -ne 'idle') { return 'busy' }
    if ($BusyTask) { return "idle, $BusyTask working" }
    $sid = [string]$Entry.sessionId
    if (-not $sid) { return 'no transcript' }
    $r = Invoke-Sessions @('quiet', '--id', $sid)
    $line = @($r.Out -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -cmatch '^(quiet|active .+)$' }) |
        Select-Object -First 1
    if ($line -ceq 'quiet') { return '' }
    if ($line -clike 'active owner *') { return 'owner active' }
    if ($line -cmatch '^active (.+)$') { return $Matches[1] }
    Write-WarnOnce "quiet $sid" "cannot tell whether $($Entry.name) is quiet: $($r.Out -replace '\s+', ' ')"
    return 'unknown'
}

# What the release rules (see the header) say for a lead stale in any plugin ($s, $m as below, $St its lead-versions.json
# entry, $V the installed dev-kit version, $Key and $Items as in Get-ReleaseKind, $CanAsk whether dev-kit is among the
# changes: the lead's handshake knows only dev-kit versions, so only then it may be asked again). Returns @{ How;
# Stop; Ask; Defer; Kind; Said }: How 'ready', 'quiet' or 'critical, quiet' to restart now, '' to wait; Stop when a
# ready mark expired (READY-EXPIRED, nothing else this round); Ask the reason a lead is not quiet for a critical
# release; Defer for a routine release on the day the lead turned stale; Kind 'critical' or 'routine' (empty before
# it was asked); Said the lead's `restart status`.
function Get-RestartPlan($s, $m, $St, [string]$V, [string]$BusyTask, [string]$Key, $Items, [bool]$CanAsk) {
    $plan = @{ How = ''; Stop = $false; Ask = ''; Defer = $false; Kind = ''; Said = '' }
    $said = Invoke-LeadRestartFile $s.Path @('status')
    $plan.Said = $said
    if ($said -match '^ready (\S+) (\d+)$') {
        # Honoured whatever the kind (the owner may have asked with restart-leads.ps1 -Ask). The lead wrote its
        # 30-second warning into its chat just before it marked itself ready.
        $readyFor = $Matches[1]; $age = [int]$Matches[2]
        if ($readyFor -ceq $V -and $age -lt $ReadyMaxAgeSec) {
            if ($age -lt $ReadyWarnSec) { Start-Sleep -Seconds ($ReadyWarnSec - $age) }
            $plan.How = 'ready'
            return $plan
        }
        $null = Invoke-LeadRestartFile $s.Path @('clear')
        # A ready mark for this version that went stale (a long hold): the lead already noted the version, so ask
        # once more; its session watcher wakes it once (exit 7), or a wake message does.
        $again = ''
        if ($readyFor -ceq $V -and $CanAsk) { $null = Invoke-LeadRestartFile $s.Path @('request', '--version', $V); $again = '; asked again' }
        Write-Log "READY-EXPIRED $($s.Session) ($($said -replace '\s+', ' '), installed $V$again)"
        $plan.Stop = $true
        return $plan
    }
    $plan.Kind = Get-ReleaseKind $s.Session $St $Key $Items
    if ($plan.Kind -ceq 'routine') {
        $today = (Get-Date).ToString('yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture)
        if ($St.StaleSince -ceq $today) { $plan.Defer = $true }
        elseif (-not (Get-LeadActivity $m $BusyTask)) { $plan.How = 'quiet' }
        return $plan  # not quiet on a later day: waits in silence, never a request
    }
    $why = Get-LeadActivity $m $BusyTask
    if ($why) { $plan.Ask = $why } else { $plan.How = 'critical, quiet' }
    return $plan
}

# One live lead ($s: its servers.psd1 row, $m: its entry in the session list, $V: the installed dev-kit
# version): records the versions its process started on and restarts it when the dev-kit version is not $V or
# an extension it uses changed (see the header).
function Invoke-LeadVersionCheck($s, $m, [string]$V) {
    $name = $s.Session
    $procId = [int]$m.pid
    $st = $leadVer[$name]
    $ext = [ordered]@{}  # the extension plugins the project uses (plugin-versions.ps1); unreadable counts as none
    if ($s.Path) {
        try { $ext = Get-LeadExtensions $s.Path $DevKitDir } catch {
            if ("$_" -ne $extWarned[$name]) { Write-Log "WARN cannot read the extensions of $name : $_"; $extWarned[$name] = "$_" }
        }
    }
    $firstLook = $leadSeen[$name] -ne $procId  # first time this watcher run sees this pid
    if ($firstLook) {
        $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
        if (-not $p) { return }  # gone since the list was read
        $started = $null
        try { $started = $p.StartTime.ToUniversalTime().ToString('o', [Globalization.CultureInfo]::InvariantCulture) } catch { return }
        $leadSeen[$name] = $procId
        # A pid alone can come back after a reboot: the process start time must match too.
        if (-not $st -or $st.Pid -ne $procId -or $st.Started -cne $started) {
            $ver = 'older'
            if ($p.StartTime -ge $pluginTime) { $ver = $V }
            $extStarted = @{}
            foreach ($n in $ext.Keys) { $extStarted[$n] = $(if ($p.StartTime -ge $ext[$n].Time) { $ext[$n].Version } else { 'older' }) }
            $st = @{ Pid = $procId; Started = $started; Version = $ver; Ext = $extStarted }
            $leadVer[$name] = $st
            $extNote = ($extStarted.Keys | Sort-Object | ForEach-Object { " $_ $($extStarted[$_])" }) -join ','
            Write-Log "LEAD-VERSION $name pid ${procId}: $ver$extNote"
            try { Save-LeadVersions } catch { Write-Log "WARN cannot save $versionFile : $_" }
        }
    }
    if (-not $st -or $st.Pid -ne $procId) { return }
    if ($Once -or -not $s.Path -or -not (Test-Path -LiteralPath $s.Path)) { return }
    # An entry saved before the extension check existed (no Ext), or an extension it has no version for yet,
    # adopts the installed version: no restart on upgrade, and none for a newly enabled extension.
    $adopted = $false
    if ($null -eq $st.Ext) { $st.Ext = @{}; $adopted = $true }
    foreach ($n in $ext.Keys) {
        if (-not $st.Ext.ContainsKey($n)) { $st.Ext[$n] = $ext[$n].Version; $adopted = $true }
    }
    if ($adopted) { try { Save-LeadVersions } catch { Write-Log "WARN cannot save $versionFile : $_" } }
    $devStale = $st.Version -cne $V
    $extList = @(Get-ExtChangeList $st.Ext $ext)
    $extChanges = @($extList | ForEach-Object { "$($_.Name) $($_.From) -> $($_.To)" })
    $anyStale = $devStale -or $extList.Count -gt 0
    # The day this watcher first saw the process stale in any plugin: a routine release waits until a later day.
    $staleDay = if ($anyStale) { (Get-Date).ToString('yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture) } else { $null }
    if (($anyStale -and -not $st.StaleSince) -or (-not $anyStale -and $st.StaleSince)) {
        $st.StaleSince = $staleDay
        try { Save-LeadVersions } catch { Write-Log "WARN cannot save $versionFile : $_" }
    }
    if (-not $anyStale) {
        # On the installed versions: a restart.json left by a HEAL, a crash or a manual restart is stale. Looked at once
        # per pid, right after the version is known, not every round.
        if ($firstLook) {
            $left = Invoke-LeadRestartFile $s.Path @('status')
            if ($left -cne 'none') {
                $null = Invoke-LeadRestartFile $s.Path @('clear')
                Write-Log "RESTART-CLEARED $name (left over: $($left -replace '\s+', ' '))"
            }
        }
        return
    }
    if ($onHold -or $starting -or (Test-Path -LiteralPath $hold)) { return }
    if ($noBansUntil[$name] -and (Get-Date) -lt $noBansUntil[$name]) { return }  # no hard bans on main: asked a moment ago
    # The key of one try: the dev-kit version and the extension versions together.
    $tryKey = $V + (($ext.Keys | Sort-Object | ForEach-Object { "|$_=$($ext[$_].Version)" }) -join '')
    if ($leadTried[$name] -ceq $tryKey) { return }
    $changed = @()
    if ($devStale) { $changed += "dev-kit $($st.Version) -> $V" }
    $changed += $extChanges
    $how = ''
    # A lead woken by message keeps no session watcher (see the header): it is not restarted at once while one of
    # its task sessions works, and it gets the request below instead of noticing the version on a watcher exit.
    $wokenByMessage = Test-WakeLead $name $procId
    $busyTask = $null
    if ($wokenByMessage -and $m.status -eq 'idle') { $busyTask = Get-BusyTask $s.Path }
    $idleFree = $m.status -eq 'idle' -and -not $busyTask
    # Each changed plugin is judged by its own releases.json (Get-ReleaseKind); one critical mark makes the change critical.
    $items = @()
    if ($devStale) { $items += @{ Plugin = 'dev-kit'; From = [string]$st.Version; To = $V; File = (Join-Path $DevKitDir 'releases.json') } }
    foreach ($c in $extList) { $items += @{ Plugin = $c.Name; From = $c.From; To = $c.To; File = (Join-Path $ext[$c.Name].Dir 'releases.json') } }
    $plan = Get-RestartPlan $s $m $st $V $busyTask $tryKey $items $devStale
    if ($plan.Stop) { return }  # a ready mark that expired (READY-EXPIRED)
    $how = $plan.How
    # A critical release that is not quiet while another plugin changed too, or one with no dev-kit change (no ask
    # possible): an idle lead is restarted at once.
    if (-not $how -and $plan.Kind -ceq 'critical' -and $extList.Count -gt 0 -and $idleFree) { $how = 'idle' }
    if (-not $how) {
        # A critical dev-kit release and a lead that is not quiet: a lead woken by message is asked (it warns the owner
        # in its chat, marks itself ready, and the ready path above restarts it); an older one waits for quiet. Any
        # other change is never asked (the handshake knows only dev-kit versions, and an ask wakes a paid turn).
        $said = $plan.Said
        if ($plan.Ask -and $devStale -and $wokenByMessage -and ($said -ceq 'none' -or ($said -match '^asked (\S+) ' -and $Matches[1] -cne $V))) {
            $null = Invoke-LeadRestartFile $s.Path @('request', '--version', $V)
            Write-Log "RESTART-ASKED $name ($($changed -join '; '), critical, $($plan.Ask))"
        } elseif ($plan.Defer -and $deferLogged[$name] -cne "$procId|$tryKey") {
            $deferLogged[$name] = "$procId|$tryKey"
            Write-Log "RESTART-DEFERRED $name ($($changed -join '; '), routine, until a later day)"
        }
        return
    }
    Write-Log "RESTART-LEAD $name ($($changed -join '; '), $how)"
    $result = Invoke-LeadRestart $name -IsReady:($how -eq 'ready')
    if ($result -eq 'busy') { return }  # turned busy meanwhile: the busy path handles it next round
    if ($result -eq 'nobans') { return }  # no hard bans on main: the lead was left running; tried again later (Register-NoBans)
    $leadTried[$name] = $tryKey
    $cleared = Invoke-LeadRestartFile $s.Path @('clear')  # also after a failure: no stale ready mark stays
    if ($cleared -cne 'restart cleared') { Write-Log "WARN restart clear for $name failed: $($cleared -replace '\s+', ' ')" }
}

# ---- Wakes (see the header) ----

function Get-Now { return [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() / 1000.0 }  # epoch seconds

# Seconds since an epoch time; a very large number for 0 (never).
function Get-Age([double]$Since) { if ($Since -le 0) { return [double]::MaxValue }; return (Get-Now) - $Since }

# True when the lead's process (lead-versions.json, by pid) started on dev-kit $WakeMinDevKit or later.
function Test-WakeLead([string]$Name, $ProcId) {
    $st = $leadVer[$Name]
    if (-not $st -or $st.Pid -ne [int]$ProcId) { return $false }
    $v = $null
    if (-not [version]::TryParse([string]$st.Version, [ref]$v)) { return $false }  # "older" too
    return $v -ge [version]$WakeMinDevKit
}

# The dev-kit state folder of a project (the registry's folder), computed by dev_kit_state.py; cached per path.
function Get-RegistryDir([string]$ProjectPath) {
    if ($registryDirs.ContainsKey($ProjectPath)) { return $registryDirs[$ProjectPath] }
    $code = 'import sys; sys.path.insert(0, sys.argv[1]); import dev_kit_state; print(dev_kit_state.project_state_dir(sys.argv[2], False))'
    $old = $env:DEV_KIT_STATE_DIR
    $env:DEV_KIT_STATE_DIR = $DevKitStateDir
    try { $r = Invoke-Python @('-c', $code, (Join-Path $DevKitDir 'scripts'), $ProjectPath) -NoStderr }
    finally { $env:DEV_KIT_STATE_DIR = $old }
    $out = $r.Out
    if ($r.Code -ne 0 -or -not $out.Trim()) { Write-WarnOnce "registry $ProjectPath" "cannot find the dev-kit state folder of $ProjectPath"; return $null }
    $registryDirs[$ProjectPath] = $out.Trim()
    return $registryDirs[$ProjectPath]
}

# The name of an active task session of the project's registry (not a lead; -NonOwner: not an owner session either)
# that is live and busy in this round's session list (status busy or state working), else $null.
function Get-BusyTask([string]$ProjectPath, [switch]$NonOwner) {
    if ($null -eq $agents -or -not $ProjectPath) { return $null }
    $dir = Get-RegistryDir $ProjectPath
    if (-not $dir) { return $null }
    $f = Join-Path $dir 'sessions.json'
    if (-not (Test-Path -LiteralPath $f)) { return $null }
    try { $records = @(Get-Content -Raw -Encoding UTF8 -LiteralPath $f | ConvertFrom-Json | ForEach-Object { $_ }) }
    catch { Write-WarnOnce "registry read $f" "cannot read $f : $_"; return $null }
    foreach ($r in $records) {
        if ($r.status -cne 'active' -or -not $r.id -or ([string]$r.name).StartsWith('P: ', [StringComparison]::Ordinal)) { continue }
        if ($NonOwner -and $r.owner -eq $true) { continue }
        $wid = ([string]$r.id).Trim()
        $hit = $agents | Where-Object { $_ -and $_.pid -and ($_.status -eq 'busy' -or $_.state -eq 'working') -and
            ((Test-IdMatch ([string]$_.sessionId) $wid) -or (Test-IdMatch ([string]$_.id) $wid)) } | Select-Object -First 1
        if ($hit) { return [string]$r.name }
    }
    return $null
}

# The live transcript file of a session id, or $null: the linkScanPath of its job (resume-lib.ps1 Get-JobState; a /clear
# keeps the job and its session id but writes a new file) when that file exists, else the newest <projects>\*\<id>.jsonl.
function Find-Transcript([string]$SessionId) {
    if (-not $SessionId) { return $null }
    $job = Get-JobState $SessionId
    if ($job -and $job.linkScanPath) {
        $live = Get-Item -LiteralPath ([string]$job.linkScanPath) -ErrorAction SilentlyContinue
        if ($live) { return $live }
    }
    $dir =if ($env:DEV_KIT_PROJECTS_DIR) { $env:DEV_KIT_PROJECTS_DIR } else { Join-Path $env:USERPROFILE '.claude\projects' }
    if (-not (Test-Path -LiteralPath $dir)) { return $null }
    return Get-ChildItem -LiteralPath $dir -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Get-Item -LiteralPath (Join-Path $_.FullName "$SessionId.jsonl") -ErrorAction SilentlyContinue } |
        Sort-Object LastWriteTimeUtc -Descending | Select-Object -First 1
}

# True when $Text is in the last 512 KB of the session's transcript.
function Test-TranscriptHas([string]$SessionId, [string]$Text) {
    $f = Find-Transcript $SessionId
    if (-not $f) { return $false }
    try {
        $fs = [IO.File]::Open($f.FullName, 'Open', 'Read', 'ReadWrite')
        try {
            $start = [Math]::Max(0, $fs.Length - 512KB)
            $null = $fs.Seek($start, 'Begin')
            $tail = (New-Object IO.StreamReader($fs, [Text.Encoding]::UTF8)).ReadToEnd()
        } finally { $fs.Dispose() }
    } catch { return $false }
    return $tail.IndexOf($Text, [StringComparison]::Ordinal) -ge 0
}

# One line of a message: no control characters, at most $Max characters.
function Get-CleanLine([string]$Text, [int]$Max = 300) {
    $t = ($Text -replace '[\x00-\x1f\x7f]+', ' ').Trim()
    if ($t.Length -gt $Max) { $t = $t.Substring(0, $Max - 3) + '...' }
    return $t
}

function New-WakeId { return [datetime]::UtcNow.ToString('MMddHHmmss') + '-' + ('{0:x4}' -f (Get-Random -Maximum 65536)) }

function New-WakeItem([string]$Target, [string]$Kind, [string]$Cause) {
    return @{ Id = (New-WakeId); Target = $Target; Kind = $Kind; Cause = $Cause; Mode = ''; Lines = @(); Kinds = @()
        EventKeys = @(); Marks = @(); Tries = 0; Created = (Get-Now); Sent = 0.0; FirstSent = 0.0; SessionId = ''
        DownSince = 0.0; NextTry = 0.0; Text = ''; From = ''; Relay = '' }
}

function ConvertTo-WakeItem($o) {
    $h = @{}
    foreach ($k in 'Id', 'Target', 'Kind', 'Cause', 'Mode', 'SessionId', 'Text', 'From', 'Relay') { $h[$k] = [string]$o.$k }
    foreach ($k in 'Created', 'Sent', 'FirstSent', 'DownSince', 'NextTry') { $h[$k] = [double]$o.$k }
    # Not named "Keys": a hashtable's own Keys property would win over such an entry.
    foreach ($k in 'Lines', 'Kinds', 'EventKeys') { $h[$k] = @(@($o.$k) | Where-Object { $null -ne $_ } | ForEach-Object { [string]$_ }) }
    $h.Marks = @(@($o.Marks) | Where-Object { $null -ne $_ } |
        ForEach-Object { @{ Project = [string]$_.Project; Kind = [string]$_.Kind; Id = [string]$_.Id; Key = [string]$_.Key } })
    $h.Tries = [int]$o.Tries
    return $h
}

function Save-WakeJson([string]$Path, $Value) {
    $json = ConvertTo-Json -InputObject $Value -Depth 6
    $tmp = "$Path.$PID.tmp"
    [IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding $false))
    Move-Item -Force -LiteralPath $tmp -Destination $Path
}

function Save-WakePending {
    try { Save-WakeJson $wakePendingFile @($wakePending) } catch { Write-Log "WARN cannot save $wakePendingFile : $_" }
}

function Save-WakeState {
    try { Save-WakeJson $wakeStateFile $wakeState } catch { Write-Log "WARN cannot save $wakeStateFile : $_" }
}

# Queues one event line for a target (a lead or Pult): merged into its message that is not sent yet while that
# stays within about 1500 characters. $Key: an event already queued with it is not queued again (sessions.py
# check prints an event each round until it is marked). $Mark: the sessions.py mark to run after delivery.
function Add-WakeLine([string]$Target, [string]$Kind, [string]$Line, [string]$EventKind, [string]$Key, $Mark) {
    if ($Key -and ($wakePending | Where-Object { $_.EventKeys -ccontains $Key })) { return }
    $Line = Get-CleanLine $Line
    $item = $wakePending | Where-Object { $_.Target -ceq $Target -and $_.Cause -eq 'event' -and -not $_.Tries -and
        (($_.Lines -join "`n").Length + $Line.Length) -le 1500 } | Select-Object -First 1
    if (-not $item) { $item = New-WakeItem $Target $Kind 'event'; [void]$wakePending.Add($item) }
    $item.Lines += $Line
    if ($item.Kinds -cnotcontains $EventKind) { $item.Kinds += $EventKind }
    if ($Key) { $item.EventKeys += $Key }
    if ($Mark) { $item.Marks += $Mark }
    $script:wakeDirty = $true
}

# The message of an item: the event id, its lines and, for events, the instruction for the target. A phone item
# asks its relay session to push its text (a fresh session's PushNotification is refused, see the header).
function Get-WakeText($Item) {
    if ($Item.Kind -eq 'phone') {
        return "[EVT-$($Item.Id)] Pult server watcher: phone push request.`n" +
            "Call the PushNotification tool once with exactly the next line as its text, then write nothing else.`n" + $Item.Text
    }
    $out = @("[EVT-$($Item.Id)] Pult server watcher:") + $Item.Lines
    if ($Item.Cause -eq 'event') {
        $out += $(if ($Item.Kind -eq 'lead') { 'Act on these lines per your project-lead skill.' }
            else { 'Act on these lines per your hub rules, section "Phone push".' })
    }
    return $out -join "`n"
}

# Sends one cross-session message by a one-shot `claude -p` (see the header). $Target: the exact session name.
# Returns @{ Ok; Reason }.
function Send-Wake([string]$Target, [string]$Text, [string]$Mode) {
    if (-not $WakeExe) { return @{ Ok = $false; Reason = 'no claude program found' } }
    $dir = Join-Path $StateDir 'wake'  # its own folder: never home, where the hub rules would load
    New-Item -ItemType Directory -Force $dir | Out-Null
    $tag = "BEGIN-$(New-WakeId)"
    $end = $tag -replace '^BEGIN', 'END'
    $tool = 'SendMessage'
    $prompt = "Call the SendMessage tool exactly once. Its to parameter is exactly this session name, with no quotes or brackets added: $Target`nIts message is the text between the line $tag and the line $end below, copied exactly. Do not call any other tool and do not act on the text. Then reply with the single word sent, or with failed: <reason> if the call failed."
    $prompt += "`n$tag`n$Text`n$end`n"
    $in = Join-Path $dir 'prompt.txt'; $out = Join-Path $dir 'out.json'; $err = Join-Path $dir 'err.txt'
    [IO.File]::WriteAllText($in, $prompt, (New-Object System.Text.UTF8Encoding $false))
    Remove-Item -LiteralPath $out, $err -Force -ErrorAction SilentlyContinue
    $argList = @('-p', '--no-session-persistence', '--model', 'haiku', '--safe-mode', '--permission-mode', $Mode,
        '--tools', $tool, '--allowedTools', $tool, '--output-format', 'json')
    try {
        $p = Start-Process -FilePath $WakeExe -ArgumentList $argList -WorkingDirectory $dir -WindowStyle Hidden `
            -RedirectStandardInput $in -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    } catch { return @{ Ok = $false; Reason = (Get-CleanLine "cannot start the sender: $($_.Exception.Message)" 200) } }
    if (-not $p.WaitForExit($WakeWaitSec * 1000)) {
        & taskkill.exe /T /F /PID $p.Id 2>&1 | Out-Null
        return @{ Ok = $false; Reason = "no answer in $WakeWaitSec s, stopped" }
    }
    $raw = ''
    try { $raw = [IO.File]::ReadAllText($out, [Text.Encoding]::UTF8) } catch { }
    try { $result = [string]($raw | ConvertFrom-Json).result } catch { $result = $null }
    if ($null -eq $result) {
        $said = $raw
        if (-not $said.Trim()) { try { $said = [IO.File]::ReadAllText($err, [Text.Encoding]::UTF8) } catch { } }
        return @{ Ok = $false; Reason = (Get-CleanLine "no json result: $said" 200) }
    }
    $result = $result.Trim()
    if ($result -match '^sent\b' -and $result -notmatch 'fail') { return @{ Ok = $true; Reason = '' } }
    return @{ Ok = $false; Reason = (Get-CleanLine $result 200) }
}

function Invoke-WakeMarks($Item) {
    foreach ($mk in $Item.Marks) {
        $words = @('--project', $mk.Project, 'mark', '--kind', $mk.Kind)
        if ($mk.Id) { $words += @('--id', $mk.Id) }
        $r = Invoke-Sessions ($words + @('--key', $mk.Key))
        if ($r.Code -ne 0) { Write-Log ("WARN mark {0} {1} failed (exit {2}): {3}" -f $mk.Kind, $mk.Id, $r.Code, ($r.Out -replace '\s+', ' ')) }
    }
}

function Remove-WakeItem($Item) { $wakePending.Remove($Item); $script:wakeDirty = $true }

# A message seen in the target's transcript: logged, its marks run, removed.
function Test-WakeTaken($Item) {
    if (-not (Test-TranscriptHas $Item.SessionId "[EVT-$($Item.Id)]")) { return $false }
    $via = if ($Item.Kind -eq 'phone') { " via $($Item.Relay)" } else { '' }
    Write-Log ("WAKE-TAKEN {0} {1}{2} ({3:N0} s)" -f $Item.Target, $Item.Id, $via, (Get-Age $Item.Sent))
    Invoke-WakeMarks $Item
    Remove-WakeItem $Item
    return $true
}

function Send-WakeItem($Item, $T) {
    if (-not $Item.Tries) { Write-Log "WAKE $($Item.Target) $($Item.Id) cause=$($Item.Cause) kinds=$($Item.Kinds -join ',')" }
    $Item.Mode = $(if ($Item.Target -ceq 'Pult') { $PultWakeMode } else { $WakeMode })
    $Item.SessionId = $T.SessionId
    $Item.Tries++
    $Item.Sent = Get-Now
    if (-not $Item.FirstSent) { $Item.FirstSent = $Item.Sent }
    $script:wakeDirty = $true
    $wakeState.LastWake[$Item.Target] = $Item.Sent
    Save-WakeState
    $r = Send-Wake $T.Name (Get-WakeText $Item) $Item.Mode  # the session name: for the hub its system name, not 'Pult'
    if (-not $r.Ok) { Write-Log "WAKE-FAILED $($Item.Target) $($Item.Id) $($r.Reason)"; return }
    Write-Log "WAKE-SENT $($Item.Target) $($Item.Id) (try $($Item.Tries), mode $($Item.Mode))"
    $null = Test-WakeTaken $Item  # usually already in the transcript; else looked for in the next rounds
}

# The session that pushes a phone item: Pult when it is live, else a live lead (an idle one first, any version, not
# one whose `restart status` says ready); never the session that did not take the original message. $null: none.
function Get-PushRelay($Item, $Targets) {
    $pult = $Targets['Pult']
    if ($pult -and $pult.Live -and $Item.From -cne 'Pult') { return 'Pult' }
    $leads = @($servers | Where-Object { $_.Lead -and $_.Session -cne $Item.From } | ForEach-Object { $_.Session } |
        Where-Object { $Targets[$_] -and $Targets[$_].Live })
    foreach ($name in @($leads | Where-Object { $Targets[$_].Idle }) + @($leads | Where-Object { -not $Targets[$_].Idle })) {
        $path = $Targets[$name].Row.Path
        if ($path -and (Invoke-LeadRestartFile $path @('status')) -match '^ready ') { continue }
        return $name
    }
    return $null
}

# A phone push (a size push, or event lines whose target did not take them), sent as a message asking a relay
# session (Get-PushRelay) to push it: a fresh session's PushNotification is refused (plugins/dev-kit/claude-facts.md,
# "A push from a fresh session is refused").
# Delivered like any wake (its id in the relay's transcript, Test-WakeTaken), then the marks run. Not taken: sent
# again after $WakeConfirmSec s, after $WakeMaxTries sends every $PhoneRetrySec s; never dropped.
function Send-PhoneItem($Item, $Targets, $Handled) {
    if ($Item.NextTry -and (Get-Now) -lt $Item.NextTry) { return }
    $relay = Get-PushRelay $Item $Targets
    if (-not $relay) {
        Write-Log "WAKE-FALLBACK-NONE phone $($Item.Id) (no live Pult or lead to push it; next try in $PhoneRetrySec s)"
        $Item.NextTry = (Get-Now) + $PhoneRetrySec
        $script:wakeDirty = $true
        return
    }
    if ($Handled[$relay]) { return }  # one message per target per round
    $Handled[$relay] = $true
    if (-not $Item.Tries -and -not $Item.From) { Write-Log "WAKE phone $($Item.Id) cause=$($Item.Cause) kinds=$($Item.Kinds -join ',')" }
    $Item.Relay = $relay
    $Item.Mode = $(if ($relay -ceq 'Pult') { $PultWakeMode } else { $WakeMode })
    $Item.SessionId = $Targets[$relay].SessionId
    $Item.Tries++
    $Item.Sent = Get-Now
    $Item.NextTry = $Item.Sent + $(if ($Item.Tries -lt $WakeMaxTries) { $WakeConfirmSec } else { $PhoneRetrySec })
    $script:wakeDirty = $true
    $wakeState.LastWake[$relay] = $Item.Sent
    Save-WakeState
    $r = Send-Wake $Targets[$relay].Name (Get-WakeText $Item) $Item.Mode  # the relay's session name (the hub's system name for 'Pult')
    if (-not $r.Ok) { Write-Log "WAKE-FAILED phone $($Item.Id) via $relay $($r.Reason)"; return }
    Write-Log "WAKE-SENT phone $($Item.Id) via $relay (try $($Item.Tries), mode $($Item.Mode))"
    $null = Test-WakeTaken $Item
}

function Get-PhoneText([string]$Head, [string[]]$Lines) {
    $t = Get-CleanLine ((@($Head) + $Lines | Where-Object { $_ }) -join '; ') 1000
    if ($t.Length -gt 199) { $t = $t.Substring(0, 196) + '...' }
    return $t
}

# A message the target did not take: event lines go to the phone (by a relay, see Send-PhoneItem); a ping or a note
# is dropped.
function Invoke-WakeFallback($Item, [string]$Why, $Targets, $Handled) {
    if ($Item.Cause -ne 'event') {
        Write-Log "WAKE-FAILED $($Item.Target) $($Item.Id) $Why; a $($Item.Cause) is not pushed, dropped"
        Remove-WakeItem $Item
        return
    }
    $head = if ($Item.Kind -eq 'pult') { "Pult не піднявся - запусти його на комп'ютері" }
        elseif ($Why -eq 'not live') { "$($Item.Target) не на зв'язку" } else { "$($Item.Target) не взяв повідомлення" }
    Write-Log "WAKE-FALLBACK $($Item.Target) $($Item.Id) ($Why)"
    $Item.From = $Item.Target; $Item.Target = 'phone'; $Item.Kind = 'phone'
    $Item.Text = Get-PhoneText $head $Item.Lines
    $Item.Tries = 0; $Item.Sent = 0.0; $Item.NextTry = 0.0; $Item.SessionId = ''
    $script:wakeDirty = $true
    Send-PhoneItem $Item $Targets $Handled
}

# One `sessions.py size` call for the live leads, task sessions and Pult: the size push and the SIZE lines.
function Invoke-SizeCheck($Targets) {
    $ids = [ordered]@{}
    foreach ($id in $liveSessions.Keys) { $ids[$id] = $liveSessions[$id] }
    $pult = $Targets['Pult']
    if ($pult -and $pult.Live -and $pult.SessionId) { $ids[$pult.SessionId] = 'Pult' }
    if (-not $ids.Count) { return }
    $logNow = (Get-Age $lastSizeLog) -ge $SizeLogMin * 60
    $words = @('size') + @($ids.Keys | ForEach-Object { '--id', $_ })
    if ($logNow) { $words += @('--wakes', (Join-Path $StateDir 'size-state.json')) }
    $r = Invoke-Sessions $words
    if ($r.Code -ne 0) { Write-WarnOnce 'size' ("size check failed (exit {0}): {1}" -f $r.Code, ($r.Out -replace '\s+', ' ')); return }
    $warnedOnce.Remove('size')
    if ($logNow) { $script:lastSizeLog = Get-Now }
    $due = @()  # (name, thousands of tokens) of the sessions that pass the share this round: one push for all
    foreach ($line in ($r.Out -split "`r?`n")) {
        $p = @($line -split ' \| ' | ForEach-Object { $_.Trim() })
        if ($p.Count -lt 4 -or -not $ids.Contains($p[0])) { continue }
        $tokens = 0L; $window = 0L
        if (-not [int64]::TryParse($p[1], [ref]$tokens) -or -not [int64]::TryParse($p[2], [ref]$window)) { continue }
        $sid = $p[0]; $name = $ids[$sid]
        if ($logNow) { Write-Log ("SIZE {0} {1} {2}{3}" -f $name, $sid, $tokens, $(if ($p.Count -ge 6) { " $($p[4]) $($p[5])" } else { '' })) }
        if ($window -gt 0 -and $tokens -ge $SizePushShare * $window -and -not $wakeState.SizePushed.ContainsKey($sid)) {
            $wakeState.SizePushed[$sid] = $tokens
            Save-WakeState
            Write-Log "PUSH-SIZE $name $sid $tokens"
            $due += , @($name, [Math]::Round($tokens / 1000))
        }
    }
    if (-not $due.Count) { return }
    $item = New-WakeItem 'phone' 'phone' 'size'
    $item.Kinds = @('size')
    $item.Text = if ($due.Count -eq 1) { Get-PhoneText '' @("$($due[0][0]): розмова $($due[0][1]) тис. токенів - перенеси її в нову сесію") }
        else { Get-PhoneText '' @((($due | ForEach-Object { "$($_[0]): $($_[1]) тис." }) -join ', ') + ' токенів - перенеси ці розмови в нові сесії') }
    [void]$wakePending.Add($item)
    $script:wakeDirty = $true
}

# The weekly limit forecast (see the header): one `usage_forecast.py check` call when the usage log changed; on `push`
# a LIMIT-FORECAST line and one phone push. The forecast, the open-task test and the once-per-window mark are its own.
function Invoke-LimitForecast {
    $usageLog = if ($env:DEV_KIT_USAGE_LOG) { Join-Path $env:DEV_KIT_USAGE_LOG 'usage-log.jsonl' }
        else { Join-Path $env:USERPROFILE '.claude\spend-kit\usage-log.jsonl' }
    $f = Get-Item -LiteralPath $usageLog -ErrorAction SilentlyContinue
    if (-not $f) { return }
    $written = "$($f.LastWriteTimeUtc.Ticks) $($liveTasks.Count -gt 0)"  # a look again when task sessions open or close
    if ($written -ceq $script:lastUsageWrite) { return }
    $script:lastUsageWrite = $written
    $py = Join-Path $SpendKitDir 'scripts\usage_forecast.py'
    $r = Invoke-Python @($py, 'check', '--open', [string]$liveTasks.Count, '--mark', (Join-Path $StateDir 'limit-forecast.json'), '--log', $usageLog) -NoStderr
    if ($r.Code -ne 0) { Write-WarnOnce 'forecast' ("limit forecast failed (exit {0}): {1}" -f $r.Code, ($r.Out -replace '\s+', ' ')); return }
    $warnedOnce.Remove('forecast')
    $p = @(($r.Out.Trim() -split ' \| ') | ForEach-Object { $_.Trim() })
    if ($p[0] -cne 'push' -or $p.Count -lt 6) { return }
    $at = { param($e) [DateTimeOffset]::FromUnixTimeSeconds([int64]$e).LocalDateTime.ToString('yyyy-MM-dd HH:mm') }
    Write-Log ("LIMIT-FORECAST runout={0} resets={1} pct={2} pace={3}" -f (& $at $p[1]), (& $at $p[2]), $p[3], $p[4])
    $item = New-WakeItem 'phone' 'phone' 'limit'
    $item.Kinds = @('limit')
    $item.Text = Get-PhoneText '' @($p[5])
    [void]$wakePending.Add($item)
    $script:wakeDirty = $true
}

# A folder path as one comparable string: resolved, no trailing slash, lower case. '' when it is empty or unreadable.
function Get-FolderKey($Path) {
    if (-not [string]$Path) { return '' }
    try {
        $full = [IO.Path]::GetFullPath([string]$Path)
        $r = Resolve-Path -LiteralPath $full -ErrorAction SilentlyContinue
        if ($r) { $full = [string]$r.ProviderPath }
        return $full.TrimEnd('\', '/').ToLowerInvariant()
    } catch { return '' }
}

# The session of the Pult hub in the session list $List: @{ Agent; Name } or $null. The hub's Remote Control session has
# a system name like "<user>-e9" there, not "Pult" (plugins/dev-kit/claude-facts.md, "The Remote Control server's own
# session has a system name"; status-page.py treats a home-folder session as Pult the same way): a session named
# "Pult" first, else an interactive session with cwd = the home folder; of several, the one whose parent process is
# the server (a claude process with ` remote-control ` and "Pult" in its command line, the test of hub.md), else the
# first. Name is what a message must name as its target.
function Find-PultAgent($List) {
    $live = @($List | Where-Object { $_.kind -eq 'interactive' -and $_.pid })
    $named = $live | Where-Object { $_.name -ceq 'Pult' } | Select-Object -First 1
    if ($named) { return @{ Agent = $named; Name = [string]$named.name } }
    $home1 = Get-FolderKey $(if ($env:USERPROFILE) { $env:USERPROFILE } else { [Environment]::GetFolderPath('UserProfile') })
    if (-not $home1) { return $null }
    $cands = @($live | Where-Object { (Get-FolderKey $_.cwd) -ceq $home1 })
    if (-not $cands.Count) { return $null }
    $pick = $cands[0]
    if ($cands.Count -gt 1) {
        foreach ($c in $cands) {
            try {
                $own = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$c.pid)" -ErrorAction Stop
                $par = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$own.ParentProcessId)" -ErrorAction Stop
            } catch { continue }
            if ($par.Name -in @('claude.exe', 'node.exe') -and [string]$par.CommandLine -match '\sremote-control\s' -and [string]$par.CommandLine -match 'Pult') {
                $pick = $c; break
            }
        }
    }
    return @{ Agent = $pick; Name = [string]$pick.name }
}

# The wake pass of a round (see the header).
function Invoke-WakePass {
    $script:wakeDirty = $false
    # Targets of this round: key -> @{ Kind; Live; SessionId; Idle; Row; Agent; Name }. The key of a lead is its session
    # name, the key of the hub is always 'Pult' (wake state, logs, items); Name is the session name a message is sent to.
    $targets = @{}
    if ($null -ne $agents) {
        foreach ($s in $servers) {
            if (-not $s.Lead) { continue }
            $m = $agents | Where-Object { $_.kind -eq 'background' -and $_.name -ceq $s.Session -and $_.pid } | Select-Object -First 1
            $targets[$s.Session] = @{ Kind = 'lead'; Live = [bool]$m; SessionId = [string]$m.sessionId
                Idle = [bool]($m -and $m.status -eq 'idle'); Row = $s; Agent = $m; Name = $s.Session }
        }
        $pm = Find-PultAgent $agents
        $targets['Pult'] = @{ Kind = 'pult'; Live = [bool]$pm; SessionId = [string]$pm.Agent.sessionId; Idle = $false; Row = $null
            Agent = $pm.Agent; Name = $(if ($pm) { $pm.Name } else { 'Pult' }) }
    }

    # Messages in flight that reached their target.
    foreach ($item in @($wakePending)) {
        if ($item.Tries -and $item.SessionId) { $null = Test-WakeTaken $item }
    }

    # Pult events of this round: queued even when the session list is unknown.
    foreach ($e in $pultEvents) { Add-WakeLine 'Pult' 'pult' $e (([string]$e -split ' ')[0]) '' $null }
    $pultEvents.Clear()

    if ($null -ne $agents) {
        $agentsFile = $null
        foreach ($s in $servers) {
            if (-not $s.Lead -or -not $s.Path -or -not (Test-Path -LiteralPath $s.Path)) { continue }
            $name = $s.Session
            $t = $targets[$name]
            if (-not $t.Live -or -not (Test-WakeLead $name $t.Agent.pid)) { continue }
            if (-not $agentsFile) {
                New-Item -ItemType Directory -Force (Join-Path $StateDir 'wake') | Out-Null
                $agentsFile = Join-Path $StateDir 'wake\agents.json'
                [IO.File]::WriteAllText($agentsFile, [string]$agentsText, (New-Object System.Text.UTF8Encoding $false))
            }
            $r = Invoke-Sessions @('--project', $s.Path, 'check') $agentsFile
            if ($r.Code -ne 0) {
                $why = if ($r.Code -eq 3) { 'the session list is unreadable' } else { "exit $($r.Code): $($r.Out -replace '\s+', ' ')" }
                Write-WarnOnce "check $name" "session check of $name failed ($why)"
                continue
            }
            $warnedOnce.Remove("check $name")
            foreach ($line in ($r.Out -split "`r?`n")) {
                $p = @($line -split ' \| ' | ForEach-Object { $_.Trim() })
                if ($p.Count -lt 5 -or $p[0] -cnotin @('gone', 'finished', 'limited', 'stale', 'fill', 'restart', 'handoff')) { continue }
                $kind = $p[0]; $key = $p[$p.Count - 1]; $detail = $p[3..($p.Count - 2)] -join ' | '
                if ($kind -eq 'limited' -and (Test-LimitResuming $p[2])) { continue }  # the watcher wakes it (see the header)
                $text = if ($kind -in 'restart', 'handoff') { "$kind requested: $detail" } else { "${kind}: $($p[1]) | $($p[2]) | $detail" }
                $mark = @{ Project = $s.Path; Kind = $kind; Id = $(if ($p[2] -ceq '-') { '' } else { $p[2] }); Key = $key }
                Add-WakeLine $name 'lead' $text $kind "$name|$kind|$($p[2])|$key" $mark
            }
            # Keep-warm ping: idle, nothing pending for it, silent and not woken for $PingQuietMin minutes, a task works.
            if (-not $t.Idle -or ($wakePending | Where-Object { $_.Target -ceq $name -or $_.From -ceq $name })) { continue }
            if ((Get-Age ([double]$wakeState.LastWake[$name])) -lt $PingQuietMin * 60) { continue }
            $tr = Find-Transcript $t.SessionId
            if (-not $tr -or ([datetime]::UtcNow - $tr.LastWriteTimeUtc).TotalMinutes -lt $PingQuietMin) { continue }
            if (-not (Get-BusyTask $s.Path -NonOwner)) { continue }
            # A lead that left a handoff is about to be replaced (or the move failed): its context is not kept warm.
            if ((Invoke-Sessions @('--project', $s.Path, 'handoff', 'status')).Out -cmatch '^(saved|go) ') { continue }
            $item = New-WakeItem $name 'lead' 'ping'
            $item.Lines = @($PingLine); $item.Kinds = @('ping')
            [void]$wakePending.Add($item)
            $script:wakeDirty = $true
        }
        if ($targets['Pult'].Live -and -not $wakeState.PultNote) {
            $item = New-WakeItem 'Pult' 'pult' 'note'
            $item.Lines = @($NoteLine); $item.Kinds = @('note')
            [void]$wakePending.Add($item)
            $wakeState.PultNote = $true
            Save-WakeState
            $script:wakeDirty = $true
        }
        try { Invoke-SizeCheck $targets } catch { Write-Log "WARN size check failed: $_" }
        try { Invoke-LimitForecast } catch { Write-Log "WARN limit forecast failed: $_" }
    }

    # Sends: one sender at a time; per target only its oldest message, at most one per round. The pass stops after
    # $WakeSendBudgetSec s (the rest waits for the next round) and when a hold file appears (a stop began).
    if ($null -ne $agents -and -not $onHold -and -not $starting) {
        $handled = @{}
        $passStart = Get-Now
        foreach ($item in @($wakePending)) {
            if ((Get-Now) - $passStart -ge $WakeSendBudgetSec -or (Test-Path -LiteralPath $hold)) { break }
            if (-not $wakePending.Contains($item)) { continue }
            if ($item.Kind -eq 'phone') { Send-PhoneItem $item $targets $handled; continue }
            if ($handled[$item.Target]) { continue }
            $handled[$item.Target] = $true
            $t = $targets[$item.Target]
            if ($item.Tries) {
                if ((Get-Age $item.Sent) -lt $WakeConfirmSec) { continue }
                if ($item.Tries -ge $WakeMaxTries) { Invoke-WakeFallback $item "not taken after $($item.Tries) sends" $targets $handled; continue }
            }
            if (-not $t -or -not $t.Live) {
                if (-not $item.DownSince) { $item.DownSince = Get-Now; $script:wakeDirty = $true }
                if ((Get-Age $item.DownSince) -ge $WakeDownSec) { Invoke-WakeFallback $item 'not live' $targets $handled }
                continue
            }
            if ($item.DownSince) { $item.DownSince = 0.0; $script:wakeDirty = $true }
            if ((Get-Age ([double]$wakeState.LastWake[$item.Target])) -lt $WakeCooldownSec) { continue }
            # A lead that marked itself ready is about to be restarted with -Ready, which would cut the turn handling
            # this message: it waits until after the restart (the restart clears the mark).
            if ($item.Kind -eq 'lead' -and $t.Row.Path -and (Invoke-LeadRestartFile $t.Row.Path @('status')) -match '^ready ') { continue }
            Send-WakeItem $item $t
        }
    }
    if ($wakeDirty) { Save-WakePending }
}

# ---- Handoff (see the header) ----

# Why the lead ($s: its servers.psd1 row, $Entry: its entry in a session list) cannot be moved for a handoff of kind
# $Kind now, '' when it can: 'busy' (not idle; also for go), 'just woken' (saved: a message was sent to it less than
# $HandoffWakeQuietSec s ago, not handled yet), else (saved) what Get-LeadActivity finds, as for a silent release
# restart: 'idle, <task> working', 'owner active', 'open question', 'no transcript', 'unknown'.
function Get-HandoffWhy($s, $Entry, [string]$Kind) {
    if (-not $Entry -or $Entry.status -ne 'idle') { return 'busy' }
    if ($Kind -eq 'go') { return '' }
    if ((Get-Age ([double]$wakeState.LastWake[[string]$Entry.name])) -lt $HandoffWakeQuietSec) { return 'just woken' }
    return (Get-LeadActivity $Entry (Get-BusyTask $s.Path))
}

# Drops the `handoff requested` lines of a lead's pending messages, sent but not seen yet ones too (the lead was moved:
# its fresh context must not get the request of the old one, so none is sent again), and their marks; a message left
# with no line is dropped.
function Remove-HandoffLines([string]$Name) {
    foreach ($item in @($wakePending)) {
        if ($item.Target -cne $Name -or $item.Kinds -cnotcontains 'handoff') { continue }
        $item.Lines = @($item.Lines | Where-Object { -not ([string]$_).StartsWith('handoff requested: ', [StringComparison]::Ordinal) })
        $item.Marks = @($item.Marks | Where-Object { $_.Kind -cne 'handoff' })
        $item.EventKeys = @($item.EventKeys | Where-Object { -not ([string]$_).StartsWith("$Name|handoff|", [StringComparison]::Ordinal) })
        $item.Kinds = @($item.Kinds | Where-Object { $_ -cne 'handoff' })
        if (-not $item.Lines.Count) { $wakePending.Remove($item) }
        $script:wakeDirty = $true
    }
    if ($wakeDirty) { Save-WakePending }
}

# Waits up to $HandoffStopWaitSec s until no background entry with this name has a pid and no claude.exe process of
# the session is left (a start in the gap would find the session still "running", see resume-lib.ps1
# Get-SessionProcessIds; every id of the session, Get-JobSessionIds). $true when gone. The round's $agents and
# $agentsText are left as they were.
function Wait-HandoffStopped([string]$Name, [string]$SessionId) {
    $ids = @(Get-JobSessionIds $SessionId)
    $until = (Get-Date).AddSeconds($HandoffStopWaitSec)
    while ($true) {
        $keep = $script:agentsText
        $list = Get-Agents -All
        $script:agentsText = $keep
        $listed = $null -eq $list -or @($list | Where-Object { $_.kind -eq 'background' -and $_.name -ceq $Name -and $_.pid }).Count
        if (-not $listed -and -not (Get-SessionProcessIds $ids).Count) { return $true }
        if ((Get-Date) -gt $until) { return $false }
        Start-Sleep -Milliseconds 500
    }
}

# One live lead ($s: its servers.psd1 row, $m: its entry in the round's session list) that may have left a handoff
# (`sessions.py handoff`): when it can be moved (Get-HandoffWhy) it is stopped and start-servers.ps1 -Handoff
# -HandoffSessionId moves it to a fresh context of the same session, or starts a fresh lead when that fails; a lead
# that is not quiet is asked once instead (`handoff request`). One try per marker (name and file) in this run.
function Invoke-HandoffCheck($s, $m) {
    $name = $s.Session
    if ($Once -or -not $s.Path -or -not (Test-Path -LiteralPath $s.Path)) { return }
    if ($onHold -or $starting -or (Test-Path -LiteralPath $hold)) { return }
    if ($noBansUntil[$name] -and (Get-Date) -lt $noBansUntil[$name]) { return }
    $r = Invoke-Sessions @('--project', $s.Path, 'handoff', 'status')
    if ($r.Code -eq 0 -and $r.Out -ceq 'none') {
        $handoffTried.Remove($name); $handoffWaited.Remove($name); $handoffAsked.Remove($name); $warnedOnce.Remove("handoff $name"); return
    }
    $parsed = ($r.Code -eq 0) -and ($r.Out -cmatch '^(saved|go) (\S+) (\d+)$')
    if (-not $parsed) {
        Write-WarnOnce "handoff $name" "cannot read the handoff status of $name (exit $($r.Code)): $($r.Out -replace '\s+', ' ')"
        return
    }
    $warnedOnce.Remove("handoff $name")
    $kind = $Matches[1]; $file = $Matches[2]; $age = [int]$Matches[3]
    if ($file -cnotmatch $HandoffNamePattern) { return }  # goes on a command line: only a bare .md name
    $key = "$name|$file"
    if ($handoffTried[$name] -ceq $key) { return }
    $sid = [string]$m.sessionId
    $why = Get-HandoffWhy $s $m $kind
    if ($why) {
        # Not quiet for another reason than a running turn or a message just sent: the lead is asked once, as for a
        # critical release (the `handoff` event of the wakes reaches it); it warns the owner and runs `handoff go`.
        if ($kind -eq 'saved' -and ($why -notin @('busy', 'just woken')) -and $handoffAsked[$name] -cne $key -and
                (Test-WakeLead $name $m.pid)) {
            $asked = Invoke-Sessions @('--project', $s.Path, 'handoff', 'request')
            if ($asked.Code -eq 0) {
                $handoffAsked[$name] = $key
                if ($asked.Out -clike 'handoff asked:*') { Write-Log "HANDOFF-ASKED $name $file ($why)" }
            } else { Write-WarnOnce "handoff request $name" "cannot ask $name for its handoff: $($asked.Out -replace '\s+', ' ')" }
        }
        if ($handoffWaited[$name] -cne $key) { $handoffWaited[$name] = $key; Write-Log "HANDOFF-WAIT $name $file" }
        return
    }
    # As restart-leads.ps1: a lead that could not be started again is not stopped.
    try { $gate = Get-LeadPermissionMode $s.Path } catch { Write-Log "WARN cannot check the hard bans for the handoff of ${name}: $_"; return }
    if (-not $gate.Start) { Register-NoBans $name "NO-BANS $name ($($gate.Reason))"; return }
    # A go lead wrote its 30-second warning right before `handoff go`: the rest of the 30 s is waited out here.
    if ($kind -eq 'go' -and $age -lt $ReadyWarnSec) { Start-Sleep -Seconds ($ReadyWarnSec - $age) }
    # Right before the stop: look again (a message may have woken the lead since the round's list was read).
    $keep = $script:agentsText
    $fresh = Get-Agents -All
    $script:agentsText = $keep
    $cur = $fresh | Where-Object { $_.kind -eq 'background' -and $_.name -ceq $name -and $_.pid } | Select-Object -First 1
    # The same job by its short id (stable; the sessionId the list shows changes with each /clear move).
    if (-not $cur -or [string]$cur.id -cne [string]$m.id -or (Get-HandoffWhy $s $cur $kind)) { return }
    $handoffTried[$name] = $key
    $null = claude stop $cur.id 2>&1
    $stopped = Wait-HandoffStopped $name $sid
    if ($stopped) {
        $words = @('-Only', $name, '-Handoff', $file, '-ConfigFile', $ConfigFile, '-StateDir', $StateDir,
            '-HandoffClearWaitSec', $HandoffClearWaitSec, '-HandoffStopWaitSec', $HandoffStopWaitSec)
        if ($sid) { $words += @('-HandoffSessionId', $sid) } else { Write-Log "HANDOFF-FALLBACK $name no session id" }
        $res = Invoke-Bounded 'powershell.exe' (@('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            (Join-Path $PSScriptRoot 'start-servers.ps1')) + $words) $HandoffMoveWaitSec
        $said = ($res.Out.Trim() -replace '\s+', ' ')
        $moved = $said -cmatch ('Resumed lead: ' + [regex]::Escape($name))
        if ($moved -or $said -cmatch ('Started lead: ' + [regex]::Escape($name))) {
            $cleared = Invoke-Sessions @('--project', $s.Path, 'handoff', 'clear')
            if ($cleared.Out -cne 'handoff cleared') { Write-Log "WARN handoff clear for $name failed: $($cleared.Out -replace '\s+', ' ')" }
            $wakeState.LastWake[$name] = Get-Now
            # The old id's size push mark is of no use any more: the list shows the new transcript's id from now on.
            if ($moved) { $wakeState.SizePushed.Remove($sid) }
            Save-WakeState
            Remove-HandoffLines $name
            $handoffWaited.Remove($name)  # the tried mark stays: a marker left by a failed clear is not moved again
            $handoffAsked.Remove($name)
            $noBansTold.Remove($name)
            if ($moved) { Write-Log "HANDOFF-CLEAR $name $sid $file" } else { Write-Log "HANDOFF $name $sid $file" }
        } elseif ($res.TimedOut) {
            # The marker and the tried mark stay, as for a failed move; a lead left down comes back by HEAL.
            Write-Critical ("HANDOFF-TIMEOUT {0} (no end in {1} s, stopped): {2}" -f $name, $HandoffMoveWaitSec, $said)
        } elseif ($said -cmatch ('NO-BANS ' + [regex]::Escape($name) + ' ')) {
            Register-NoBans $name $said
        } else {
            Write-Critical "HANDOFF-FAILED ${name}: $said"
        }
    } else {
        Write-Critical "HANDOFF-FAILED ${name}: still running after the stop"
    }
    # The list of the round is out of date now: the old lead is gone and a new one may run.
    $script:agents = Get-Agents -All
}

# SHA-256 (hex) over the files of $CodeFiles, or $null when one cannot be read (mid-merge, locked).
function Get-CodeFingerprint {
    try {
        $ms = New-Object IO.MemoryStream
        foreach ($f in $CodeFiles) { $b = [IO.File]::ReadAllBytes($f); $ms.Write($b, 0, $b.Length) }
        $sha = [Security.Cryptography.SHA256]::Create()
        return ([BitConverter]::ToString($sha.ComputeHash($ms.ToArray())) -replace '-', '').ToLowerInvariant()
    } catch { return $null }
}

# The pult version (plugin.json next to this script's plugin folder) or '?'.
function Get-PultVersion {
    $info = Get-PluginInfo (Join-Path $PSScriptRoot '..')
    if ($info) { return $info.Version }
    return '?'
}

# $null when every file of $CodeFiles parses, else the first problem as one line.
function Test-CodeParses {
    foreach ($f in $CodeFiles) {
        $tokens = $null; $errors = $null
        try { [void][System.Management.Automation.Language.Parser]::ParseFile($f, [ref]$tokens, [ref]$errors) }
        catch { return "cannot parse $(Split-Path -Leaf $f): $($_.Exception.Message)" }
        if ($errors -and $errors.Count) {
            return "$(Split-Path -Leaf $f) line $($errors[0].Extent.StartLineNumber): $($errors[0].Message)"
        }
    }
    return $null
}

# Starts a fresh copy of this script with the parameters this one got, hidden, as start-servers.ps1 does.
# Returns $null when the new copy is confirmed (a "WATCH started (pid N" line it wrote to the log, so it entered
# its loop), else the reason it was not. A copy that does not confirm within $RestartWaitSec is stopped when it
# still runs, so the caller can go on with the old code and never two watchers run.
$RestartWaitSec = 20
function Start-NewWatcher {
    $argList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"")
    foreach ($k in $scriptParams.Keys) {
        $v = $scriptParams[$k]
        if ($v -is [switch]) { if ($v) { $argList += "-$k" }; continue }
        $argList += "-$k"
        $argList += $(if ($v -is [string]) { "`"$v`"" } else { "$v" })
    }
    $before = if (Test-Path -LiteralPath $log) { (Get-Item -LiteralPath $log).Length } else { 0 }
    try { $proc = Start-Process -FilePath $RestartExe -WindowStyle Hidden -ArgumentList $argList -PassThru }
    catch { return "cannot start the new copy: $($_.Exception.Message)" }
    $until = (Get-Date).AddSeconds($RestartWaitSec)
    while ($true) {
        $gone = $proc.HasExited  # read before the log: a copy that wrote its line and exited still counts
        try {
            $fs = [IO.File]::Open($log, 'Open', 'Read', 'ReadWrite')
            try {
                if ($fs.Length -lt $before) { $before = 0 }  # the log was rotated meanwhile
                $null = $fs.Seek($before, 'Begin')
                $text = (New-Object IO.StreamReader($fs, [Text.Encoding]::UTF8)).ReadToEnd()
            } finally { $fs.Dispose() }
            foreach ($m2 in [regex]::Matches($text, 'WATCH started \(pid (\d+),')) {
                if ([int]$m2.Groups[1].Value -ne $PID) { return $null }
            }
        } catch { }  # the new copy is writing: look again
        if ($gone -or (Get-Date) -ge $until) { break }
        Start-Sleep -Milliseconds 300
    }
    $reason = "the new copy did not confirm with a WATCH started line"
    if ($gone) { $reason += " and exited (code $($proc.ExitCode))" }
    else { $reason += " within $RestartWaitSec s, stopped it"; try { Stop-Process -Id $proc.Id -Force -ErrorAction Stop } catch { $reason += " (cannot stop it: $($_.Exception.Message))" } }
    return $reason
}

Write-Log "WATCH started (pid $PID, every $IntervalSec s)"
$fpStart = Get-CodeFingerprint   # the code this run started with ($null: taken in the first round it can be read)
$fpPrev = $null                  # the fingerprint of the previous round
$fpSkipped = $null               # the fingerprint WATCH-RESTART-SKIPPED was logged for
$pultStart = Get-PultVersion
$versionFile = Join-Path $StateDir 'lead-versions.json'
$leadVer = @{}      # lead name -> @{ Pid; Started; Version; Ext }: the dev-kit version and the extension versions (name -> version) its process started on
$extWarned = @{}    # lead name -> the last error text logged for its extension list
try {
    if (Test-Path -LiteralPath $versionFile) {
        $saved = Get-Content -Raw -Encoding UTF8 -LiteralPath $versionFile -ErrorAction Stop | ConvertFrom-Json
        foreach ($e in $saved.PSObject.Properties) {
            $started = $e.Value.started
            if ($started -is [datetime]) { $started = $started.ToUniversalTime().ToString('o', [Globalization.CultureInfo]::InvariantCulture) }
            $x = $null  # no "ext" in the entry: saved before the extension check existed
            if ($e.Value.PSObject.Properties['ext']) {
                $x = @{}
                if ($e.Value.ext) { foreach ($q in $e.Value.ext.PSObject.Properties) { $x[$q.Name] = [string]$q.Value } }
            }
            $since = $e.Value.staleSince
            if ($since -is [datetime]) { $since = $since.ToString('yyyy-MM-dd', [Globalization.CultureInfo]::InvariantCulture) }
            $leadVer[$e.Name] = @{ Pid = [int]$e.Value.pid; Started = [string]$started; Version = [string]$e.Value.version; Ext = $x
                StaleSince = [string]$since }
        }
    }
} catch { Write-Log "WARN cannot read $versionFile : $_" }
$leadSeen = @{}     # lead name -> the pid whose start time was checked in this run
$ReadyMaxAgeSec = 600  # a ready mark older than this is not acted on (READY-EXPIRED)
$leadTried = @{}    # lead name -> the version a restart was tried for
$releaseKinds = @{} # "<lead>|<pid>|<installed dev-kit>" -> critical or routine (Get-ReleaseKind)
$deferLogged = @{}  # lead name -> "<pid>|<installed dev-kit>" RESTART-DEFERRED was logged for
$handoffTried = @{}   # lead name -> "<name>|<file>" of the handoff a move was tried for (one try per marker)
$handoffWaited = @{}  # lead name -> "<name>|<file>" of the handoff HANDOFF-WAIT was logged for
$handoffAsked = @{}   # lead name -> "<name>|<file>" of the handoff `handoff request` was run for
$lastVersion = $null
$versionWarned = $null
$pluginTime = $null
$prev = @{}
$downRounds = @{}   # name -> rounds in a row seen down
$noBansUntil = @{}  # name -> no start or restart is tried before this time (no hard bans on main)
$noBansTold = @{}   # name -> $true once the owner was told (Register-NoBans)
$heals = @{}        # name -> times of HEAL tries in the last hour
$gaveUp = @{}       # name -> $true after GIVEUP, until seen up
$taskClosed = @{}   # task session id -> rounds in a row seen closed
$taskHeals = @{}    # task session id -> times of HEAL-TASK tries in the last hour
$taskGaveUp = @{}   # task session id -> $true after GIVEUP-TASK, until seen alive
$limitSeen = @{}    # session id -> key of the usage-limit stop already logged (LIMIT)
$limitResume = @{}  # session id -> resume state of that stop (Invoke-LimitResume)
$holdLogged = $false
$lastCheck = Get-Date
$round = 0
$warnedOnce = @{}   # key -> the last WARN text logged for it (Write-WarnOnce)
$pultEvents = New-Object System.Collections.ArrayList  # critical lines of this round, for Pult (Write-Critical)
$registryDirs = @{} # project path -> its dev-kit state folder
$agentsText = $null # the session list of the round as read
$wakeDirty = $false
$lastSizeLog = 0.0  # epoch of the last SIZE lines
$wakePendingFile = Join-Path $StateDir 'wake-pending.json'
$wakeStateFile = Join-Path $StateDir 'wake-state.json'
$wakePending = New-Object System.Collections.ArrayList  # messages not delivered yet (New-WakeItem)
$lastUsageWrite = $null  # the usage log's last write time at the last forecast look (Invoke-LimitForecast)
$wakeState = @{ PultNote = $false; SizePushed = @{}; LastWake = @{} }  # SizePushed: session id -> tokens; LastWake: target -> epoch
try {
    if (Test-Path -LiteralPath $wakePendingFile) {
        $saved = Get-Content -Raw -Encoding UTF8 -LiteralPath $wakePendingFile -ErrorAction Stop | ConvertFrom-Json
        foreach ($o in @($saved)) { if ($o) { [void]$wakePending.Add((ConvertTo-WakeItem $o)) } }
    }
} catch { Write-Log "WARN cannot read $wakePendingFile : $_" }
try {
    if (Test-Path -LiteralPath $wakeStateFile) {
        $saved = Get-Content -Raw -Encoding UTF8 -LiteralPath $wakeStateFile -ErrorAction Stop | ConvertFrom-Json
        $wakeState.PultNote = [bool]$saved.PultNote
        foreach ($k in 'SizePushed', 'LastWake') {
            if ($saved.$k) { foreach ($q in $saved.$k.PSObject.Properties) { $wakeState[$k][$q.Name] = [double]$q.Value } }
        }
    }
} catch { Write-Log "WARN cannot read $wakeStateFile : $_" }

while ($true) {
    $round++
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='claude.exe' OR Name='node.exe'" |
        Where-Object { $_.CommandLine -match '\sremote-control\s' })
    $agents = Get-Agents -All  # also ended and closed sessions; the lead check below needs a pid, so it is unchanged
    # A full start-servers.ps1 run (logon, restart-leads.ps1) starts the leads itself: no restarts meanwhile.
    $starting = [bool](Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
        Where-Object { $_.CommandLine -like '*start-servers.ps1*' -and $_.CommandLine -notlike '*-Only*' })
    if (-not $Once -and -not $starting) { try { Clear-StaleHold } catch { Write-Log "WARN stale hold check failed: $_" } }
    $onHold = Test-Path -LiteralPath $hold
    if ($onHold -and -not $holdLogged) {
        Write-Log "HOLD on ($((Get-Content -Raw -LiteralPath $hold).Trim())): no restarts until start-servers.ps1 runs"
    } elseif (-not $onHold -and $holdLogged) {
        Write-Log 'HOLD off'
    }
    $holdLogged = $onHold
    $devKitVersion = Get-DevKitVersion
    $liveSessions = @{}  # session id -> name of each live lead and task session this round (for Invoke-LimitCheck)
    $liveTasks = @{}     # session id -> name of each live task session of a lead's registry (not a lead, not an owner's)
    if ($devKitVersion -and $devKitVersion -cne $lastVersion) { $leadTried.Clear(); $lastVersion = $devKitVersion }

    foreach ($s in $servers) {
        $name = $s.Session
        $procId = $null
        if ($s.Lead) {
            if ($null -eq $agents) { continue }  # unknown this round; logged as WARN
            $m = $agents | Where-Object { $_.kind -eq 'background' -and $_.name -ceq $name -and $_.pid } |
                Select-Object -First 1
            if ($m) { $procId = $m.pid; if ($m.sessionId) { $liveSessions[[string]$m.sessionId] = $name } }
        } else {
            $m = $procs | Where-Object { $_.CommandLine -like "*$name*" } | Select-Object -First 1
            if ($m) { $procId = $m.ProcessId }
        }
        $alive = [bool]$procId
        $was = $prev[$name]

        if ($null -eq $was) {
            Write-Log ("STATE {0}: {1}" -f $name, $(if ($alive) { "up, pid $procId" } else { 'down' }))
        } elseif ($was.Alive -and -not $alive) {
            Write-Log ("DOWN {0} (was pid {1}, seen up at {2:s})" -f $name, $was.Pid, $lastCheck)
            if ($s.Lead) {
                $all = $agents
                $last = $all | Where-Object { $_.name -ceq $name } |
                    Sort-Object { [int64]$_.startedAt } -Descending | Select-Object -First 1
                if ($last) { Write-Log "  session $($last.id) state: $($last.state)" }
            }
            try {
                Get-WinEvent -FilterHashtable @{ LogName = 'Application'; StartTime = $lastCheck.AddSeconds(-30) } -ErrorAction Stop |
                    Where-Object { $_.Message -match 'claude|node\.exe' } |
                    Select-Object -First 3 |
                    ForEach-Object { Write-Log ("  event {0} {1}: {2}" -f $_.Id, $_.ProviderName, ($_.Message -split "`n")[0].Trim()) }
            } catch { }  # no matching events
        } elseif (-not $was.Alive -and $alive) {
            Write-Log "UP $name, pid $procId"
        }
        $prev[$name] = @{ Alive = $alive; Pid = $procId }

        if ($s.Lead -and $alive -and $devKitVersion) {
            try { Invoke-LeadVersionCheck $s $m $devKitVersion } catch { Write-Log "WARN version check of $name failed: $_" }
        }
        if ($s.Lead -and $alive) {
            try { Invoke-HandoffCheck $s $m } catch { Write-Log "WARN handoff check of $name failed: $_" }
        }

        # Bring back an entry that is down for two rounds in a row (one round may be a start or a
        # restart in progress).
        # A planned stop or a running start resets the count, so the two rounds start after it.
        if ($alive -or $onHold -or $starting) { $downRounds[$name] = 0; if ($alive) { $gaveUp.Remove($name) }; continue }
        $downRounds[$name] = [int]$downRounds[$name] + 1
        if ($Once -or $downRounds[$name] -lt 2 -or $gaveUp[$name]) { continue }
        if (Test-Path -LiteralPath $hold) { continue }  # a stop began during this round
        if ($noBansUntil[$name] -and (Get-Date) -lt $noBansUntil[$name]) { $downRounds[$name] = 0; continue }  # blocked, not broken
        $tries = @($heals[$name] | Where-Object { $_ -and ((Get-Date) - $_).TotalHours -lt 1 })
        if ($tries.Count -ge $MaxHeals) {
            Write-Critical "GIVEUP $name ($MaxHeals restarts in the last hour did not keep it up; restart it by hand)"
            $gaveUp[$name] = $true
            continue
        }
        $heals[$name] = $tries + @(Get-Date)
        Write-Log ("HEAL {0} (down for {1} rounds, try {2} of {3})" -f $name, $downRounds[$name], ($tries.Count + 1), $MaxHeals)
        $res = Invoke-Bounded 'powershell.exe' @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
            (Join-Path $PSScriptRoot 'start-servers.ps1'), '-Only', $name, '-ConfigFile', $ConfigFile, '-StateDir', $StateDir) $HealWaitSec
        $said = ($res.Out.Trim() -replace '\s+', ' ')
        if ($res.TimedOut) {
            Write-Log ("HEAL-TIMEOUT {0} (no end in {1} s, stopped): {2}" -f $name, $HealWaitSec, $said)
            $downRounds[$name] = 0
            continue
        }
        $nameEsc = [regex]::Escape($name)
        if ($s.Lead -and $said -notmatch ('(Resumed|Started)( lead)?: ' + $nameEsc) -and $said -cmatch ('NO-BANS ' + $nameEsc + ' ')) {
            # Not a failed try: the lead is blocked until the owner says yes to the hard bans (Register-NoBans).
            $heals[$name] = $tries
            Register-NoBans $name $said
            $downRounds[$name] = 0
            continue
        }
        if ($said -match '(Resumed|Started)( lead)?: ') { $noBansTold.Remove($name) }
        if ($res.Code -ne 0 -or $said -notmatch '(Resumed|Started)( lead)?: ') {
            Write-Log ("HEAL-FAILED {0} (exit {1}): {2}" -f $name, $res.Code, $said)
        }
        $downRounds[$name] = 0  # give the start two rounds before the next try
    }

    try { Invoke-TaskHeal } catch { Write-Log "WARN task session check failed: $_" }
    if ($null -ne $agents) {
        try { Invoke-LimitCheck } catch { Write-Log "WARN usage-limit check failed: $_" }
    }
    try { Clear-StaleLocks } catch { Write-Log "WARN lock check failed: $_" }
    # The wakes (see the header): after the heal work, so a message never holds up a heal.
    if (-not $Once) {
        try { Invoke-WakePass } catch { Write-Log "WARN wake pass failed: $_" }
    }

    # Its own code changed (see the header): at the end of a round, so no work of this round is cut. Not
    # during a full start-servers.ps1 run (it may look for a running watcher); the check is made again next round.
    if (-not $Once -and -not $starting) {
        $fp = Get-CodeFingerprint
        if ($fp) {
            if (-not $fpStart) { $fpStart = $fp }
            if ($fp -cne $fpStart -and $fp -ceq $fpPrev -and $fp -cne $fpSkipped) {
                $why = Test-CodeParses
                if (-not $why) {
                    $pultNow = Get-PultVersion
                    $label = if ($pultNow -cne $pultStart) { "$pultStart -> $pultNow" } else { "$pultStart+$($fpStart.Substring(0, 8)) -> $pultNow+$($fp.Substring(0, 8))" }
                    $why = Start-NewWatcher
                    if (-not $why) { Write-Log "WATCH-RESTART $label"; exit 0 }  # logged once the new copy is confirmed
                }
                Write-Log "WATCH-RESTART-SKIPPED $why"
                $fpSkipped = $fp
            }
            $fpPrev = $fp
        } else { $fpPrev = $null }
    }
    $lastCheck = Get-Date
    if ($Once -or ($Rounds -gt 0 -and $round -ge $Rounds)) { break }
    Start-Sleep -Seconds $IntervalSec
}
