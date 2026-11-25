# Helpers for start-servers.ps1 (ASCII only; dot-source to test).

# Project leads are named "L: <project>"; until the running ones are renamed they carry the old name "P: <project>"
# (plans/role-names.md). The old name is found by these helpers only: a lead "L: X" counts as running when a session
# named "P: X" runs, and its stopped "P: X" session is resumed and renamed (Get-LeadResumeEntry, Set-LeadStateName).
# Drop the helpers' P: side once no session of the old name is left.

# The old name of a lead name "L: X" ("P: X"), else $null.
function Get-LegacyLeadName([string]$Name) {
    if ($Name -cmatch '^L: (.+)$') { return 'P: ' + $Matches[1] }
    return $null
}

# True when $Name is a lead name, the new "L: " or the old "P: " one.
function Test-LeadName([string]$Name) {
    return [bool]($Name -cmatch '^[LP]: ')
}

# True when a session named $EntryName is the lead $LeadName: its own name or its old name (Get-LegacyLeadName).
function Test-LeadEntryName([string]$EntryName, [string]$LeadName) {
    if ($EntryName -ceq $LeadName) { return $true }
    $old = Get-LegacyLeadName $LeadName
    return [bool]($old -and $EntryName -ceq $old)
}

# True when a session named $EntryName is one of the leads in $LeadNames (Test-LeadEntryName).
function Test-AnyLeadEntryName([string]$EntryName, [string[]]$LeadNames) {
    foreach ($n in @($LeadNames)) { if (Test-LeadEntryName $EntryName $n) { return $true } }
    return $false
}

# Full sessionId of the newest background session with this exact name and folder, or $null.
# Works for stopped and finished sessions: `claude --bg --resume <sessionId>` wakes it under the same id
# (plugins/dev-kit/claude-facts.md, "`claude --bg --resume <id>` with any other flag starts a copy"). After a /clear
# this is the new transcript's id; start-servers.ps1 resumes by Get-JobResumeId of it.
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

# The session to resume for the lead $Name: @{ SessionId; Name } of the newest background session named $Name in $Path,
# else of the one with its old name (Get-LegacyLeadName); $null when there is none. Name is the name the session has now.
# $Sessions: a parsed session list (default: `claude agents --json --all`, read once).
function Get-LeadResumeEntry([string]$Name, [string]$Path, $Sessions) {
    if ($null -eq $Sessions) {
        $Sessions = claude agents --json --all | Out-String | ConvertFrom-Json
    }
    $names = @($Name)
    $old = Get-LegacyLeadName $Name
    if ($old) { $names += $old }
    foreach ($n in $names) {
        $id = Get-ResumeSessionId $n $Path $Sessions
        if ($id) { return @{ SessionId = [string]$id; Name = $n } }
    }
    return $null
}

# The note a lead gets after the skill name in its first prompt when it was restarted for a plugin
# update (the project-lead skill, "Restart for a plugin update"). No double quotes
# (plugins/dev-kit/claude-facts.md, "Windows PowerShell 5.1 cuts a prompt at the first double quote").
$RestartNote = 'restart: plugin update'

# The word that, followed by the handoff file name, ends the first prompt of a lead started for a handoff (the
# project-lead skill, "Restart the Lead"; the watcher does this, watch-servers.ps1 Invoke-HandoffCheck).
# Same rule as sessions.py HANDOFF_NAME: a bare file name that goes on a command line, so no space or quote.
$HandoffNote = 'handoff:'
$HandoffNamePattern = '^[A-Za-z0-9][A-Za-z0-9._-]*\.md\z'

