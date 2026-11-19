# Plugin versions of a project lead (ASCII only; dot-sourced by watch-servers.ps1 and restart-leads.ps1).
# A lead loads dev-kit and the extension plugins its project enables (web-kit, unity-kit, ...); a version
# change of any of them is a reason to restart the lead (the watcher header explains how).

# @{ Version; Time } of the plugin in <PluginDir> (.claude-plugin\plugin.json: its version and last write
# time), or $null when it cannot be read.
function Get-PluginInfo([string]$PluginDir) {
    $f = Join-Path $PluginDir '.claude-plugin\plugin.json'
    try {
        $v = [string](Get-Content -Raw -Encoding UTF8 -LiteralPath $f -ErrorAction Stop | ConvertFrom-Json).version
        if (-not $v) { return $null }
        return @{ Version = $v; Time = (Get-Item -LiteralPath $f).LastWriteTime }
    } catch { return $null }
}

# The extension plugins a project uses: the keys <name>@korov-dev (not dev-kit, not pult) that are true in
# <ProjectPath>\.claude\settings.json enabledPlugins, each with its Get-PluginInfo from the plugin folder next
# to <DevKitDir> (plugins\<name>). Returns name -> info, only for plugins whose version can be read; empty
# when the project has no settings file or none of them.
function Get-LeadExtensions([string]$ProjectPath, [string]$DevKitDir) {
    $found = [ordered]@{}
    $f = Join-Path $ProjectPath '.claude\settings.json'
    if (-not (Test-Path -LiteralPath $f)) { return $found }
    $plugins = (Get-Content -Raw -Encoding UTF8 -LiteralPath $f | ConvertFrom-Json).enabledPlugins
    if (-not $plugins) { return $found }
    $root = Split-Path -Parent ([IO.Path]::GetFullPath($DevKitDir).TrimEnd('\'))
    foreach ($p in ($plugins.PSObject.Properties | Sort-Object Name)) {
        if ($p.Value -ne $true -or $p.Name -notmatch '^([A-Za-z0-9._-]+)@korov-dev$') { continue }
        $n = $Matches[1]
        if ($n -ceq 'dev-kit' -or $n -ceq 'pult') { continue }
        $info = Get-PluginInfo (Join-Path $root $n)
        if ($info) { $found[$n] = $info }
    }
    return $found
}

# What changed in the extensions since a lead process started. $Stored: name -> version the process
# started on, or $null when nothing was stored (an old lead-versions.json entry); $Current: the result of
# Get-LeadExtensions. Returns lines like "web-kit 0.1.0 -> 0.2.0". An extension with no stored version
# (stored before this check existed, or newly enabled) is not a change.
function Get-ExtChanges($Stored, $Current) {
    if ($null -eq $Stored) { return @() }
    $out = @()
    foreach ($n in $Current.Keys) {
        if ($Stored.ContainsKey($n) -and [string]$Stored[$n] -cne $Current[$n].Version) {
            $out += "$n $($Stored[$n]) -> $($Current[$n].Version)"
        }
    }
    return $out
}
