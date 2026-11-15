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

# The command line (as an argument array for `claude`) that continues a lead, or starts it fresh.
function Get-LeadStartArgs([string]$SessionName, [string]$SessionId) {
    if ($SessionId) {
        # No flags besides the prompt: any flag makes claude start a copy instead of waking this one.
        return @('--bg', '--resume', $SessionId, '--', '/dev-kit:project-lead')
    }
    return @('--bg', '--remote-control', $SessionName, '--name', $SessionName,
        '--permission-mode', 'auto', '--model', $LeadModel, '--effort', $LeadEffort, '--', '/dev-kit:project-lead')
}

# Leads run on this model and reasoning level (the owner's rule: sessions he talks with use Opus, medium).
$LeadModel = 'opus'
$LeadEffort = 'medium'

# A resumed session takes its model from the saved options of its job
# (~/.claude/jobs/<short id>/state.json, "respawnFlags"). Set --model and --effort there before
# resuming, so the lead wakes on $LeadModel / $LeadEffort. Returns $true when the file was changed.
function Set-LeadRespawnModel([string]$SessionName, [string]$SessionId, [string]$JobsDir) {
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
        $keep += @('--model', $LeadModel, '--effort', $LeadEffort)
        $arr = '[' + (($keep | ForEach-Object { ConvertTo-Json ([string]$_) }) -join ', ') + ']'
        $new = [regex]::Replace($text, '"respawnFlags"\s*:\s*\[[^\]]*\]', { param($m) '"respawnFlags": ' + $arr })
        if ($new -ne $text) { [IO.File]::WriteAllText($f.FullName, $new, $utf8); return $true }
        return $false
    }
    return $false
}
