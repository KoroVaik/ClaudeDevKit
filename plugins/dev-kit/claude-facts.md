# Claude facts

How the Claude apps behave in practice, where official docs say little: the desktop and phone apps, claude.ai,
Remote Control, background sessions, headless `claude -p`, plugins and hooks, subagents, the shell under Claude
Code. Facts only, no rules: a rule that relies on a fact keeps what to do and links here.

Last re-check: 2026-11-23 | Claude Code: 2.1.330

## How to use

- Find the section of the app or area you rely on and read its entries.
- `checked`: trust it. `doubtful`: a hypothesis; check it before you build on it. `outdated`: no longer true.
- Met a quirk and used a workaround for it, and it is not here or behaves otherwise: add one line, no subagent
  and no message: `dev-kit-retro add --project ClaudeDevKit --text "claude app: <app>: <what happened>; workaround:
  <what you did>"` (in Bash; where `dev-kit-retro` is not found, `python -X utf8 <dev-kit plugin>/scripts/retro.py`
  with the same arguments).
  Errors of tools (a failed send, a refused launch) are collected by the daily scan by themselves.
- Only the `dev-kit:facts-keeper` agent edits this file. The ClaudeDevKit retro hands it new findings and has it
  re-check the facts weekly and after a Claude Code update.

Why: owner, 2026-11-23 (`plans/claude-quirks-docs.md`): official docs say almost nothing about these app
behaviours, they were scattered over skills, scripts and notes, and one fact had two contradicting wordings.

## Entry format

    ### <short plain title>
    - What happens: <the behaviour, with the exact error text if any>
    - Workaround: <how it is got around, or "none">
    - App: <app or area> | Claude Code: <version or unknown>
    - Seen: <YYYY-MM-DD> | <how it was checked: live test, error text, owner's report> | <project, session>
    - Re-check: <command or steps> | safe | owner-only
    - Status: checked | doubtful | outdated (<YYYY-MM-DD>)
    - History: <older behaviour or sightings, optional>

One entry per behaviour. A newer direct observation replaces an older one; the older goes to `History`.

## Desktop app

### The desktop app folds a turn's tool calls into one line
- What happens: In the desktop app the tool calls of a turn show as one folded line, and the text of the turn shows below it.
- Workaround: none.
- App: desktop app | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill, start status
- Re-check: look at a turn with tool calls in the desktop app | owner-only
- Status: doubtful

### A lead is not a local session in the desktop app, so the owner cannot type a `!` command in its chat
- What happens: The owner cannot type a `!` command in the chat of a lead (or of the hub). From the phone app a `!` message arrives as a plain message. In the desktop app a lead is not a local session.
- Workaround: none for the owner; an agent can run the command for him (see `plugins/dev-kit/skills/project-lead/SKILL.md`, "Hard bans").
- App: desktop app, phone app | Claude Code: unknown
- Seen: 2026-11-21 | owner's report, not re-seen | ClaudeDevKit, hard-ban approval
- Re-check: type `!echo hi` in a lead's chat in the desktop app and from the phone | owner-only
- Status: doubtful

### `claude stop <id>` fails when the session is open in an app window
- What happens: `claude stop <id>` fails when the session is open in a window of the desktop app.
- Workaround: none known; what the lead does when a stop fails: see `plugins/dev-kit/skills/project-lead/SKILL.md`, "Take over a session the owner started".
- App: desktop app | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill, stopping a session
- Re-check: open a throwaway session in the app, run `claude stop <id>` | owner-only
- Status: doubtful

### Desktop app data layout
- What happens: Sessions are `local_*.json` files under `%LOCALAPPDATA%/Claude-Data/claude_pzs8sxrjxfjjc/claude-code-sessions/<accountUuid>/<orgUuid>/`. The CLI writes `~/.claude/sessions/<pid>.json` with a `cliSessionId`. The app shows the statuses `blocked`, `completed` and `review_ready`.
- Workaround: none; `plugins/pult/scripts/list-sessions.py` reads this layout.
- App: desktop app | Claude Code: unknown
- Seen: 2026-11-15 | read of the folders ("Layout of the desktop app data checked on 2026-11-15") | ClaudeDevKit, Pult
- Re-check: `python -I -X utf8 plugins/pult/scripts/list-sessions.py` | safe
- Status: checked

### The in-app browser screenshot is at most about 800 px wide
- What happens: The in-app browser (`mcp__Claude_Browser__*`, only in the desktop app) returns a screenshot at most about 800 px wide whatever the window size: 3840x2160 comes back 800x452, 1024 px wide 800 px, a phone window 375 px wide 657 px (its real size). `zoom` only crops the small image.
- Workaround: a headless capture (`web-kit-shot`) renders the page at its real size (full resolution).
- App: desktop app, in-app browser | Claude Code: unknown
- Seen: 2026-11-10 | measured | `plugins/web-kit/browser-checks.md`
- Re-check: take a screenshot of a wide window in the in-app browser, read its size | owner-only
- Status: checked

### A board sent with `SendUserFile` and `display: render` may not show as a page
- What happens: An HTML board sent with `SendUserFile` and `display: render` is said to open in one click in the built-in browser. Whether the desktop app and the phone app show an HTML file as a page was not tested.
- Workaround: `plugins/web-kit/skills/design-screen/SKILL.md` sends the HTML board itself with `display: render` (the page carries its styles inside) and its screen shots as PNGs; `plugins/unity-kit/skills/scene-sketch/SKILL.md` renders the page to a PNG and sends that, the page only on request.
- App: desktop app, phone app | Claude Code: unknown
- Seen: date not stated | check not stated | web-kit design-screen skill, unity-kit scene-sketch skill
- Re-check: send a small HTML file with `display: render` to the desktop app and the phone | owner-only
- Status: doubtful

## Phone app

### Every image the main session opens shows in the owner's phone chat
- What happens: In the phone app every image the session opens (a `Read` of a PNG) shows in the owner's chat, unnumbered, next to the set being sent.
- Workaround: a subagent opens the image and reports (see `plugins/web-kit/browser-checks.md`, "Roles").
- App: phone app | Claude Code: unknown
- Seen: 2026-11-20 | owner's report, not re-seen | Zhratva
- Re-check: open a PNG with `Read` in a session the owner watches on the phone | owner-only
- Status: doubtful

