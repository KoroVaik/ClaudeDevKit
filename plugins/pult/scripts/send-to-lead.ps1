# Passes the owner's request from the Pult hub to a project's lead (hub.md, "Passing work to a lead"). ASCII only.
# Usage: powershell -NoProfile -File send-to-lead.ps1 -Lead "L: <project>" -TextFile <path to a UTF-8 file>
# The file holds the whole message, kind word first. The hub's own SendMessage is not used: the hub's session runs
# in auto mode, and a send from it to a bypassPermissions lead is not checked; a one-shot bypassPermissions sender
# is the one the watcher reaches the leads with every day (watch-servers.ps1, $WakeMode).
# Prints "sent" (exit 0) or "failed: <reason>" (exit 1).
param([Parameter(Mandatory = $true)][string]$Lead, [Parameter(Mandatory = $true)][string]$TextFile,
    [string]$WakeExe, [string]$StateDir, [int]$WakeWaitSec = 60)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'resume-lib.ps1')  # Test-LeadName
. (Join-Path $PSScriptRoot 'send-lib.ps1')  # Send-Wake

if (-not (Test-LeadName $Lead)) { Write-Output "failed: not a lead name: $Lead"; exit 1 }
try { $text = [IO.File]::ReadAllText($TextFile, [Text.Encoding]::UTF8).Trim() } catch { Write-Output "failed: cannot read $TextFile"; exit 1 }
if (-not $text) { Write-Output "failed: the message file is empty"; exit 1 }
if (-not $WakeExe) {  # an Application: claude.exe or claude.cmd, never the npm claude.ps1 that Start-Process cannot run
    $WakeExe = [string](Get-Command claude -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1).Source
}
if (-not $StateDir) { $StateDir = Join-Path $env:USERPROFILE '.claude\pult\relay' }  # its own folder, not the watcher's

$r = Send-Wake $Lead $text 'bypassPermissions'
if ($r.Ok) { Write-Output 'sent'; exit 0 }
Write-Output "failed: $($r.Reason)"; exit 1
