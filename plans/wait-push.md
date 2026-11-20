# Phone push when a session waits on the owner too long

Owner's words (2026-11-20, P: ClaudeDevKit): «Чи можем кидать пуш нотифікацію якщо якійсь сесії треба моя
відповідь і пройшло уже більше ніж 20хв? Щоб уникнуть ситуації, що кеш запишеться заново і відповідно
згорять токени. Здаєтся там дається година... запусти обговорення».

## Facts
- The prompt cache of these sessions lives about one hour (the host states a 1-hour TTL for session
  requests); after it runs out, the next turn of a waiting session re-reads its whole context at the
  full price.
- Today P pushes only critical items, once, when the queue had no question and gets one
  (`plugins/dev-kit/skills/project-lead/SKILL.md`, "Owner queue and critical items", "Phone push").
  Nothing reminds the owner later. P wakes only on a C report, an owner message or a watcher exit;
  the watcher (`dev-kit-sessions watch`) checks the registry every minute.
- A discussion session («Обговорення:») waits on the owner in its own chat; P sees it as
  `чекає на тебе` only through `dev-kit-sessions state`.
- Checked 2026-11-20: `state` says `waiting` for any live, not busy session and keeps no time
  (`plugins/dev-kit/scripts/sessions.py` 618-666); `watch` has no "waiting for N minutes" event
  (848-922). Transcript jsonl entries carry `timestamp`, so the wait start is the time of the last
  assistant entry. Who is awaited (owner or P) is known only from P's owner queue; a discussion
  session always waits on the owner. Sessions the owner started and P has not taken over are not in
  the registry, so no reminder can cover them.
- How it would work: `watch` gets a new event (`stale: <name> | <id> | waiting N min`) when a
  registered session in `waiting` has its last assistant entry older than the threshold; P wakes,
  checks the session waits on the owner (queue item or discussion), and pushes.

## To agree with the owner
Which waits trigger a reminder push (C waiting on P's question to the owner, a discussion waiting in
its own chat, both), after how long (20 minutes or another time before the cache runs out), how many
times, and what the push says.

## Owner's approval
Owner said «так» on 2026-11-20 to all three points below.

1. Which waits: both kinds remind. (a) A C session whose question to the owner stands in P's owner
   queue (PROGRESS.md "Open questions", the asker is that C) and the session is in `waiting`.
   (b) A discussion session («Обговорення: ...») in `waiting`: it always waits on the owner.
   Owner-taken sessions (`add --owner`) shown as `чекає на тебе` count as (a). A C waiting on P
   (no owner-queue item from it) never triggers a push. Sessions not in the registry are not covered.
2. Threshold: 20 minutes, counted from the `timestamp` of the session's last assistant entry in its
   transcript jsonl (the cache lives about one hour, so 40 minutes stay for the answer).
3. Count: one push per wait. A wait ends when the session gets a new message or turns busy, finished
   or gone; a new wait after that may push again. No repeat pushes for the same wait. Text, one line
   under 200 characters: `P: <project>: «<session name>» чекає 20 хв - кеш згорить за ~40 хв`. If
   several sessions pass the threshold in one wake-up, one push names the first and the count
   («... і ще 2»). The PushNotification tool skipping a push while the owner is at the screen is
   expected; that wait still counts as pushed.

Build notes (agent's method, within the approved points):
- `dev-kit-sessions watch` gets a new event `stale: <name> | <id> | waiting <N> min`, printed and
  exiting 0 when a registered session is `waiting` and its last assistant entry is older than
  `--stale-minutes` (default 20). The watcher remembers which (id, last-entry timestamp) pairs it
  already reported, in a small file beside its lock, so a restart does not re-fire the same wait.
- P on a `stale:` wake-up: checks the session against points 1a/1b; on a match, pushes per point 3
  and records the push (session id + wait timestamp) so the next wake-up does not push again; no
  match: no text, re-arm the watcher.
- `project-lead` SKILL.md "Phone push": add this time-based push as a second case beside the existing
  "queue gets its first question" push, with the owner's reason (cache burn after one hour).
- Cheapest test: a registry with one fake `waiting` session whose transcript's last assistant
  `timestamp` is 21 minutes old makes `watch --stale-minutes 20` print one `stale:` line and exit 0;
  19 minutes old prints nothing; the same wait after a watcher restart prints nothing.

## Success criterion
The owner approves a short plan; the «Owner's approval» section here holds every agreed point in the
detail a builder needs.

## Build (2026-11-20)
- `dev-kit-sessions watch` reports `stale: <name> | <id> | waiting <N> min` (`--stale-minutes`, default 20);
  `stale.json` beside the registry keeps each reported wait (kept through busy or no-pid flickers, pruned
  after 7 days), so one push per wait also across watcher restarts. P keeps no push record of its own.
- `project-lead` SKILL.md: "Reminder push" beside "Phone push", and the `stale:` exit in "Wake-up".
  Feature doc and tech doc updated; dev-kit 0.1.66. Tests: 2 new in `tools/tests/test_sessions.py`; all
  tests and the lint pass.
- Known limits (reviewer doubts, left as is): the push text says «20 хв ... ~40 хв» even when a session
  already waited longer (only after a P restart with an old wait); a wait whose question is not yet in the
  owner queue at the wake-up is not reminded (the watcher has already counted it).
- Paid spend: $0.
