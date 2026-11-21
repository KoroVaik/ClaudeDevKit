# Messages between sessions

Every message one session sends another by SendMessage (P, a C, an «Обговорення:» session, a lead of
another project) starts with one kind word from the table, in capitals, then ` - ` and the text. The
receiver reads the kind first and so knows what the message asks of it. Who may message whom is the
skills' rule (`dev-kit:project-lead`, `dev-kit:manager`); this file only sets the kinds.

| Kind | Sent by | When | Receiver does |
|---|---|---|---|
| `ГОТОВО` | a C | its task is done and its branch is ready; 3 lines: state, result, what is needed | merges ("Acceptance and merge") |
| `ЗАКРИТО` | an «Обговорення:» session, a retro session | the owner said «так» to its short plan and wrote nothing after it; this is its done report | merges and closes it |
| `ПИТАННЯ` | a C to its P; any session to a lead | it needs a decision or a consent; it waits for the answer | answers with `ВІДПОВІДЬ`, or puts it in the owner queue |
| `ЗАСТРЯГ` | a C | it cannot go on, and no choice by P would unblock it (a crash of a tool, a queue timeout) | shows it as `чекає на тебе` or `стоїть, сесія впала` with its own question |
| `ВЛАСНИК ВІДПОВІВ` | a session the owner talks with | the owner answered or decided there something its lead may ask or show (a question the lead put to the owner, closing, a change of scope); the owner's words verbatim | drops the matching queue item, never asks the owner again |
| `ВІДПОВІДЬ` | the session that was asked | the answer to a `ПИТАННЯ` (the owner's words verbatim, or the lead's own decision) or a `ВКАЗІВКА`'s reply | goes on |
| `ВКАЗІВКА` | P to its sessions | an order that answers nothing: resend missed reports after a restart, refresh an overfull context, a branch sent back | does it |

- One kind per message. A message that needs two kinds (a result and a question) is sent as two.
- In an English project the same capital words are used: they are fixed markers, not chat text.
- A message with no kind word (a session started before this rule) is read as before, by its text.
- Not covered: the Pult watcher's event messages (`gone:`, `finished:` and the rest, `dev-kit:project-lead`
  "Wake-up"), which are machine lines, and a session's first prompt.

Why: on 2026-11-21 the owner said «Так» inside «Обговорення: Повідомлення між сесіями» after its last report;
nothing told P, and P asked him again. The owner agreed the same day on a short fixed list of kinds, so
each session type knows what to send and the receiver what to expect.