### A push from a fresh session is refused
- What happens: A `PushNotification` from a fresh session (a `-p` one-shot, a background session, one with Remote Control) is refused with "Not sent - this terminal is active". A push from a session the owner is attached to (Pult, a live lead) goes through.
- Workaround: a session the owner is attached to (Pult, a live lead) calls `PushNotification`; the Pult watcher asks it by message (see `plugins/pult/rules/hub.md`, "Phone push").
- App: phone app, `PushNotification` tool | Claude Code: unknown
- Seen: 2026-11-20 | live test, error text | ClaudeDevKit, `docs/findings/idle-wake-cost.md`
- Re-check: call `PushNotification` from a throwaway `claude -p` session | owner-only
- Status: checked

### No push shows while the Claude app is open on the phone
- What happens: While the Claude app is open on the phone screen, no push shows. A test push arrived only after the app was closed.
- Workaround: none.
- App: phone app | Claude Code: unknown
- Seen: 2026-11-20 | live test | ClaudeDevKit, `docs/findings/idle-wake-cost.md`
- Re-check: send a push with the app open, then closed | owner-only
- Status: checked

### The push tool skips a push while the owner is at the screen
- What happens: `PushNotification` skips a push while the owner is at the screen; the lead's skill treats that as expected. It is not known whether this is the same rule as "Not sent - this terminal is active" (see "A push from a fresh session is refused").
- Workaround: none; a skipped push still counts as sent.
- App: `PushNotification` tool | Claude Code: unknown
- Seen: 2026-11-19 | check not stated | ClaudeDevKit, project-lead skill
- Re-check: call `PushNotification` from an attached session while the owner is at the screen, read the answer | owner-only
- Status: doubtful

### The phone app's session list does not group by project or show what waits on the owner
- What happens: The session list of the phone app is not grouped by project and does not show which sessions wait on the owner.
- Workaround: the Pult status page.
- App: phone app | Claude Code: unknown
- Seen: 2026-11-20 | backlog verdict, check not stated | ClaudeDevKit, `BACKLOG.md`
- Re-check: look at the session list on the phone | owner-only
- Status: doubtful

### A background session started without Remote Control does not show in the phone app
- What happens: A background session that has no Remote Control does not show in the phone app; an «Обговорення:» session (with it) does. Stated as a consequence of having Remote Control, not tested. Leaving out `--remote-control` does not by itself mean no Remote Control: `remoteControlAtStartup: true` in the user settings gives it to every new session (see "`remoteControlAtStartup: true` gives every new session Remote Control, with or without `--remote-control`").
- Workaround: none.
- App: phone app, Remote Control | Claude Code: unknown
- Seen: date not stated | not tested | `docs/epics/run-all-projects-from-the-phone.md`
- Re-check: start a throwaway background session without the flag, look at the phone | owner-only
- Status: doubtful

## claude.ai and the Console

### The Anthropic API gives no credit balance
- What happens: The Anthropic API gives no credit balance, so the Console pages (Billing, Cost) are the only place to read it.
- Workaround: the weekly Console check by the owner, now as a reconciliation against the dev-kit API log.
- App: Console | Claude Code: unknown
- Seen: 2026-11-21 | owner's statement, not re-seen | ClaudeDevKit, API spend log
- Re-check: look for a balance in the API reference and the Console | owner-only
- Status: doubtful

## Remote Control

### `claude remote-control --continue` cannot be combined with `--spawn`
- What happens: `claude remote-control --continue` cannot take `--spawn` (same-dir is the default).
- Workaround: try `--continue` first; if it fails within 20 s, log CONTINUE-FAILED and start fresh with `--spawn same-dir`.
- App: Remote Control | Claude Code: unknown
- Seen: date not stated | check not stated; "not yet checked on a real restart" | Pult hub rules
- Re-check: restart a Remote Control server of a throwaway folder with `--continue` | owner-only
- Status: doubtful

### The Remote Control server's own session has a system name
- What happens: The session of a Remote Control server (cwd = the home folder) has a system name like "<user>-f1" in `claude agents --json` (kind `interactive`). The app shows the name the server sets ("Pult").
- Workaround: the name the server sets ("Pult") is the one that shows in the app; the system name appears only in the `claude agents --json` list (see `plugins/pult/rules/hub.md`, "Answering "статус"").
- App: Remote Control | Claude Code: unknown
- Seen: date not stated | check not stated | Pult hub rules
- Re-check: `claude agents --json` | safe
- Status: doubtful

### Stopping a Remote Control server: Ctrl-C is graceful, a kill can lock the folder
- What happens: Ctrl-C typed in the console of a `claude remote-control` server is graceful: the server shuts its sessions down and keeps them for the next start. Killing the process can lock the project folder for minutes.
- Workaround: send Ctrl-C into the server's console (`plugins/pult/scripts/stop-servers.ps1` injects it).
- App: Remote Control | Claude Code: unknown
- Seen: date not stated | check not stated | Pult scripts
- Re-check: stop a throwaway server with Ctrl-C, then restart it | owner-only
- Status: doubtful

### The phone gets one push when a brand-new session first gets Remote Control
- What happens: The phone push «Remote control enabled» comes once, when a brand-new session first gets Remote Control. It is not tied to the `--remote-control` flag (see the next entry). `claude --bg --resume <id>` of the same session gives no push, with or without a stored `--remote-control`. `CLAUDE_CLIENT_PRESENCE_FILE` in the environment of `claude --bg` did not stop the push of a new session.
- Workaround: start the session with `--settings` holding `{"remoteControlAtStartup":false}` (file or inline form: see the next entry): it has no Remote Control (no `bridgeSessionId` in its job `state.json`) and no push; wake an existing session with `claude --bg --resume <id>` (no push).
- App: phone app, Remote Control | Claude Code: unknown
- Seen: 2026-11-23 | live test, the owner watched the phone with the Claude app closed | ClaudeDevKit, `plans/push-noise.md`
- Re-check: start a throwaway background session, watch the phone; resume it, watch again | owner-only
- Status: checked
- History: 2026-11-20, owner's report, not re-seen (title then: "Every `--remote-control` launch pushes "Remote control enabled" to the phone"): every launch with `--remote-control` pushes «Remote control enabled» to the owner's phone, and no setting turns it off. Replaced on 2026-11-23: the push comes with the first Remote Control of a new session, not with the flag, and the `--settings` override above turns it off.

