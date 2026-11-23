# pult

"Пульт" (the hub), a plugin of the `korov-dev` marketplace. It starts the project leads at Windows logon,
runs one Remote Control server whose session you open from the phone, and shows all projects' sessions,
their state and what waits on you. It only reads other projects' status files and session state; on a
problem it proposes a fix and acts after an explicit yes.

## How it works

- The plugin is enabled at user scope, so it loads in every session on the machine. It acts only in a
  session whose cwd is exactly the home folder: the SessionStart hook `hooks/hub-rules.py` then adds the
  hub rules (`rules/hub.md`) to the context. Everywhere else (any project folder, including those under
  home) the hook prints nothing.
- The Remote Control server "Pult" runs with cwd = the home folder, so its sessions get these rules.
- The project list is the lead entries of `scripts/servers.psd1`. To add a project, add one row there.
- One permission mode: every session the plugin starts (leads, the hub, `start-session.ps1`) runs in
  `bypassPermissions`, never `auto`. A project with no hard-ban deny lines on main starts no sessions: its
  lead is not started (log NO-BANS), Pult tells you which project lacks them and asks your «так» to the exact
  lines; on it the hub writes `.claude/hard-bans.json` in the project and adds them itself with
  `dev-kit-bans add-approved` (one commit on main, adding only). No agent runs `dev-kit-bans add` or `undo`, and
  no agent removes or edits a ban; `undo` (the latest add only) you type yourself.
- Logs: `~/.claude/pult/logs/servers.log` (written by `start-servers.ps1` and `watch-servers.ps1`; nothing is
  written inside the plugin folder).
