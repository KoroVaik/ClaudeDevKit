# Plugin versions of a project lead (ASCII only; dot-sourced by watch-servers.ps1 and restart-leads.ps1).
# A lead loads dev-kit, the user-scope plugins every lead gets (rules-kit, spend-kit) and the extension plugins its
# project enables (web-kit, unity-kit, ...); a version change of any of them is a reason to restart the lead (the
# watcher header explains how). Each plugin keeps its release marks in its own releases.json.

# The plugins every lead loads whatever its project enables: they are enabled at user scope.
$script:UserScopePlugins = @('rules-kit', 'spend-kit')

# @{ Version; Time; Dir } of the plugin in <PluginDir> (.claude-plugin\plugin.json: its version and last write
# time; Dir is the folder, where releases.json lies), or $null when it cannot be read.
function Get-PluginInfo([string]$PluginDir) {
    $f = Join-Path $PluginDir '.claude-plugin\plugin.json'
    try {
        $v = [string](Get-Content -Raw -Encoding UTF8 -LiteralPath $f -ErrorAction Stop | ConvertFrom-Json).version
        if (-not $v) { return $null }
        return @{ Version = $v; Time = (Get-Item -LiteralPath $f).LastWriteTime; Dir = $PluginDir }
    } catch { return $null }
}

# The plugins of a lead besides dev-kit and pult: the user-scope plugins (rules-kit, spend-kit) and the
# <name>@korov-dev keys that are true in <ProjectPath>\.claude\settings.json enabledPlugins, each with its
# Get-PluginInfo from the plugin folder next to <DevKitDir> (plugins\<name>). Returns name -> info, only for
# plugins whose version can be read; empty when none of them exists.
function Get-LeadExtensions([string]$ProjectPath, [string]$DevKitDir) {
    $found = [ordered]@{}
    $root = Split-Path -Parent ([IO.Path]::GetFullPath($DevKitDir).TrimEnd('\'))
    $names = @($script:UserScopePlugins)
    $f = Join-Path $ProjectPath '.claude\settings.json'
    if (Test-Path -LiteralPath $f) {
        $plugins = (Get-Content -Raw -Encoding UTF8 -LiteralPath $f | ConvertFrom-Json).enabledPlugins
        if ($plugins) {
            foreach ($p in ($plugins.PSObject.Properties | Sort-Object Name)) {
                if ($p.Value -ne $true -or $p.Name -notmatch '^([A-Za-z0-9._-]+)@korov-dev$') { continue }
                $n = $Matches[1]
                if ($n -ceq 'dev-kit' -or $n -ceq 'pult') { continue }
                if ($names -cnotcontains $n) { $names += $n }
            }
        }
    }
    foreach ($n in ($names | Sort-Object)) {
        $info = Get-PluginInfo (Join-Path $root $n)
        if ($info) { $found[$n] = $info }
    }
    return $found
}

# What changed in the extensions since a lead process started. $Stored: name -> version the process
# started on, or $null when nothing was stored (an old lead-versions.json entry); $Current: the result of
# Get-LeadExtensions. Returns one @{ Name; From; To } per changed plugin. An extension with no stored version
# (stored before this check existed, or newly enabled) is not a change.
function Get-ExtChangeList($Stored, $Current) {
    if ($null -eq $Stored) { return @() }
    $out = @()
    foreach ($n in $Current.Keys) {
        if ($Stored.ContainsKey($n) -and [string]$Stored[$n] -cne $Current[$n].Version) {
            $out += @{ Name = $n; From = [string]$Stored[$n]; To = $Current[$n].Version }
        }
    }
    return $out
}

# The same as lines like "web-kit 0.1.0 -> 0.2.0".
function Get-ExtChanges($Stored, $Current) {
    return @(Get-ExtChangeList $Stored $Current | ForEach-Object { "$($_.Name) $($_.From) -> $($_.To)" })
}
