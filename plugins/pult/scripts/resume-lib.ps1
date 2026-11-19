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

# The command line (as an argument array for `claude`) that continues a lead, or starts it fresh.
# -Restarted adds $RestartNote to the first prompt of a resumed lead. -Prompt, -Model and -Effort
# come from the lead's servers.psd1 row when it has them (a throwaway test lead uses a cheap model).
function Get-LeadStartArgs([string]$SessionName, [string]$SessionId, [switch]$Restarted,
        [string]$Prompt = '/dev-kit:project-lead', [string]$Model = $LeadModel, [string]$Effort = $LeadEffort,
        [string]$Mode = 'auto') {
    if ($SessionId) {
        if ($Restarted) { $Prompt += ' ' + $RestartNote }
        # No flags besides the prompt: any flag makes claude start a copy instead of waking this one.
        return @('--bg', '--resume', $SessionId, '--', $Prompt)
    }
    return @('--bg', '--remote-control', $SessionName, '--name', $SessionName,
        '--permission-mode', $Mode, '--model', $Model, '--effort', $Effort, '--', $Prompt)
}

# Leads run on this model and reasoning level (the owner's rule: sessions he talks with use Opus, medium).
$LeadModel = 'opus'
$LeadEffort = 'medium'

# A resumed session takes its model and permission mode from the saved options of its job
# (~/.claude/jobs/<short id>/state.json, "respawnFlags"). Set --model, --effort and --permission-mode
# there before resuming, so the lead wakes on $LeadModel / $LeadEffort (or -Model / -Effort) and in
# -Mode. Returns $true when the file was changed.
function Set-LeadRespawnModel([string]$SessionName, [string]$SessionId, [string]$JobsDir,
        [string]$Model = $LeadModel, [string]$Effort = $LeadEffort, [string]$Mode = 'auto') {
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
        $keep += @('--model', $Model, '--effort', $Effort, '--permission-mode', $Mode)
        $arr = '[' + (($keep | ForEach-Object { ConvertTo-Json ([string]$_) }) -join ', ') + ']'
        $new = [regex]::Replace($text, '"respawnFlags"\s*:\s*\[[^\]]*\]', { param($m) '"respawnFlags": ' + $arr })
        if ($new -ne $text) { [IO.File]::WriteAllText($f.FullName, $new, $utf8); return $true }
        return $false
    }
    return $false
}

# A lead runs in the permission mode its C sessions get (the project-lead skill, "Permission mode"),
# so P -> C messages are not held for the owner's approval: bypassPermissions when the settings
# committed on main of the project hold the hard-ban deny rules for both shells (a Bash and a
# PowerShell deny line of the hard-ban set: git push, rm -rf / Remove-Item, docker) and the owner has accepted the bypass disclaimer on this machine
# (skipDangerousModePermissionPrompt in the user settings; without it `claude --bg` with
# bypassPermissions exits 1). Otherwise auto. Returns @{ Mode; Reason }.
function Get-LeadPermissionMode([string]$Path, [string]$UserSettings) {
    if (-not $UserSettings) { $UserSettings = Join-Path $env:USERPROFILE '.claude\settings.json' }
    $text = $null
    try { $text = (git -C $Path show 'main:.claude/settings.json' 2>$null) -join "`n" } catch { }
    if (-not $text) { return @{ Mode = 'auto'; Reason = 'no .claude/settings.json committed on main' } }
    try { $deny = @(($text | ConvertFrom-Json).permissions.deny) } catch { return @{ Mode = 'auto'; Reason = 'settings on main do not parse' } }
    $bash = @($deny | Where-Object { $_ -like 'Bash(git push*' -or $_ -like 'Bash(rm -rf*' -or $_ -like 'Bash(docker*' })
    $pwsh = @($deny | Where-Object { $_ -like 'PowerShell(git push*' -or $_ -like 'PowerShell(Remove-Item*' -or $_ -like 'PowerShell(docker*' })
    if (-not $bash.Count -or -not $pwsh.Count) {
        return @{ Mode = 'auto'; Reason = 'no Bash and PowerShell hard-ban deny lines on main' }
    }
    $accepted = $false
    try { $accepted = [bool]((Get-Content -Raw -Encoding UTF8 $UserSettings | ConvertFrom-Json).skipDangerousModePermissionPrompt) } catch { }
    if (-not $accepted) { return @{ Mode = 'auto'; Reason = 'bypass disclaimer not accepted on this machine' } }
    return @{ Mode = 'bypassPermissions'; Reason = 'hard bans on main' }
}