### `remoteControlAtStartup: true` gives every new session Remote Control, with or without `--remote-control`
- What happens: With `remoteControlAtStartup: true` in `~/.claude/settings.json`, every new session gets Remote Control (and its one push), whether or not it is started with `--remote-control`. So a session started without the flag still has Remote Control and pushes.
- Workaround: `claude --bg --settings <path to a JSON file holding {"remoteControlAtStartup": false}> ...` starts a session with no Remote Control; the user's own settings file stays as it is. The file form works like the inline JSON (no `bridgeSessionId` in the job `state.json`; a session with no `--settings` had one) and is the safer form from Windows PowerShell 5.1. Inline from PowerShell 5.1 needs the inner quotes escaped: `--settings '{\"remoteControlAtStartup\":false}'` gave no `bridgeSessionId`, but the job's `respawnFlags` stored the value cut (`remoteControlAtStartup\":false}`). Not tested: whether the plain `'{"remoteControlAtStartup":false}'` fails in PowerShell 5.1 (the quote-cut entry under "Windows shell" suggests it does). `--settings` is kept in the job's `respawnFlags`, so `claude --bg --resume <id>` keeps it: confirmed 2026-11-23 by a resume with `/clear` of a job started with the file (no `bridgeSessionId` after it).
- App: Remote Control, `claude` CLI | Claude Code: unknown
- Seen: 2026-11-23 | live test, the owner watched the phone; later three throwaway `claude --bg` sessions (haiku), each job's `state.json` read | ClaudeDevKit, `plans/push-noise.md`
- Re-check: start a throwaway background session with and without the `--settings` file, look for `bridgeSessionId` in its job `state.json` | owner-only
- Status: checked

### A resume with `/clear` as its prompt clears the context and keeps the job and the Remote Control link
- What happens: `claude --bg --resume <id> -- "/clear"` clears the context: same job (same short id), same `sessionId` in the job's `state.json` (it keeps the OLD id and gains `resumeSessionId` = the new id), same `bridgeSessionId` (the Remote Control link), no phone push. A later question showed the old context gone. The live transcript moves to a NEW `.jsonl` file (`linkScanPath` in the job's `state.json` points at it); `--resume <old id>` still wakes the job. But `claude agents --json --all` lists the job (status idle) with `sessionId` = the NEW id, so the two sources differ; both processes (pty host and worker) keep the OLD id in their command line (`--resume ...<old id>.jsonl ... -- /clear`). `claude stop <short id>` stops it at once. `/compact` as the resume prompt works the same way but keeps the same transcript. `/remote-control` as a resume prompt was not retested.
- Workaround: in Git Bash set `MSYS_NO_PATHCONV=1`, or `/clear` becomes a path (from PowerShell it needs nothing).
- App: Remote Control, background sessions | Claude Code: unknown
- Seen: 2026-11-23 | live test, the owner watched the phone; later a throwaway job without Remote Control, `claude stop` then resume with `/clear`, `state.json` and `claude agents --json --all` compared | ClaudeDevKit, `plans/push-noise.md`
- Re-check: throwaway background session with Remote Control, `claude stop`, then resume with `/clear`, read its `state.json` and watch the phone | owner-only
- Status: checked

## Background sessions

### `claude --bg` with `bypassPermissions` fails until the owner accepts a disclaimer once
- What happens: `claude --bg --permission-mode bypassPermissions` fails with exit 1 until the owner accepts a disclaimer once per machine. The accepted choice is recorded as `skipDangerousModePermissionPrompt` in the user settings.
- Workaround: the owner runs `claude --dangerously-skip-permissions` interactively once and accepts.
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-15 | live, exit code | ClaudeDevKit, project-lead skill
- Re-check: look for `skipDangerousModePermissionPrompt` in `~/.claude/settings.json` | safe
- Status: checked

### After the disclaimer, a background session in `bypassPermissions` runs commands with no prompt
- What happens: After the owner accepted the disclaimer, a background session in `bypassPermissions` ran a shell command with no prompt.
- Workaround: none needed.
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-15 | live test | ClaudeDevKit, project-lead skill
- Re-check: start a throwaway background session, ask it to run `echo hi` | owner-only
- Status: checked

### `--add-dir <path> -- "<prompt>"` swallows the prompt as a path
- What happens: The `--add-dir` flag takes several values, so `--add-dir <path> -- "<prompt>"` reads the prompt as one more path, and the session starts idle with no prompt.
- Workaround: always write `--add-dir=<path>`.
- App: background sessions, `claude` CLI | Claude Code: unknown
- Seen: 2026-11-15 | live | Zhratva
- Re-check: start a throwaway session both ways and see whether it works on the prompt | owner-only
- Status: checked

### `claude -w` cuts the worktree from the remote's default branch
- What happens: `claude -w` cuts the new worktree from the remote's default branch, not from the local main, so it can be far behind (seen: 6 weeks old, without `.claude/dev-kit.md`).
- Workaround: create the worktree by hand with `git worktree add`.
- App: `claude` CLI | Claude Code: unknown
- Seen: date not stated | seen live | project-lead skill
- Re-check: `claude -w` in a throwaway repo whose local main is ahead of the remote | owner-only
- Status: checked

### `claude --bg` prints only a short id
- What happens: `claude --bg` prints only the 8-hex short id. An id pasted from its output may carry a CR or spaces and then matches nothing.
- Workaround: trim the id before use (`plugins/dev-kit/scripts/sessions.py` does).
- App: background sessions | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill, `sessions.py`
- Re-check: `claude --bg` a throwaway session, read the output bytes | owner-only
- Status: doubtful

### "Workspace not trusted" blocks a background session in a new folder
- What happens: A background session in a folder never opened with `claude` stops with "Workspace not trusted".
- Workaround: the owner runs `claude` once in that folder and accepts the prompt.
- App: background sessions | Claude Code: unknown
- Seen: date not stated | error text | project-lead skill
- Re-check: `claude --bg` in a fresh folder | owner-only
- Status: checked

### `claude --bg --resume <id>` with any other flag starts a copy
- What happens: `claude --bg --resume <sessionId>` with no other flag wakes the session under the same id with its saved options (name, Remote Control, model, permission mode). Any other flag makes claude start a copy instead.
- Workaround: set model, effort and mode in the job's saved options (`~/.claude/jobs/<short id>/state.json`, "respawnFlags") before the resume; add no flag.
- App: background sessions | Claude Code: unknown
- Seen: date not stated | check not stated | Pult hub rules, `plugins/pult/scripts/resume-lib.ps1`
- Re-check: throwaway session, `claude stop`, then `claude --bg --resume <id> -- 'x'` | owner-only
- Status: doubtful

### A just-stopped session keeps its processes for about 1 s
- What happens: A stopped session keeps its processes about 1 s after `claude agents` drops its pid. A `claude --bg --resume` in that gap says "already running" and starts a copy without the saved flags (default model and mode): 2 copies in 3 resumes right after the pid left the list.
- Workaround: wait until the session's processes are gone (up to 60 s); if a copy appears ("started a copy as <id>"), `claude stop` and `claude rm` it (`rm` works only after it exited) and retry once.
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-19 | live test | ClaudeDevKit, Pult resume
- Re-check: throwaway session, `claude stop`, resume at once | owner-only
- Status: checked

