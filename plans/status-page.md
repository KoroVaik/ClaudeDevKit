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
