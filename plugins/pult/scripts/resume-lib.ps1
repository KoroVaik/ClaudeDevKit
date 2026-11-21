# Helpers for start-servers.ps1 (ASCII only; dot-source to test).

# Full sessionId of the newest background session with this exact name and folder, or $null.
# Works for stopped and finished sessions: `claude --bg --resume <sessionId>` with no other flags
# wakes it under the same id with its saved options (name, Remote Control, model, permission mode).
function Get-ResumeSessionId([string]$Name, [string]$Path, $Sessions) {
    if ($null -eq $Sessions) {
        $Sessions = claude agents --json --all | Out-String | ConvertFrom-Json
    }
    $want = ([IO.Path]::GetFullPath($Path)).TrimEnd('\').ToLowerInvariant()
    $Sessions |
        Where-Object {
            $_.kind -eq 'background' -and $_.name -ceq $Name -and $_.sessionId -and $_.cwd -and
            ([IO.Path]::GetFullPath($_.cwd)).TrimEnd('\').ToLowerInvariant() -eq $want
        } |
        Sort-Object { [int64]$_.startedAt } -Descending |
        Select-Object -First 1 -ExpandProperty sessionId
}

# The note a lead gets after the skill name in its first prompt when it was restarted for a plugin
# update (the project-lead skill, "Restart for a plugin update"). No double quotes: Windows
# PowerShell cuts an argument passed to a native command at its first double quote.
$RestartNote = 'restart: plugin update'

# The word that, followed by the handoff file name, ends the first prompt of a lead started for a handoff (the
# project-lead skill, "Restart P"; the watcher does this, watch-servers.ps1 Invoke-HandoffCheck).
# Same rule as sessions.py HANDOFF_NAME: a bare file name that goes on a command line, so no space or quote.
$HandoffNote = 'handoff:'
$HandoffNamePattern = '^[A-Za-z0-9][A-Za-z0-9._-]*\.md\z'

# The command line (as an argument array for `claude`) that continues a lead, or starts it fresh.
# -Restarted adds $RestartNote to the first prompt of a resumed lead. -Prompt, -Model and -Effort
# come from the lead's servers.psd1 row when it has them (a throwaway test lead uses a cheap model).
# -Handoff <file>: always a fresh start, even with a SessionId (a resume would bring back the full context), and
# the prompt ends with `handoff: <file>`; a name that is not a bare .md file name throws.
function Get-LeadStartArgs([string]$SessionName, [string]$SessionId, [switch]$Restarted,
        [string]$Prompt = '/dev-kit:project-lead', [string]$Model = $LeadModel, [string]$Effort = $LeadEffort,
        [string]$Handoff) {
    if ($Handoff) {
        if ($Handoff -cnotmatch $HandoffNamePattern) { throw "the handoff file name is not a bare .md file name: $Handoff" }
        $Prompt += ' ' + $HandoffNote + ' ' + $Handoff
        $SessionId = $null
    }
    if ($SessionId) {
        if ($Restarted) { $Prompt += ' ' + $RestartNote }
        # No flags besides the prompt: any flag makes claude start a copy instead of waking this one.
        return @('--bg', '--resume', $SessionId, '--', $Prompt)
    }
    return @('--bg', '--remote-control', $SessionName, '--name', $SessionName,
        '--permission-mode', $LeadPermissionMode, '--model', $Model, '--effort', $Effort, '--', $Prompt)
}

# Process ids of a background session that still runs: its pty host and its worker. Both command lines
# hold the full session id (`--session-id <id>`, or `--resume <transcript folder>\<id>.jsonl` once resumed;
# the job's short id in the pty pipe name may differ from the id's first 8 characters). A copy forked from
# it (`--fork-session`) is another session and is left out. After `claude stop`, `claude agents` drops the
# pid about a second before these exit; a `claude --bg --resume` in that gap says "already running" and
# starts a copy without the saved flags (default model and mode). Checked live 2026-11-19: 2 copies in 3
# resumes right after the pid left the list.
function Get-SessionProcessIds([string]$SessionId, $Processes) {
    if (-not $SessionId) { return @() }
    if ($null -eq $Processes) { $Processes = Get-CimInstance Win32_Process -Filter "Name = 'claude.exe'" }
    @($Processes | Where-Object {
            $_.CommandLine -and $_.CommandLine.Contains($SessionId) -and -not $_.CommandLine.Contains('--fork-session')
        } | ForEach-Object { $_.ProcessId })
}

# Waits until no process of the session is left (Get-SessionProcessIds). $true when gone, $false on timeout.
function Wait-SessionGone([string]$SessionId, [int]$TimeoutSec = 60) {
    $until = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-SessionProcessIds $SessionId).Count) {
        if ((Get-Date) -gt $until) { return $false }
        Start-Sleep -Milliseconds 500
    }
    return $true
}

# The short id of the copy `claude --bg --resume` started instead of waking the session, from its note
# "... is already running in the background, so this started a copy as <id>. ...", else $null.
function Get-ResumeCopyId([string]$Output) {
    if ($Output -match 'started a copy as ([0-9a-f]{8})') { return $Matches[1] }
    return $null
}

