---
name: prune-tests
description: Use when the owner asks to prune a project's existing tests, to mark old tests with what they protect, or to verify the tests marked as suspect.
---

# Prune and mark existing tests

The rule for a test worth keeping is `dev-kit:test-change`, section "Which tests to write", and the
mark syntax is the project's test rules. Read both first, and the profile section `## prune-tests`
of `.claude/dev-kit.md` if it exists; it overrides the defaults here. The owner's approval of the
pass covers every step below: do not ask per test or per domain.

## 1. Baseline

Run `dev-kit-check-tests --report` and keep its output: domains, marked and unmarked tests per
domain. A project with no domains is walked folder by folder. Run the project's full test suite
once (the `run-tests` slot) so that a later failure is known to be new. Tests the project's rules
allow only with the owner's consent (browser, UI, frontend) are judged from their code and are not
deleted in this pass unless that consent is given.

## 2. One domain at a time

For each domain, smallest first. With no domains, a group is a folder, or a set of test files on
one area of code (clustering, validation, transport); the steps below apply to each group.

1. **Judge.** A `dev-kit:reviewer` (sonnet) reads the domain's tests and the code they call and
   returns one line per test: `file:line name - verdict - reason`. Verdicts:
   - `keep <Mark>`: it names what breaks without it; the mark is `Flow`, `Rule`, `Bug` or `Edge`.
     `Bug` only when a comment or the test name shows the bug, or `git log -S` on the test where
     the project's rules allow reading old history; the reason then says what broke.
   - `merge into <test>`: the same rule as another test, through the same code path; the reason
     names the target test by `file:line` and the data row it becomes. Without both, it is `doubt`.
   - `delete`: it tests what types or the database rule out, or the language or framework itself
     (a record copy, "the constructor does not throw", constants are distinct), or it repeats
     another test with nothing new.
   - `doubt <Mark>`: anything not clearly one of the above. A doubtful test is kept with its best
     mark and a `Suspect:` line (`dev-kit:test-change`); it is never deleted in this pass.
2. **Apply.** A `dev-kit:coder` (sonnet) adds the marks, merges and deletes exactly as judged, and
   nothing else. A `Bug` mark gets its `Broke:` line, a `doubt` test its `Suspect:` line, both from
   the reviewer's reason.
3. **Check.** Build, then run the domain's tests: all pass, and none that passed at the baseline
   now fails. Run `dev-kit-check-tests` (0 errors) and `dev-kit-check-tests --report`: the
   domain's row shows 0 unmarked and 0 invalid (`--base` sees only brand-new tests). A failure
   after a delete means the test protected something: restore it with its best mark.
4. **Commit** the domain on its own, per the project's git rules. The commit message lists every
   deleted or merged test with its reason; the `Suspect:` lines in the code are the record of the
   doubtful ones, no separate file.

## 3. Report

Run `dev-kit-check-tests --report` again and compare it with the baseline. Tell the owner the
outcome in the project's report format: what changed (tests marked, merged, deleted, suspect),
what failed or was skipped (tests left for the owner's consent), and what needs their action.
Suspect tests are not put to the owner one by one: agents verify them when they change that code.

## 4. Verify suspects (only on the owner's request)

Run `dev-kit-check-tests --suspects`. For each listed test, a `dev-kit:coder` (sonnet) does the
break-check of `dev-kit:test-change` (break the code, run the test, restore the code exactly):
still passing, delete it with the reason "passes without the code"; failing, remove its
`Suspect:` line. Check and commit per domain as in section 2. A project-wide mutation run over all
tests is a separate decision of the owner.
