# Stops all Remote Control servers ("claude remote-control") gracefully, as Ctrl-C in their window
# would: the server shuts down its sessions and keeps them for the next start.
# Never kill these processes: a forced stop can lock the project folder for minutes.
# Usage: run without parameters. -TargetPid is internal (the helper that types Ctrl-C).

param([int]$TargetPid = 0)

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

# Project leads "P: <name>" are background sessions: stop them through Claude (conversation kept).
try {
    (claude agents --json | Out-String | ConvertFrom-Json) |
        Where-Object { $_.kind -eq 'background' -and $_.name -like 'P: *' -and $_.pid } |
        ForEach-Object { claude stop $_.id | Select-Object -First 1 }
} catch { Write-Output "Could not list background sessions: $_" }

# Servers only: the `remote-control` subcommand, not the --remote-control flag of a background P.
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
