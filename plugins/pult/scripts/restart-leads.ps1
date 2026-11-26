# Restarts project leads "L: <name>" so they load a new dev-kit version. Each lead continues its
# conversation: stop it, then start-servers.ps1 resumes it on Opus, medium, pinned, with the first
# prompt '/dev-kit:project-lead restart: plugin update' (the lead goes on where it stopped).
# Normal path: watch-servers.ps1 does the restart by itself when it sees a lead on an older dev-kit version
# (see its header): -Name for an idle lead, -Ready for a busy one that marked itself ready with
# `dev-kit-sessions restart ready --version V`. The output lines (Busy, skipped / Resumed lead / Started
# lead ...) are parsed there. -Ready restarts the named leads even when they show busy (a lead on dev-kit
# before 0.1.78 keeps a background watcher, so it always shows busy while it only waits).
# By hand, on the owner's ask: -Ask restarts the idle leads now and, for each busy one, writes the request
# `dev-kit-sessions restart request --version V` (V from <DevKitDir>\.claude-plugin\plugin.json) and prints
# `Asked: <name>`; watch-servers.ps1 sends it to the lead as a `restart` event message (an older lead's own
# session watcher reads it), and restarts that lead when it marks itself ready.
# A lead whose pending versions include a clean release (`"clean": true` in a plugin's releases.json, asked with
# `sessions.py release` as the watcher does; see watch-servers.ps1, "Clean") is not restarted directly by -Ask, idle or
# busy: it is asked with `restart request --version V --clean` and `Asked: <name>` is printed. It answers with a
# handoff, which the watcher moves to a fresh context; the watcher's clean fallbacks apply (a ready mark is honoured).
# A lead that cannot get event messages (it started on dev-kit before 0.1.78) is handled plainly, as without the mark.
# -Ask also counts the other plugins a lead loads (rules-kit, spend-kit and the ones its project enables: web-kit,
# unity-kit; see plugin-versions.ps1): a lead
# stale only in an extension is restarted now when idle, and a busy one is not asked (the watcher restarts it
# when it is idle: `Not asked, busy and only an extension changed: <name>`).
# A lead whose project has no hard-ban lines on main is not stopped: `NO-BANS <name> (<reason>): not restarted`
# (start-servers.ps1 would not start it again; the watcher parses this line).
# Without -Ready and -Ask, only idle leads are restarted and a busy one is skipped (its turn would be cut);
# -Force restarts busy ones too, only after checking they are not in the middle of a step.
# -ConfigFile and -StateDir: another server list and Pult state folder (hold file); both are passed on to
# start-servers.ps1 (for tests with a throwaway lead; defaults: servers.psd1 and ~\.claude\pult).
# -DevKitDir and -DevKitStateDir (only for -Ask): the dev-kit plugin folder (default: ..\..\dev-kit next to
# this plugin) and the dev-kit state folder (default: env DEV_KIT_STATE_DIR, else ~\.claude\dev-kit).
# A lead that still runs under its old name "P: <name>" is found as the lead "L: <name>" and restarted: start-servers.ps1
# then resumes it under the new name (resume-lib.ps1, Set-LeadStateName). -Name and -Ready take the old name too.
# Usage: restart-leads.ps1 -Ready 'L: Zhratva','L: Prishch'
#        restart-leads.ps1 -Ask
#        restart-leads.ps1 [-Name 'L: Zhratva'] [-Force]

param([string[]]$Name, [string[]]$Ready, [switch]$Force, [switch]$Ask, [string]$ConfigFile, [string]$StateDir,
    [string]$DevKitDir, [string]$DevKitStateDir)

$scripts = $PSScriptRoot
if (-not $ConfigFile) { $ConfigFile = Join-Path $scripts 'servers.psd1' }
if (-not $StateDir) { $StateDir = Join-Path $env:USERPROFILE '.claude\pult' }  # outside the plugin folder
if (-not $DevKitDir) { $DevKitDir = Join-Path $scripts '..\..\dev-kit' }
$DevKitDir = [IO.Path]::GetFullPath($DevKitDir)
. (Join-Path $scripts 'plugin-versions.ps1')
. (Join-Path $scripts 'resume-lib.ps1')  # Get-LeadPermissionMode
$rows = @((Import-PowerShellDataFile $ConfigFile).Servers | Where-Object { $_.Lead })
$leads = @($rows | ForEach-Object { $_.Session })
if ($Ready) { $Name = $Ready }
$Name = @($Name | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })  # -File passes one comma-joined string
if ($Name) { $leads = @($leads | Where-Object { $l = $_; @($Name | Where-Object { Test-LeadEntryName $_ $l }).Count }) }  # an old "P: X" name selects the lead "L: X"
if (-not $leads) { Write-Output 'No matching leads.'; exit 1 }

