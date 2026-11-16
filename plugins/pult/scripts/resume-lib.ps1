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
        [string]$Prompt = '/dev-kit:project-lead', [string]$Model = $LeadModel, [string]$Effort = $LeadEffort) {
    if ($SessionId) {
        if ($Restarted) { $Prompt += ' ' + $RestartNote }
        # No flags besides the prompt: any flag makes claude start a copy instead of waking this one.
        return @('--bg', '--resume', $SessionId, '--', $Prompt)
    }
    return @('--bg', '--remote-control', $SessionName, '--name', $SessionName,
        '--permission-mode', 'auto', '--model', $Model, '--effort', $Effort, '--', $Prompt)
}

# Leads run on this model and reasoning level (the owner's rule: sessions he talks with use Opus, medium).
$LeadModel = 'opus'
$LeadEffort = 'medium'

# A resumed session takes its model from the saved options of its job
# (~/.claude/jobs/<short id>/state.json, "respawnFlags"). Set --model and --effort there before
# resuming, so the lead wakes on $LeadModel / $LeadEffort (or -Model / -Effort). Returns $true when the file was changed.
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
            if ($flags[$i] -eq '--model' -or $flags[$i] -eq '--effort') { $i++; continue }
            $keep += $flags[$i]
        }
        $keep += @('--model', $Model, '--effort', $Effort)
        $arr = '[' + (($keep | ForEach-Object { ConvertTo-Json ([string]$_) }) -join ', ') + ']'
        $new = [regex]::Replace($text, '"respawnFlags"\s*:\s*\[[^\]]*\]', { param($m) '"respawnFlags": ' + $arr })
        if ($new -ne $text) { [IO.File]::WriteAllText($f.FullName, $new, $utf8); return $true }
        return $false
    }
    return $false
}
