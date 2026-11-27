# Catch wasted work

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

Status: built. Plan: [plans/limit-spend.md](../../plans/limit-spend.md).

## Purpose
The owner cares about tokens spent against the quality of the work, not the type of limit. Owner: «Мені пофігу на тип
ліміту, головне це кількість потрачених токенів і якість виконаной роботи»; «Потрібно різними шляхами відловлювати
лишню роботу». Several signals catch work that was wasted, the retro fixes the costliest causes first, and once a week
the owner sees where the tokens went.

## Rules
### Re-asks and rework
- Every owner message is checked: a bare «?», «що?», «ще раз», a repeated question and the strong correction words
  all count as a re-ask. No per-run cap drops one; the first message of a `M:` / `Discuss:` session is the task and
  is skipped.
- The tokens from a re-ask to the next owner message (the session and the helpers it launched in that span) are its
  rework, counted per session and per task.
- Each retro item carries the share of the weekly limit behind its sightings; the retro fixes the costliest first.

### Model, reasoning and duplicated work
- Each step's model and reasoning level are read from the transcripts. Flagged: a helper running above its agent
  file's model or reasoning, and a cheap model or low reasoning whose step was then redone (a re-ask or a repeated
  helper launch for the same task).
- Flagged too: several helpers of one session reading the same files, and a session reading again what its helper
  already read and reported, or launching the same helper task again.

### Model choice without micromanagement
- `dev-kit:investigator` runs on Opus with low reasoning; `dev-kit:reviewer` and `rules-kit:rule-reviewer` have medium
  reasoning in their files; `dev-kit:coder` keeps high.
- A caller's Opus or Fable choice for a helper whose work fills a large context but is not hard goes back to the
  helper's own model.

### Experiments
- `dev-kit:coder`, `dev-kit:reviewer` and `rules-kit:rule-reviewer` alternate Sonnet high and Opus low, every other
  run; Managers alternate Opus low and Opus medium, every other task. Each run is marked with its variant.
- Once a day a script counts each variant's runs, units per run and the signs after them (re-asks, a repeated helper
  launch, a failed check). After 3 runs of each, an alarming sign has a cheap model read those runs: an obvious
  problem stops that variant (the old one takes over); unclear goes on to 10 runs per variant, then the decision.

### Out-of-turn retro
A critical finding (an experiment variant with an obvious problem, a critical token problem, a refusal to move to a
fresh context) starts an out-of-turn ClaudeDevKit retro past the usual start gaps, with no question to the owner,
one at a time; the owner sees one line in Pult's status. The retro's spend cap stays.

### Main retro session
Once a week and on the owner's request a retro session he can talk with opens with the week's spend by cause
(large context, cold restarts, expensive models, duplicated work, rework), each with last week's share next to it,
the counts of re-asks and flagged cases, the experiments, and the important retro items, fixed and planned,
costliest first. It asks nothing on its own. The service retro sessions in the projects stay as they are.

### Moving to a fresh context
Sessions move to a fresh context through the handoff route at a safe point (no helper, background job or build
running; the work's state written into the handoff). A live session idle about 50 minutes, before its cache expires,
is moved. A session may refuse only with a written reason whose effect is critical (work or a decision the handoff
cannot carry would be lost); a refusal is logged and starts an out-of-turn retro.

## Acceptance criteria
- A bare «?» from the owner after a reply shows as a re-ask with its rework share in the retro's findings.
- `spend-kit stats` shows the spend by cause with last week's share next to each.
- A helper running above its agent file's model or reasoning shows as a finding.
- Two helpers of one session reading the same files show as a duplicated-work finding.
- Every other `dev-kit:coder` launch runs on Opus with low reasoning while the experiment runs.
- An alarming experiment sign starts an out-of-turn retro without waiting 20 hours.
- The weekly retro session opens with the spend by cause and the retro items, costliest first.
- An idle session is moved to a fresh context before its cache expires, or its refusal is logged with the reason.

## Built in
- `plugins/spend-kit/scripts/signals.py`, `spend.py` (scan, `findings`, `stats` block «Куди пішли токени», weekly `causes`)
- `plugins/spend-kit/scripts/experiments.py`, `plugins/spend-kit/hooks/experiment.py`, `plugins/spend-kit/agents/run-reader.md`
- `plugins/rules-kit/scripts/packets.py` (re-asks), `retro.py` (`items` by cost, out-of-turn start, `weekly`), `plugins/rules-kit/skills/retro/SKILL.md`, `plugins/rules-kit/skills/weekly-retro/SKILL.md`
- `plugins/pult/scripts/watch-servers.ps1`, `resume-lib.ps1` (move ask and move), `plugins/dev-kit/scripts/sessions.py` (`handoff --session`, `refuse`, `rekey`)
- `plugins/dev-kit/agents/investigator.md`, `reviewer.md`, `plugins/rules-kit/agents/rule-reviewer.md`, the `dev-kit:manager` and `dev-kit:project-lead` skills
