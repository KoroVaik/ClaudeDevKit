# Starts the project leads and the hub at logon.
# A project with Lead = $true gets a ready project lead: a background session "P: <name>" with
# Remote Control that loads the dev-kit project-lead skill on start (no server, so the phone shows
# one P per project). Stop it with `claude stop <id>` (ids: `claude agents`).
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
# -Handoff <file>: only with exactly one -Only name (else an error and exit 1). That lead is started fresh, never
# resumed (no Set-LeadRespawnModel, no wait for the old session to go), with the file name at the end of its first
# prompt (`handoff: <file>`, resume-lib.ps1 Get-LeadStartArgs); the file is a bare .md name. The log says
# STARTED <name> handoff <file>, the output stays `Started lead: <name>`. The hard-ban gate and the pin are as for
# any start. The watcher runs this when a lead left a handoff (watch-servers.ps1, Invoke-HandoffCheck).
param([string[]]$Restarted, [string[]]$Only, [string]$ConfigFile, [string]$StateDir, [string]$Handoff)
$Restarted = @($Restarted | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })  # -File passes one comma-joined string
$Only = @($Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if (-not $ConfigFile) { $ConfigFile = Join-Path $PSScriptRoot 'servers.psd1' }
if (-not $StateDir) { $StateDir = Join-Path $env:USERPROFILE '.claude\pult' }  # outside the plugin folder
. (Join-Path $PSScriptRoot 'resume-lib.ps1')
if ($Handoff) {
    if ($Only.Count -ne 1) { Write-Output 'Error: -Handoff needs exactly one -Only name.'; exit 1 }
    if ($Handoff -cnotmatch $HandoffNamePattern) { Write-Output "Error: -Handoff is not a bare .md file name: $Handoff"; exit 1 }
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

# The watcher restarts a dead entry of the list (watch-servers.ps1).
$watching = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -like '*watch-servers.ps1*' }
if (-not $Only -and -not $watching) {
    Start-Process powershell.exe -WindowStyle Hidden -ArgumentList '-NoProfile', '-ExecutionPolicy',
        'Bypass', '-File', "`"$(Join-Path $PSScriptRoot 'watch-servers.ps1')`""
    Write-Output 'Started: watcher'
}

$running = Get-CimInstance Win32_Process -Filter "Name='node.exe' OR Name='claude.exe'" |
    Where-Object { $_.CommandLine -match '\sremote-control\s' } |  # the server subcommand, not the --remote-control flag of a P
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
        if ($liveLeads -ccontains $sessionName) { Write-Output "Already running: $sessionName"; continue }
        # Look again right before the start: the watcher or another run may have started it meanwhile.
        try {
            $now = @((claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ } |
                Where-Object { $_.kind -eq 'background' -and $_.pid -and $_.name -ceq $sessionName })
            if ($now) { Write-Output "Already running: $sessionName"; continue }
        } catch { }
        if (-not (Test-Path $p.Path)) { Write-Output "Folder missing, skipped: $($p.Path)"; continue }
        Push-Location $p.Path
        # Continue the previous conversation of this lead when one exists (stopped or finished).
        $resumeId = $null
        if (-not $Handoff) {  # a handoff lead starts empty: it never resumes the full conversation
            try { $resumeId = Get-ResumeSessionId $sessionName $p.Path } catch { Write-Output "Could not look up a session to resume: $_" }
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
        # A lead stopped a moment ago may still have its processes (plugins/dev-kit/claude-facts.md, "A just-stopped
        # session keeps its processes for about 1 s"; resume-lib.ps1, Get-SessionProcessIds). Wait until they are gone, before the saved flags are set.
        if ($resumeId -and -not (Wait-SessionGone $resumeId)) {
            Write-Log "STILL-RUNNING $sessionName $resumeId"
            Write-Output "Still running after the stop, not resumed: $sessionName"
            Pop-Location; continue
        }
        if ($resumeId) {
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
            claude stop $copyLeft | Out-Null
            $rmUntil = (Get-Date).AddSeconds(20)  # rm works only once the copy has exited (see the facts entry above)
            do { Start-Sleep -Seconds 1; $rm = (claude rm $copyLeft 2>&1 | Out-String) }
            while ($rm -notmatch 'removed' -and (Get-Date) -lt $rmUntil)
            Write-Log "COPY-REMOVED $sessionName $copyLeft (try $try)"
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
            Where-Object { $_.kind -eq 'background' -and $_.pid -and $leadNames -contains $_.name } |
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
}
if (-not $Only -and (Test-Path $hold)) { Remove-Item -LiteralPath $hold -Force; Write-Log 'HOLD off' }
