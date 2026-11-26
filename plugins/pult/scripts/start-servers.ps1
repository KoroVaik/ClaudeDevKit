# Starts the project leads and the hub at logon.
# A project with Lead = $true gets a ready project lead: a background session "L: <name>" with
# Remote Control that loads the dev-kit project-lead skill on start (no server, so the phone shows
# one lead per project). Stop it with `claude stop <id>` (ids: `claude agents`).
# A lead still running under its old name "P: <name>" counts as the running lead "L: <name>" (resume-lib.ps1,
# Test-LeadEntryName): not started again. A stopped one is resumed under the new name when no "L: <name>" session
# exists: its job's saved name is rewritten first (Set-LeadStateName, log RENAMED <old> -> <new> <id>), so its history stays.
# Other entries get one Remote Control server each, in its own hidden PowerShell window; the window
# closes when the server stops.
# Stop the servers gracefully with stop-servers.ps1 (plugins/dev-kit/claude-facts.md, "Stopping a Remote
# Control server: Ctrl-C is graceful, a kill can lock the folder").
# Run at Windows logon by the Startup folder shortcut "Pult - project servers"
# (not a scheduled task: plugins/dev-kit/claude-facts.md, "Windows scheduled tasks start hidden windows that die when the task ends").

# The list of servers is servers.psd1 (shared with watch-servers.ps1).
# Every start and every server exit (with its exit code) goes to ~\.claude\pult\logs\servers.log.
# Keep this file saved as UTF-8 with BOM (plugins/dev-kit/claude-facts.md, "Windows PowerShell 5.1 misreads Cyrillic in a script saved without a BOM").
# -Restarted: names of leads that restart-leads.ps1 stopped for a plugin update; when resumed, their
# first prompt carries the restart note (resume-lib.ps1, $RestartNote).
# -Only: start only these entries and nothing else (no watcher start, hold kept); watch-servers.ps1
# uses it to bring back a dead one. -ConfigFile and -StateDir point at another server list and state
# folder (for tests with a throwaway lead; defaults: servers.psd1 and ~\.claude\pult).
# A full run (no -Only) removes the hold file that stop-servers.ps1 and restart-leads.ps1 leave, at its end;
# the watcher restarts nothing while a full run is going on.
# -Handoff <file>: only with exactly one -Only name (else an error and exit 1). Without -HandoffSessionId (below), or
# when that move fails, that lead is started fresh, never resumed (no Set-LeadRespawnModel, no wait for the old session
# to go), with the file name at the end of its first
# prompt (`handoff: <file>`, resume-lib.ps1 Get-LeadStartArgs); the file is a bare .md name. The log says
# STARTED <name> handoff <file>, the output stays `Started lead: <name>`. The hard-ban gate and the pin are as for
# any start. The watcher runs this when a lead left a handoff (watch-servers.ps1, Invoke-HandoffCheck).
# -HandoffSessionId <id> (only with -Handoff): the session the watcher just stopped is moved without a new session, so
# no phone push (plans/push-noise.md): after the hard-ban gate and the saved flags (Set-LeadRespawnModel) it is resumed
# with `/clear` (resume-lib.ps1 Get-LeadClearArgs); the turn has ended once its job's linkScanPath names a new file and
# the session list shows it idle (Test-ClearEnded, up to -HandoffClearWaitSec s, default 120); it is stopped again (a
# resumed session stays alive while idle, and a resume of a running one starts a copy) and waited for up to
# -HandoffStopWaitSec s (default 60); then it is resumed with the handoff prompt (Get-LeadStartArgs -ResumeHandoff).
# After a /clear the session list shows the new transcript's id as the entry's sessionId, while the job keeps its first
# one: every resume uses the job's own id (Get-JobResumeId; also for a plain resume above), the session's list entry is
# found by the job's short id or any id of the session (Get-SessionEntries) and stopped by that short id. The move
# resolves the job's own id once from the passed id, before the /clear moves resumeSessionId on, and looks everything
# up by it; the stop waits also for the ids seen before the /clear.
# Moved: the log says RESUMED <name> <id> handoff <file>, the output `Resumed lead: <name>`. Any failure on the way (no
# job state, a resume that exits with an error or starts a copy, which is stopped and removed, the turn not ended in
# time, a stop that does not finish): HANDOFF-FALLBACK <name> <reason> in the log, the session is stopped if it runs,
# and the lead is started fresh as above (one push). A session still running after that stop: STILL-RUNNING <name>
# <id>, output `Not started, still running after the stop: <name>`, and nothing is started (never two leads of one name).
param([string[]]$Restarted, [string[]]$Only, [string]$ConfigFile, [string]$StateDir, [string]$Handoff,
    [string]$HandoffSessionId, [int]$HandoffClearWaitSec = 120, [int]$HandoffStopWaitSec = 60)