### Claude closes an idle background session after 8 h of waiting, 1 h without Remote Control
- What happens: Claude's background service closes (retires) an unpinned background session that waits for input for 8 h, and for 1 h without Remote Control. The close shows in `~/.claude/daemon.log` as `[bg] bg retire <id>` (with `idle-prompt`) and `bg spawned <id>`. A plain `claude stop` writes no retire line. Whether a C started without `--remote-control` is closed after 1 h is not settled: one place names only 8 h.
- Workaround: pin a lead; a closed session is brought back with `claude respawn <id>`.
- App: background sessions | Claude Code: unknown
- Seen: date not stated | read of daemon.log, rule not tested | Pult scripts, Pult hub rules
- Re-check: `tail -n 200 ~/.claude/daemon.log | grep 'bg retire'` | safe
- Status: doubtful

### A low-memory spell closes idle background sessions
- What happens: On low memory Claude Code closes idle background sessions early. On 2026-11-16 a C that waited on the owner vanished; a stopped background watcher of a lead was seen in the same spell. A long low-memory spell can close pinned sessions too.
- Workaround: bring the session back with `claude respawn <id>`; the Pult watcher heals leads.
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-16 | seen live | ClaudeDevKit, Pult
- Re-check: `tail -n 200 ~/.claude/daemon.log | grep 'bg retire'` | safe
- Status: checked

### Pinned sessions are not closed when idle
- What happens: Pins live in `~/.claude/jobs/pins.json`, a JSON array of short ids (the list `Ctrl+T` toggles in `claude agents`). A pinned session is not retired after 8 h or 1 h of waiting.
- Workaround: Pult pins the leads it starts.
- App: background sessions | Claude Code: unknown
- Seen: date not stated | check not stated | Pult scripts
- Re-check: read `~/.claude/jobs/pins.json` | safe
- Status: doubtful

### In `claude agents --json`, `blocked` with status `idle` only means the turn ended
- What happens: In `claude agents --json` the state `blocked` with status `idle` only means the turn ended. It is not a block or a denial.
- Workaround: show it as idle.
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-14 | check of the output ("Traps (checked 2026-11-14)") | Pult hub rules
- Re-check: `claude agents --json` | safe
- Status: checked

### Other sessions listed as `blocked` or `done` in `claude agents --json`
- What happens: An entry with no `pid` is not live. An idle session whose process died stays `done`. A session closed on low memory shows `blocked` with no pid. A session that hit the usage limit keeps its process and is listed `blocked`, so the list cannot tell it from an idle one. The word `blocked` has three meanings: turn ended (see the entry above), closed on low memory, usage limit.
- Workaround: detect the usage limit in the transcript: its last entry is a synthetic assistant message with `apiError` usage_limit_reached (older: `error` rate_limit).
- App: background sessions | Claude Code: unknown
- Seen: date not stated | check not stated | Pult scripts, `sessions.py`
- Re-check: `claude agents --json` next to the transcript tail of a session that hit the limit | safe
- Status: doubtful

### The usage-limit notice gives its reset time in `rate_limit_info`
- What happens: The usage-limit notice in a transcript is a synthetic assistant entry with `apiError` `usage_limit_reached`. Its `apiErrorParams.rate_limit_info` holds `resetsAt` (epoch seconds), `rateLimitType` (e.g. `five_hour`) and `status` `rejected`. Its text reads "You've hit your 5-hour limit · resets 7:10pm (Europe/Copenhagen)".
- Workaround: read `resetsAt` for the reset time, not the clock text.
- App: background sessions, `claude` CLI | Claude Code: 2.1.325
- Seen: 2026-11-15 | read of the transcript (fields checked 2026-11-23, `resetsAt` = 18:10 UTC) | ClaudeDevKit, session 90f30cba
- Re-check: `grep -o 'rate_limit_info.\{0,160\}' <transcript>.jsonl` on the next transcript with `usage_limit_reached` | safe
- Status: checked

### A session stopped by the usage limit does not go on after the reset
- What happens: A session stopped by the usage limit writes nothing after its reset time until an incoming message arrives. In transcript 90f30cba the notice came at 17:12 UTC, the reset was at 18:10 UTC, and the next entry was the owner's message at 20:49 UTC.
- Workaround: the Pult watcher sends the session a «go on» message after the reset (`plugins/pult/scripts/watch-servers.ps1`, LIMIT-RESUME; ClaudeDevKit `plans/limit-resume.md`).
- App: background sessions, `claude` CLI | Claude Code: 2.1.325
- Seen: 2026-11-15 | read of the transcript (entries after the notice checked 2026-11-23) | ClaudeDevKit, session 90f30cba
- Re-check: in a transcript with a limit notice, list the entries after its `resetsAt` time: `grep -n '"timestamp"' <transcript>.jsonl` and read the lines after the notice | safe
- Status: checked

### A session with a background shell shows as busy
- What happens: A session that has a background shell running shows as busy; one with none shows as idle.
- Workaround: none.
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-20 | measured from transcripts | ClaudeDevKit, `docs/findings/idle-wake-cost.md`
- Re-check: `claude agents --json` while a throwaway session runs a background shell (starts a session) | owner-only
- Status: checked

### The host kills a background Bash run after 2 hours
- What happens: The host kills a background Bash run after 2 hours (a 125-minute run was killed at 120). The Monitor tool caps at 30 minutes. So a watcher inside a session cannot stay armed without re-arming, and each re-arm was a paid cold turn.
- Workaround: the watcher runs outside the session (the Pult watcher).
- App: background sessions, Bash tool | Claude Code: unknown
- Seen: 2026-11-15 | measured from transcripts and `servers.log` | ClaudeDevKit, `docs/findings/idle-wake-cost.md`
- Re-check: read `docs/findings/idle-wake-cost.md` data | safe
- Status: checked

### A CronCreate job can outlive a lead restart
- What happens: A job made with `CronCreate` can still exist after a lead is restarted; creating it again blindly made one reminder fire 4 times.
- Workaround: check `CronList` first and create the job only if it is gone.
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-20 | seen (a reminder fired 4 times) | ClaudeDevKit
- Re-check: create a throwaway job, restart a throwaway session, run `CronList` | owner-only
- Status: doubtful

