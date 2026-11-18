# Watches the servers from servers.psd1 and writes every change to ~\.claude\pult\logs\servers.log
# (the health log the Pult hub reads): STATE (first look), DOWN (with what is known about why), UP.
# It fixes four mechanical problems itself:
# - A lead or server of the list that is down for two rounds in a row is brought back by
#   start-servers.ps1 -Only <name> (the same resume as at logon): HEAL. At most $MaxHeals tries per
#   hour per entry, then GIVEUP until it is seen up again. A hold file (~\.claude\pult\hold, left by
#   stop-servers.ps1 and restart-leads.ps1, removed by a full start-servers.ps1 run) pauses this: HOLD.
#   Other sessions it touches only as the next item says; never an owner session.
# - A task session that a project lead registered as active (<DevKitStateDir>\<repo>-<hash>\sessions.json,
#   not a lead) and that Claude Code closed is brought back by `claude respawn <id>`. It is closed when
#   it is in `claude agents --json --all` with no pid and its state is not stopped (an idle session
#   whose process died stays done; a low-memory close shows blocked), or its state is stopped and
#   ~\.claude\daemon.log (last 2000 lines) has a `bg retire <id>` line after the last `bg spawned <id>`
#   line (a plain `claude stop` writes no retire line, so it is left alone). Two rounds in a row:
#   HEAL-TASK (the same hold file pauses it; HEAL-TASK-FAILED when the command exits with an error). At
#   most $MaxHeals respawns per hour per session, then GIVEUP-TASK (once, until it is seen alive again).
#   The lead's own watcher (dev-kit-sessions watch) waits 300 s before it calls such a session gone,
#   so this watcher gets its chance first.
# - A live lead of the list or active task session that stopped on the usage limit (5-hour or weekly) keeps
#   its process and shows as blocked, so it looks alive: LIMIT <name> <session id> (resets <time>) once per
#   stop, LIMIT-END when it goes on. Its transcript tells (`sessions.py limited`, one call per round); the
#   watcher only logs it: a respawn or restart would hit the same limit.
# - A dev-kit lock file whose owner is gone is removed: UNLOCK (see Clear-StaleLocks).
# - A lead that runs on an older dev-kit version than the one installed (<DevKitDir>\.claude-plugin\plugin.json)
#   is restarted so it loads the new skills. The version each lead process started on is kept by pid and
#   process start time in <StateDir>\lead-versions.json (LEAD-VERSION on a new entry; a process that started
#   after plugin.json was last written gets the installed version, else "older"). An idle lead (status idle)
#   is restarted at once with restart-leads.ps1 -Name: RESTART-LEAD. A busy one is not asked by the watcher:
#   the lead itself notices the new version on its ordinary wake-ups, reaches a safe point and runs
#   `dev-kit-sessions restart ready --version V`; or the owner's `restart-leads.ps1 -Ask` writes a request
#   `restart request --version V` for it and its session watcher exits 7 once. The watcher restarts a busy
#   stale lead only when `restart status` says `ready V <seconds>` with less than 10 minutes: restart-leads.ps1
#   -Ready, RESTART-LEAD (..., ready). A ready mark that is older or for another version is cleared:
#   READY-EXPIRED. restart.json is cleared after a restart and after a failure, and a lead already on the
#   installed version has a left-over one cleared (RESTART-CLEARED; checked once per pid). One try per lead
#   per version; a failure is logged as RESTART-LEAD-FAILED. The hold file and a running full start pause
#   it, as for HEAL.
# start-servers.ps1 starts it at logon in a hidden window. -Once: one check, then exit; -Rounds N:
# N checks, then exit (both for tests; -Once never restarts anything or touches restart.json).
# -ConfigFile / -StateDir / -DevKitStateDir / -DaemonLog: another server list, Pult state folder,
# dev-kit state folder and Claude Code daemon log (for tests with a throwaway lead).
# -DevKitDir: the dev-kit plugin folder (default: ..\..\dev-kit next to this plugin); it holds
# .claude-plugin\plugin.json (the installed version) and scripts\sessions.py.
# Keep this file saved as UTF-8 with BOM.
param([int]$IntervalSec = 60, [switch]$Once, [int]$Rounds = 0, [int]$MaxHeals = 3,
    [string]$ConfigFile, [string]$StateDir, [string]$DevKitStateDir, [string]$DaemonLog, [string]$DevKitDir)