$Restarted = @($Restarted | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })  # -File passes one comma-joined string
$Only = @($Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if (-not $ConfigFile) { $ConfigFile = Join-Path $PSScriptRoot 'servers.psd1' }
if (-not $StateDir) { $StateDir = Join-Path $env:USERPROFILE '.claude\pult' }  # outside the plugin folder
. (Join-Path $PSScriptRoot 'resume-lib.ps1')
if ($Handoff) {
    if ($Only.Count -ne 1) { Write-Output 'Error: -Handoff needs exactly one -Only name.'; exit 1 }
    if ($Handoff -cnotmatch $HandoffNamePattern) { Write-Output "Error: -Handoff is not a bare .md file name: $Handoff"; exit 1 }
}
if ($HandoffSessionId) {
    if (-not $Handoff) { Write-Output 'Error: -HandoffSessionId needs -Handoff.'; exit 1 }
    if ($HandoffSessionId -cnotmatch '^[0-9A-Za-z-]+$') { Write-Output "Error: -HandoffSessionId is not a session id: $HandoffSessionId"; exit 1 }
}
$projects = (Import-PowerShellDataFile $ConfigFile).Servers
foreach ($p in $projects) { if ($p.Hub) { $p.Path = $env:USERPROFILE } }  # the hub server runs in the home folder
if ($Only) { $projects = @($projects | Where-Object { $Only -ccontains $_.Session }) }
$logDir = Join-Path $StateDir 'logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir 'servers.log'
function Write-Log($msg) {
    Add-Content -LiteralPath $log -Encoding UTF8 -Value ('{0} {1}' -f (Get-Date -Format s), $msg)
}
if ($Only) { Write-Log "START-SCRIPT run for $($Only -join ', ')" } else { Write-Log 'START-SCRIPT run' }
$hold = Join-Path $StateDir 'hold'

# The parsed `claude agents --json --all`, or $null when it cannot be read.
function Get-AgentList {
    try { return @((claude agents --json --all | Out-String | ConvertFrom-Json) | ForEach-Object { $_ }) } catch { return $null }
}

# Stops the copy a resume started instead of waking the session, and removes it once it exited.
function Remove-ResumeCopy([string]$Name, [string]$Copy, [string]$Note) {
    claude stop $Copy | Out-Null
    # rm works only once the copy has exited (plugins/dev-kit/claude-facts.md, "A just-stopped session keeps its processes for about 1 s").
    $rmUntil = (Get-Date).AddSeconds(20)
    do { Start-Sleep -Seconds 1; $rm = (claude rm $Copy 2>&1 | Out-String) }
    while ($rm -notmatch 'removed' -and (Get-Date) -lt $rmUntil)
    Write-Log "COPY-REMOVED $Name $Copy ($Note)"
}

# One `claude` resume of a lead for the handoff move: '' when it woke the session, else why not (an exit code, or a
# copy, which is removed).
function Invoke-HandoffResume([string]$Name, [string[]]$ResumeArgs) {
    $said = @(claude @ResumeArgs 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
    $copy = Get-ResumeCopyId ($said -join "`n")
    if ($copy) { Remove-ResumeCopy $Name $copy 'handoff move'; return "claude started a copy $copy" }
    if ($code) { return "exit $code ($($said | Where-Object { $_ -notlike 'note:*' -and $_.Trim() } | Select-Object -First 1))" }
    return ''
}

# Stops the lead's session when it runs (by the short id of its list entry, Get-SessionEntries: after a /clear the
# entry's sessionId is the new transcript's id) and waits until no list entry of that name has a pid and no process
# holds one of its ids: those of its job now (Get-JobSessionIds) and $KnownIds (the ids seen before the /clear, which a
# process started then may still carry). $JobId: the job's first sessionId (Get-JobResumeId), the one id that stays
# across moves. '' when it is stopped, else the reason.
function Stop-HandoffSession([string]$Name, [string]$JobId, [string[]]$KnownIds) {
    $ids = @(@(Get-JobSessionIds $JobId) + @($KnownIds) | Where-Object { $_ } | Select-Object -Unique)
    $until = (Get-Date).AddSeconds($HandoffStopWaitSec)
    $stopped = $false
    while ($true) {
        $list = Get-AgentList
        $live = @($list | Where-Object { $_ -and $_.kind -eq 'background' -and (Test-LeadEntryName ([string]$_.name) $Name) -and $_.pid })
        if ($null -ne $list -and -not $live.Count -and -not (Get-SessionProcessIds $ids).Count) { return '' }
        if (-not $stopped -and $null -ne $list) {
            foreach ($e in @(Get-SessionEntries $list $Name $JobId)) { $null = claude stop $e.id 2>&1 }
            $stopped = $true
        }
        if ((Get-Date) -gt $until) { return "still running $HandoffStopWaitSec s after the stop" }
        Start-Sleep -Milliseconds 500
    }
}

# The handoff move without a new session (see the header, -HandoffSessionId). $JobId: the job's first sessionId
# (Get-JobResumeId of the id the watcher passed). Every look-up goes by it: the /clear moves the job's resumeSessionId
# and the list's sessionId to a new id, so the passed one (the list's, new after an earlier move) is lost. '' when the
# lead was moved, else why not.
function Invoke-HandoffClear([string]$Name, [string]$JobId, [string[]]$KnownIds, [string]$File, $Opt) {
    $job = Get-JobState $JobId
    if (-not $job) { return 'no job state for the session' }
    $scanBefore = [string]$job.linkScanPath
    $why = Invoke-HandoffResume $Name (Get-LeadClearArgs $JobId)
    if ($why) { return "the /clear resume failed: $why" }
    $until = (Get-Date).AddSeconds($HandoffClearWaitSec)
    while (-not (Test-ClearEnded $Name $JobId $scanBefore (Get-AgentList))) {
        if ((Get-Date) -gt $until) { return "the /clear turn did not end in $HandoffClearWaitSec s" }
        Start-Sleep -Seconds 1
    }
    $why = Stop-HandoffSession $Name $JobId $KnownIds
    if ($why) { return "after the /clear: $why" }
    $why = Invoke-HandoffResume $Name (Get-LeadStartArgs $Name $JobId -Handoff $File -ResumeHandoff @Opt)
    if ($why) { return "the handoff resume failed: $why" }
    return ''
}

# The watcher restarts a dead entry of the list (watch-servers.ps1).
$watching = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -like '*watch-servers.ps1*' }
if (-not $Only -and -not $watching) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile', '-ExecutionPolicy',
        'Bypass', '-File', "`"$(Join-Path $PSScriptRoot 'watch-servers.ps1')`""
    Write-Output 'Started: watcher'
}

$running = Get-CimInstance Win32_Process -Filter "Name='node.exe' OR Name='claude.exe'" |
    Where-Object { $_.CommandLine -match '\sremote-control\s' } |  # the server subcommand, not the --remote-control flag of a lead
    ForEach-Object { $_.CommandLine }

# Background sessions that are still alive (not stopped or done), by name.
$liveLeads = @()
try {
    $liveLeads = (claude agents --json | Out-String | ConvertFrom-Json) |
        Where-Object { $_.kind -eq 'background' -and $_.pid } |
        ForEach-Object { $_.name }
} catch { Write-Output "Could not list background sessions: $_" }

foreach ($p in $projects) {
    $sessionName = $p.Session
    if ($p.Lead) {
        # A lead still running under its old name counts as running (resume-lib.ps1, Test-LeadEntryName).
        if (Test-AnyLeadEntryName $sessionName @($liveLeads | Where-Object { $_ } | ForEach-Object { [string]$_ })) { Write-Output "Already running: $sessionName"; continue }
        # Look again right before the start: the watcher or another run may have started it meanwhile.
        try {
            $now = @((claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ } |
                Where-Object { $_.kind -eq 'background' -and $_.pid -and (Test-LeadEntryName ([string]$_.name) $sessionName) })
            if ($now) { Write-Output "Already running: $sessionName"; continue }
        } catch { }
        if (-not (Test-Path $p.Path)) { Write-Output "Folder missing, skipped: $($p.Path)"; continue }
        Push-Location $p.Path
        # Continue the previous conversation of this lead when one exists (stopped or finished).
        $resumeId = $null
        if (-not $Handoff) {  # a handoff lead starts empty: it never resumes the full conversation
            # The session of this name, else the one with the lead's old name "P: <name>" (renamed below, before the resume).
            try { $found = Get-LeadResumeEntry $sessionName $p.Path; if ($found) { $resumeId = $found.SessionId } } catch { Write-Output "Could not look up a session to resume: $_" }
            if ($resumeId) { $resumeId = Get-JobResumeId $resumeId }  # after a /clear the list shows another id than the job's
        }
        $opt = @{}  # optional per-lead Prompt, Model, Effort from the server list
        foreach ($k in 'Prompt', 'Model', 'Effort') { if ($p[$k]) { $opt[$k] = $p[$k] } }
        $model = @{}
        foreach ($k in 'Model', 'Effort') { if ($p[$k]) { $model[$k] = $p[$k] } }
        # The one permission mode, bypassPermissions, only with hard bans on main (resume-lib.ps1,
        # Get-LeadPermissionMode); no fallback: a failed check counts as "do not start".
        $perm = @{ Start = $false; Mode = ''; Reason = 'the hard-ban check failed' }
        try { $perm = Get-LeadPermissionMode $p.Path } catch { Write-Output "Could not check the lead's permission mode: $_" }
        if (-not $perm.Start) {
            # The watcher reads this line from the output (watch-servers.ps1) and the hub shows the log line.
            Write-Log "NO-BANS $sessionName ($($perm.Reason))"
            Write-Output "NO-BANS $sessionName ($($perm.Reason)): lead not started. Hard bans are missing on main. Hub: show the owner the exact lines, on his yes write .claude/hard-bans.json in the project's main checkout and run: $(Get-AddBansCommand $p.Path)"
            Pop-Location; continue
        }
        Write-Log "MODE $sessionName $($perm.Mode) ($($perm.Reason))"
        if ($Handoff -and $HandoffSessionId) {
            # Resolved once, before the /clear changes the job's resumeSessionId (Invoke-HandoffClear).
            $jobId = Get-JobResumeId $HandoffSessionId
            $knownIds = @(@($HandoffSessionId) + @(Get-JobSessionIds $HandoffSessionId))
            try { if (Set-LeadStateName $sessionName $jobId) { Write-Log "RENAMED $(Get-LegacyLeadName $sessionName) -> $sessionName $jobId" } }
            catch { Write-Output "Could not rename the lead's job: $_" }
            try { if (Set-LeadRespawnModel $sessionName $jobId @model) { Write-Log "MODEL $sessionName $(if ($p.Model) { $p.Model } else { $LeadModel })/$(if ($p.Effort) { $p.Effort } else { $LeadEffort })/$($perm.Mode)" } }
            catch { Write-Output "Could not set the lead's model: $_" }
            $why = 'the move failed'
            try { $why = Invoke-HandoffClear $sessionName $jobId $knownIds $Handoff $opt } catch { $why = "the move failed: $_" }
            if (-not $why) {
                Pop-Location
                Write-Log "RESUMED $sessionName $HandoffSessionId handoff $Handoff"
                Write-Output "Resumed lead: $sessionName"
                continue
            }
            Write-Log "HANDOFF-FALLBACK $sessionName $why"
            if (Stop-HandoffSession $sessionName $jobId $knownIds) {
                Pop-Location
                Write-Log "STILL-RUNNING $sessionName $HandoffSessionId"
                Write-Output "Not started, still running after the stop: $sessionName"
                continue
            }
        }
        # A lead stopped a moment ago may still have its processes (plugins/dev-kit/claude-facts.md, "A just-stopped
        # session keeps its processes for about 1 s"; resume-lib.ps1, Get-SessionProcessIds). Wait until they are gone, before the saved flags are set.
        if ($resumeId -and -not (Wait-SessionGone $resumeId)) {
            Write-Log "STILL-RUNNING $sessionName $resumeId"
            Write-Output "Still running after the stop, not resumed: $sessionName"
            Pop-Location; continue
        }
        if ($resumeId) {
            # A job that still has the old name "P: <name>" gets the new one first, so it resumes as "L: <name>".
            try { if (Set-LeadStateName $sessionName $resumeId) { Write-Log "RENAMED $(Get-LegacyLeadName $sessionName) -> $sessionName $resumeId" } }
            catch { Write-Output "Could not rename the lead's job: $_" }
            try { if (Set-LeadRespawnModel $sessionName $resumeId @model) { Write-Log "MODEL $sessionName $(if ($p.Model) { $p.Model } else { $LeadModel })/$(if ($p.Effort) { $p.Effort } else { $LeadEffort })/$($perm.Mode)" } }
            catch { Write-Output "Could not set the lead's model: $_" }
        }
        $leadArgs = Get-LeadStartArgs $sessionName $resumeId -Restarted:($Restarted -ccontains $sessionName) -Handoff $Handoff @opt
        $copyLeft = $null
        $exitCode = 0
        for ($try = 1; $try -le 2; $try++) {
            $said = @(claude @leadArgs 2>&1 | ForEach-Object { "$_" })
            $exitCode = $LASTEXITCODE  # right after the call: the lines below are cmdlets, but keep it safe
            $said | Where-Object { $_ -notlike 'note:*' } | Select-Object -First 1
            $copyLeft = if ($resumeId) { Get-ResumeCopyId ($said -join "`n") } else { $null }
            if (-not $copyLeft) { break }
            # The resume started a copy: remove it, wait for the lead's process, retry once.
            Remove-ResumeCopy $sessionName $copyLeft "try $try"
            $null = Wait-SessionGone $resumeId
        }
        Pop-Location
        if ($copyLeft) {
            Write-Log "NOT-RESUMED $sessionName $resumeId (claude started a copy twice)"
            Write-Output "Not resumed, claude started a copy twice: $sessionName"
            continue
        }
        if ($exitCode) {
            # claude refused to start or resume it (for example the bypass disclaimer is not accepted, see
            # plugins/dev-kit/claude-facts.md, "`claude --bg` with `bypassPermissions` fails until the owner accepts a disclaimer once"): not started.
            $first = ($said | Where-Object { $_ -notlike 'note:*' -and $_.Trim() } | Select-Object -First 1)
            Write-Log "START-FAILED $sessionName exit $exitCode ($first)"
            Write-Output "Start failed, exit ${exitCode}: ${sessionName}: $first"
            continue
        }
        if ($resumeId) {
            Write-Log "RESUMED $sessionName $resumeId"
            Write-Output "Resumed lead: $sessionName"
        } else {
            Write-Log "STARTED $sessionName$(if ($Handoff) { " handoff $Handoff" })"
            Write-Output "Started lead: $sessionName"
        }
        continue
    }
    if ($running | Where-Object { $_ -like "*$sessionName*" }) {
        Write-Output "Already running: $sessionName"
        continue
    }
    if (-not (Test-Path $p.Path)) {
        Write-Output "Folder missing, skipped: $($p.Path)"
        continue
    }
    $base = "--name '$sessionName' --permission-mode $LeadPermissionMode"
    if ($p.Prefix) { $base += " --remote-control-session-name-prefix '$($p.Prefix)'" }
    # First try to reattach to the server's last session (no --spawn: plugins/dev-kit/claude-facts.md,
    # "`claude remote-control --continue` cannot be combined with `--spawn`"). If that fails at once (nothing recorded in the last hours), start fresh.
    $cmd = "`$t = Get-Date; claude remote-control --continue $base; " +
        "if (`$LASTEXITCODE -ne 0 -and ((Get-Date) - `$t).TotalSeconds -lt 20) { " +
        "Add-Content -LiteralPath '$log' -Encoding UTF8 -Value ((Get-Date -Format s) + ' CONTINUE-FAILED $sessionName, starting fresh'); " +
        "claude remote-control $base --spawn same-dir }"
    # When the server process ends, its window writes the exit time and code to the log.
    $cmd += "; Add-Content -LiteralPath '$log' -Encoding UTF8 -Value ((Get-Date -Format s) + ' EXIT $sessionName code ' + `$LASTEXITCODE)"
    Start-Process powershell.exe -WindowStyle Hidden -WorkingDirectory $p.Path `
        -ArgumentList '-ExecutionPolicy', 'Bypass', '-Command', $cmd
    Write-Log "STARTED $sessionName"
    Write-Output "Started: $sessionName"
}

# Pin every live lead, so Claude's background service does not close it while it waits (plugins/dev-kit/claude-facts.md,
# "Claude closes an idle background session after 8 h of waiting, 1 h without Remote Control", "Pinned sessions are not
# closed when idle"). Pins are a JSON array of short ids (the `id` from `claude agents --json`) in ~/.claude/jobs/pins.json.
$leadNames = @($projects | Where-Object { $_.Lead } | ForEach-Object { $_.Session })
if ($leadNames) {
    Start-Sleep -Seconds 3
    try {
        $pinFile = Join-Path $env:USERPROFILE '.claude\jobs\pins.json'
        $pins = @()
        if (Test-Path $pinFile) { $pins = @(Get-Content -Raw $pinFile | ConvertFrom-Json) | Where-Object { $_ } }
        $ids = @((claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ } |
            Where-Object { $_.kind -eq 'background' -and $_.pid -and (Test-AnyLeadEntryName ([string]$_.name) $leadNames) } |
            ForEach-Object { $_.id })
        $new = @($ids | Where-Object { $pins -notcontains $_ })
        if ($new) {
            $all = @($pins) + $new
            $json = '[' + (($all | ForEach-Object { '"' + $_ + '"' }) -join ',') + ']'
            [IO.File]::WriteAllText($pinFile, $json, (New-Object System.Text.UTF8Encoding $false))
            Write-Log "PINNED $($new -join ', ')"
        }
        Write-Output "Pinned leads: $($ids -join ', ')"
    } catch { Write-Output "Could not pin leads: $_" }
    # The app keeps the title a lead had when it first connected; a renamed lead ("P: X" -> "L: X") gets its title
    # set to its name here (sync-app-titles.py; plugins/dev-kit/claude-facts.md, "The app's session title is set once,
    # at the first Remote Control connect"). Already right: no change.
    try {
        $sync = Join-Path $PSScriptRoot 'sync-app-titles.py'
        foreach ($line in @(& python -I -X utf8 $sync @leadNames 2>&1 | ForEach-Object { [string]$_ })) {
            if ($line -cmatch '^TITLE(-FAILED)? ') { Write-Log $line }
            Write-Output $line
        }
    } catch { Write-Output "Could not set the leads' app titles: $_" }
}
if (-not $Only -and (Test-Path $hold)) { Remove-Item -LiteralPath $hold -Force; Write-Log 'HOLD off' }