### A fresh background C in an existing worktree loads a handoff from its first prompt
- What happens: A fresh background C started in an existing worktree loads a handoff file named in its first prompt and can write there.
- Workaround: none needed.
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-14 | live test | ClaudeDevKit
- Re-check: start a throwaway session in a throwaway worktree with a handoff | owner-only
- Status: checked

### `claude rm <id>` does not remove a worktree made by hand
- What happens: `claude rm <id>` removes the session's job state but not a worktree that was made by hand.
- Workaround: remove the worktree with git.
- App: background sessions | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill
- Re-check: `claude rm` a throwaway session that has a hand-made worktree | owner-only
- Status: doubtful

### `claude respawn <id>` brings back a session Claude Code closed
- What happens: `claude respawn <id>` brings back a task session that Claude Code closed.
- Workaround: none needed.
- App: background sessions | Claude Code: unknown
- Seen: date not stated | check not stated (used in practice) | Pult scripts
- Re-check: respawn a throwaway session that was retired | owner-only
- Status: doubtful

### Resuming without `-n` renames the session after its first prompt
- What happens: A resume without `-n` renamed the session after its first prompt.
- Workaround: a resume keeps the name with `-n` (Pult's resume does).
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-23 | live test | ClaudeDevKit, `plans/restart-notice.md`
- Re-check: resume a throwaway session with and without `-n` | owner-only
- Status: checked

### The host's worktree guard blocks writes to the main checkout from another worktree
- What happens: Writes to the main checkout from outside the session's own worktree are blocked, also for a subagent (a coder sent to the main checkout was blocked four times in a minute). Shell edits were half-applied. It is not clear whether the guard is Claude Code's own or a project hook.
- Workaround: edit in a throwaway worktree (a stopgap: re-read after each edit).
- App: background sessions, Claude Code | Claude Code: unknown
- Seen: 2026-11-18 | seen in Zhratva; a coder case on 2026-11-21 | Zhratva, ClaudeDevKit
- Re-check: write to the main checkout from a worktree session | owner-only
- Status: doubtful

## Messages between sessions

### A send to a stopped session fails at the sender and is not queued
- What happens: A `SendMessage` to a stopped (or restarting) session fails at the sender and is not queued. Error text: "No agent named ... is reachable", or over Remote Control "HTTP 409 ... Session ... is not active". After a resume a send to the same name is delivered and answered. A restarting lead is unreachable about 10 s in practice.
- Workaround: send the same message again after the target is back (see `plugins/dev-kit/skills/manager/SKILL.md`, "A task from the project lead", for the retry steps).
- App: `SendMessage` tool, background sessions, Remote Control | Claude Code: unknown
- Seen: 2026-11-23 | live test with a throwaway background session | ClaudeDevKit, `plans/restart-notice.md`
- Re-check: throwaway background session, `claude stop <id>`, send to it with a one-shot `claude -p --no-session-persistence --model haiku --safe-mode --tools SendMessage`, read the error; resume and send again | owner-only
- Status: checked
- History: 2026-11-16, live test with a throwaway session: only "No agent named ... is reachable" was seen. On 2026-11-23 the second text appeared over Remote Control.

### A message between sessions in different permission modes may be held
- What happens: Earlier sightings: a session held a message from a session in another permission mode for the owner's approval (the message may expire). The measurement of 2026-11-21 shows delivery across modes works from manual and acceptEdits to auto, and between two bypassPermissions sessions; "a held message was the earlier trouble of mixed modes". It may depend on the sender (a session's own `SendMessage` against the `-p` sender).
- Workaround: sessions in one permission mode (see `plugins/dev-kit/skills/project-lead/SKILL.md`, "Start a C").
- App: `SendMessage` tool | Claude Code: unknown
- Seen: 2026-11-21 | measured with the `-p` sender | ClaudeDevKit, `docs/findings/idle-wake-cost.md`
- Re-check: send between two throwaway sessions in different modes, with a session's own `SendMessage` | owner-only
- Status: doubtful
- History: 2026-11-19 (Zhratva) and 2026-11-20 (two projects): held for approval, seen live.

### The owner's message in a lead's chat during a restart is not lost
- What happens: A message the owner types into a lead's chat during a restart is not lost; it is answered after the restart.
- Workaround: none needed.
- App: desktop app, phone app | Claude Code: unknown
- Seen: 2026-11-23 | owner checked himself, not re-seen | ClaudeDevKit, `plans/restart-notice.md`
- Re-check: type a message in a lead's chat during its restart | owner-only
- Status: doubtful

### `notify_when_idle` wakes the lead on every idle notice
- What happens: With `notify_when_idle` for a C, every idle notice woke the lead, and the host forced a visible reply each time.
- Workaround: leave `notify_when_idle` off; the lead is woken by a report, an owner message or an event message instead (see `plugins/dev-kit/skills/project-lead/SKILL.md`, "Wake-up").
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-15 | seen in Zhratva | Zhratva
- Re-check: none cheap | owner-only
- Status: doubtful

### A C's text in its own chat never reaches the lead
- What happens: A session's text in its own chat never reaches another session. Seen live: without a `SendMessage` to the lead's session name, both C wrote only in their own chat and the lead waited forever.
- Workaround: a report goes through the `SendMessage` tool to the lead's session name.
- App: `SendMessage` tool | Claude Code: unknown
- Seen: date not stated | seen live | project-lead skill
- Re-check: none cheap | owner-only
- Status: checked

### Two sessions can share one name during a refresh
- What happens: Two sessions can share one name for a while (during a refresh).
- Workaround: message the new one by its `[ref]` from `ListAgents`.
- App: `SendMessage` tool | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill
- Re-check: none cheap | owner-only
- Status: doubtful

### The host forces a visible reply on some wake-ups, and an empty turn is not accepted
- What happens: The host demands a visible reply on some wake-ups. A turn forced to answer with nothing got filler text from the lead ("No response requested."). Claude Code does not accept an empty turn. A turn with tool calls can end with no text.
- Workaround: a reply with the short current state is accepted (see `plugins/dev-kit/skills/project-lead/SKILL.md`, "Message templates").
- App: background sessions | Claude Code: unknown
- Seen: 2026-11-19 | seen in Zhratva; owner's screenshot of repeated messages 2026-11-22 | Zhratva
- Re-check: none cheap | owner-only
- Status: doubtful

## Headless claude -p