if (-not $DaemonLog) { $DaemonLog = Join-Path $env:USERPROFILE '.claude\daemon.log' }
if (-not $DevKitDir) { $DevKitDir = Join-Path $PSScriptRoot '..\..\dev-kit' }
$DevKitDir = [IO.Path]::GetFullPath($DevKitDir)

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
            if ($live) { $liveSessions[[string]$live.sessionId] = [string]$r.name }
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
                Write-Log "GIVEUP-TASK $($r.name) $wid ($MaxHeals respawns in the last hour did not keep it up; respawn it by hand)"
                $taskGaveUp[$wid] = $true
                continue
            }
            $taskHeals[$wid] = $tries + @(Get-Date)
            $rid = if ($entries[0].id) { [string]$entries[0].id } else { $wid }
            Write-Log ("HEAL-TASK {0} {1} (closed for {2} rounds, state {3}, try {4} of {5})" -f $r.name, $rid, $taskClosed[$wid], $states[0], ($tries.Count + 1), $MaxHeals)
            $out = claude respawn $rid 2>&1 | Out-String
            if ($LASTEXITCODE -ne 0) {
                Write-Log ("HEAL-TASK-FAILED {0} {1} (exit {2}): {3}" -f $r.name, $rid, $LASTEXITCODE, ($out.Trim() -replace '\s+', ' '))
            }
            $taskClosed[$wid] = 0  # give the respawn two rounds before the next try
        }
    }
    foreach ($k in @($taskClosed.Keys)) { if (-not $seen[$k]) { $taskClosed.Remove($k) } }  # no longer active
}

# Logs the live sessions in $liveSessions (session id -> name: the leads and task sessions of this round) that
# stopped on the usage limit (see the header). $limitSeen keeps the stop already logged per session id.
function Invoke-LimitCheck {
    $ids = @($liveSessions.Keys)
    $now = @{}
    if ($ids.Count) {
        $words = @('limited') + @($ids | ForEach-Object { '--id', $_ })
        $out = & python (Join-Path $DevKitDir 'scripts\sessions.py') @words 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { Write-Log ("WARN usage-limit check failed (exit {0}): {1}" -f $LASTEXITCODE, ($out.Trim() -replace '\s+', ' ')); return }
        foreach ($line in ($out -split "`r?`n")) {
            $parts = @($line -split ' \| ')
            if ($parts.Count -eq 3) { $now[$parts[0].Trim()] = @{ Resets = $parts[1].Trim(); Key = $parts[2].Trim() } }
        }
    }
    foreach ($id in $now.Keys) {
        if ($limitSeen[$id] -cne $now[$id].Key) {
            Write-Log ("LIMIT {0} {1} (resets {2})" -f $liveSessions[$id], $id, $now[$id].Resets)
            $limitSeen[$id] = $now[$id].Key
        }
    }
    foreach ($id in @($limitSeen.Keys)) {
        if ($now.ContainsKey($id)) { continue }
        if ($liveSessions.ContainsKey($id)) { Write-Log ("LIMIT-END {0} {1}" -f $liveSessions[$id], $id) }
        $limitSeen.Remove($id)
    }
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
    }
    $json = if ($o.Count) { $o | ConvertTo-Json -Depth 3 } else { '{}' }
    $tmp = "$versionFile.$PID.tmp"
    [IO.File]::WriteAllText($tmp, $json, (New-Object System.Text.UTF8Encoding $false))
    Move-Item -Force -LiteralPath $tmp -Destination $versionFile
}

# Runs `dev-kit-sessions --project <path> restart <args>` against the dev-kit state folder of this watcher;
# returns its trimmed output (stdout and stderr).
function Invoke-LeadRestartFile([string]$LeadPath, [string[]]$Words) {
    $old = $env:DEV_KIT_STATE_DIR
    $env:DEV_KIT_STATE_DIR = $DevKitStateDir
    try {
        $out = & python (Join-Path $DevKitDir 'scripts\sessions.py') --project $LeadPath restart @Words 2>&1 | Out-String
    } catch { $out = "$_" } finally { $env:DEV_KIT_STATE_DIR = $old }
    return $out.Trim()
}

