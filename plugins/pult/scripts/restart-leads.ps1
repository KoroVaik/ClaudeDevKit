# Restarts project leads "P: <name>" so they load a new dev-kit version. Each lead continues its
# conversation: stop it, then start-servers.ps1 resumes it on Opus, medium, pinned.
# A busy lead is skipped (its turn would be cut); restart it once it is idle.
# Note: a lead that keeps a background watcher (`dev-kit-sessions watch`) shows as busy while it
# only waits; use -Force for such a lead after checking it is not in the middle of a step.
# Usage: restart-leads.ps1 [-Name 'P: Zhratva','P: Prishch'] [-Force]

param([string[]]$Name, [switch]$Force)

$scripts = $PSScriptRoot
$leads = @((Import-PowerShellDataFile (Join-Path $scripts 'servers.psd1')).Servers |
    Where-Object { $_.Lead } | ForEach-Object { $_.Session })
if ($Name) { $leads = @($leads | Where-Object { $Name -contains $_ }) }
if (-not $leads) { Write-Output 'No matching leads.'; exit 1 }

$sessions = @(claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ }
$stopped = 0
foreach ($lead in $leads) {
    $s = $sessions | Where-Object { $_.kind -eq 'background' -and $_.name -ceq $lead -and $_.pid } |
        Select-Object -First 1
    if (-not $s) { Write-Output "Not running, will be started: $lead"; continue }
    if ($s.status -eq 'busy' -and -not $Force) { Write-Output "Busy, skipped: $lead"; continue }
    claude stop $s.id | Select-Object -First 1
    $stopped++
}
if ($stopped) { Start-Sleep -Seconds 5 }
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $scripts 'start-servers.ps1')
