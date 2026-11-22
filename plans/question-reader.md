# Reader check of the lead's questions

Source: BACKLOG.md, «Reader check of the lead's questions before the owner sees them» (Verdict: owner yes in retro 2026-11-22).

## Owner's words
- 2026-11-22, retro: «так» to «Перевіряти кожне моє питання до тебе окремим помічником, поки ти його не побачив?»
- 2026-11-22, on P's question «Додати правило підписувати цифри вартості?» with an «USD-еквівалент за цінами API» example: «всеодно неясно що це».

## The entry
- What: before P shows a new question, a cheap reader subagent checks it is in the owner's own words (what he sees or does, no agent terms, internal names) and rewrites it if not. Where and how cheap: the builder decides.
- Why: the rule «every question in the owner's words» (project-lead, «The question form») existed, yet P asked a question with «USD-еквівалент за цінами API»; a plain version came only on the second try.
- Cheapest test: feed the reader the 2026-11-22 question; it flags the terms and returns a plain version.

## Builder's decisions
- A new agent `dev-kit:question-reader` (haiku, effort low, only `Read`): it sees only the question text and the owner's list of terms he is still learning (`jargon.md` in his `.claude/docs`), with no context of the task. Haiku, since the check is short reading with no code.
- Scope: P's questions, its own and those it relays from sessions, each checked once, when it is first written in full. All new questions of one message go to the reader in one call. Counted lines and repeated full lists are not rechecked.
- The reader returns, per question, `ok` or the flagged terms and a plain rewrite; P shows the rewrite (keeping the facts) or the original on `ok`.
- Not covered: sessions that talk with the owner directly (not P). The owner's yes named P's questions; widening needs a new entry.

## Success criterion
The reader, given the 2026-11-22 question with its example, flags «USD-еквівалент за цінами API» and returns a version with no agent terms; a plain question («Видалити 12 влитих гілок?») comes back `ok`. P's skill tells it to run the reader before every new question message.

## Build
- Spend: <0.1% of the weekly limit, estimate (`dev-kit-retro session`); API: 0 USD.
- Rule text: `dev-kit:project-lead` «The reader check» (after «The question form»); a row in the `dev-kit:manager` subagent table; feature doc `docs/features/hand-work-to-the-project-lead.md` and `docs/tech/map.md` updated. dev-kit 0.1.94.
- Test (`claude -p`, haiku, the agent body as system prompt, three questions): the 2026-11-22 question flagged «USD-еквівалент, за цінами API» with a plain rewrite; a question full of agent words (P, handoff, worktree) came back `unclear`; the git-branches question was flagged for «влитих у main» (stricter than needed, harmless).
- Retest after the review fixes: session prefix «C: ...» and ❗ kept unchanged; «влитих у main» again rewritten as «чиї зміни вже в основній версії» (the success criterion's `ok` for that question did not hold: the reader counts «main» as a developer word, which fits a non-developer owner).
- Not covered by a live run: P calling the new type; P's session gets it after the plugin-update restart.
- Review (dev-kit:reviewer, sonnet): example made a true yes/no with no new fact; session prefix and ❗ kept; queue item overwritten with the plain text; manager row points to «The reader check».
