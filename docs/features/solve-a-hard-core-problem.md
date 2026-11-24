# Solve a hard core problem

Epic: [Run a task through the process](../epics/run-a-task.md)

## Purpose
Some projects have a complex core (a physics solver, an AI analysis pipeline) where a cheap agent cannot
find the cause or two fixes in a row fail. A strong engineer agent then takes the one subproblem from the
cause to the change, and helpers do its side research without filling anyone's context.

## Rules
### One shared engineer, tuned per project
`dev-kit:core-engineer` runs on Fable with high effort and a 1-hour prompt cache. A project turns it on
with a `## core-engineer` section in its profile: its core areas, what the engineer reads first, what it
never does there (for example paid analysis runs). Without that section the engineer is not used.
Why: owner, 2026-11-23 (Zhratva «Обговорення: Інженер ядра аналізу»): Prishch's local engineer was wanted
in Zhratva too, reusable rather than copied.

### Every launch needs the owner's yes
Each fresh launch, a test launch included, needs the owner's yes for that launch. A continuation of the
same run (helper answers, check results, a go-ahead) needs none. It is proposed only after an investigator
could not find the cause with confidence, or two fix attempts failed, unless the project says otherwise.

### A new approach is described first
A new approach or an architecture change comes back described without code. After the owner's yes the
session sends the go-ahead to the same run within the hour, while its cache is warm, and it builds it.

### Helpers pass file paths
A subagent cannot start subagents, so the engineer stops with helper questions. The session runs a cheap
`dev-kit:investigator` per question; it writes its answer to `.claude/helper-notes/` (never committed) and
returns only the path. The session passes the paths on and the engineer reads the files.

How it runs: `plugins/dev-kit/skills/manager/SKILL.md`, "A core engineer and its helpers".

## Acceptance criteria
- A session launches `dev-kit:core-engineer` after the owner's yes: its transcript shows 1-hour cache writes.
- An investigator in helper mode writes its note and returns only the path; the engineer reads that file.
- A project with no `## core-engineer` section gets no engineer launch.

## Built in
- `plugins/dev-kit/agents/core-engineer.md`
- `plugins/dev-kit/agents/investigator.md`
- `plugins/dev-kit/skills/manager/SKILL.md`
