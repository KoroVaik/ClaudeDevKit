# Fewer "session started" pushes on restarts

Status: plan approved by the owner, waiting for a builder.

## Owner's words

«запусти обговорення стосовно пуш повідомлень. Зараз мені іде купа повідомлень про те що сесія запущена, хоча це просто перезапуск існуючой. Треба думати над воркераундом» (2026-11-23, P: ClaudeDevKit chat).

## Known context (from the lead, to check)

- Every launch with `--remote-control` pushes «Remote control enabled» to the owner's phone, and no setting turns it off (project-lead SKILL.md, "Start a C", 2026-11-20). That is why a C gets no `--remote-control`.
- Sessions that still launch with it: leads (P) started by Pult, «Обговорення:» sessions, and their restarts (Pult watcher: plugin-update restarts, self-move of P, `claude respawn` of a crashed session).
- With releases marked routine/critical (dev-kit 0.1.103) leads restart less often, but each restart still pushes.

## Success criterion

The owner no longer gets a "session started" push when an existing session is only restarted or moved; a push for a truly new session the owner must open stays only where the owner agrees it is useful.

## Facts checked live (2026-11-23, owner watched the phone with the Claude app closed)

- The push comes once, when a brand-new session first gets Remote Control (RC). `remoteControlAtStartup: true`
  in the owner's `~/.claude/settings.json` gives RC to every new session, with or without `--remote-control`,
  so a C gets RC and pushes today; the "no --remote-control for a C" rule in project-lead "Start a C" saves nothing.
- `claude --bg --resume <id>` of the same session gives no push, with or without a stored `--remote-control`.
- `claude --bg --settings '{"remoteControlAtStartup":false}' ...` starts a session with no RC (no
  `bridgeSessionId` in its job `state.json`) and no push.
- `CLAUDE_CLIENT_PRESENCE_FILE` in the env of `claude --bg` did not stop the new-session push.
- `claude --bg --resume <id> -- "/clear"` (from PowerShell; in Git Bash set `MSYS_NO_PATHCONV=1`, or
  `/clear` becomes a path) clears the context: same job, same `sessionId` in the job state, same
  `bridgeSessionId` (RC link), no push. A later question showed the old context gone. The live transcript
  moves to a NEW `.jsonl` file (job `state.json` `linkScanPath` points at it); `--resume <old id>` still wakes
  the job. `/compact` works the same way as a resume prompt (keeps the same transcript).
- `/remote-control` as a resume prompt was not retested after the Git Bash path fix; not needed now.

## Owner's approval

Owner «+» (= так) to the plan, 2026-11-23, in «Обговорення: Пуш-повідомлення про запуск сесій»:

1. **P self-move without a new session.** The Pult watcher's handoff (`watch-servers.ps1` ~:1184-1240,
   `start-servers.ps1 -Handoff`, `resume-lib.ps1` `Get-LeadStartArgs -Handoff` which today forces a fresh
   session) changes to: stop P as now, then resume the same session id with `/clear`, wait until that turn
   ends, then resume it again with the handoff prompt (`/dev-kit:project-lead` + `$HandoffNote` + the file
   name), the way a restart resumes today. P still writes the handoff file as now. No push results.
   - Whatever reads P's transcript by session id (the `$sid` compare at ~:1214, the WAKE-TAKEN transcript
     lookup, size/context checks that decide the next move) must follow the new transcript file after
     `/clear` (job `state.json` `linkScanPath`, or the newest `.jsonl` of the job); otherwise P looks full or
     stale right after the move. The builder checks every reader of the lead's transcript path.
   - Log a distinct line (e.g. `HANDOFF-CLEAR <name> <sid> <file>`).
2. **Fallback.** If the `/clear` resume or the handoff resume fails (no session id, resume error, the turn
   does not end in time), Pult falls back to today's fresh start with `--remote-control` (one push
   accepted) and logs why.
3. **C sessions start with no phone link.** The C launch in project-lead "Start a C" (SKILL.md ~:396) and any
   wrapper that starts a C add `--settings '{"remoteControlAtStartup":false}'`; the owner's global setting is
   not touched (the owner's own manual sessions keep RC). Fix the wrong claim at SKILL.md ~:397-399 with the checked
   facts above. P keeps relaying C pushes; a C never calls PushNotification itself (check, since without RC
   it cannot push).
4. **«Обговорення:» sessions keep `--remote-control` and their one push** (the owner must open them).
5. Record the checked facts where the owner's global rule points for Claude app facts
   (`plugins/dev-kit/claude-facts.md`, Remote Control section; create it if still missing) and in the
   Pult feature doc.

Success check for the builder: a test lead with RC is handed off by the watcher; job id and
`bridgeSessionId` unchanged, the new turn has no old context, the watcher reads the new transcript, and the
owner confirms no phone push (one «+/-» via P). A new C started by the changed rule has no `bridgeSessionId`.

Not in scope: the restart-notice discussion (messages held during restarts) works near the same restart
code; coordinate on `watch-servers.ps1` when merging.