# The command line (as an argument array for `claude`) that continues a lead, or starts it fresh.
# -Restarted adds $RestartNote to the first prompt of a resumed lead. -Prompt, -Model and -Effort
# come from the lead's servers.psd1 row when it has them (a throwaway test lead uses a cheap model).
# -Handoff <file>: the prompt ends with `handoff: <file>`; a name that is not a bare .md file name throws. A fresh start,
# even with a SessionId (a resume would bring back the full context), unless -ResumeHandoff: then the session is resumed
# (start-servers.ps1 does that only right after it emptied the session's context with /clear, Get-LeadClearArgs).
function Get-LeadStartArgs([string]$SessionName, [string]$SessionId, [switch]$Restarted,
        [string]$Prompt = '/dev-kit:project-lead', [string]$Model = $LeadModel, [string]$Effort = $LeadEffort,
        [string]$Handoff, [switch]$ResumeHandoff) {
    if ($Handoff) {
        if ($Handoff -cnotmatch $HandoffNamePattern) { throw "the handoff file name is not a bare .md file name: $Handoff" }
        $Prompt += ' ' + $HandoffNote + ' ' + $Handoff
        if (-not $ResumeHandoff) { $SessionId = $null }
    }
    if ($SessionId) {
        if ($Restarted) { $Prompt += ' ' + $RestartNote }
        # No flags besides the prompt (plugins/dev-kit/claude-facts.md, "`claude --bg --resume <id>` with any other flag starts a copy").
        return @('--bg', '--resume', $SessionId, '--', $Prompt)
    }
    return @('--bg', '--remote-control', $SessionName, '--name', $SessionName,
        '--permission-mode', $LeadPermissionMode, '--model', $Model, '--effort', $Effort, '--', $Prompt)
}

# The resume that empties a stopped session's context and keeps its job and phone link (no push): `/clear` as the
# only prompt and no other flag (plugins/dev-kit/claude-facts.md, "A resume with `/clear` as its prompt clears the
# context and keeps the job and the Remote Control link", "`claude --bg --resume <id>` with any other flag starts a copy").
function Get-LeadClearArgs([string]$SessionId) {
    return @('--bg', '--resume', $SessionId, '--', '/clear')
}

# The background jobs folder: env DEV_KIT_JOBS_DIR (tests), else ~\.claude\jobs.
function Get-JobsDir {
    if ($env:DEV_KIT_JOBS_DIR) { return $env:DEV_KIT_JOBS_DIR }
    return Join-Path $env:USERPROFILE '.claude\jobs'
}

# The state.json of the background job whose sessionId or resumeSessionId is $SessionId (the newest file when several
# match), parsed, with its short id (`daemonShort`, else the folder name; the `id` of `claude agents`) added as
# `jobShort`; $null when there is none. After a /clear the job keeps its first sessionId while resumeSessionId,
# linkScanPath and the sessionId that `claude agents` shows name the new transcript.
function Get-JobState([string]$SessionId, [string]$JobsDir) {
    if (-not $SessionId) { return $null }
    if (-not $JobsDir) { $JobsDir = Get-JobsDir }
    if (-not (Test-Path -LiteralPath $JobsDir)) { return $null }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    $files = Get-ChildItem -LiteralPath $JobsDir -Directory -ErrorAction SilentlyContinue |
        ForEach-Object { Get-Item -LiteralPath (Join-Path $_.FullName 'state.json') -ErrorAction SilentlyContinue } |
        Sort-Object LastWriteTimeUtc -Descending
    foreach ($f in $files) {
        try { $text = [IO.File]::ReadAllText($f.FullName, $utf8) } catch { continue }
        if (-not $text.Contains($SessionId)) { continue }  # most jobs are another session's: skip the parse
        try { $s = $text | ConvertFrom-Json } catch { continue }
        if ([string]$s.sessionId -cne $SessionId -and [string]$s.resumeSessionId -cne $SessionId) { continue }
        $short = if ($s.daemonShort) { [string]$s.daemonShort } else { $f.Directory.Name }
        $s | Add-Member -NotePropertyName jobShort -NotePropertyValue $short -Force
        return $s
    }
    return $null
}

# The id to resume a session by: the sessionId of its job (Get-JobState). After a /clear the session list shows the new
# transcript's id as the sessionId, while the job keeps its first one, and `--resume <first id>` wakes the job
# (plugins/dev-kit/claude-facts.md, "A resume with `/clear` as its prompt clears the context and keeps the job and the
# Remote Control link"). No job state: $SessionId as given.
function Get-JobResumeId([string]$SessionId, [string]$JobsDir) {
    $job = Get-JobState $SessionId $JobsDir
    if ($job -and $job.sessionId) { return [string]$job.sessionId }
    return $SessionId
}

# The live background entries of $Agents (a parsed session list) with this name (or the old name of a lead, Test-LeadEntryName) that belong to the session: its `id` is
# the job's short id, or its sessionId is one of the session's ids (Get-JobSessionIds; after a /clear the list shows
# the new transcript's id as the sessionId).
function Get-SessionEntries($Agents, [string]$Name, [string]$SessionId, [string]$JobsDir) {
    $ids = @(Get-JobSessionIds $SessionId $JobsDir)
    $job = Get-JobState $SessionId $JobsDir
    $short = if ($job) { [string]$job.jobShort } else { '' }
    return @($Agents | Where-Object { $_ -and $_.kind -eq 'background' -and (Test-LeadEntryName ([string]$_.name) $Name) -and $_.pid -and
            (($short -and [string]$_.id -ceq $short) -or ($ids -ccontains [string]$_.sessionId)) })
}

