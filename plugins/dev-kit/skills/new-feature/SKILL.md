---
name: new-feature
description: Use when the owner asks to add, build or implement something, or to start the next step of a plan in `plans/`, as opposed to fixing something broken (that is `dev-kit:fix-bug`).
---

# New feature

Sequences the project's rules (`CLAUDE.md`) for one piece of work. Read the profile section
`## new-feature` of `.claude/dev-kit.md` if it exists; it adds to these steps and overrides them.

## 1. Orient

Read `PROGRESS.md` (current status), the map `docs/tech/map.md` and the feature and tech file(s) the
task touches; run `dev-kit-check-docs --who <path>` before editing code. Do not "fix" a feature rule
or a `Why:` line without the owner.

## 2. Brainstorm (when the design is open)

Skip for small or fully specified changes (a bug-sized tweak, a step the plan already
details). Otherwise settle the design with the owner before proposing an implementation:

- Ask at most 3 numbered questions at the end of the reply about what the plan and docs leave open
  (who does what, edge cases, scope limits). Do not re-ask settled decisions.
- Offer 2-3 approaches in the scratchpad file of step 3, one line each, with a recommendation; show
  each on the same real example (as the project's rules say, `CLAUDE.md` "Explanation level").
- For a UI change, add to that file the user flow (numbered steps, including empty, error and
  loading states) and an ASCII wireframe of the main screen.
- Mark your own guesses as guesses, and say every default you pick aloud so the owner can
  reject it.
- When talking would cost more than trying, offer a quick throwaway spike. It stays labeled
  throwaway; keeping its code is a new request.
- Record each accepted product rule in its feature or standard (see the
  `dev-kit:documentation` skill, section "Where things go").

Write no product code until the owner agrees on the approach.

## 3. Explain, then wait

The chat gets one plain line (what changes for the owner, on one real example) inside the plan
message, in the format of the owner's global rule "One yes per plan", with no paragraph before or
after the parts. The plan covers steps 4-6: the edits, each test or UI
check that needs consent on its own line, the docs. One question covers it all. The detailed approach (who does each part, risks, open details, examples)
goes into a file in the session scratchpad; attach it to the chat with SendUserFile only if the owner
must read it, and never mention a diagnosis file that only agents use. Explain there, at the level the
project's rules set (`CLAUDE.md` "Explanation level"), the parts the owner does not know. Hard stop:
wait for an explicit go-ahead; it covers every step the plan lists, and nothing else.

## 4. Implement

One scope, no drive-by cleanup; unrelated findings are recorded or proposed as "Where things go" in
the `dev-kit:documentation` skill says. No stubs; if the scope must grow, say so and confirm.
Comments only for non-obvious decisions (the project's comment policy).

## 5. Test the change

Follow `dev-kit:test-change`: run the `run-tests` slot, check a changed interface (API) first, then
UI checks (`check-ui`, `check-usability`, `check-look` slots) only after the consent the project's rules require;
restart the application with the `run-app` slot when fresh code is needed, and run the `stop-app` slot
when the owner says the work is done (see `slots.md`). Report the real results and the skipped checks.

## 6. Record the outcome

Record the outcome as the `dev-kit:documentation` skill says: update the feature, its epic and the
tech files whose description changed, report the result as "Outcome of a task" says, and finish with
"Before finishing" (the `check-docs` slot, `dev-kit-check-docs --pre-commit`). A change to feature
rules gets a `dev-kit:reviewer` (model sonnet) check of the feature file ("Review"). Mark a finished
step in its plan.

## Boundaries

Commit the finished work as the project's rules say; never push or create a branch unless the
owner asks.
