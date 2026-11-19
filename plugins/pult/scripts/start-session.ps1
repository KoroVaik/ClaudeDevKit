# Starts a background session with Remote Control in a project folder, with a long first prompt
# read from a file. Windows PowerShell 5.1 does not escape double quotes inside an argument to a
# native program, so a prompt with " was cut at the first quote. This script escapes them.
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
Push-Location $Path
try {
    # Capture all output first: `| Select-Object -First 1` cut the pipe and left exit code -1 or 255
    # although the session had started.
    $said = @(claude --bg --remote-control $Name --name $Name --permission-mode auto --model $Model `
        --effort $Effort -- (ConvertTo-NativeArg $prompt) 2>&1 | ForEach-Object { "$_" })
    $code = $LASTEXITCODE
} finally { Pop-Location }
if ($said -match 'backgrounded') { $said | Select-Object -First 1; exit 0 }
$said
exit $(if ($code) { $code } else { 1 })
