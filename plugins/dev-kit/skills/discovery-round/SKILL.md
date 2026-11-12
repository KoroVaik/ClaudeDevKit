---
name: discovery-round
description: Use when the owner answers numbered questions, says "continue" ("продовж"), or discusses how the product should work rather than asking for code.
---

# Discovery round

One round of product discovery: reflect the owner's answers, record accepted product decisions in the
feature, epic, standard or `docs/product.md` they belong to and open questions in `PROGRESS.md`, then ask
the next numbered questions with recommendations. The owner shapes the idea deliberately before any
plan. Your job is to keep the thread, record every answer, and move one step forward per round. The
project's `CLAUDE.md` sets the language rules. Read the profile section `## discovery-round` of
`.claude/dev-kit.md` if it exists; it adds to these steps and overrides them.

## 1. Load context

Read `PROGRESS.md` for current state, open questions, and next steps; read the epic and feature files
in `docs/epics/` and `docs/features/` and the `docs/standards/` files that the answers touch, for the
accepted rules. Open `docs/product.md` or a plan in `plans/` only for the area the answers touch. Read the
`BACKLOG.md` entries of that area; a part with an "Owner said:" line is already answered, so do not ask it
again. Record it as accepted when the words are an explicit yes, and ask only what is left open.

## 2. Map the answers

The owner answers by number, sometimes with **their own numbering** that differs from the
questions asked (e.g. answers "42–44" to questions "38–40"). Match by meaning, not by digit.
If an answer is genuinely ambiguous, ask, do not guess.

- "так" / "ок" / "чудово" → accept the recommendation as asked.
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

One line on what was recorded, then **at most 3 numbered questions** per round, numbering continuing
from the last round. Each question is at most 30 words: the question, its example (one real example
from the project of at most 15 words, as the owner's global rules ask) and
the **recommendation** with its reason. This is the only exception to the owner's global reply cap. No long
explanations unless asked.

## Boundaries

No code and no scaffolding in this skill. When discovery for an area is done, offer to move
to a plan in `plans/` and let the owner choose.
