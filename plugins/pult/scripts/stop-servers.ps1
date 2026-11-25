# Stops all Remote Control servers ("claude remote-control") gracefully, as Ctrl-C in their window
# would. Never kill these processes (plugins/dev-kit/claude-facts.md, "Stopping a Remote Control server:
# Ctrl-C is graceful, a kill can lock the folder").
# Usage: run without parameters. It refuses while a session under a server's folder is busy;
# -Force stops anyway, -CheckOnly only lists busy sessions. It leaves a hold file
# (~\.claude\pult\hold) so the watcher does not restart them; start-servers.ps1 removes it. -TargetPid is internal (the helper
# that types Ctrl-C).

param([int]$TargetPid = 0, [switch]$Force, [switch]$CheckOnly)

if ($TargetPid -ne 0) {
    # Helper mode: attach to the server's console and type Ctrl-C into it.
    Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class ConCtrlC {
  [DllImport("kernel32.dll")] static extern bool FreeConsole();
  [DllImport("kernel32.dll")] static extern bool AttachConsole(uint pid);
  [DllImport("kernel32.dll")] static extern IntPtr CreateFile(string n, uint a, uint s, IntPtr sa, uint c, uint f, IntPtr t);
  [StructLayout(LayoutKind.Explicit, CharSet=CharSet.Unicode)] struct KEY_EVENT_RECORD {
    [FieldOffset(0)] public int bKeyDown; [FieldOffset(4)] public short wRepeatCount;
    [FieldOffset(6)] public short wVirtualKeyCode; [FieldOffset(8)] public short wVirtualScanCode;
    [FieldOffset(10)] public char UnicodeChar; [FieldOffset(12)] public int dwControlKeyState; }
  [StructLayout(LayoutKind.Explicit)] struct INPUT_RECORD {
    [FieldOffset(0)] public short EventType; [FieldOffset(4)] public KEY_EVENT_RECORD KeyEvent; }
  [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern bool WriteConsoleInput(IntPtr h, INPUT_RECORD[] r, uint n, out uint w);
  public static bool Send(uint pid) {
    FreeConsole();
    if (!AttachConsole(pid)) return false;
    IntPtr h = CreateFile("CONIN$", 0xC0000000, 3, IntPtr.Zero, 3, 0, IntPtr.Zero);
    var recs = new INPUT_RECORD[2];
    for (int d = 0; d < 2; d++) {
      recs[d].EventType = 1; recs[d].KeyEvent.bKeyDown = d == 0 ? 1 : 0;
      recs[d].KeyEvent.wRepeatCount = 1; recs[d].KeyEvent.UnicodeChar = (char)3;
    }
    uint w; bool ok = WriteConsoleInput(h, recs, 2, out w);
    FreeConsole();
    return ok;
  }
}
"@
    if ([ConCtrlC]::Send([uint32]$TargetPid)) { exit 0 } else { exit 1 }
}

# Busy check: a session working right now under a server's folder would lose its turn.
# The session that runs this script (an ancestor process) is not counted.
if (-not $Force) {
    $entries = (Import-PowerShellDataFile (Join-Path $PSScriptRoot 'servers.psd1')).Servers
    # Home is a prefix of every project, so the hub counts only a session whose cwd is exactly home.
    $hubRoot = [IO.Path]::GetFullPath($env:USERPROFILE).TrimEnd('\') + '\'
    $roots = @($entries | Where-Object { -not $_.Hub } |
        ForEach-Object { [IO.Path]::GetFullPath($_.Path).TrimEnd('\') + '\' })
    $hasHub = [bool]($entries | Where-Object { $_.Hub })
    $ancestors = @()
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
    for ($i = 0; $p -and $i -lt 30; $i++) {
        $ancestors += $p.ProcessId
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$($p.ParentProcessId)"
    }
    try {
        $sessions = @(claude agents --json | Out-String | ConvertFrom-Json) | ForEach-Object { $_ }
    } catch { Write-Output "Could not list sessions, nothing stopped (use -Force): $_"; exit 1 }
    $busy = @($sessions | Where-Object {
        if ($_.status -ne 'busy' -or -not $_.cwd -or $ancestors -contains $_.pid) { return $false }
        $cwd = [IO.Path]::GetFullPath($_.cwd).TrimEnd('\') + '\'
        ($hasHub -and $cwd -eq $hubRoot) -or
            [bool]($roots | Where-Object { $cwd.StartsWith($_, [StringComparison]::OrdinalIgnoreCase) })
    })
    if ($busy) {
        Write-Output 'Busy sessions, nothing stopped (use -Force to stop anyway):'
        $busy | ForEach-Object { Write-Output "  $($_.name) ($($_.kind)) in $($_.cwd)" }
        exit 1
    }
    if ($CheckOnly) { Write-Output 'No busy sessions.'; exit 0 }
}

# Hold the watcher (watch-servers.ps1) so it does not bring back what is stopped on purpose; the next
# full start-servers.ps1 run removes the hold.
$stateDir = Join-Path $env:USERPROFILE '.claude\pult'
New-Item -ItemType Directory -Force $stateDir | Out-Null
Set-Content -LiteralPath (Join-Path $stateDir 'hold') -Encoding UTF8 -Value "stop-servers.ps1 $(Get-Date -Format s)"

# Project leads "L: <name>" (or still "P: <name>", resume-lib.ps1 Test-LeadName) are background sessions: stop them
# through Claude (conversation kept).
. (Join-Path $PSScriptRoot 'resume-lib.ps1')
try {
    (claude agents --json | Out-String | ConvertFrom-Json) |
        Where-Object { $_.kind -eq 'background' -and (Test-LeadName ([string]$_.name)) -and $_.pid } |
        ForEach-Object { @(claude stop $_.id) | Select-Object -First 1 }  # capture first: a cut pipe sets exit code -1
} catch { Write-Output "Could not list background sessions: $_" }

# Servers only: the `remote-control` subcommand, not the --remote-control flag of a background lead.
$servers = Get-CimInstance Win32_Process -Filter "Name='claude.exe' OR Name='node.exe'" |
    Where-Object { $_.CommandLine -match '\sremote-control\s' }
if (-not $servers) { Write-Output 'No servers running.'; exit 0 }

foreach ($s in $servers) {
    $name = if ($s.CommandLine -match "--name ['""]?([^'""]+)") { $Matches[1] } else { "PID $($s.ProcessId)" }
    $helper = Start-Process powershell.exe -WindowStyle Hidden -Wait -PassThru -ArgumentList `
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", '-TargetPid', $s.ProcessId
    if ($helper.ExitCode -ne 0) { Write-Output "Could not reach: $name"; continue }
    $proc = Get-Process -Id $s.ProcessId -ErrorAction SilentlyContinue
    if ($proc -and -not $proc.WaitForExit(30000)) { Write-Output "Still running after 30 s: $name" }
    else { Write-Output "Stopped: $name" }
}