# Restarts one lead with restart-leads.ps1 (-Name, or -Ready when it marked itself ready). Returns 'busy' when
# the script skipped it as busy, 'ok' when it was resumed or started, else 'failed' (logged).
function Invoke-LeadRestart([string]$LeadName, [switch]$IsReady) {
    $cmd = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $PSScriptRoot 'restart-leads.ps1'))
    $cmd += $(if ($IsReady) { '-Ready' } else { '-Name' })
    $cmd += $LeadName
    $cmd += @('-ConfigFile', $ConfigFile, '-StateDir', $StateDir)
    $out = & powershell.exe @cmd 2>&1 | Out-String
    $said = ($out.Trim() -replace '\s+', ' ')
    if ($said -match 'Busy, skipped') { return 'busy' }
    if ($said -match ('(Resumed|Started) lead: ' + [regex]::Escape($LeadName))) { return 'ok' }
    Write-Log ("RESTART-LEAD-FAILED {0}: {1}" -f $LeadName, $said)
    return 'failed'
}

# One live lead ($s: its servers.psd1 row, $m: its entry in the session list, $V: the installed dev-kit
# version): records the version its process started on and restarts it when that is not $V (see the header).
function Invoke-LeadVersionCheck($s, $m, [string]$V) {
    $name = $s.Session
    $procId = [int]$m.pid
    $st = $leadVer[$name]
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
            $st = @{ Pid = $procId; Started = $started; Version = $ver }
            $leadVer[$name] = $st
            Write-Log "LEAD-VERSION $name pid ${procId}: $ver"
            try { Save-LeadVersions } catch { Write-Log "WARN cannot save $versionFile : $_" }
        }
    }
    if (-not $st -or $st.Pid -ne $procId) { return }
    if ($Once -or -not $s.Path -or -not (Test-Path -LiteralPath $s.Path)) { return }
    if ($st.Version -ceq $V) {
        # On the new version: a restart.json left by a HEAL, a crash or a manual restart is stale. Looked at once
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
    if ($leadTried[$name] -ceq $V) { return }
    $how = ''
    if ($m.status -eq 'idle') {
        $how = 'idle'
    } else {
        # Busy: only a fresh `ready <V> <seconds>` of the lead itself (or of restart-leads.ps1 -Ask) counts.
        $said = Invoke-LeadRestartFile $s.Path @('status')
        if ($said -match '^ready (\S+) (\d+)$') {
            $readyFor = $Matches[1]  # kept: later calls may reset $Matches
            if ($Matches[1] -ceq $V -and [int]$Matches[2] -lt $ReadyMaxAgeSec) {
                $how = 'ready'
            } else {
                $null = Invoke-LeadRestartFile $s.Path @('clear')
                # A ready mark for this version that went stale (a long hold): the lead already noted the
                # version, so ask once more; its session watcher wakes it once (exit 7).
                $again = ''
                if ($readyFor -ceq $V) { $null = Invoke-LeadRestartFile $s.Path @('request', '--version', $V); $again = '; asked again' }
                Write-Log "READY-EXPIRED $name ($($said -replace '\s+', ' '), installed $V$again)"
                return
            }
        } else { return }  # none, or asked and not ready yet
    }
    Write-Log "RESTART-LEAD $name ($($st.Version) -> $V, $how)"
    $result = Invoke-LeadRestart $name -IsReady:($how -eq 'ready')
    if ($result -eq 'busy') { return }  # turned busy meanwhile: the busy path handles it next round
    $leadTried[$name] = $V
    $cleared = Invoke-LeadRestartFile $s.Path @('clear')  # also after a failure: no stale ready mark stays
    if ($cleared -cne 'restart cleared') { Write-Log "WARN restart clear for $name failed: $($cleared -replace '\s+', ' ')" }
}

