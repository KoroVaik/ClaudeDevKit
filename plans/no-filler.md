# P shows the current state instead of a filler

Owner's words (2026-11-20, P: ClaudeDevKit), after a screenshot of «P: Zhratva» answering «No response
requested.» twice: «Зараз такий статус. Це погано». Then «1 так» to: «Записати в правила керівника для
всіх проєктів: замість заглушок він показує короткий поточний стан, а після перезапуску завжди повний
статус?».

## Cause (checked by an investigator, 2026-11-19)
- `plugins/dev-kit/skills/project-lead/SKILL.md` orders turns with no text: the restart handshake
  («ends the turn with no text»), the restart resume («no message about the restart itself», skip the
  start status), watcher exits 4/5/6 («end the turn empty again» even when the host demands output),
  and «a message with neither block is not sent».
- Claude Code does not accept an empty turn («[Your previous response had no visible output...]»), so
  P invents a filler: before, it re-sent an old question; in P: Zhratva on 2026-11-19 it wrote «No
  response requested.» (transcript C:/Users/korov/.claude/projects/C--Users-korov-MyRepositories-Zhratva/53f175f7-a3d0-4394-b41d-197327fe6a68.jsonl,
  lines 2633 and 2662). Pult sends `/dev-kit:project-lead restart: plugin update` correctly.
- Side gaps: a watcher exit -1 (a watcher P stopped itself, or killed by the restart) is not in the
  Wake-up exit list; a question shown in chat only (not in PROGRESS.md «Open questions») is lost on restart.

## What the owner approved
1. After a plugin-update restart P always sends the full start status (every session, the question
   counts), in the «Message templates» form, instead of nothing.
2. Whenever a rule says «no text» and the host still demands visible output, P sends the short current
   state in the same form (the question counts and the sessions), never a filler phrase and never a
   re-sent old question. With no session and no question, one line in that form that nothing runs and
   nothing waits.

## Success criterion
No rule in the project-lead skill leaves P with nothing to write; the restart and forced-output cases
name the exact form; the watcher exit -1 case is covered; dev-kit version bumped; lint and docs check clean.

## Done (C, 2026-11-20)
- `project-lead/SKILL.md`: a «Forced output» rule in "Message templates" (short current state, one line
  when nothing runs and nothing waits, no filler, no re-sent question); exits 4/5/6/-1 and the handshake
  point to it; watcher exit -1 added (re-arm, no text); the restart resume always ends with the full start status.
- dev-kit 0.1.63; lint 0 errors, docs check clean.
- Out of scope, left as is: `plugins/pult/rules/hub.md` (Pult hub role) also says «end the turn empty» on
  watcher exits; the same filler can appear there. A candidate BACKLOG entry if the owner wants it.
- Paid spend: $0.