# Leads run on this model and reasoning level (the owner's rule: sessions he talks with use Opus, medium).
$LeadModel = 'opus'
$LeadEffort = 'medium'
# The one permission mode of every session the plugin starts (owner, 2026-11-20): no fallback to another mode.
$LeadPermissionMode = 'bypassPermissions'

# A resumed session takes its model and permission mode from the saved options of its job
# (~/.claude/jobs/<short id>/state.json, "respawnFlags"). Set --model, --effort and --permission-mode
# there before resuming, so the lead wakes on $LeadModel / $LeadEffort (or -Model / -Effort) and in
# $LeadPermissionMode. Returns $true when the file was changed.
function Set-LeadRespawnModel([string]$SessionName, [string]$SessionId, [string]$JobsDir,
        [string]$Model = $LeadModel, [string]$Effort = $LeadEffort) {
    if (-not $JobsDir) { $JobsDir = Join-Path $env:USERPROFILE '.claude\jobs' }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    foreach ($f in Get-ChildItem $JobsDir -Filter state.json -Recurse -Depth 1 -ErrorAction SilentlyContinue) {
        $text = [IO.File]::ReadAllText($f.FullName, $utf8)
        $s = $text | ConvertFrom-Json
        if ($s.name -cne $SessionName) { continue }
        if ($s.sessionId -ne $SessionId -and $s.resumeSessionId -ne $SessionId) { continue }
        $flags = @($s.respawnFlags)
        $keep = @()
        for ($i = 0; $i -lt $flags.Count; $i++) {
            if ($flags[$i] -in '--model', '--effort', '--permission-mode') { $i++; continue }
            if ($flags[$i] -like '--permission-mode=*' -or $flags[$i] -eq '--dangerously-skip-permissions') { continue }
            $keep += $flags[$i]
        }
        $keep += @('--model', $Model, '--effort', $Effort, '--permission-mode', $LeadPermissionMode)
        $arr = '[' + (($keep | ForEach-Object { ConvertTo-Json ([string]$_) }) -join ', ') + ']'
        $new = [regex]::Replace($text, '"respawnFlags"\s*:\s*\[[^\]]*\]', { param($m) '"respawnFlags": ' + $arr })
        if ($new -ne $text) { [IO.File]::WriteAllText($f.FullName, $new, $utf8); return $true }
        return $false
    }
    return $false
}

# The command the owner types himself (no agent runs it) once the hub has written .claude/hard-bans.json in the
# project's main checkout; the dev-kit folder is the one next to this plugin (as in the other Pult scripts).
function Get-AddBansCommand([string]$ProjectPath) {
    $bin = ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\dev-kit\bin\dev-kit-bans')) -replace '\\', '/')
    return "! python `"$bin`" add-approved `"$($ProjectPath -replace '\\', '/')`""
}

# Every session the plugin starts runs in $LeadPermissionMode (bypassPermissions); there is no other mode
# and no fallback. A lead starts only when the settings committed on main of its project hold the
# hard-ban deny rules for both shells (a Bash and a PowerShell deny line of the hard-ban set: git push,
# rm -rf / Remove-Item, docker) and the owner has accepted the bypass disclaimer on this machine
# (skipDangerousModePermissionPrompt in the user settings; without it `claude --bg` with
# bypassPermissions exits 1). Returns @{ Start; Mode; Reason }: Start $true and Mode bypassPermissions when
# the gate passes, else Start $false, Mode empty and the reason: the lead is then not started and the owner is
# told (start-servers.ps1: NO-BANS).
function Get-LeadPermissionMode([string]$Path, [string]$UserSettings) {
    if (-not $UserSettings) { $UserSettings = Join-Path $env:USERPROFILE '.claude\settings.json' }
    $no = { param($why) @{ Start = $false; Mode = ''; Reason = $why } }
    $text = $null
    try { $text = (git -C $Path show 'main:.claude/settings.json' 2>$null) -join "`n" } catch { }
    if (-not $text) { return (& $no 'no .claude/settings.json committed on main') }
    try { $deny = @(($text | ConvertFrom-Json).permissions.deny) } catch { return (& $no 'settings on main do not parse') }
    $bash = @($deny | Where-Object { $_ -like 'Bash(git push*' -or $_ -like 'Bash(rm -rf*' -or $_ -like 'Bash(docker*' })
    $pwsh = @($deny | Where-Object { $_ -like 'PowerShell(git push*' -or $_ -like 'PowerShell(Remove-Item*' -or $_ -like 'PowerShell(docker*' })
    if (-not $bash.Count -or -not $pwsh.Count) {
        return (& $no 'no Bash and PowerShell hard-ban deny lines on main')
    }
    $accepted = $false
    try { $accepted = [bool]((Get-Content -Raw -Encoding UTF8 $UserSettings | ConvertFrom-Json).skipDangerousModePermissionPrompt) } catch { }
    if (-not $accepted) { return (& $no 'bypass disclaimer not accepted on this machine') }
    return @{ Start = $true; Mode = $LeadPermissionMode; Reason = 'hard bans on main' }
}
