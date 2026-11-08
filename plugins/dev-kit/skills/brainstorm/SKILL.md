---
name: brainstorm
description: Use when the owner wants to brainstorm or generate ideas about an open product direction (a feature, a flow, a screen, "what next") - "брейншторм", "накидай ідей", "куди рухатись далі", "які є варіанти", "не певен, як це зробити". Not for recording decisions or answering numbered questions (that is `dev-kit:discovery-round`), nor for designing and building a change (that is `dev-kit:new-feature`).
---

# Brainstorm

A live ping-pong of short ideas between the owner and the agent, not an interview: the agent offers an
idea from the first message, the owner keeps, kills or twists it, and the survivors get a cheapest
honest test and a short recommendation. It ends with new entries in `BACKLOG.md`, never with decisions.
The product exists, the next direction does not. The project's rules are in its `CLAUDE.md`. Read the
profile section `## brainstorm` of `.claude/dev-kit.md` if it exists; it adds to these rules and
overrides them.

## Rules

- A ping-pong, not an interview and not a report: ideas flow both ways.
- Every message is short: at most 3 sentences, ONE new idea (or one twist of the owner's
  idea) and at most one short question at the end. No lists of ideas or tables unless asked. The idea is
  the concrete example the project's rules ask for (`CLAUDE.md`, "Explanation level"); a bare yes/no
  guess needs none.
- A visual idea (a screen, a header, a layout, a scene) is shown, not described: use the `show-idea`
  slot (the manager's slot tables name the skill) and send the result, following that skill's rules for
  temporary, one-theme pictures.
- Offer an idea from the very first message; do not collect answers first. A question may
  carry a guess ("може, вам ближче X?") so the owner only says yes or no.
- Build on the owner's last line: take their words, twist or extend them, then add one fresh
  idea. Their reaction ("ні", "о, це", a half-sentence) steers the next one. Do not re-ask.
- Keep a private list of ideas (alive / dead / twisted). Show it only when asked, or as one
  short line after about six ideas.
- Facts first: what the product really does today and what the feature rules already say - read it,
  do not guess. Mark claims known / assumed in a few words. If an idea contradicts a feature rule
  or a standard, say so in a few words; the idea may still live, but the owner must reopen the rule.
- Do not judge ideas while generating. No code names or internal labels in chat; plain words.
- Write nothing but backlog entries: no decisions, no `PROGRESS.md`, no feature or tech docs, no code.
- Do not invent a market. Judge by fit with the people who really use the product and by the cost of
  one honest test, not by trends.

## Flow (no fixed order; follow the owner)

1. **Read the ground.** The entries of `BACKLOG.md` on the topic; `PROGRESS.md`, the standards in
   `docs/standards/` and the epic and feature files in `docs/epics/` and `docs/features/` for the area.
   Say 3 lines: what the product does here, what it does well and cannot do, what is still open.
   Add the first idea in the same message. Fix mistakes the owner points out.
2. **Feelings, woven in.** Learn the best moment, 1-3 target feelings (relief, surprise, delight),
   references, one thing to avoid, constraints (time, cost, what must not change) - one at a time,
   each next to an idea that tests it. If the owner says "this is why you are here", stop asking and
   propose.
3. **Idea flow.** Rotate the angles, one idea at a time:
   - moment-first: start from a real moment of the user's day (or of a session of play or work) and what
     takes effort or feels flat there;
   - mashup: the product + an unrelated app or system (say what is borrowed from each);
   - feeling-backward: start from a target feeling, find the form that delivers it;
   - role: a whole feature / a hint inside an existing screen or scene / an admin or authoring tool /
     background automation nobody sees;
   - any further angle the profile adds.

   For an idea the owner likes, add in a line: what they do in that moment, why the product is needed
   (if something much simpler and non-digital could replace it, it is weak), the biggest risk.
4. **Narrow.** When asked, or after about six ideas: one line each for the survivors, scored
   only on "solves a real effort of the user", "excites the owner", "cheap to build". The owner
   strikes out; keep two or three.
5. **Test one survivor at a time.** One sentence a newcomer would understand; how it fits
   the feature rules and standards; 3 falsifiable pillars and 2 anti-pillars; the cheapest honest test
   (a wireframe or sketch via the `show-idea` slot, a prompt try with the project's AI experiment skill
   if its profile names one, a paper run over a week) and what result kills it; who or which
   situation it is not for.
6. **Close.** Recommended direction and why in 3 lines; what the owner must decide; one next
   step - usually `dev-kit:discovery-round` to turn it into rules, or `dev-kit:new-feature`.

## Backlog entries

Every session ends with entries in `BACKLOG.md`, so the next session starts from
them. Its format and rules are in the `dev-kit:documentation` skill (section "Where things go",
"Idea").

- One entry per surviving idea, 2-4 lines: what, why and the cheapest test. Rejected ideas are not
  kept; an idea already in the backlog is edited, not duplicated.
- Write them when the owner says the session is over or asks for it. Do not announce it every message.
- A working file, if the session needs one, goes in the session scratchpad or a temporary folder and is
  deleted once the surviving ideas are in the backlog. No dated file is kept in the repo.
- In the project's documentation language; keep the owner's own words in quotes where they matter.
  Mark numbers and costs as unmeasured.
