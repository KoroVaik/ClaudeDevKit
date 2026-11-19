# Starts the project leads and the hub at logon.
# A project with Lead = $true gets a ready project lead: a background session "P: <name>" with
# Remote Control that loads the dev-kit project-lead skill on start (no server, so the phone shows
# one P per project). Stop it with `claude stop <id>` (ids: `claude agents`).
# Other entries get one Remote Control server each, in its own hidden PowerShell window; the window
# closes when the server stops.
# Stop the servers gracefully with stop-servers.ps1 (killing the process can lock
# the folder for minutes).
# Run at Windows logon by the Startup folder shortcut "Pult - project servers"
# (not a scheduled task: windows started by a task died after the task ended).

# The list of servers is servers.psd1 (shared with watch-servers.ps1).
# Every start and every server exit (with its exit code) goes to ~\.claude\pult\logs\servers.log.
# Keep this file saved as UTF-8 with BOM: Windows PowerShell 5.1 misreads Cyrillic otherwise.
# -Restarted: names of leads that restart-leads.ps1 stopped for a plugin update; when resumed, their
# first prompt carries the restart note (resume-lib.ps1, $RestartNote).
# -Only: start only these entries and nothing else (no watcher start, hold kept); watch-servers.ps1
# uses it to bring back a dead one. -ConfigFile and -StateDir point at another server list and state
# folder (for tests with a throwaway lead; defaults: servers.psd1 and ~\.claude\pult).
# A full run (no -Only) removes the hold file that stop-servers.ps1 and restart-leads.ps1 leave, at its end;
# the watcher restarts nothing while a full run is going on.
param([string[]]$Restarted, [string[]]$Only, [string]$ConfigFile, [string]$StateDir)
$Restarted = @($Restarted | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })  # -File passes one comma-joined string
$Only = @($Only | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if (-not $ConfigFile) { $ConfigFile = Join-Path $PSScriptRoot 'servers.psd1' }
if (-not $StateDir) { $StateDir = Join-Path $env:USERPROFILE '.claude\pult' }  # outside the plugin folder
. (Join-Path $PSScriptRoot 'resume-lib.ps1')
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
        try { $resumeId = Get-ResumeSessionId $sessionName $p.Path } catch { Write-Output "Could not look up a session to resume: $_" }
        $opt = @{}  # optional per-lead Prompt, Model, Effort from the server list
        foreach ($k in 'Prompt', 'Model', 'Effort') { if ($p[$k]) { $opt[$k] = $p[$k] } }
        $model = @{}
        foreach ($k in 'Model', 'Effort') { if ($p[$k]) { $model[$k] = $p[$k] } }
        # The same permission mode the lead's C sessions get (resume-lib.ps1, Get-LeadPermissionMode).
        $perm = @{ Mode = 'auto'; Reason = 'mode check failed' }
        try { $perm = Get-LeadPermissionMode $p.Path } catch { Write-Output "Could not check the lead's permission mode: $_" }
        Write-Log "MODE $sessionName $($perm.Mode) ($($perm.Reason))"
        if ($resumeId) {
            try { if (Set-LeadRespawnModel $sessionName $resumeId @model -Mode $perm.Mode) { Write-Log "MODEL $sessionName $(if ($p.Model) { $p.Model } else { $LeadModel })/$(if ($p.Effort) { $p.Effort } else { $LeadEffort })/$($perm.Mode)" } }
            catch { Write-Output "Could not set the lead's model: $_" }
        }
        $leadArgs = Get-LeadStartArgs $sessionName $resumeId -Restarted:($Restarted -ccontains $sessionName) @opt -Mode $perm.Mode
        claude @leadArgs | Select-Object -First 1
        Pop-Location
        if ($resumeId) {
            Write-Log "RESUMED $sessionName $resumeId"
            Write-Output "Resumed lead: $sessionName"
        } else {
            Write-Log "STARTED $sessionName"
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
    $base = "--name '$sessionName' --permission-mode auto"
    if ($p.Prefix) { $base += " --remote-control-session-name-prefix '$($p.Prefix)'" }
    # First try to reattach to the server's last session (--continue cannot take --spawn; same-dir
    # is the default). If that fails at once (nothing recorded in the last hours), start fresh.
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

# Pin every live lead: Claude's background service closes an unpinned background session that
# waits for input for 8 h (1 h without Remote Control), and sooner on low memory. Pins live in
# ~/.claude/jobs/pins.json, a JSON array of short ids (the `id` from `claude agents --json`),
# the same list Ctrl+T toggles in `claude agents`. A long low-memory spell can still close them.
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