### A one-shot `claude -p` delivers a message into a running session
- What happens: `claude -p --no-session-persistence --model haiku --safe-mode ... --tools SendMessage` delivers a message into a running session in 1-3 s, costs about 0.0008 USD (about 0.016 USD with plugins loaded), needs no approval, delivers to a busy target, and answers `failed: ...` with exit 0 when the target is missing.
- Workaround: none needed; `Send-Wake` of the Pult watcher uses it (prompt on stdin, `--output-format json`, the `result` says sent or failed).
- App: headless `claude -p` | Claude Code: unknown
- Seen: 2026-11-20 | measured in the watcher design test | ClaudeDevKit, `docs/findings/idle-wake-cost.md`
- Re-check: send a `-p` message to a throwaway session | owner-only
- Status: checked

### A headless `claude -p` bills `ANTHROPIC_API_KEY` if it is set
- What happens: A headless `claude -p` bills the key in `ANTHROPIC_API_KEY` if it is set, with no log line. Without it, `claude -p` runs on the subscription.
- Workaround: leave `ANTHROPIC_API_KEY` unset in the environment of the `claude` process; a key for our own API calls goes under another name (`DEV_KIT_API_KEY`, read by `dev-kit-api`).
- App: headless `claude -p` | Claude Code: unknown
- Seen: 2026-11-21 | owner's statement, not re-seen | ClaudeDevKit, API spend log
- Re-check: none cheap (a paid call) | owner-only
- Status: doubtful

### `claude -p` and background sessions have no in-app browser; the web-kit headless server's tools load with `--plugin-dir`
- What happens: `claude -p` (like `claude --bg`) has no in-app browser tools. The web-kit headless MCP server's tools appear as `mcp__plugin_web-kit_headless__browser_*` with `--plugin-dir`; navigate, click, snapshot and screenshot work, and a phone-window shot is full size (375x812). The server also starts in desktop sessions with web-kit enabled, and its tools load deferred (a small cost).
- Workaround: none needed.
- App: headless `claude -p`, MCP | Claude Code: unknown
- Seen: 2026-11-23 | live test in `claude -p --plugin-dir` | ClaudeDevKit, `plans/bg-browser-checks.md`
- Re-check: `claude -p --plugin-dir <web-kit>` and list the tools (starts a session) | owner-only
- Status: checked

