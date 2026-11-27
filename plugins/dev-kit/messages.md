# Messages between sessions

Every message one session sends another by SendMessage (a Lead, a Manager, a «Discuss:» session, a Lead of
another project) starts with one kind word from the table, in capitals, then ` - ` and the text. The
receiver reads the kind first and so knows what the message asks of it. Who may message whom is the
skills' rule (`dev-kit:project-lead`, `dev-kit:manager`); this file only sets the kinds.

| Kind | Sent by | When | Receiver does |
|---|---|---|---|
| `ГОТОВО` | a Manager; a «Retro:» session (`rules-kit:retro`, its only message); a «Docs:» session (`dev-kit:maintain-project-docs`) | its task is done and its branch is ready; 3 lines: state, result, what is needed (a «Retro:» one may add `task: <what to build>` lines) | merges ("Acceptance and merge"); starts a Manager per `task:` line, with no owner ask |
| `ЗАКРИТО` | a «Discuss:» session | the owner said «так» to its short plan (or to «Закриваємо обговорення?» when nothing is built) and wrote nothing after it; this is its done report | merges and closes it |
| `ПИТАННЯ` | a Manager to its own Lead; a Lead or a «Discuss:» session to a Lead | it needs a decision or a consent; it waits for the answer | answers with `ВІДПОВІДЬ`, or puts it in the owner queue |
| `ЗАСТРЯГ` | a Manager | it cannot go on, and no choice by the Lead would unblock it (a crash of a tool, a queue timeout) | shows it as `чекає на тебе` or `стоїть, сесія впала` with its own question |
| `ЧЕКАЮ` | a Manager | it will wait more than 1 minute on something other than the Lead or the owner (low memory, a retry timer, a store cool-off, another session, the app queue), idle itself (not its own build, test run or subagent); the reason in plain words and the time it resumes, if known | shows it at once as `чекає` with that reason (`dev-kit:project-lead`, «Статуси сесій») |
| `ПРОДОВЖУЮ` | a Manager | it goes on after a `ЧЕКАЮ` | shows it as `працює` again |
| `ВЛАСНИК ВІДПОВІВ` | a session the owner talks with; a Manager the owner wrote to in its chat (`dev-kit:manager`, "A task from the project lead") | the owner answered or decided there something its lead may ask or show (a question the lead put to the owner, a change of scope; the closing «так» is `ЗАКРИТО` instead); the owner's words verbatim | drops the matching queue item, never asks the owner again |
| `ДОРУЧЕННЯ` | the Pult hub to a Lead (`plugins/pult/rules/hub.md`, "Passing work to a lead"); the weekly retro session «Retro: тиждень» (`rules-kit:weekly-retro`) | the owner asked Pult in its chat for work in the Lead's project; his words verbatim in «» | takes it as a new owner request (`dev-kit:project-lead`, "A request passed by Pult") |
| `ВІДПОВІДЬ` | the session that was asked | the answer to a `ПИТАННЯ` (the owner's words verbatim, or the lead's own decision) or a `ВКАЗІВКА`'s reply | goes on |
| `ВКАЗІВКА` | a Lead to its sessions; a review «Discuss:» session to the Manager whose screen it reviews | an order that answers nothing: refresh an overfull context, a branch sent back, stop at a safe point near a usage limit or go on after its reset, «May message» for a review, the owner's remarks on a built screen (`dev-kit:project-lead`, "Build a designed screen") | does it |

- One kind per message. A message that needs two kinds (a result and a question) is sent as two.
- In an English project the same capital words are used: they are fixed markers, not chat text.
- A message with no kind word (a session started before this rule) is read as before, by its text.
- Not covered: the Pult watcher's event messages (`gone:`, `finished:`, the usage limit notice `ЛІМІТ:` and the
  rest, `dev-kit:project-lead` "Wake-up"), which are machine lines, the Pult hub's other messages, and a session's first prompt.

Why: on 2026-11-21 the owner said «Так» inside «Discuss: Повідомлення між сесіями» after its last report;
nothing told the Lead, and the Lead asked him again. The owner agreed the same day on a short fixed list of kinds, so
each session type knows what to send and the receiver what to expect.
