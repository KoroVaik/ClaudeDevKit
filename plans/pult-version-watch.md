# The Pult watcher notices a new dev-kit version by itself

## Owner's words (2026-11-16)

Owner: «керівники мають актуальний плагін?» P checked: no. Owner's «так» to «Запустити нову сесію «C: Сторож
«Pult» сам помічає нову версію»? (керівники оновлюватимуться без участі чату)».

## Facts (checked by P, 2026-11-16)

- All three leads (P: Zhratva, P: Prishch, P: ClaudeDevKit) started 20:42 on dev-kit 0.1.44 (servers.log
  «UP ... pid»); dev-kit 0.1.45 merged 20:44 and 0.1.46 at 21:58.
- P: ClaudeDevKit sent the Pult hub session (interactive, cwd = home folder, system name korov-c5) «Злито
  dev-kit 0.1.45 / 0.1.46; перезапусти керівників.» Delivery succeeded («in that session's inbox, not yet read
  by its Claude»), but no restart followed: the hub seems to act only when someone writes in it. So the
  trigger in project-lead ("Plugin backlog": P messages the hub after a version bump) does not work in practice.

## Goal

Make the lead restart after a dev-kit version bump independent of the hub's chat:
- The Pult watcher (plugins/pult/scripts/watch-servers.ps1, runs from logon outside Claude Code) compares the
  dev-kit version (plugins/dev-kit/.claude-plugin/plugin.json) with the version the leads were started on, and
  when it changed, runs the restart flow (plugins/pult/scripts/restart-leads.ps1 and the hub rules
  "Restart leads for a plugin update"). The «готовий» handshake needs a session that can SendMessage; find
  the cheapest reliable way (for example the watcher starts a short throwaway session that does the
  handshake, or a lead restart that is safe without it, e.g. only leads that are idle and have no running
  step). Decide, then build.
- Update project-lead "Plugin backlog" and the Pult rules so the message to the hub is no longer the only
  trigger (drop it if it becomes useless).

## Success criterion

- Live test on throwaway sessions (never stop the real leads or the hub without P's yes): a version bump in a
  test copy makes the watcher restart a throwaway lead-like session, which comes back on the new version.
- Lint and tests pass; versions bumped.
- The running Pult watcher needs a restart to load the new script: report it to P (the owner does it).

## Decision (C, 2026-11-16; the owner chose the variant in this C's chat)

Checked: the watcher runs from the main checkout (`plugins/pult/scripts`), so the dev-kit version is
`plugins/dev-kit/.claude-plugin/plugin.json` next to it; leads read that same folder. A lead is `idle` with
no turn and no background task, `busy` with its session watcher armed. A script cannot SendMessage, but a
lead wakes when its background `dev-kit-sessions watch` exits. Owner's choice: no extra paid turns by
default (a busy lead may run old hooks and agents up to 2 hours), a fast path only on his ask.

- Pult watcher: keeps the version each lead process started on (`lead-versions.json`, by pid and start
  time). A stale idle lead: restarted at once (RESTART-LEAD). A stale busy lead: restarted only after it
  marks itself ready (`dev-kit-sessions restart ready --version V`, younger than 10 min; an older one
  READY-EXPIRED, and for the current version asked once more). One try per lead per version. A lead
  already on V: a leftover restart.json is cleared (RESTART-CLEARED).
- Lead (project-lead skill): the skill update check, now also on the watcher's 2 h time limit, finds the
  new version, reaches a safe point, runs `ready`, re-arms its watcher, ends the turn silently.
- Fast path: the owner asks Pult «онови керівників»; Pult runs `restart-leads.ps1 -Ask` (up-to-date leads
  skipped, idle ones restarted, busy ones get a request); `watch` exits 7 once per request; the lead then
  does the same handshake.
- Pult hub: re-reads its rules when the pult version changes (the hook passes the version).

## Result

- Live test on a throwaway lead (haiku): idle restart on a bump, and the fast path (`-Ask` -> exit 7 ->
  `ready` -> restart) both came back on the new version. Not run live: a restart on `ready` while the lead
  stays busy (the test lead stopped reading messages after its restarts); the same `restart-leads.ps1
  -Ready` call as before.
- Paid spend: a few haiku turns, well under $1.