# Hold the watcher (watch-servers.ps1) while the leads are down on purpose; start-servers.ps1 below
# removes the hold. The hold names this process (pid): if the script dies before that, the watcher sees the
# process gone and removes the stale hold itself (watch-servers.ps1, HOLD-STALE).
New-Item -ItemType Directory -Force $StateDir | Out-Null
Set-Content -LiteralPath (Join-Path $StateDir 'hold') -Encoding UTF8 -Value "restart-leads.ps1 $(Get-Date -Format s) pid $PID"
$sessions = @(claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ }
$stopped = @()

# -Ask: writes the restart request of a busy lead's project; returns the line to print.
function Request-LeadRestart($Row, [switch]$Clean) {
    if (-not $Row.Path -or -not (Test-Path -LiteralPath $Row.Path)) { return "Not asked, folder missing: $($Row.Session)" }
    $v = $null
    try {
        $v = [string](Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $DevKitDir '.claude-plugin\plugin.json') -ErrorAction Stop |
            ConvertFrom-Json).version
    } catch { }
    if (-not $v) { return "Not asked, cannot read the dev-kit version: $($Row.Session)" }
    $old = $env:DEV_KIT_STATE_DIR
    if ($DevKitStateDir) { $env:DEV_KIT_STATE_DIR = $DevKitStateDir }
    try {
        $words = @('restart', 'request', '--version', $v)
        if ($Clean) { $words += '--clean' }
        $out = & python (Join-Path $DevKitDir 'scripts\sessions.py') --project $Row.Path @words 2>&1 | Out-String
    } catch { $out = "$_" } finally { $env:DEV_KIT_STATE_DIR = $old }
    $said = ($out.Trim() -replace '\s+', ' ')
    if ($said -ceq "asked $v") { return "Asked: $($Row.Session)" }
    return "Not asked, the request failed: $($Row.Session): $said"
}

# -Ask: what the watcher's lead-versions.json says about this lead process against the installed versions:
# 'current' (dev-kit and every extension the project uses are as installed), 'ext' (dev-kit is as installed,
# an extension changed: the lead's handshake knows only dev-kit versions, so it is not asked), or 'devkit'
# (dev-kit changed, or nothing is known). An entry with no "ext" counts as current for the extensions, as in
# the watcher.
function Get-LeadStaleness([string]$Lead, $ProcId, $Row) {
    try {
        $v = [string](Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $DevKitDir '.claude-plugin\plugin.json') -ErrorAction Stop |
            ConvertFrom-Json).version
        $all = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $StateDir 'lead-versions.json') -ErrorAction Stop |
            ConvertFrom-Json
        $e = $all.$Lead
        $old = Get-LegacyLeadName $Lead
        if (-not $e -and $old) { $e = $all.$old }  # saved before the lead was renamed
        if (-not ($v -and $e -and [int]$e.pid -eq [int]$ProcId -and [string]$e.version -ceq $v)) { return 'devkit' }
        $stored = $null
        if ($e.PSObject.Properties['ext']) {
            $stored = @{}
            if ($e.ext) { foreach ($q in $e.ext.PSObject.Properties) { $stored[$q.Name] = [string]$q.Value } }
        }
        $now = Get-LeadExtensions $Row.Path $DevKitDir
        if (@(Get-ExtChanges $stored $now).Count) { return 'ext' }
        return 'current'
    } catch { return 'devkit' }
}

