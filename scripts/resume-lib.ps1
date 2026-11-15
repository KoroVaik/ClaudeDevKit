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
        '--permission-mode', 'auto', '--model', 'sonnet', '--', '/dev-kit:project-lead')
}
