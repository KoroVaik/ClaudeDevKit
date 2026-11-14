# Watches the servers from servers.psd1 and writes every change to logs/servers.log:
# STATE (first look), DOWN (with what is known about why), UP. It never starts or stops anything.
# start-servers.ps1 starts it at logon in a hidden window. -Once: one check, then exit (for tests).
# Keep this file saved as UTF-8 with BOM.
param([int]$IntervalSec = 60, [switch]$Once)

$servers = (Import-PowerShellDataFile (Join-Path $PSScriptRoot 'servers.psd1')).Servers
$logDir = Join-Path (Split-Path $PSScriptRoot) 'logs'
New-Item -ItemType Directory -Force $logDir | Out-Null
$log = Join-Path $logDir 'servers.log'

function Write-Log($msg) {
    if ((Test-Path $log) -and (Get-Item $log).Length -gt 1MB) {
        Move-Item -Force $log "$log.old"
    }
    Add-Content -LiteralPath $log -Encoding UTF8 -Value ('{0} {1}' -f (Get-Date -Format s), $msg)
}

function Get-Agents([switch]$All) {
    try {
        $out = if ($All) { claude agents --json --all } else { claude agents --json }
        return @($out | Out-String | ConvertFrom-Json)
    } catch {
        Write-Log "WARN cannot list background sessions: $_"
        return $null
    }
}

Write-Log "WATCH started (pid $PID, every $IntervalSec s)"
$prev = @{}
$lastCheck = Get-Date

while ($true) {
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='claude.exe' OR Name='node.exe'" |
        Where-Object { $_.CommandLine -match '\sremote-control\s' })
    $agents = Get-Agents

    foreach ($s in $servers) {
        $name = $s.Session
        $procId = $null
        if ($s.Lead) {
            if ($null -eq $agents) { continue }  # unknown this round; logged as WARN
            $m = $agents | Where-Object { $_.kind -eq 'background' -and $_.name -eq $name -and $_.pid } |
                Select-Object -First 1
            if ($m) { $procId = $m.pid }
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
                $all = Get-Agents -All
                $last = $all | Where-Object { $_.name -eq $name } |
                    Sort-Object startedAt -Descending | Select-Object -First 1
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
    }

    $lastCheck = Get-Date
    if ($Once) { break }
    Start-Sleep -Seconds $IntervalSec
}
