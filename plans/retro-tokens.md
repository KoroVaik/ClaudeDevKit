# Token spend in the retro

Owner's words (2026-11-19): «Треба подумати над тим, як трекати кількість токенів які витрачаються на всі діяльності, щоб потім юзати це в ретро сесіях»; then «Запусти обговорення. Хочу деталі обговорить».

## Checked facts
- Session transcripts (`~/.claude/projects/<repo>/<session>.jsonl`, subagents in `<session>/subagents/`) hold token usage per message; no model is needed to count it.
- The daily scan exists: plugins/dev-kit/scripts/retro.py (`dev-kit-retro`), run by P: ClaudeDevKit; the retro session is the dev-kit:retro skill (plans/session-retro.md).
- There is no task label in transcripts; an activity can be told only by project, session name, subagent type or tool.
- retro.py reads no token usage today; it scans only new bytes per file (state.json offsets), so a spend sum fits the same scan.
- Usage per assistant line: input, output, cache_creation (5m/1h split), cache_read, thinking, model. One message id repeats on several lines with the same usage: dedupe by message id globally (also across resumed files).
- Labels: `custom-title` line (last wins) is the session name; subagent `.meta.json` gives agentType, description, model; the folder ties it to the parent session; job state.json maps a job to its transcript.
- No costUSD per message. A `cost-state` line holds totalCostUSD and per-model costUSD, but whether it is cumulative per process is not checked; otherwise a price table is kept by hand.
- 3 days (2026-11-16..18): cache_read is about 95% of raw tokens, so a raw token sum misleads; subagents gave 78% of output tokens; one Zhratva worktree session was the top spender.

## Reviewer findings (2026-11-19, sonnet, scripts in the job tmp folder; weights inferred from list prices, not from the subscription meter)
- Proposed unit: 1 = one fresh Sonnet input token; output 5, cache read 0.1, cache write 1.25/2; Opus x5, Haiku x1/3. The model multiplier is the number that matters; top sessions stay the same under other per-kind weights.
- 3 days: Opus about 86% of units, subagents 25%, cache read 59%.
- Long sessions: 4 of 53 sessions with 150+ main turns hold 42% of units; cost per turn triples from under 50 turns to past 200.
- Opus coder subagents: 5 runs = 11% of all units, one run about 22x a Sonnet coder run.
- "Main model reads big files itself" is not supported by the data (0.5%).
- "% of usual" works only for kinds of work with 10+ runs, against the median, within one model.
- Anthropic does not publish how much faster Opus uses the subscription limit; blogs say about 3x.

## Owner's answers so far
- No dollars: the owner is on a subscription, so money is the wrong measure (2026-11-19).
- The goal is not to hunt the biggest spends but to find better ways of working; spend is evidence for a pattern, not the finding itself (2026-11-19).

## Owner's approval (2026-11-19, «Ок» to questions 4-6 after the retro flow was explained)
- Spend is counted in units, not dollars or raw tokens: 1 = one fresh Sonnet input token; output 5, cache read 0.1, cache write 1.25 (5m) / 2 (1h); Opus x5, Haiku x1/3. Messages are deduped by message id. Lives in: the daily scan, `plugins/dev-kit/scripts/retro.py` (weights as constants there).
- The Opus weight is checked once against the owner's subscription meter (`/usage`) on one day, and corrected if it is off. Lives in: the session that builds the scan change; the owner reads the meter once.
- The scan sums units per session (by its title) and per subagent (type, model), and writes spend findings into the same daily scan file as the other findings. Lives in: `retro.py`, the scan file under `~/.claude/dev-kit/retro/`.
- Two habits become findings: a too-long main session (around 100+ main turns, where each turn costs far more), and an Opus coder subagent. "% of usual" is used only for kinds of work with 10+ runs, against the median, within one model. Lives in: `retro.py` thresholds.
- The goal is better ways of working, not the biggest spenders: spend is evidence, a finding proposes a rule change. Each retro proposes at most 1-2 spend rules, each with its evidence and marked "try a week and compare"; the next retro compares. Lives in: `plugins/dev-kit/skills/retro/SKILL.md`.
- The numbers are shown only in the retro session; no page, no P status. Lives in: the retro session.
- Build: a plugin change by a separate session after P's routing (`BACKLOG.md` entry with "Verdict: owner yes").

