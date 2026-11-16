# Restarts project leads "P: <name>" so they load a new dev-kit version. Each lead continues its
# conversation: stop it, then start-servers.ps1 resumes it on Opus, medium, pinned, with the first
# prompt '/dev-kit:project-lead restart: plugin update' (the lead goes on where it stopped).
# Normal path (the hub rules, "Restart leads for a plugin update"): the hub session first asks each
# lead by SendMessage to reach a safe point; a script cannot send or receive those messages. The
# leads that answered the ready word (see the hub rules) are passed in -Ready: they are restarted even when they show busy (a
# lead with a background watcher always shows busy while it only waits).
# Without -Ready, only idle leads are restarted and a busy one is skipped (its turn would be cut);
# -Force restarts busy ones too, only after checking they are not in the middle of a step.
# Usage: restart-leads.ps1 -Ready 'P: Zhratva','P: Prishch'
#        restart-leads.ps1 [-Name 'P: Zhratva'] [-Force]

param([string[]]$Name, [string[]]$Ready, [switch]$Force)

$scripts = $PSScriptRoot
$leads = @((Import-PowerShellDataFile (Join-Path $scripts 'servers.psd1')).Servers |
    Where-Object { $_.Lead } | ForEach-Object { $_.Session })
if ($Ready) { $Name = $Ready }
$Name = @($Name | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })  # -File passes one comma-joined string
if ($Name) { $leads = @($leads | Where-Object { $Name -ccontains $_ }) }
if (-not $leads) { Write-Output 'No matching leads.'; exit 1 }

$sessions = @(claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ }
$stopped = @()
foreach ($lead in $leads) {
    $s = $sessions | Where-Object { $_.kind -eq 'background' -and $_.name -ceq $lead -and $_.pid } |
        Select-Object -First 1
    if (-not $s) { Write-Output "Not running, will be started: $lead"; continue }
    if ($s.status -eq 'busy' -and -not $Force -and -not $Ready) { Write-Output "Busy, skipped: $lead"; continue }
    claude stop $s.id | Select-Object -First 1
    $stopped += $lead
}
# start-servers.ps1 skips a lead whose process is still alive, so wait until every stopped one is gone.
if ($stopped) {
    $until = (Get-Date).AddSeconds(60)
    do {
        Start-Sleep -Seconds 3
        $alive = @((claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ } |
            Where-Object { $_.kind -eq 'background' -and $_.pid -and $stopped -ccontains $_.name })
    } while ($alive -and (Get-Date) -lt $until)
    if ($alive) { Write-Output "Still running after the stop, not resumed: $(($alive | ForEach-Object { $_.name }) -join ', ')" }
}
$startArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $scripts 'start-servers.ps1'))
if ($stopped) { $startArgs += @('-Restarted', ($stopped -join ',')) }
& powershell.exe @startArgs
