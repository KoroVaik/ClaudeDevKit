---
name: discovery-round
description: Use when the owner answers numbered questions, says "continue" ("продовж"), or discusses how the product should work rather than asking for code.
---

# Discovery round

One round of product discovery: reflect the owner's answers, record accepted product decisions in the
feature, epic, standard or `docs/product.md` they belong to and open questions in `PROGRESS.md`, then ask
the next numbered questions with recommendations (a talk on an idea he is still weighing opens with an
open question first, step 4). The owner shapes the idea deliberately before any
plan. Your job is to keep the thread, record every answer, and move one step forward per round. The
project's `CLAUDE.md` sets the language rules. Read the profile section `## discovery-round` of
`.claude/dev-kit.md` if it exists; it adds to these steps and overrides them.

## 1. Load context

Read `PROGRESS.md` for current state, open questions, and next steps; read the epic and feature files
in `docs/epics/` and `docs/features/` and the `docs/standards/` files that the answers touch, for the
accepted rules. Open `docs/product.md` or a plan in `plans/` only for the area the answers touch. Read the
`BACKLOG.md` entries of that area; a part with an "Owner said:" line is already answered, so do not ask it
again. Record it as accepted when the words are an explicit yes, and ask only what is left open.

When the talk is about how an existing mechanism behaves (a script, a hook, a watcher, who starts or
restarts what), check how it works now in its code and rules before a recommendation, a weak spot or a
plan line rests on it; a sweep over about 100 lines goes to a `dev-kit:investigator` (sonnet). Why:
ClaudeDevKit, 2026-11-22: a discussion told the owner a project lead may stay closed for days and wrote it
into the plan; Pult's watcher restarts leads.

The same holds for a new mechanism you recommend: a key fact that code and docs cannot settle (does a
failed send succeed after a resume) is checked live during the talk, before the question to the owner,
when the check is cheap and safe: a throwaway background session you start and stop yourself, no real
session touched, no money spent. This is a named exception to the owner's global "offer a check that is
not read-only". A check that needs the owner (his device, his sign-in) or is not cheap and safe is asked as a
question during the talk. The agreed plan and the written section hold only build work, never a point
like "check whether X works"; every key fact is checked or answered before the short plan is shown. Why: owner,
2026-11-23, ClaudeDevKit: «Обговорення має видавати план розробки, а не план тестування ідеї».

## 2. Map the answers

The owner answers by number, sometimes with **their own numbering** that differs from the
questions asked (e.g. answers "42-44" to questions "38-40"). Match by meaning, not by digit.
If an answer is genuinely ambiguous, ask, do not guess. In a live test with the owner (the phone, the
screen), no conclusion is drawn until every step has a clear answer. A «+» or «-» is clear only after a
step that ended with «+ або -» («мінус значить ні», owner), and a «+» after the readiness step of a
push test means "ready" (`dev-kit:project-lead`, "Push test with the owner"; a «-» there gets the step again); a bare sign after any other question, or an
unclear answer, gets the same step again in one line, asking exactly what was or was not seen. Why: ClaudeDevKit,
2026-11-23: a session read an unclear «-» as a test result; the owner: «тестував незрозуміло що ... і
вже зробив висновки».

- "так" / "ок" / "чудово" → accept the recommendation as asked. A bare «так» answers only the
  question(s) written out in full in your last message: one written question, that question; a
  question only named there (for example «4 і 5 ще чекають») stays open. This is one reading, so
  never ask «1 чи 2?» about it. Why: the session wrote one question and named two others; the
  owner's «Так» got «1 чи 2?» and he answered «??» (ClaudeDevKit, 2026-11-21).
- "треба думать" / "окремий флоу" → record as open, offer options next round, don't push.
- A counter-proposal → it wins; adjust the recommendation and record it as the decision.
- A question back ("чим X краще за Y?") → answer it briefly with the trade-off and a
  recommendation; keep the item open until confirmed.

## 3. Record (before replying)

Record each explicitly accepted product decision as "Accepted product rule" in the
`dev-kit:documentation` skill says (feature, epic, standard or `docs/product.md`; the standard also
gives the rule format and how a changed rule is edited). Before recording an open question in
`PROGRESS.md`, read its feature and the plan it links, as "Open question" there says; close one only
when the owner's answer resolves it, and do not mark implementation checks complete. Ideas the owner has
not agreed go to `BACKLOG.md`. Use the existing headings, in the project's documentation language.

## 4. Reply

The first message of a talk about an idea the owner is still weighing (his own words doubt whether to do it, e.g.
«думаю над тим, щоб...», «не знаю, чи...»; no question of yours open) is an open talk, not a round. A message that
already names what to design and why (the goal plus a reason or an example, e.g. «подумать над тим, як X ... Приклад
...») is not one: the first reply is a round of numbered questions with recommendations. Why: owner, 2026-11-24,
ClaudeDevKit, «Обговорення: Плавна зупинка при вичерпанні ліміту»: an open question that made him restate his task
got «якесь тупе питання ти задав». The open talk is at most 4 plain sentences on what he weighs and how
it is now, then one open question on his reason or what bothers him. That question asks his view, not a
decision, so it has no «Рекомендую» (a named exception to the owner's global question format) and no
numbered batch. Numbered questions with recommendations start once his answer makes the direction clear,
or when he asks for them; until then each reply is one plain sentence on what he said plus one more
open question of the same kind. Why: owner, 2026-11-24, ClaudeDevKit, «Обговорення» on separating Pult: «Нашо
відраду купу питань і рекомендацій, миж обговрбєм».

Every other reply: one line on what was recorded, then **at most 3 numbered questions** per round, numbering continuing
from the last round. Each question is at most 30 words: the question, its example (one real example
from the project of at most 15 words, as the owner's global rules ask) and
the **recommendation** with its reason. This skill's questions are its own exception to the owner's global reply cap. No long
explanations unless asked.

Each question stands alone: it names the screen or thing it is about in its own words, so the owner need
not recall an earlier screen or message, and no paragraph of facts or numbers comes before the questions.
Why: owner, 2026-11-23, P: Zhratva, seen in «Обговорення: Схвалення страви»: the questions came after a
long block of facts and pointed at a screen shown earlier; the owner agreed to this rule with «так».

## Boundaries

No code and no scaffolding in this skill. When discovery for an area is done, offer to move
to a plan in `plans/` and let the owner choose. In a session named «Обговорення: ...» the end follows
`dev-kit:project-lead`, "Start an «Обговорення:» session".
