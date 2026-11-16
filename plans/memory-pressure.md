# Sessions and watchers survive low memory

## Owner's words (2026-11-16)

To P: ClaudeDevKit: «Запускай сесію для обговорення і вирішення».
Via P: Zhratva (its summary): the owner asks for a radical fix that removes this class of problem, not a stopgap.

## What happened (from P: Zhratva and P: ClaudeDevKit)

- 2026-11-16, Zhratva: while «C: По N хвилин» ran a heavy check (rules-check --final), the PC (31 GB RAM) ran
  low on memory. Claude Code reaped P's background `dev-kit-sessions watch` with the note «stopped because the
  system is running low on memory... Do not start it again on your own... start it again only when asked», and
  the C's own memory-heavy check died too. Free memory later: 6.7 GB. P lost crash detection for every C until
  the owner said yes, and the owner did not know what the watcher was.
- Same day, P: ClaudeDevKit: its watcher was reaped the same way while the session was idle.
- The note says the owner can turn the reaping off by starting Claude Code with
  CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1 (a stopgap, not the fix).

## Asks from P: Zhratva

1. A rule in project-lead for a reaped watcher: who decides to re-arm, and whether P may re-arm once memory
   is back without asking the owner.
2. Root cause of the memory pressure: several Opus C sessions plus subagents plus heavy checks in parallel on
   one PC. Consider a memory-aware limit on parallel C sessions or heavy steps (like the shared-app queue) and a
   cheap memory check before starting a C.
3. A lighter watcher (no long-lived shell in P), or a crash signal by hook instead of polling. Note: the Pult
   watcher (plugins/pult/scripts/watch-servers.ps1) already runs outside Claude Code from logon and heals dead
   leads; it may be a better home for crash detection of C sessions.

## Goal

Talk with the owner first (dev-kit:discovery-round): measure what eats memory, agree the design in plain
words (the owner approves ideas, not wording). Then build it here, test it, and report to P.

## Measured (2026-11-16)

- Who killed the watcher: Claude Code itself. When Windows reports critically low memory, it stops the
  background shells of idle sessions (text found in the claude.exe binary). It also closed this idle C
  session while it waited for the owner (P brought it back with `claude respawn`).
- Physical RAM was not exhausted (8 GB free of 31). The commit limit was: 49 of 54 GB, because the
  pagefile was system-managed and grows only near the limit (it later grew to 40 GB, limit 71 GB).
  Not checked: which exact signal Claude Code reads.
- Biggest users at the time: Claude sessions about 9 GB together, an idle Unity editor about 6 GB, a
  Zhratva recipe check with 18 parallel Python workers about 5 GB.

## Agreed design

- No queues and no memory gate before C sessions or heavy steps (owner: memory is enough, Windows is
  the problem).
- Pagefile fixed at 48 GB initial, 64 GB max (done 2026-11-16 on the owner's yes; works after a reboot).
- P re-arms its watcher by itself when Claude Code stopped it for low memory; no owner yes needed
  (owner's yes 2026-11-16). A dead watcher's leftover lock must not block the new one.
- The Pult watcher (runs outside Claude Code, so it is never reaped) also brings back C sessions that
  Claude Code closed: a session P registered as active that has no process and did not end on its own
  gets `claude respawn <id>` (owner's yes 2026-11-16). P's own watcher reports a session with no process
  as gone only after 5 minutes, so Pult has its chance. Taken-over owner sessions are never respawned.

## Checked (2026-11-16)

- Live: a throwaway session's process was killed; the Pult watcher on a temp registry respawned it
  (HEAL-TASK, new pid), and the lead's watcher on it exited "time limit, all alive" instead of gone.
- Not checked: whether a reaped watcher's python process can outlive its shell (then the re-armed one
  exits "already watching" and the old one keeps watching, which is fine).
- The running Pult watcher uses the new script only after its restart (next logon or start-servers.ps1).