### Headless MCP browser: dialogs stay open and a screenshot file lands in the session's folder
- What happens: Native dialogs are not dismissed by themselves. A screenshot `filename` is written into the session's working folder, and screenshots are full size at any width (`@playwright/mcp@0.0.84`).
- Workaround: `browser_handle_dialog` closes a dialog; a screenshot called with no `filename` writes no file into the folder (its result's link gives the PNG path under `%TEMP%/web-kit-headless`); the agent briefs: see `plugins/web-kit/browser-checks.md`, "Two browsers".
- App: headless `claude -p`, MCP | Claude Code: unknown
- Seen: 2026-11-23 | live test in `claude -p --plugin-dir` | ClaudeDevKit, `plugins/web-kit/browser-checks.md`
- Re-check: `claude -p --plugin-dir <web-kit>`, open a page with `alert()` (starts a session) | owner-only
- Status: checked

### A narrow headless browser window has no phone emulation
- What happens: A narrow window of the headless MCP browser has no touch and no phone user-agent emulation. This is asserted in the web-kit notes, not shown as tested.
- Workaround: none.
- App: headless `claude -p`, MCP | Claude Code: unknown
- Seen: 2026-11-23 | not shown as tested | ClaudeDevKit, `plugins/web-kit/browser-checks.md`
- Re-check: read `navigator.userAgent` and touch support in a 375 px window of the headless browser (needs a session with the browser tools) | owner-only
- Status: doubtful

## Plugins, hooks and MCP

### Plugins load in place from the repo folder; the shown version only records the install
- What happens: Plugins load in place from the repo folder (`claude plugin list --json` shows `readFromFolder` and `folderVersion`). The `version` the list and `installed_plugins.json` show only records the install and may lag.
- Workaround: none.
- App: plugins | Claude Code: unknown
- Seen: date not stated | check not stated | ClaudeDevKit README
- Re-check: `claude plugin list --json` | safe
- Status: doubtful

### A running session sees a new agent or skill only after `/reload-plugins`
- What happens: A session that was already running sees a new or edited agent or skill only after `/reload-plugins`, and the desktop app too. A session gets agent types only at its start, so one older than a plugin update may lack a newer type. A new session needs no `claude plugin update`.
- Workaround: run `/reload-plugins`, or start a new session.
- App: plugins, desktop app | Claude Code: unknown
- Seen: 2026-11-15 | seen (an older session lacked a newer agent type) | Zhratva
- Re-check: add a throwaway agent file, check a running session's agent list before and after `/reload-plugins` | owner-only
- Status: doubtful

### Plugin install rewrites `.claude/settings.json`
- What happens: A plugin install rewrites `.claude/settings.json`; existing hook fields (for example `onFailure`) may not survive.
- Workaround: re-check the hooks after an install.
- App: plugins | Claude Code: unknown
- Seen: date not stated | check not stated | ClaudeDevKit README
- Re-check: install a plugin in a throwaway project with a hook field, diff the file | safe
- Status: doubtful

### Claude Code replaces `$1` and `$ARGUMENTS` in a skill or agent body
- What happens: Claude Code replaces `$1`, `$ARGUMENTS` and the like in a skill or agent body with the call's arguments ("past $1" read "past plugin").
- Workaround: write money as `1 USD`.
- App: skills, agents | Claude Code: unknown
- Seen: date not stated | seen | ClaudeDevKit, `tools/lint.py`
- Re-check: call a throwaway skill that contains "$1" and read what the session sees | owner-only
- Status: checked

### The Skill tool answers "already loaded" for a skill already read
- What happens: The Skill tool only answers "already loaded" for a skill that was already read; it does not show the new text.
- Workaround: `Read` the `SKILL.md` to see new text.
- App: Skill tool | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill
- Re-check: edit a loaded skill, call the Skill tool again (the keeper has no Skill tool) | owner-only
- Status: doubtful

### A `UserPromptSubmit` hook note reaches a session only at the owner's next message
- What happens: The note of a `UserPromptSubmit` hook reaches a session only at the owner's next message to it, so a session that was already idle may never get it.
- Workaround: none; named a known limit.
- App: hooks | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill
- Re-check: none cheap | owner-only
- Status: doubtful

### A `SessionStart` hook of a user-scope plugin runs in every session on the machine
- What happens: A plugin enabled at user scope runs its `SessionStart` hook in every session on the machine. A long-lived resumed session gets the hook's output only at its start (the hub server resumes the same conversation for days).
- Workaround: the hub rules hook decides by the session's folder.
- App: hooks | Claude Code: unknown
- Seen: 2026-11-16 | owner's report, not re-seen | ClaudeDevKit, Pult
- Re-check: start a throwaway session in another folder and read what the hook printed | owner-only
- Status: doubtful

### The status line JSON holds the subscription limits
- What happens: For subscribers the status line JSON holds `rate_limits.seven_day.used_percentage` and `resets_at` (and `five_hour`). Claude Code runs the status line script on each turn. Without `rate_limits` (API login, old version) nothing is given.
- Workaround: none.
- App: status line | Claude Code: 2.1.330
- Seen: date not stated | read in the Claude Code 2.1.330 bundle | ClaudeDevKit, `plugins/dev-kit/scripts/statusline.py`
- Re-check: pipe a sample JSON to `dev-kit-statusline`, or read `~/.claude/dev-kit/usage-log.jsonl` | safe
- Status: checked

## Subagents and models

### Built-in agent types load every session tool
- What happens: The built-in types (`general-purpose`, `Explore`, no type) load every session tool: about 67K tokens of cold start against 15-25K for dev-kit's narrow agent types.
- Workaround: use dev-kit's narrow agent types.
- App: subagents | Claude Code: unknown
- Seen: date not stated | figures, check not stated | project-lead skill, manager skill
- Re-check: start each type and read the first `usage` line of its transcript (starts subagents) | owner-only
- Status: doubtful

### A subagent cannot start other subagents
- What happens: A subagent cannot start other subagents.
- Workaround: the caller launches every agent of a chain.
- App: subagents | Claude Code: unknown
- Seen: date not stated | check not stated | manager skill
- Re-check: ask a throwaway subagent to launch one (starts a subagent) | owner-only
- Status: doubtful

### A subagent's prompt cache lives 5 minutes; `cacheTtl: 1h` gives 1 hour
- What happens: A subagent's prompt cache lives 5 minutes by default; `experimental: cacheTtl: 1h` in the agent file gives 1 hour. A subagent's transcript is `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`.
- Workaround: none.
- App: subagents | Claude Code: unknown
- Seen: 2026-11-11 | checked on this machine and subscription (the owner's note); the measurement itself is in no findings file or commit of this repo | the earliest trace is the Prishch repo, commit 27a0ce6 of 2026-11-11 (`.claude/agents/core-engineer.md` gets `experimental: cacheTtl: 1h`)
- Re-check: `grep -h cache_creation ~/.claude/projects/*/*/subagents/agent-*.jsonl | tail -n 5` and read `ephemeral_5m_input_tokens` against `ephemeral_1h_input_tokens` (1h writes show that `cacheTtl: 1h` took effect) | safe
- Status: doubtful

### A main session's prompt cache lives about one hour
- What happens: A main session's prompt cache lives about one hour (leads write a 1-hour cache; 5-minute writes also occur). A warm cache read costs about 1/20 of a cold rewrite. The next turn of a long-waiting session re-reads its whole context at full price: 21 of 22 Pult wakes found the cache cold, each rewrote about 110k and read about 230k tokens.
- Workaround: none; Pult's keep-warm ping is a design on top of it.
- App: Claude Code sessions | Claude Code: unknown
- Seen: 2026-11-20 | measured from transcripts | ClaudeDevKit, `docs/findings/idle-wake-cost.md`
- Re-check: read `usage` lines of a long-waiting session's transcript | safe
- Status: checked

### Context window by model
- What happens: Fable models, Sonnet 5+, Haiku 5.5 and Opus 4.7+ run with a 1M context by default (no `[1m]` suffix). `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` makes them 200K. Older models have 200K unless the id carries `[1m]`.
- Workaround: none.
- App: models | Claude Code: unknown
- Seen: date not stated | seen live (a fresh Sonnet 5.5 C at 80k showed 40% against an assumed 200K); Claude Code docs, "model-config" | ClaudeDevKit, `plugins/dev-kit/scripts/sessions.py`
- Re-check: read the context share of a fresh session (needs a new session) | owner-only
- Status: doubtful

### Claude Code's own USD figure prices tokens at API rates
- What happens: The USD figure of `/cost` and `costUSD` in session records prices tokens at API rates, so it is not what the subscription costs.
- Workaround: count tokens with weights per kind and model into a share of the weekly limit (`docs/findings/token-weights-and-weekly-limit.md`).
- App: Claude Code | Claude Code: unknown
- Seen: 2026-11-21 | owner's statement, not re-seen | ClaudeDevKit, cost feature
- Re-check: none cheap | owner-only
- Status: doubtful

### A resumed session's file copies old lines with their old timestamps
- What happens: The transcript file of a resumed session copies the old lines with their old timestamps, so the same call shows up twice when files are summed.
- Workaround: count a line once (`retro.py` and the usage scripts de-duplicate).
- App: Claude Code sessions | Claude Code: unknown
- Seen: 2026-11-16 | measured from transcripts | ClaudeDevKit, `docs/findings/token-weights-and-weekly-limit.md`
- Re-check: compare line ids of a resumed session's file with its parent | safe
- Status: checked

### One message id repeats on several transcript lines
- What happens: One message id repeats on several lines of a transcript, so summing every line over-counts tokens.
- Workaround: count a message id once.
- App: Claude Code sessions | Claude Code: unknown
- Seen: 2026-11-16 | measured from transcripts | ClaudeDevKit, `docs/findings/token-weights-and-weekly-limit.md`
- Re-check: count equal message ids in one transcript | safe
- Status: checked

## Windows shell

### Windows PowerShell 5.1 cuts a prompt at the first double quote
- What happens: Windows PowerShell 5.1 does not escape a double quote inside an argument to a native command, so a prompt passed to `claude` is cut at the first `"` (C got only the first word).
- Workaround: no `"` in the prompt (use «» and single quotes), a single-quoted here-string, or `start-session.ps1`, which escapes.
- App: Windows PowerShell 5.1 | Claude Code: unknown
- Seen: 2026-11-15 | live | Zhratva
- Re-check: `claude -p 'say "hi there" please'` in Windows PowerShell 5.1 | owner-only
- Status: checked

### Git Bash rewrites a prompt that starts with `/` and `C:/` paths
- What happens: Git Bash rewrites a prompt that starts with `/` and any `C:/...` path in it.
- Workaround: run `claude ...` from PowerShell, or set `MSYS_NO_PATHCONV=1` in Git Bash (it kept `/clear` a prompt on 2026-11-23, `plans/push-noise.md`).
- App: Bash tool (Git Bash) | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill
- Re-check: run `claude -p '/help'` in the Bash tool, with and without `MSYS_NO_PATHCONV=1` | owner-only
- Status: doubtful

### Plugin `bin` commands run only in the Bash tool
- What happens: A plugin's `bin` folder is on the PATH of the Bash tool only. PowerShell cannot run these extensionless files, and in the home folder they are not on the PATH.
- Workaround: run the `bin` commands (`dev-kit-sessions`, `dev-kit-app`) in the Bash tool.
- App: Bash tool, plugins | Claude Code: unknown
- Seen: date not stated | check not stated | project-lead skill
- Re-check: `which dev-kit-sessions` in the Bash tool, and the same lookup in PowerShell | owner-only
- Status: doubtful

### Git Bash may run with path conversion off in background sessions
- What happens: Git Bash may run with path conversion off in background sessions, so a `/c/...` path reaches Windows python or node unchanged.
- Workaround: `cygpath` gives them a path they can open.
- App: Bash tool, background sessions | Claude Code: unknown
- Seen: date not stated | "as seen in background sessions" | plugin `bin` scripts
- Re-check: `echo $MSYS_NO_PATHCONV` in a throwaway background session | owner-only
- Status: doubtful

### The PowerShell tool keeps its folder between calls
- What happens: The PowerShell tool keeps its folder between calls. A shell left inside a worktree locks the folder, so `git worktree remove` later fails with "Permission denied".
- Workaround: `Pop-Location` or `Set-Location <main>` before removing the worktree.
- App: PowerShell tool | Claude Code: unknown
- Seen: 2026-11-15 | live | Zhratva
- Re-check: in the PowerShell tool `cd` into a throwaway worktree, then in a later call `git worktree remove` it | owner-only
- Status: checked

### Removing a folder with a junction may delete the target's data
- What happens: Removing a folder that holds a junction with `Remove-Item`, `rm -r` or `--force` may delete the data of the main checkout it points to. Not tested.
- Workaround: `cmd /c rmdir "<path>"` with no `/s`.
- App: Windows | Claude Code: unknown
- Seen: date not stated | not tested | project-lead skill
- Re-check: make a junction to a throwaway folder in a throwaway directory and remove it each way (`Remove-Item` is PowerShell) | owner-only
- Status: doubtful

### Python on Windows crashes printing Cyrillic, and `-I` ignores the UTF-8 variables
- What happens: The Python console on Windows is cp1252, so printing Cyrillic crashes with `UnicodeEncodeError`. `-I` ignores `PYTHONIOENCODING` and `PYTHONUTF8`. About 130 encoding failures were in the hook data.
- Workaround: run `python -I -X utf8`.
- App: Python under the Bash tool | Claude Code: unknown
- Seen: 2026-11-19 | retro; hook data of 2026-11-20 and 2026-11-21 | ClaudeDevKit
- Re-check: plain `python -c "print(chr(1111))"` (Cyrillic ї written in ASCII) should end in `UnicodeEncodeError`, and the same with `python -I -X utf8` prints it; the dev-kit windows-traps hook refuses the plain form in the Bash tool, so the owner runs it | owner-only
- Status: checked

### Git Bash's `/tmp` and Python's `/tmp` are different folders
- What happens: Git Bash's `/tmp` and Python's `/tmp` are different folders (Python reads `/tmp` as `C:\tmp`).
- Workaround: keep scratch files in `$CLAUDE_JOB_DIR/tmp`, written as a `C:/` path.
- App: Bash tool, Python | Claude Code: unknown
- Seen: 2026-11-19 | retro | ClaudeDevKit
- Re-check: write `/tmp/x` in Git Bash and read it with Python | safe
- Status: checked

### A large heredoc in the shell fails with "unexpected EOF while looking for matching quote"
- What happens: A heredoc over about 7000 characters fails in the shell wrapper with "unexpected EOF while looking for matching quote". Hundreds of small heredocs worked.
- Workaround: write the file with the Write tool, then run it.
- App: Bash tool | Claude Code: unknown
- Seen: 2026-11-19 | error text in retro data; again 2026-11-20 and 2026-11-21 | ClaudeDevKit
- Re-check: a heredoc of 8000 characters in the Bash tool (the dev-kit windows-traps hook refuses it, so the owner runs it) | owner-only
- Status: checked

### `| Select-Object -First 1` on a native command leaves a wrong exit code
- What happens: `... | Select-Object -First 1` on a native command cuts the pipe and leaves exit code -1 or 255 although the command succeeded.
- Workaround: capture all output first, then pick the line.
- App: PowerShell | Claude Code: unknown
- Seen: date not stated | check not stated | Pult scripts
- Re-check: in PowerShell, `python -c "print(1);print(2)" | Select-Object -First 1; $LASTEXITCODE` | owner-only
- Status: doubtful

### Windows PowerShell decodes a native program's output with the console code page
- What happens: Windows PowerShell decodes the output of a native program with the console code page, so Cyrillic session names became mojibake.
- Workaround: set `[Console]::OutputEncoding` to UTF-8 around the python calls.
- App: Windows PowerShell 5.1 | Claude Code: unknown
- Seen: date not stated | seen | Pult scripts
- Re-check: print Cyrillic from python through Windows PowerShell with and without the setting | owner-only
- Status: doubtful

### Windows PowerShell 5.1 misreads Cyrillic in a script saved without a BOM
- What happens: Windows PowerShell 5.1 misreads Cyrillic in a `.ps1` or `.psd1` file saved without a BOM.
- Workaround: save these files as UTF-8 with BOM.
- App: Windows PowerShell 5.1 | Claude Code: unknown
- Seen: date not stated | check not stated | Pult scripts
- Re-check: run a `.ps1` with a Cyrillic string, saved without a BOM, in Windows PowerShell 5.1 | owner-only
- Status: doubtful

### Windows scheduled tasks start hidden windows that die when the task ends
- What happens: A Windows scheduled task starts hidden windows that die after the task ends.
- Workaround: a Startup-folder shortcut is used instead.
- App: Windows | Claude Code: unknown
- Seen: date not stated | check not stated | Pult scripts
- Re-check: none cheap | owner-only
- Status: doubtful

### Claude Code blocks a lone long `sleep`
- What happens: Claude Code itself already refuses a lone long `sleep` or `Start-Sleep`; the same commands with `run_in_background: true` run.
- Workaround: run long waits in the background.
- App: Bash and PowerShell tools | Claude Code: unknown
- Seen: 2026-11-23 | live test (both refused, the same commands in the background ran) | ClaudeDevKit, `plans/long-commands.md`
- Re-check: `sleep 90` in the Bash tool, then with `run_in_background` | safe
- Status: checked
