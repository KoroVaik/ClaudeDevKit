---
name: prune-tests
description: Use when the owner asks to prune a project's existing tests or to mark old tests with what they protect - one pass, domain by domain.
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

For each domain, smallest first:

1. **Judge.** A `dev-kit:reviewer` (sonnet) reads the domain's tests and the code they call and
   returns one line per test: `file:line name - verdict - reason`. Verdicts:
   - `keep <Mark>`: it names what breaks without it; the mark is `Flow`, `Rule`, `Bug` or `Edge`.
     `Bug` only when a comment, the test name or `git log -S` on the test shows the bug; the reason
     then says what broke.
   - `merge into <test>`: the same rule as another test; it becomes a data row of that test.
   - `delete`: it tests what types or the database rule out, or the language or framework itself
     (a record copy, "the constructor does not throw", constants are distinct), or it repeats
     another test with nothing new.
   - `doubt <Mark>`: anything not clearly one of the above. A doubtful test is kept with its best
     mark; it is never deleted.
2. **Apply.** A `dev-kit:coder` (sonnet) adds the marks, merges and deletes exactly as judged, and
   nothing else. A `Bug` mark gets its `Broke:` line from the reviewer's reason.
3. **Check.** Build, then run the domain's tests: all pass, and none that passed at the baseline
   now fails. Run `dev-kit-check-tests --base <commit before this domain>`: 0 errors. A failure
   after a delete means the test protected something: restore it with its best mark and count it
   as doubtful.
4. **Commit** the domain on its own, per the project's git rules. The commit message lists every
   deleted or merged test with its reason and the doubtful tests by name; that is the record, no
   separate file.

## 3. Report

Run `dev-kit-check-tests --report` again and compare it with the baseline. Tell the owner the
outcome in the project's report format: what changed (tests marked, merged, deleted), what failed
or was skipped (tests left for the owner's consent), and what needs their action. Doubtful tests
are not put to the owner one by one.
