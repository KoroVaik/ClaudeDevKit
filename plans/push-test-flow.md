# A clear flow for testing phone pushes with the owner

Status: discussion done, owner «так» to the plan (2026-11-24); next: a C builds it.

## Owner's words

«потрібно чітко описати флоу тестування пуш сповіщень, бо ти спамиш якусь фігнб постійно. Запускай обговорення» (2026-11-23, P: ClaudeDevKit chat).

## Known context (to check)

- Today, 2026-11-23, P relayed step-by-step phone checks from C sessions («C: Переїзд керівника без пушів», «C: Перевірка, що Pult не будить керівників дарма»): several «+ або -» messages, a «1 чи 2?», repeated asks, test pushes the owner missed (one at 17:27 checked hours later), a test while the app was open, and a question about the Pult chat.
- Rules in force: the owner's global CLAUDE.md («A live test that needs the owner's hands ... goes one step at a time ... «+ або -»»), project-lead SKILL.md (P relays, C never asks the owner; push request form), `plans/wake-check.md`, `plans/push-noise.md` («Facts checked live»), `plugins/dev-kit/claude-facts.md` (push and Remote Control sections).
- Found today: Pult holds messages from leads (different permission mode), so pushes relayed via Pult do not arrive; whether a push shows while the app is open is unclear.

## Owner's approval

Owner «так» to the short plan, 2026-11-24, «Обговорення: Як тестувати пуші на телефоні». Build work for a
C; rule text goes through `dev-kit:edit-rules`; the owner's global `CLAUDE.md` edit is made by the C on
this approval (it is the owner's own file, local, not in the repo).

### What went wrong on 2026-11-23 (why)

- A readiness step («напиши +, коли зможеш закрити застосунок») ended with «+ або -», so «+» meant
  "ready" but read as a result; the owner answered «Ок» 1.5 h later.
- Steps came wrapped in status blocks, re-sent on a stale wake-up, and «прийшов? + або -» went twice
  in 4 seconds from two C relays.
- The owner was asked at 19:47 about a push sent at 17:27; then «1 чи 2?»; then the owner: «?».
- A test push was sent while the owner was writing in the app (20:32).
- Owner: «ти спамиш якусь фігню постійно».

### Agreed flow (points 1-4 of the plan)

1. One step per push test, in the owner's chat (P's chat for a C's test; a session the owner talks
   with in its own chat). Text pattern (Ukrainian): «Тест пушу: напиши + і одразу закрий застосунок.
   Через 5 секунд прийде пуш «Тест N · HH:MM».». The step does NOT end with «+ або -»: here «+» means
   "ready". On the owner's «+» the sender waits 5 seconds (background or a short `sleep 5`) and sends
   exactly one push. Then one line: «Пуш «Тест N» надіслано. Прийшов? + або -» - this is the only
   result question, asked once; never re-asked, never repeated by a second relay, never inside a
   status block.
2. Every test push text starts with the word «Тест» (with number and time, e.g. «Тест 3 · 21:40»), so
   the owner tells it from real pushes. Nothing else is blocked during a test: other messages and
   real pushes go as usual (owner: «не треба нічого блочить. Якщо я забуду про тест, то пуши просто
   зупиняться»). No "quiet window", no queue of tests.
3. No answer to the result question within 10 minutes: the test counts as not done. Nobody asks
   about that push later (no «глянь у сповіщення, пуш о 17:27»); when needed, the test is run again
   from step 1 with a new push.
4. Several pushes in one test go one after another with at least 3 seconds between them, never as
   parallel tool calls in one message: pushes sent at the same moment collapse on the phone into
   the last one.

### Where it goes (for the builders)

- `plugins/dev-kit/skills/project-lead/SKILL.md`: a short section «Push test with the owner» with
  points 1-4; P relays a C's push test in this form (the C sends P the test: what is checked and the
  push text; P runs the steps and returns the owner's «+»/«-» to the C as `ВІДПОВІДЬ`). A step of a
  push test is exempt from the status blocks around P's messages. The push itself is sent by the
  session that runs the step (P for a C's test; P can push, confirmed 2026-11-23 23:52), never via a
  message to the Pult hub (held, different permission mode).
- Owner's global `C:/Users/korov/.claude/CLAUDE.md`, the «A live test that needs the owner's hands»
  bullet (line ~197-202): a notification test's readiness step does not end with «+ або -»; only the
  result question does; point to the project-lead section for the rest. Keep it one or two lines.
- `plugins/dev-kit/skills/discovery-round/SKILL.md` line ~44 (bare «+»/«-» reading): consistent with
  the above (a «+» after the readiness step means ready, not a result).
- `plans/wake-check.md` and the feature «start-leads-at-logon-and-heal-them» open item on a push
  relayed by a lead: use this flow for its phone check.

### Facts checked live (point 5: to `plugins/dev-kit/claude-facts.md` via `dev-kit:facts-keeper`)

All on Claude Code 2.1.330, Windows, phone app fully closed after the owner's «+», 2026-11-23/24:
- «Mobile push requested.» means only that the request went to the server; it is returned the same
  way whether the push reaches the phone or not.
- Pushes sent at the same moment (parallel tool calls) collapse: of «4 с», «5 с», «6 с», «7 с» only
  «7 с» arrived (00:48); of «Тест 8» and «Тест 9» only «9» was seen.
- Pushes sent one after another about 3-5 seconds apart all arrive: «3 с», «6 с», «9 с», «12 с» all
  arrived (00:51-00:52), the first about 3 seconds after the owner's «+». So a short delay after the
  owner leaves the app is not by itself the cause.
- A push from a background `cli` session with Remote Control arrives (this discussion session, P).
- Still unexplained: single pushes «Тест 4» (23:47, 5 s after «+»), three pushes at 20:56 and the Pult
  hub's «Тест Pult» (21:08, 14 s after the owner's message in the Pult chat) did not arrive. Record as
  an open fact, not a rule.
- The last confirmed tool push before 2026-11-23 was 2026-11-20 22:27Z from the Pult hub (2.1.329);
  the theory "tool pushes broke in 2.1.330" is disproved by the arrivals above.

### Done when

The project-lead section, the global rule line and the facts entries exist; a reviewer reads the
three texts against points 1-4; dev-kit version bumped as usual.
