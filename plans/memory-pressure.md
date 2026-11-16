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

## Agreed design

(to fill)
