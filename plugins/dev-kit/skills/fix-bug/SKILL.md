---
name: fix-bug
description: Use when the owner reports something broken (wrong behaviour, a crash, a layout or visual defect, a failed job) or takes a defect from the docs' Open lists, as opposed to new functionality (that is `dev-kit:new-feature`).
---

# Fix a bug

Same rules as `dev-kit:new-feature`, starting from a symptom instead of a spec. Read the profile
section `## fix-bug` of `.claude/dev-kit.md` if it exists; it adds to these steps and overrides them.

## 1. Orient

Read `PROGRESS.md`, the current plan, and the feature and tech file the symptom touches
(`dev-kit-check-docs --who <path>` finds the feature of a code path). A "bug" may be a deliberate
feature rule (see its `Why:` and Known limits) - flag it to the owner instead of silently changing it.
A bug may also come from `dev-kit-check-docs --defects`; when it is fixed, delete its line.

## 2. Classify - this picks the UI check after any changed API passes

| The report sounds like... | It is a... | UI check, if authorized |
|---|---|---|
| wrong data, a crash, a click that does nothing, a failed save | functional bug | `check-ui` slot |
| overlap, clipping, sideways scroll, misalignment | layout bug | `check-look` slot, layout |
| a screen that differs from its mockup | visual bug | `check-look` slot, mockup comparison |
| users get lost, a step is unclear or awkward | usability bug | `check-usability` slot |
| unclear | - | ask the owner |

Extra rows come from the profile's `## fix-bug` section (for example a bug of the project's own
pipeline).

## 3. Diagnose

Find the root cause in code. Compare the broken path with similar code that works and list
every difference. Chat: at most 3 sentences with one example; the full diagnosis goes in a
scratchpad file, as in `dev-kit:new-feature` step 3. Hard stop: wait for a go-ahead.

## 4. Fix

Root cause, narrowly. If the real fix is wider than expected, say so and confirm instead of
layering a workaround. Comment only if a future reader would otherwise "fix" it back.

Where the bug is testable in code, first reproduce it with a failing test (per `dev-kit:test-change`),
then fix. If three fixes in a row fail, stop and discuss the design with the owner instead of
trying a fourth.

## 5. Test the fix

Follow `dev-kit:test-change`: run the `run-tests` slot, check a changed interface (API) first, then
UI checks only after the consent the project's rules require; restart the application with the
`run-app` slot when fresh code is needed, and run the `stop-app` slot before the task ends. For an
authorized UI check, use the check selected in step 2. If the bug still reproduces, report it and
continue fixing within the agreed scope.

## 6. Record the outcome

Record the outcome as the `dev-kit:documentation` skill says: update the feature, its epic and the
tech files whose description changed, report the result as "Outcome of a task" says (what broke, what
fixed it, the checks run, skipped or unverified checks, remaining work), and finish with "Before
finishing" (the `check-docs` slot, `dev-kit-check-docs --pre-commit`). A change to feature rules gets
a `dev-kit:reviewer` (model sonnet) check ("Review").

## Boundaries

Commit the finished fix as the project's rules say; never push or create a branch unless the owner
asks.
