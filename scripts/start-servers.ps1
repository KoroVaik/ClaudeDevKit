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
# Every start and every server exit (with its exit code) goes to logs/servers.log.
# Keep this file saved as UTF-8 with BOM: Windows PowerShell 5.1 misreads Cyrillic otherwise.
$projects = (Import-PowerShellDataFile (Join-Path $PSScriptRoot 'servers.psd1')).Servers
$logDir = Join-Path (Split-Path $PSScriptRoot) 'logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir 'servers.log'
function Write-Log($msg) {
    Add-Content -LiteralPath $log -Encoding UTF8 -Value ('{0} {1}' -f (Get-Date -Format s), $msg)
}
Write-Log 'START-SCRIPT run'

# The watcher only logs; it never starts or stops anything.
$watching = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -like '*watch-servers.ps1*' }
if (-not $watching) {
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
        if ($liveLeads -contains $sessionName) { Write-Output "Already running: $sessionName"; continue }
        if (-not (Test-Path $p.Path)) { Write-Output "Folder missing, skipped: $($p.Path)"; continue }
        Push-Location $p.Path
        claude --bg --remote-control $sessionName --name $sessionName --permission-mode auto --model sonnet -- '/dev-kit:project-lead' | Select-Object -First 1
        Pop-Location
        Write-Log "STARTED $sessionName"
        Write-Output "Started lead: $sessionName"
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
    $cmd = "claude remote-control --name '$sessionName' --permission-mode auto --spawn same-dir"
    if ($p.Prefix) { $cmd += " --remote-control-session-name-prefix '$($p.Prefix)'" }
    # When the server process ends, its window writes the exit time and code to the log.
    $cmd += "; Add-Content -LiteralPath '$log' -Encoding UTF8 -Value ((Get-Date -Format s) + ' EXIT $sessionName code ' + `$LASTEXITCODE)"
    Start-Process powershell.exe -WindowStyle Hidden -WorkingDirectory $p.Path `
        -ArgumentList '-ExecutionPolicy', 'Bypass', '-Command', $cmd
    Write-Log "STARTED $sessionName"
    Write-Output "Started: $sessionName"
}
