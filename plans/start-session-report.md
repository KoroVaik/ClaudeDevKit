# Pult: start-session.ps1 reports a failure on success

From BACKLOG.md (owner yes, retro 2026-11-19); entry removed once built.

## Cause (checked)

`native | Select-Object -First 1` stops the pipe after the first line, so PowerShell 5.1 sets
`$LASTEXITCODE` to -1 (255 seen by some callers) although the native command succeeded. Reproduced
with a Python one-liner: piped -1, captured first 0. `powershell -File` still exits 0, so only callers
that run the script in their own PowerShell (`& script.ps1`) saw the failure.

## Change (pult 0.1.14)

- `start-session.ps1`: captures all output, prints the first line and exits 0 when it says
  "backgrounded"; otherwise prints everything and exits with claude's code (1 if none).
- `restart-leads.ps1`, `stop-servers.ps1`: `claude stop` output captured before `Select-Object`.
- `start-servers.ps1` already captured first; `watch-servers.ps1` runs it with `-File`, so no false
  HEAL-FAILED (none in servers.log either). No change there.

## Checks

- Live: one throwaway haiku session started through the script: "backgrounded", `$LASTEXITCODE=0`;
  session stopped and removed afterwards.

## Paid spend

One haiku session with a one-line prompt: well under $0.05. Total: < $0.05.
