# Watches the servers from servers.psd1 and writes every change to ~\.claude\pult\logs\servers.log
# (the health log the Pult hub reads): STATE (first look), DOWN (with what is known about why), UP.
# It fixes two mechanical problems itself:
# - A lead or server of the list that is down for two rounds in a row is brought back by
#   start-servers.ps1 -Only <name> (the same resume as at logon): HEAL. At most $MaxHeals tries per
#   hour per entry, then GIVEUP until it is seen up again. A hold file (~\.claude\pult\hold, left by
#   stop-servers.ps1 and restart-leads.ps1, removed by a full start-servers.ps1 run) pauses this: HOLD.
#   It never touches a session that is not in the list (task sessions, owner sessions).
# - A dev-kit lock file whose owner is gone is removed: UNLOCK (see Clear-StaleLocks).
# start-servers.ps1 starts it at logon in a hidden window. -Once: one check, then exit; -Rounds N:
# N checks, then exit (both for tests; -Once never restarts anything).
# -ConfigFile / -StateDir / -DevKitStateDir: another server list, Pult state folder and dev-kit state
# folder (for tests with a throwaway lead).
# Keep this file saved as UTF-8 with BOM.
param([int]$IntervalSec = 60, [switch]$Once, [int]$Rounds = 0, [int]$MaxHeals = 3,
    [string]$ConfigFile, [string]$StateDir, [string]$DevKitStateDir)

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

function Get-Agents([switch]$All) {
    try {
        $out = if ($All) { claude agents --json --all } else { claude agents --json }
        return @($out | Out-String | ConvertFrom-Json)
    } catch {
        Write-Log "WARN cannot list background sessions: $_"
        return $null
    }
}

function Test-PidAlive([int]$Id, [string]$NameLike = '*') {
    $p = Get-Process -Id $Id -ErrorAction SilentlyContinue
    return [bool]($p -and $p.ProcessName -like $NameLike)
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

Write-Log "WATCH started (pid $PID, every $IntervalSec s)"
$prev = @{}
$downRounds = @{}   # name -> rounds in a row seen down
$heals = @{}        # name -> times of HEAL tries in the last hour
$gaveUp = @{}       # name -> $true after GIVEUP, until seen up
$holdLogged = $false
$lastCheck = Get-Date
$round = 0

while ($true) {
    $round++
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='claude.exe' OR Name='node.exe'" |
        Where-Object { $_.CommandLine -match '\sremote-control\s' })
    $agents = Get-Agents
    $onHold = Test-Path -LiteralPath $hold
    if ($onHold -and -not $holdLogged) {
        Write-Log "HOLD on ($((Get-Content -Raw -LiteralPath $hold).Trim())): no restarts until start-servers.ps1 runs"
    } elseif (-not $onHold -and $holdLogged) {
        Write-Log 'HOLD off'
    }
    $holdLogged = $onHold

    foreach ($s in $servers) {
        $name = $s.Session
        $procId = $null
        if ($s.Lead) {
            if ($null -eq $agents) { continue }  # unknown this round; logged as WARN
            $m = $agents | Where-Object { $_.kind -eq 'background' -and $_.name -ceq $name -and $_.pid } |
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

        # Bring back an entry that is down for two rounds in a row (one round may be a start or a
        # restart in progress).
        if ($alive) { $downRounds[$name] = 0; $gaveUp.Remove($name); continue }
        $downRounds[$name] = [int]$downRounds[$name] + 1
        if ($Once -or $onHold -or $downRounds[$name] -lt 2 -or $gaveUp[$name]) { continue }
        $tries = @($heals[$name] | Where-Object { $_ -and ((Get-Date) - $_).TotalHours -lt 1 })
        if ($tries.Count -ge $MaxHeals) {
            Write-Log "GIVEUP $name ($MaxHeals restarts in the last hour did not keep it up; restart it by hand)"
            $gaveUp[$name] = $true
            continue
        }
        $heals[$name] = $tries + @(Get-Date)
        Write-Log ("HEAL {0} (down for {1} rounds, try {2} of {3})" -f $name, $downRounds[$name], ($tries.Count + 1), $MaxHeals)
        $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'start-servers.ps1') `
            -Only $name -ConfigFile $ConfigFile -StateDir $StateDir 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) {
            Write-Log ("HEAL-FAILED {0} (exit {1}): {2}" -f $name, $LASTEXITCODE, ($out.Trim() -replace '\s+', ' '))
        }
    }

    try { Clear-StaleLocks } catch { Write-Log "WARN lock check failed: $_" }

    $lastCheck = Get-Date
    if ($Once -or ($Rounds -gt 0 -and $round -ge $Rounds)) { break }
    Start-Sleep -Seconds $IntervalSec
}
