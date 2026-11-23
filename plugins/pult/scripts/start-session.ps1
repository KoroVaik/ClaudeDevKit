# Starts a background session with Remote Control in a project folder, with a long first prompt
# read from a file. A prompt with " is cut at the first quote (plugins/dev-kit/claude-facts.md,
# "Windows PowerShell 5.1 cuts a prompt at the first double quote"). This script escapes them.
# Usage: start-session.ps1 -Name 'C: <task>' -Path <project folder> -PromptFile <file>
#        [-Model opus] [-Effort medium]   (sessions the owner talks with run on Opus, medium)

param(
    [Parameter(Mandatory)] [string]$Name,
    [Parameter(Mandatory)] [string]$Path,
    [Parameter(Mandatory)] [string]$PromptFile,
    [string]$Model = 'opus',
    [string]$Effort = 'medium'
)

# Escape for the Windows command line: backslashes before a quote are doubled, the quote gets \.
function ConvertTo-NativeArg([string]$s) {
    $s = [regex]::Replace($s, '(\\*)"', { param($m) ($m.Groups[1].Value * 2) + '\"' })
    # Backslashes at the very end would escape the closing quote PowerShell adds.
    return [regex]::Replace($s, '(\\+)$', { param($m) $m.Groups[1].Value * 2 })
}

$prompt = [IO.File]::ReadAllText((Resolve-Path $PromptFile), (New-Object System.Text.UTF8Encoding $false))
if (-not $prompt.Trim()) { Write-Output 'Empty prompt file.'; exit 1 }
# The one mode is bypassPermissions, only in a project with hard bans on main (resume-lib.ps1): no fallback.
. (Join-Path $PSScriptRoot 'resume-lib.ps1')
$gate = @{ Start = $false; Reason = 'the hard-ban check failed' }
try { $gate = Get-LeadPermissionMode $Path } catch { }
if (-not $gate.Start) {
    Write-Output "NO-BANS $Name ($($gate.Reason)): session not started. Hard bans are missing on main. Hub: show the owner the exact lines, on his yes write .claude/hard-bans.json in the project's main checkout and run: $(Get-AddBansCommand $Path)"
    exit 2
}
Push-Location $Path
try {
    # Capture all output first (plugins/dev-kit/claude-facts.md, "`| Select-Object -First 1` on a native command
    # leaves a wrong exit code").
    $said = @(claude --bg --remote-control $Name --name $Name --permission-mode $LeadPermissionMode --model $Model `
        --effort $Effort -- (ConvertTo-NativeArg $prompt) 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
} finally { Pop-Location }
if ($said -match 'backgrounded') { $said | Select-Object -First 1; exit 0 }
$said
exit $(if ($code) { $code } else { 1 })