- The watcher (`scripts/watch-servers.ps1`, started at logon) checks every minute. The rules of what it
  brings back, how often, and what a stop on purpose does are in the feature
  [Start leads at logon and heal them](../../docs/features/start-leads-at-logon-and-heal-them.md); this
  file holds its logs, files and parameters. A lead or server of `servers.psd1` that is down is brought back
  the same way as at logon (log HEAL; GIVEUP when it gave up; a start still running after 5 minutes is stopped:
  HEAL-TIMEOUT, a failed try). A task session a project lead registered,
  closed by Claude Code (no process, not stopped on purpose), comes back with `claude respawn` (`plugins/dev-kit/claude-facts.md`, "`claude respawn <id>` brings back a session Claude Code closed"; log HEAL-TASK; HEAL-TASK-TIMEOUT when it hangs past the same bound). A live lead or task session that stopped on the
  usage limit is logged once per stop (LIMIT, with the reset time; LIMIT-END when it goes on). It also removes
  dev-kit lock files whose owner is gone (log UNLOCK). It restarts a lead that runs on an older dev-kit version
  than the installed `plugins/dev-kit/.claude-plugin/plugin.json`, with no message from the hub. When depends on
  the release's mark in `plugins/dev-kit/releases.json`: a routine release waits for a later day (log
  RESTART-DEFERRED) and then for a quiet moment (the lead idle, no task session of it working, its last
  message not an open question, no owner message for 5 minutes: `sessions.py quiet`); a critical one
  restarts a quiet lead at once (log RESTART-LEAD). A critical release when the lead is not quiet: the
  watcher writes a restart request (`restart.json` in the project's dev-kit state folder, RESTART-ASKED) and
  sends it to the lead as a `restart requested: <V>` event message; the lead reaches a safe point, runs
  `dev-kit-sessions restart ready --version <V>` right after its 30-second warning; the watcher restarts it 30
  seconds after the mark (RESTART-LEAD with `ready`) if the mark is under 10 minutes old, else it clears it
  (READY-EXPIRED). A lead on dev-kit before 0.1.78 is restarted only when quiet. `scripts/restart-leads.ps1 -Ask`
  is the fast path on your ask: it restarts the idle leads now and writes a request for each busy one
  (`Asked: <name>`), which reaches the lead the same way (an older lead: its session watcher exits 7 once with
  `restart requested: <V>`). One try per lead per version; a
  failure is logged as RESTART-LEAD-FAILED; a restart still running after 10 minutes is stopped, logged as
  RESTART-LEAD-TIMEOUT, and its pause lifted at once (HOLD-STALE). A leftover `restart.json` of a lead already on the new version
  is cleared (RESTART-CLEARED). The versions the lead processes started on (by pid and start time) are kept
  in `~/.claude/pult/lead-versions.json` (log LEAD-VERSION). The same goes for the extension plugins a
  project enables in its `.claude/settings.json` (web-kit, unity-kit): a lead whose extension changed version
  is restarted when it is idle; a busy one is not woken and waits until it is idle (the log line names the
  changed plugins). The watcher also takes its own new code: when `watch-servers.ps1` or a script it loads
  changed on disk and stayed the same for two checks, it checks that the new file parses and starts a fresh
  copy of itself; once the new copy has written its own "WATCH started" line it logs WATCH-RESTART and exits
  (a broken file, or a new copy that dies at start-up, is logged once as WATCH-RESTART-SKIPPED and the old
  copy keeps running). It never touches your own sessions, taken-over ones included. `stop-servers.ps1` and
  `restart-leads.ps1` pause it with a hold file (`~/.claude/pult/hold`; log HOLD on, HOLD off) that a full
  `start-servers.ps1` run removes. A hold that `restart-leads.ps1` left and whose process is gone (it crashed
  before its start run) the watcher removes itself (log HOLD-STALE). To retire one project, remove its row from `servers.psd1`.
- No Claude session keeps a watcher of its own. Each minute the watcher also runs `dev-kit-sessions check`
  for every lead on dev-kit 0.1.78 or later and sends each new event (a task session gone, finished, on the
  usage limit, waiting 20 minutes, past a third of its context, or a restart request) to the lead as a
  cross-session message `[EVT-<id>] Pult server watcher: ...`, by a one-shot `claude -p` (haiku, safe mode,
  only the SendMessage tool, `bypassPermissions`; `plugins/dev-kit/claude-facts.md`, "A one-shot `claude -p` delivers a message into a running session"). GIVEUP, GIVEUP-TASK, RESTART-LEAD-FAILED, RESTART-LEAD-TIMEOUT, HANDOFF-FAILED and HANDOFF-TIMEOUT go to
  the Pult session the same way; Pult pushes them to your phone. A lead silent 50 minutes while one of its
  task sessions works gets a keep-warm ping. A lead past a third of its own context that saved a handoff
  (`dev-kit-sessions handoff save`) is moved to a fresh context in the same session, by a resume with `/clear`
  and then the handoff prompt, so no phone push; if that fails, a fresh session of the same name loads it (when:
  the feature above; HANDOFF-CLEAR, or HANDOFF-FALLBACK and HANDOFF, in the log; a move still running after 10
  minutes is stopped as HANDOFF-TIMEOUT and the old lead comes back by HEAL). A message counts as delivered once its id shows in the
  target's transcript; until then it is sent again, then pushed to your phone (for Pult: «Pult не піднявся -
  запусти його на комп'ютері»). A push also goes once per session when a conversation passes 0.7 of its
  window. The watcher cannot push by itself (a fresh session's push is refused: `plugins/dev-kit/claude-facts.md`,
  "A push from a fresh session is refused"), so every push is a message asking a relay session to push it: Pult when it is live, else a
  live lead. It logs each live session's size every 10 minutes (log WAKE, WAKE-SENT, WAKE-TAKEN,
  WAKE-FAILED, WAKE-FALLBACK, WAKE-FALLBACK-NONE, PUSH-SIZE, SIZE). Its files in `~/.claude/pult`: `wake-pending.json`,
  `wake-state.json`, `size-state.json`.
- A lead row in `servers.psd1` may set `Prompt`, `Model` and `Effort` (defaults: `/dev-kit:project-lead`,
  Opus, medium); a throwaway test lead uses a cheap model this way.

## Start at logon

Put a shortcut "Pult - project servers" in the Windows Startup folder (`shell:startup`) with the target:

    powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "<repo>/plugins/pult/scripts/start-servers.ps1"

`<repo>` is this repository's folder. `scripts/stop-servers.ps1` stops everything gracefully (it refuses while
a session is busy, `-Force` overrides, `-CheckOnly` only lists).

## Commands for the phone flow

The steps of a day with a project lead (P) from the phone and the rules behind them are in the epic
[Run all projects from the phone](../../docs/epics/run-all-projects-from-the-phone.md) and the feature
[Hand work to the project lead](../../docs/features/hand-work-to-the-project-lead.md). The commands:

- Status page: `python -X utf8 scripts/status-page.py` writes `~/.claude/pult/status.html` (`--out` for another file).
- All desktop-app sessions of all projects: `python -X utf8 scripts/list-sessions.py`.
- After a dev-kit plugin update the watcher restarts each P by itself (a routine release on a later day); to hurry it, run `scripts/restart-leads.ps1 -Ask`. By hand: `scripts/restart-leads.ps1`, or `scripts/stop-servers.ps1` (graceful stop) and then `scripts/start-servers.ps1`, or restart Windows.
