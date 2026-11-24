# Token units and the weekly limit

Measured 2026-11-16..20 from the session transcripts under `~/.claude/projects` and from the owner's `/usage` meter.
The weights are in `plugins/spend-kit/scripts/spend.py` (`WEIGHTS`, `MODEL_WEIGHTS`, `WEEKLY_LIMIT_UNITS`).

## Raw tokens mislead

- Claim: cache reads are about 95% of raw tokens (2026-11-16..18), so a raw token sum says little; a unit sum
  with weights is needed. Subagents gave 78% of the output tokens in the same 3 days.
- Consequence: spend is counted in units (1 = one fresh Sonnet input token; output 5, cache read 0.1, cache write
  1.25 for 5 minutes and 2 for 1 hour), never in dollars (a subscription is not billed per token).
- One message id repeats on several lines with the same usage, and a resumed session file copies old lines with
  their old timestamps (12 of 18 cross-file repeats in 4 days). Consequence: the scan counts a message id once
  and skips lines dated before the previous scan started.

## The Opus weight is about 1.5, not 5

- Claim: one Opus token uses about 1.5 times a Sonnet token of the owner's subscription limit. Evidence
  (2026-11-20, readings of `/usage` on 2026-11-19 and 20): two 5-hour windows (22% with Opus 10.68M and Sonnet
  3.52M raw tokens, 61% with Opus 23.57M and Sonnet 18.61M) solve to 1.47; the meter's 1-point rounding gives
  1.2-1.8. Weight 5 puts the two windows 16% apart, weight 3 10% apart, weight 1.5 agrees. A cross-check from the
  API-equivalent split of one session (Opus 94% of 11.54 USD) gives about 2-2.3, also far below 5.
- Consequence: `MODEL_WEIGHTS` has Opus 1.5; the weekly limit is about 690M units (about 8 five-hour limits of
  87M), uncertain by about 30%. A status line log of the weekly per cent (`spend-kit-statusline`) refits the limit
  from the next days on, replacing the hand fit.
- Weak spots: the first window is short (1.6 hours, 14M units); the weights per kind (cache read 0.1, writes
  1.25 and 2) are assumed, not checked, and a different meter weighting would shift the fit; Haiku 1/3 and other
  models (Fable) are untested for lack of use. Anthropic does not publish how much faster Opus uses the limit;
  blogs say about 3x.

## Habits that cost most

- Claim: long sessions and Opus coder subagents carry the spend (3 days, 53 sessions; first real scan of one day,
  89 transcripts, 417M units). Evidence: Opus about 86-92% of units, subagents 17-25%; 4 of 53 sessions with 150+
  main turns hold 42% of the units, and the cost per turn triples from under 50 turns to over 200; 4-5 Opus coder
  runs hold 11% of all units, one run about 22x a Sonnet coder run (3-13x in the one-day scan).
- Not supported by the data: "the main model reads big files itself" (0.5% of units).
- Consequence: the scan raises `long session` (100+ main turns) and `opus coder` as findings, and a "% of
  usual" is shown only for a kind of work with 10+ runs, against the median, within one model.