## Questions to settle with the owner (closed by the approval above)
- Which breakdown matters (project, session, task, subagent, model, tool, kind of activity), and over what period.
- Tokens only or also money, and how the price per model is kept current.
- What counts as too much (thresholds, comparison with past days), and what the retro does with it.
- Where the numbers are shown (retro session only, P's status, a page).

## Success criterion
The owner's «так» to the approved idea, written in the section «Owner's approval» below, with where each part lives.

## Build (2026-11-19, session «retro-tokens-build»)
- Paid spend: $0 (no paid calls; subagents run on the subscription).
- Code: `plugins/dev-kit/scripts/retro.py` counts units per message (weights as constants `WEIGHTS`, `MODEL_WEIGHTS`), dedupes message ids within a scan and skips lines dated before the previous scan started (a resumed file copies old lines with their timestamps: 12 of 18 cross-file repeats in 4 days kept the timestamp). Session titles and main-turn totals are kept in `state.json`, so a long session is seen across days.
- A main turn = a user line that is not a tool result and not `isMeta` (owner or injected message). `long session`: 100+ turns so far, with this scan's units per turn against the median of sessions under 50 turns. `opus coder`: a coder subagent run whose units are mostly Opus, against the median Sonnet coder run kept in `state.json` (last 50 runs per type and model).
- Spend tables go to a `## Spend` section of the scan file (`| ` lines, not counted as findings); `list` prints them after the notes. "Usual per run" shows only with 10+ runs of one type on one model.
- A model that is not Opus, Sonnet or Haiku (e.g. Fable) gets weight 1 for now; not in the approved weights.
- First real run (1 day, 89 transcripts): 417M units, Opus 92%, subagents 17%; 4 Opus coder runs, x3-x13 of a Sonnet coder run.
- Rule edits (edit-rules steps 1-2): home of the spend-trial rule is `plugins/dev-kit/skills/retro/SKILL.md` (new section «Token spend»; trials logged in `trials.md` of the findings folder so the next retro can compare); restatement updated in `README.md` (scan description). No duplicates or conflicts found: `project-lead` counts only `new findings`, which the tables do not change; manager's retro line unaffected.
- Review (sonnet reviewer): fixed - ratios in findings show only with 10+ runs (or 10+ short sessions) behind them; the weight comment no longer claims the meter check; the skill compares a trial after 7+ days from the `scan-*.md` files, not from `list`; a `|` in a title no longer breaks the table.
- Left as is (reviewer doubts): dedupe across scans is by timestamp, so a resumed copy with fresh timestamps (6 of 18 cases in 4 days) is counted twice; a subagent run that spans two scans counts as two runs; a `long session` finding repeats on each later scan while the session goes on; `state.json` keeps one title and one turn total per session.
- Done: the Opus weight check against the owner's `/usage` meter, see «Opus weight check».

## Usage readings (owner, /usage)
- 2026-11-19 19:15: week all models 23%, week Fable 0%, 5-hour session 22% (resets 22:39).
- 2026-11-20 19:15: week all models 54%, week Fable 0%, 5-hour session 61% (resets 20:39). P session alone (7h41m): 11.54 USD API-equivalent, Opus 94% / Sonnet 6% / Haiku 0%; tokens Opus in 4.8k, out 37.6k, cache read 17M, cache write 827.2k; Sonnet 72 / 20.3k / 785.9k / 174.7k; Haiku 8.5k / 14.8k / 789.6k / 104.2k (owner screenshot).

## Opus weight check (2026-11-20, session «opus-weight»)
- Paid spend: $0.
- Method: all transcripts under `~/.claude/projects` (subagents included), deduped by message id, units by `retro.units_of` with Opus at weight 1, summed per model inside each meter window. Times read as local UTC+1 (the machine's zone); UTC+2 gives a negative weight, so UTC+1 is the consistent reading.
- Week window 11-19 19:15 -> 11-20 19:15 (23% -> 54%, 31 points): Opus 95.1M raw, Sonnet 73.7M, Haiku 0.5M. One equation with the unknown week limit: alone it cannot settle the weight.
- 5-hour windows, assumed to have one fixed limit: #1 11-19 17:39-19:15 at 22%: Opus 10.68M, Sonnet 3.52M; #2 11-20 15:39-19:15 at 61%: Opus 23.57M, Sonnet 18.61M. Solving both: Opus weight 1.47; the meter's 1-point rounding gives 1.2-1.8. Weight 5 puts the two windows 16% apart (259M vs 224M limit), weight 3 10% apart, weight 1.5 agrees.
- Cross-check: the P-session API-equivalent split (Opus 94% / Sonnet 6% of 11.54 USD) against its token counts gives about 2-2.3 (5-minute vs 1-hour cache writes), also far below 5.
- Result: Opus weight set to 1.5 in `retro.py` (`MODEL_WEIGHTS`), tests in `tools/tests/test_retro.py` updated. Week limit at 1.5: about 690M units, about 8 five-hour limits (87M).
- Weak spots: window #1 is short (1.6 h, 14M units); the per-kind weights (cache read 0.1, writes 1.25/2) are assumed, not checked, and a different meter weighting would shift the fit; Haiku 1/3 and Fable are untested (too little use).
