# Status page of all projects (Pult)

## Owner's words (2026-11-16)

Owner's «+» to P's proposal: «Запустити нову сесію «C: Сторінка стану всіх проєктів»? (усі сесії по проєктах на
одній сторінці)».

Source idea, BACKLOG.md entry «Pult: own remote client for agents»:
- What: a custom remote interface for agents, maybe an own Claude client app without the extra features and
  with the missing ones (grouping by project, what waits on me, health). A self-updating status page instead
  of a chat list is the first step.
- Why: the phone app's session list does not group by project or show what waits on the owner.
- Cheapest test: one static page that reads `claude agents --json` and the projects' PROGRESS.md files and
  shows them grouped by project.

## Scope

Only the cheapest test: one static page (generated file), no server, no own client app. The project list
comes from plugins/pult/scripts/servers.psd1 (lead entries). Per project: its sessions with state (working /
waits on the owner / idle), and the items waiting on the owner from PROGRESS.md "Open questions".
Read-only: the script never messages, starts or stops sessions.

Open for P to decide with the C (ask P): how the owner opens it on the phone (a file is not reachable from
the phone; a Pult session could send it with SendUserFile, or another way the C finds cheaper).

## Success criterion

- A script in plugins/pult generates the page; run once on this machine, the page shows the current
  sessions grouped by project and matches `claude agents --json` (checked by the C).
- README of plugins/pult says how to make and open it; the BACKLOG entry is updated (first step built, the
  rest stays as an idea).

## Result (C, 2026-11-16)

- Built `plugins/pult/scripts/status-page.py`: reads lead entries of servers.psd1, `claude agents --json` and each
  project's PROGRESS.md "Open questions"; writes `~/.claude/pult/status.html` (`--out`, `--agents-json` for tests).
- Phone: P's yes (2026-11-16) - the Pult hub sends the file with SendUserFile on "статус" (one line in rules/hub.md).
- Session state is shown as вільна / зайнята / завершена, not "waits on the owner": hub.md "Traps" says state
  "blocked" with status "idle" only means the turn ended. What waits on the owner comes from PROGRESS.md only.
- Check: run on this machine against a saved `claude agents --json` (12 sessions): 12 rows on the page, none
  missing, grouped Zhratva / Prishch / ClaudeDevKit / other folders; ClaudeDevKit has no PROGRESS.md (shown so).
- Paid spend: $0.