Write-Log "WATCH started (pid $PID, every $IntervalSec s)"
$versionFile = Join-Path $StateDir 'lead-versions.json'
$leadVer = @{}      # lead name -> @{ Pid; Started; Version }: the dev-kit version its process started on
try {
    if (Test-Path -LiteralPath $versionFile) {
        $saved = Get-Content -Raw -Encoding UTF8 -LiteralPath $versionFile -ErrorAction Stop | ConvertFrom-Json
        foreach ($e in $saved.PSObject.Properties) {
            $started = $e.Value.started
            if ($started -is [datetime]) { $started = $started.ToUniversalTime().ToString('o', [Globalization.CultureInfo]::InvariantCulture) }
            $leadVer[$e.Name] = @{ Pid = [int]$e.Value.pid; Started = [string]$started; Version = [string]$e.Value.version }
        }
    }
} catch { Write-Log "WARN cannot read $versionFile : $_" }
$leadSeen = @{}     # lead name -> the pid whose start time was checked in this run
$ReadyMaxAgeSec = 600  # a ready mark older than this is not acted on (READY-EXPIRED)
$leadTried = @{}    # lead name -> the version a restart was tried for
$lastVersion = $null
$versionWarned = $null
$pluginTime = $null
$prev = @{}
$downRounds = @{}   # name -> rounds in a row seen down
$heals = @{}        # name -> times of HEAL tries in the last hour
$gaveUp = @{}       # name -> $true after GIVEUP, until seen up
$taskClosed = @{}   # task session id -> rounds in a row seen closed
$taskHeals = @{}    # task session id -> times of HEAL-TASK tries in the last hour
$taskGaveUp = @{}   # task session id -> $true after GIVEUP-TASK, until seen alive
$limitSeen = @{}    # session id -> key of the usage-limit stop already logged (LIMIT)
$holdLogged = $false
$lastCheck = Get-Date
$round = 0

while ($true) {
    $round++
    $procs = @(Get-CimInstance Win32_Process -Filter "Name='claude.exe' OR Name='node.exe'" |
        Where-Object { $_.CommandLine -match '\sremote-control\s' })
    $agents = Get-Agents -All  # also ended and closed sessions; the lead check below needs a pid, so it is unchanged
    $onHold = Test-Path -LiteralPath $hold
    # A full start-servers.ps1 run (logon, restart-leads.ps1) starts the leads itself: no restarts meanwhile.
    $starting = [bool](Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
        Where-Object { $_.CommandLine -like '*start-servers.ps1*' -and $_.CommandLine -notlike '*-Only*' })
    if ($onHold -and -not $holdLogged) {
        Write-Log "HOLD on ($((Get-Content -Raw -LiteralPath $hold).Trim())): no restarts until start-servers.ps1 runs"
    } elseif (-not $onHold -and $holdLogged) {
        Write-Log 'HOLD off'
    }
    $holdLogged = $onHold
    $devKitVersion = Get-DevKitVersion
    $liveSessions = @{}  # session id -> name of each live lead and task session this round (for Invoke-LimitCheck)
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

        # Bring back an entry that is down for two rounds in a row (one round may be a start or a
        # restart in progress).
        # A planned stop or a running start resets the count, so the two rounds start after it.
        if ($alive -or $onHold -or $starting) { $downRounds[$name] = 0; if ($alive) { $gaveUp.Remove($name) }; continue }
        $downRounds[$name] = [int]$downRounds[$name] + 1
        if ($Once -or $downRounds[$name] -lt 2 -or $gaveUp[$name]) { continue }
        if (Test-Path -LiteralPath $hold) { continue }  # a stop began during this round
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
        $said = ($out.Trim() -replace '\s+', ' ')
        if ($LASTEXITCODE -ne 0 -or $said -notmatch '(Resumed|Started)( lead)?: ') {
            Write-Log ("HEAL-FAILED {0} (exit {1}): {2}" -f $name, $LASTEXITCODE, $said)
        }
        $downRounds[$name] = 0  # give the start two rounds before the next try
    }

    try { Invoke-TaskHeal } catch { Write-Log "WARN task session check failed: $_" }
    if ($null -ne $agents) {
        try { Invoke-LimitCheck } catch { Write-Log "WARN usage-limit check failed: $_" }
    }
    try { Clear-StaleLocks } catch { Write-Log "WARN lock check failed: $_" }

    $lastCheck = Get-Date
    if ($Once -or ($Rounds -gt 0 -and $round -ge $Rounds)) { break }
    Start-Sleep -Seconds $IntervalSec
}