# Every id a session's processes may carry on their command lines: the id itself and, from its job state, the
# sessionId, the resumeSessionId and the name of the linkScanPath file (a session resumed after a /clear runs as
# `--resume <new id>.jsonl`).
function Get-JobSessionIds([string]$SessionId, [string]$JobsDir) {
    if (-not $SessionId) { return @() }
    $ids = @($SessionId)
    $job = Get-JobState $SessionId $JobsDir
    if ($job) {
        $ids += @([string]$job.sessionId, [string]$job.resumeSessionId)
        if ($job.linkScanPath) { $ids += [IO.Path]::GetFileNameWithoutExtension([string]$job.linkScanPath) }
    }
    return @($ids | Where-Object { $_ } | Select-Object -Unique)
}

# True when the /clear resume of a session has ended its turn: its job's linkScanPath is set and is not $ScanBefore (the
# value before the resume: /clear writes a new transcript file) and the live entry of the session in $Agents (a parsed
# session list; Get-SessionEntries, whose sessionId is the new transcript's id by then) has status idle.
function Test-ClearEnded([string]$Name, [string]$SessionId, [string]$ScanBefore, $Agents, [string]$JobsDir) {
    $job = Get-JobState $SessionId $JobsDir
    if (-not $job -or -not $job.linkScanPath -or [string]$job.linkScanPath -eq $ScanBefore) { return $false }
    $m = @(Get-SessionEntries $Agents $Name $SessionId $JobsDir) | Select-Object -First 1
    return [bool]($m -and $m.status -eq 'idle')
}

# Process ids of a background session that still runs: its pty host and its worker. Both command lines
# hold the full session id (`--session-id <id>`, or `--resume <transcript folder>\<id>.jsonl` once resumed;
# the job's short id in the pty pipe name may differ from the id's first 8 characters). A copy forked from
# # it (`--fork-session`) is another session and is left out. After `claude stop` the processes outlive the
# pid in `claude agents` (plugins/dev-kit/claude-facts.md, "A just-stopped session keeps its processes for about 1 s").
# $SessionId may hold several ids of one session (Get-JobSessionIds): a process that carries any of them counts.
function Get-SessionProcessIds([string[]]$SessionId, $Processes) {
    $ids = @($SessionId | Where-Object { $_ })
    if (-not $ids.Count) { return @() }
    if ($null -eq $Processes) { $Processes = Get-CimInstance Win32_Process -Filter "Name = 'claude.exe'" }
    @($Processes | Where-Object {
            $line = $_.CommandLine
            $line -and -not $line.Contains('--fork-session') -and @($ids | Where-Object { $line.Contains($_) }).Count
        } | ForEach-Object { $_.ProcessId })
}

# Waits until no process of the session is left (Get-SessionProcessIds over its ids, Get-JobSessionIds). $true when
# gone, $false on timeout.
function Wait-SessionGone([string]$SessionId, [int]$TimeoutSec = 60) {
    $ids = @(Get-JobSessionIds $SessionId)
    $until = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-SessionProcessIds $ids).Count) {
        if ((Get-Date) -gt $until) { return $false }
        Start-Sleep -Milliseconds 500
    }
    return $true
}

# The short id of the copy `claude --bg --resume` started instead of waking the session, from its note
# "... so this started a copy as <id>. ..." (plugins/dev-kit/claude-facts.md, "A just-stopped session keeps its
# processes for about 1 s"), else $null.
function Get-ResumeCopyId([string]$Output) {
    if ($Output -match 'started a copy as ([0-9a-f]{8})') { return $Matches[1] }
    return $null
}

# Leads run on this model and reasoning level (the owner's rule: sessions he talks with use Opus, medium).
$LeadModel = 'opus'
$LeadEffort = 'medium'
# The one permission mode of every session the plugin starts (owner, 2026-11-20): no fallback to another mode.
$LeadPermissionMode = 'bypassPermissions'

