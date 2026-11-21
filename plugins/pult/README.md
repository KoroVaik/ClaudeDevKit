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
  lines; on it the hub writes `.claude/hard-bans.json` in the project and gives you one command to type
  yourself: `! python -X utf8 <dev-kit folder>/bin/dev-kit-bans add-approved <project path>`. No agent runs
  `dev-kit-bans add`, `add-approved` or `undo`; `undo` (the latest add only) is typed by you too.
- Logs: `~/.claude/pult/logs/servers.log` (written by `start-servers.ps1` and `watch-servers.ps1`; nothing is
  written inside the plugin folder).
- The watcher (`scripts/watch-servers.ps1`, started at logon) checks every minute. A lead or server of
  `servers.psd1` that is down for two checks is brought back the same way as at logon (log HEAL; at most 3
  tries an hour, then GIVEUP). A task session a project lead registered, closed by Claude Code (no
  process, not stopped on purpose), comes back with `claude respawn` (log HEAL-TASK). A live lead or task session that stopped on the
  usage limit is logged once per stop (LIMIT, with the reset time; LIMIT-END when it goes on). It also removes
  dev-kit lock files whose owner is gone (log UNLOCK). It restarts a lead that runs on an older dev-kit version
  than the installed `plugins/dev-kit/.claude-plugin/plugin.json`, with no message from the hub: an idle lead
  at once (log RESTART-LEAD). A busy lead (or, from dev-kit 0.1.78, an idle one while a task session of it
  works) is not interrupted: the watcher writes a restart request (`restart.json` in the project's dev-kit
  state folder, RESTART-ASKED) and sends it to the lead as a `restart requested: <V>` event message; the lead
  reaches a safe point and runs `dev-kit-sessions restart ready --version <V>`; the watcher then restarts it
  (RESTART-LEAD with `ready`) if the mark is under 10 minutes old, else it clears it (READY-EXPIRED). A lead on
  dev-kit before 0.1.78 notices the version on its ordinary wake-ups instead. `scripts/restart-leads.ps1 -Ask`
  is the fast path on your ask: it restarts the idle leads now and writes a request for each busy one
  (`Asked: <name>`), which reaches the lead the same way (an older lead: its session watcher exits 7 once with
  `restart requested: <V>`). One try per lead per version; a
  failure is logged as RESTART-LEAD-FAILED. A leftover `restart.json` of a lead already on the new version
  is cleared (RESTART-CLEARED). The versions the lead processes started on (by pid and start time) are kept
  in `~/.claude/pult/lead-versions.json` (log LEAD-VERSION). The same goes for the extension plugins a
  project enables in its `.claude/settings.json` (web-kit, unity-kit): a lead whose extension changed version
  is restarted when it is idle; a busy one is not woken and waits until it is idle (the log line names the
  changed plugins). The watcher also takes its own new code: when `watch-servers.ps1` or a script it loads
  changed on disk and stayed the same for two checks, it checks that the new file parses and starts a fresh
  copy of itself; once the new copy has written its own "WATCH started" line it logs WATCH-RESTART and exits
  (a broken file, or a new copy that dies at start-up, is logged once as WATCH-RESTART-SKIPPED and the old
  copy keeps running). It never touches your own sessions, taken-over ones included. `stop-servers.ps1` and `restart-leads.ps1` pause it
  (a hold file) until the next `start-servers.ps1` run, so a stop on purpose stays stopped. A lead stopped
  only with `claude stop` comes back; to retire one project, remove its row from `servers.psd1`.
- No Claude session keeps a watcher of its own. Each minute the watcher also runs `dev-kit-sessions check`
  for every lead on dev-kit 0.1.78 or later and sends each new event (a task session gone, finished, on the
  usage limit, waiting 20 minutes, past half its context, or a restart request) to the lead as a
  cross-session message `[EVT-<id>] Pult server watcher: ...`, by a one-shot `claude -p` (haiku, safe mode,
  only the SendMessage tool, `bypassPermissions`). GIVEUP, GIVEUP-TASK, RESTART-LEAD-FAILED and HANDOFF-FAILED go to
  the Pult session the same way; Pult pushes them to your phone. A lead silent 50 minutes while one of its
  task sessions works gets a keep-warm ping. A lead past half its own context that saved a handoff
  (`dev-kit-sessions handoff save`) is moved to a fresh session of the same name once it has been idle and
  quiet for 5 minutes, or at once after `handoff go`; HANDOFF in the log. A message counts as delivered once its id shows in the
  target's transcript; until then it is sent again, then pushed to your phone (for Pult: «Pult не піднявся -
  запусти його на комп'ютері»). A push also goes once per session when a conversation passes 0.7 of its
  window. The watcher cannot push by itself (a fresh session's push is refused: «Not sent - this terminal
  is active»), so every push is a message asking a relay session to push it: Pult when it is live, else a
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
- After a dev-kit plugin update the watcher restarts each P by itself; to hurry it, run `scripts/restart-leads.ps1 -Ask`. By hand: `scripts/restart-leads.ps1`, or `scripts/stop-servers.ps1` (graceful stop) and then `scripts/start-servers.ps1`, or restart Windows.