# -Ask: whether a release this lead process lacks is marked clean ("clean": true in a releases.json; dev-kit up to the
# installed version, every changed extension up to its own), asked per changed plugin with `sessions.py release` as the
# watcher does (watch-servers.ps1, Get-ReleaseKind). Nothing known about the lead process, or any failure: not clean.
$WakeMinDevKit = '0.1.78'  # as in watch-servers.ps1: a lead that started on this dev-kit or later is woken by message
function Test-LeadCleanChange([string]$Lead, $ProcId, $Row) {
    try {
        $dev = Get-PluginInfo $DevKitDir
        $all = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $StateDir 'lead-versions.json') -ErrorAction Stop |
            ConvertFrom-Json
        $e = $all.$Lead
        $old = Get-LegacyLeadName $Lead
        if (-not $e -and $old) { $e = $all.$old }
        if (-not ($dev -and $e -and [int]$e.pid -eq [int]$ProcId)) { return $false }
        # A lead that cannot get event messages (it started on dev-kit before $WakeMinDevKit, or an unknown one) never
        # sees the clean request: it is restarted plainly, as without a clean mark.
        $ver = $null
        if (-not [version]::TryParse([string]$e.version, [ref]$ver) -or $ver -lt [version]$WakeMinDevKit) { return $false }
        $items = @()
        if ([string]$e.version -cne $dev.Version) { $items += @{ From = [string]$e.version; To = $dev.Version; File = (Join-Path $dev.Dir 'releases.json') } }
        if ($e.PSObject.Properties['ext']) {
            $stored = @{}
            if ($e.ext) { foreach ($q in $e.ext.PSObject.Properties) { $stored[$q.Name] = [string]$q.Value } }
            $now = Get-LeadExtensions $Row.Path $DevKitDir
            foreach ($c in @(Get-ExtChangeList $stored $now)) { $items += @{ From = $c.From; To = $c.To; File = (Join-Path $now[$c.Name].Dir 'releases.json') } }
        }
        foreach ($item in $items) {
            $words = @('release', '--from', $item.From, '--to', $item.To, '--file', $item.File)
            if ($e.started) {
                $started = $e.started
                if ($started -is [datetime]) { $started = $started.ToUniversalTime().ToString('o', [Globalization.CultureInfo]::InvariantCulture) }
                $words += @('--started', [string]$started)
            }
            $out = & python (Join-Path $DevKitDir 'scripts\sessions.py') @words 2>$null | Out-String
            if (@($out -split "`r?`n" | ForEach-Object { $_.Trim() }) -ccontains 'clean') { return $true }
        }
    } catch { }
    return $false
}

foreach ($lead in $leads) {
    # The running session may still have the old name "P: X" (resume-lib.ps1, Test-LeadEntryName); start-servers.ps1 renames it.
    $s = $sessions | Where-Object { $_.kind -eq 'background' -and (Test-LeadEntryName ([string]$_.name) $lead) -and $_.pid } |
        Select-Object -First 1
    if (-not $s) { Write-Output "Not running, will be started: $lead"; continue }
    $row = $rows | Where-Object { $_.Session -ceq $lead } | Select-Object -First 1
    $stale = if ($Ask) { Get-LeadStaleness $lead $s.pid $row } else { '' }
    if ($stale -eq 'current') { Write-Output "Up to date: $lead"; continue }
    # A clean release (a pending version marked "clean": true) is never restarted directly: the lead is asked, busy or
    # idle, with `restart request --version V --clean`; it answers with a handoff and the watcher moves it.
    $clean = $Ask -and -not $Force -and -not $Ready -and (Test-LeadCleanChange $lead $s.pid $row)
    if ($s.status -eq 'busy' -and $Ask -and -not $Force -and -not $Ready) {
        if ($stale -eq 'ext' -and -not $clean) { Write-Output "Not asked, busy and only an extension changed: $lead"; continue }
        Write-Output (Request-LeadRestart $row -Clean:$clean)
        continue
    }
    if ($clean) { Write-Output (Request-LeadRestart $row -Clean); continue }
    if ($s.status -eq 'busy' -and -not $Force -and -not $Ready) { Write-Output "Busy, skipped: $lead"; continue }
    # start-servers.ps1 starts a lead only with hard bans on main: without them a stopped lead would stay down.
    $gate = @{ Start = $false; Reason = 'the hard-ban check failed' }
    try { $gate = Get-LeadPermissionMode $row.Path } catch { }
    if (-not $gate.Start) {
        Write-Output "NO-BANS $lead ($($gate.Reason)): not restarted, it keeps running. Hard bans are missing on main. Hub: show the owner the exact lines, on his yes write .claude/hard-bans.json in the project's main checkout and run: $(Get-AddBansCommand $row.Path)"
        continue
    }
    @(claude stop $s.id) | Select-Object -First 1  # capture first: a cut pipe sets exit code -1
    $stopped += $lead
}
# start-servers.ps1 skips a lead whose process is still alive, so wait until every stopped one is gone.
if ($stopped) {
    $until = (Get-Date).AddSeconds(60)
    do {
        Start-Sleep -Seconds 3
        $alive = @((claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ } |
            Where-Object { $_.kind -eq 'background' -and $_.pid -and (Test-AnyLeadEntryName ([string]$_.name) $stopped) })
    } while ($alive -and (Get-Date) -lt $until)
    if ($alive) { Write-Output "Still running after the stop, not resumed: $(($alive | ForEach-Object { $_.name }) -join ', ')" }
}
$startArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $scripts 'start-servers.ps1'),
    '-ConfigFile', $ConfigFile, '-StateDir', $StateDir)
if ($stopped) { $startArgs += @('-Restarted', ($stopped -join ',')) }
& powershell.exe @startArgs