# Renames the saved job of a lead that still has its old name (Get-LegacyLeadName) to $SessionName before the resume:
# the job's state.json ("name") and its saved options ("respawnFlags": every entry that holds the old name, that is
# `--name <old>` and `--remote-control <old>`) get the new name, so the resumed session keeps its history under it. The
# resume itself takes no flag. Only the job whose sessionId or resumeSessionId is $SessionId and whose name is the old
# one is touched, and only those values: the rest of the file keeps its bytes. Returns $true when the file was changed
# (no old name, another job or a name that is already new: $false).
function Set-LeadStateName([string]$SessionName, [string]$SessionId, [string]$JobsDir) {
    $old = Get-LegacyLeadName $SessionName
    if (-not $old -or -not $SessionId) { return $false }
    if (-not $JobsDir) { $JobsDir = Get-JobsDir }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    foreach ($f in Get-ChildItem $JobsDir -Filter state.json -Recurse -Depth 1 -ErrorAction SilentlyContinue) {
        $text = [IO.File]::ReadAllText($f.FullName, $utf8)
        try { $s = $text | ConvertFrom-Json } catch { continue }
        if ($s.name -cne $old) { continue }
        if ($s.sessionId -ne $SessionId -and $s.resumeSessionId -ne $SessionId) { continue }
        $newJson = ConvertTo-Json ([string]$SessionName)
        $new = [regex]::Replace($text, '("name"\s*:\s*)"((?:[^"\\]|\\.)*)"', {
            param($m) if ([regex]::Unescape($m.Groups[2].Value) -ceq $old) { $m.Groups[1].Value + $newJson } else { $m.Value } })
        $flags = @($s.respawnFlags)
        if ($flags -ccontains $old) {
            $arr = '[' + (($flags | ForEach-Object { ConvertTo-Json ([string]$(if ([string]$_ -ceq $old) { $SessionName } else { $_ })) }) -join ', ') + ']'
            $new = [regex]::Replace($new, '"respawnFlags"\s*:\s*\[[^\]]*\]', { param($m) '"respawnFlags": ' + $arr })
        }
        if ($new -ne $text) { [IO.File]::WriteAllText($f.FullName, $new, $utf8); return $true }
        return $false
    }
    return $false
}

# A resumed session takes its model and permission mode from the saved options of its job
# (~/.claude/jobs/<short id>/state.json, "respawnFlags"; plugins/dev-kit/claude-facts.md, "`claude --bg --resume <id>`
# with any other flag starts a copy"). Set --model, --effort and --permission-mode
# there before resuming, so the lead wakes on $LeadModel / $LeadEffort (or -Model / -Effort) and in
# $LeadPermissionMode. Returns $true when the file was changed.
function Set-LeadRespawnModel([string]$SessionName, [string]$SessionId, [string]$JobsDir,
        [string]$Model = $LeadModel, [string]$Effort = $LeadEffort) {
    if (-not $JobsDir) { $JobsDir = Get-JobsDir }
    $utf8 = New-Object System.Text.UTF8Encoding $false
    foreach ($f in Get-ChildItem $JobsDir -Filter state.json -Recurse -Depth 1 -ErrorAction SilentlyContinue) {
        $text = [IO.File]::ReadAllText($f.FullName, $utf8)
        $s = $text | ConvertFrom-Json
        if (-not (Test-LeadEntryName ([string]$s.name) $SessionName)) { continue }  # the old name too (Set-LeadStateName renames it)
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

# The command the hub runs itself on the owner's yes, once it has written .claude/hard-bans.json in the
# project's main checkout; the dev-kit folder is the one next to this plugin (as in the other Pult scripts).
function Get-AddBansCommand([string]$ProjectPath) {
    $bin = ([IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\dev-kit\bin\dev-kit-bans')) -replace '\\', '/')
    return "python `"$bin`" add-approved `"$($ProjectPath -replace '\\', '/')`""
}

# Every session the plugin starts runs in $LeadPermissionMode (bypassPermissions); there is no other mode
# and no fallback. A lead starts only when the settings committed on main of its project hold the
# hard-ban deny rules for both shells (a Bash and a PowerShell deny line of the hard-ban set: git push,
# rm -rf / Remove-Item, docker) and the owner has accepted the bypass disclaimer on this machine
# (skipDangerousModePermissionPrompt in the user settings; plugins/dev-kit/claude-facts.md, "`claude --bg` with
# `bypassPermissions` fails until the owner accepts a disclaimer once"). Returns @{ Start; Mode; Reason }: Start $true and Mode bypassPermissions when
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
