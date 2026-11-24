# Messages between sessions

Every message one session sends another by SendMessage (P, a C, an «Обговорення:» session, a lead of
another project) starts with one kind word from the table, in capitals, then ` - ` and the text. The
receiver reads the kind first and so knows what the message asks of it. Who may message whom is the
skills' rule (`dev-kit:project-lead`, `dev-kit:manager`); this file only sets the kinds.

| Kind | Sent by | When | Receiver does |
|---|---|---|---|
| `ГОТОВО` | a C; a «Ретро:» session (`rules-kit:retro`, its only message); a «Документація:» session (`dev-kit:maintain-project-docs`) | its task is done and its branch is ready; 3 lines: state, result, what is needed (a «Ретро:» one may add `task: <what to build>` lines) | merges ("Acceptance and merge"); starts a C per `task:` line, with no owner ask |
| `ЗАКРИТО` | an «Обговорення:» session | the owner said «так» to its short plan and wrote nothing after it; this is its done report | merges and closes it |
| `ПИТАННЯ` | a C to its own P; a lead or an «Обговорення:» session to a lead | it needs a decision or a consent; it waits for the answer | answers with `ВІДПОВІДЬ`, or puts it in the owner queue |
| `ЗАСТРЯГ` | a C | it cannot go on, and no choice by P would unblock it (a crash of a tool, a queue timeout) | shows it as `чекає на тебе` or `стоїть, сесія впала` with its own question |
| `ЧЕКАЮ` | a C | it will wait more than 1 minute on something other than P or the owner (low memory, a retry timer, a store cool-off, another session, the app queue), idle itself (not its own build, test run or subagent); the reason in plain words and the time it resumes, if known | shows it at once as `чекає` with that reason (`dev-kit:project-lead`, «Статуси сесій») |
| `ПРОДОВЖУЮ` | a C | it goes on after a `ЧЕКАЮ` | shows it as `працює` again |
| `ВЛАСНИК ВІДПОВІВ` | a session the owner talks with; a C the owner wrote to in its chat (`dev-kit:manager`, "A task from the project lead") | the owner answered or decided there something its lead may ask or show (a question the lead put to the owner, a change of scope; the closing «так» is `ЗАКРИТО` instead); the owner's words verbatim | drops the matching queue item, never asks the owner again |
| `ВІДПОВІДЬ` | the session that was asked | the answer to a `ПИТАННЯ` (the owner's words verbatim, or the lead's own decision) or a `ВКАЗІВКА`'s reply | goes on |
| `ВКАЗІВКА` | P to its sessions | an order that answers nothing: refresh an overfull context, a branch sent back | does it |

- One kind per message. A message that needs two kinds (a result and a question) is sent as two.
- In an English project the same capital words are used: they are fixed markers, not chat text.
- A message with no kind word (a session started before this rule) is read as before, by its text.
- Not covered: the Pult watcher's event messages (`gone:`, `finished:` and the rest, `dev-kit:project-lead`
  "Wake-up"), which are machine lines, the Pult hub's own messages, and a session's first prompt.

Why: on 2026-11-21 the owner said «Так» inside «Обговорення: Повідомлення між сесіями» after its last report;
nothing told P, and P asked him again. The owner agreed the same day on a short fixed list of kinds, so
each session type knows what to send and the receiver what to expect.
