# Spend the 5-hour limit slower

Status: discussion started 2026-11-27 by L: ClaudeDevKit.

## Owner's words

2026-11-27: «Проаналізуй витрати лімітів за останній 5 годинний ліміт. Надто бистро витратився». After the Lead's answer,
to «запустити обговорення, як зменшити витрати? (наприклад, менше одночасних сесій на Opus)»: «Давай обговорення.»

## What the Lead found (estimate, token prices assumed)

Window 2026-11-27 06:40-11:40 UTC; 95% by 09:30 UTC. About 85% of the weighted cost was Opus. About ten Opus sessions
lived at once (leads, Managers, a review session, Pult); each turn re-reads a large cached context, and sessions that
woke after a pause wrote their whole context to the cache again. Top: Prishch pain-feedback Manager with Opus
subagents (~23%), Zhratva catalogue-next with a Sonnet judge loop (~19%), L: Prishch (~10%), Pult (~9%). Fastest rise:
09:19-09:30, 78% to 95%, four sessions at once. Full tables: C:/Users/korov/.claude/handoffs/ClaudeDevKit/spend-5h-2026-11-27.md
(local file).

## Direction confirmed by the owner (2026-11-27)

- The limit type does not matter; what matters is tokens spent against the quality of the work done. Owner: «Мені
  пофігу на тип ліміту, головне це кількість потрачених токенів і якість виконаной роботи».
- One measure per task: tokens spent and how many times it was redone after the owner's remarks (owner: «Так»).
- Catch wasted work by several signals; an owner re-asking is a sign of a badly built reply, which comes from a rule
  problem. Owner: «Потрібно різними шляхами відловлювати лишню роботу».
- More waste signals from the owner: the wrong model chosen, too little reasoning, or too much reasoning. Owner:
  «Або ж вибрана невірна модель, або недостатній різонінг, або завищений різонінг».
- Checked 2026-11-27 (investigator, sonnet): owner messages reach only the CORRECTION regex
  (`plugins/rules-kit/scripts/packets.py:48-49`), strong words only (a bare «?» or «що?» never matches), run only by
  `rules-kit parts` in a retro session, cap PACKETS_MAX 20 per run (`retro.py:296`), first message of M:/Discuss:
  skipped; 9 of 69 stored packets carry the sign. Reasoning effort is in every transcript line (`effort`,
  `perTurnEffort`, `requestedModel`) but no plugin reads it. No tokens are tied to a correction or to a retro item;
  `spend-kit` has `range_units` (`spend.py:1187`) for a line range. Unused: several helpers reading the same files,
  a session redoing a helper's work. Questions 1-3 of the first round were replaced by 4-6.
- Checked now: the retro already flags `owner correction` (rules-kit `scripts/packets.py`, GENERAL) and spend-kit
  already counts tokens and waste per session (idle wakes, cold restarts, bloated context); nothing ties the
  tokens to the rework or ranks the retro's fixes by tokens wasted.

## Check of the plan on real data (2026-11-27, reviewer, sonnet; transcripts 2026-11-24 to 27)

Scripts and numbers: C:/Users/korov/.claude/jobs/11a30bb3/tmp (b1-b6, local). Confirmed: tokens from an owner
correction to the next owner message are about 0.14% of spend (10 events), so a rework share alone shows ~0%; the
wider re-ask pattern adds 4 hits to 6 in 543 owner messages; reasoning is ~6% of spend, lowering it for investigator
and reviewers saves ~0.5%. Main Opus sessions are 59% of spend; prompts over 200k tokens are 48% of main Opus cost;
cache writes after over 60 min idle are 12% (74 events, 25 of them after 1-2 h); `dev-kit:coder` ran on Opus by
caller override in 903 messages, ~10% (`coder.md:5` says sonnet); Fable subagents 6%. Duplicate reads ~1%, mostly
`CLAUDE.md` that agent files order to read. Point 7 needs an exception to the owner's rule that a reply ends with a
next-step question, and its numbers come from a script.

Owner on question 13 (2026-11-27): «Не хочу мікроменеджити опус і сонет. Хіба що для задач які очікують сильного
заповнення контексту, а самі задачі не дуже важкі». He asks whether Sonnet high can be replaced by Opus low and
holds that the lowest reasoning of the stronger model equals the highest of the weaker one (a hypothesis, not
checked). Checked: the limit weighs Opus 1.5x Sonnet per token (`spend.py:158`), and ~80% of spend is reading and
writing context, ~6% reasoning; so Opus low costs more than Sonnet high on the same steps unless it needs fewer
steps. Quality of Opus low vs Sonnet high: not checked.

Comparison run (question 15, 2026-11-27): the same read-only research brief (4 questions on rules-kit / spend-kit)
to `dev-kit:investigator` twice, reports in C:/Users/korov/.claude/jobs/11a30bb3/tmp/ab (local). Sonnet high: 117k
tokens, 36 tool calls, 113 s. Opus low: 56k tokens, 9 tool calls, 61 s; with the Opus weight 1.5 about 84k units vs
117k, roughly 30% cheaper. Quality compared by the discussion session: both answered all four with correct file:line
facts; Sonnet added a few finer points (the correction check runs only in `parts`, `rules-kit check` judges
nothing, the retro session's own model), Opus used approximate line numbers in docstrings. One sample, research
task only; not checked on coding.

## Owner's approval

2026-11-27, owner «Так» to questions 4-6 (the talk goes on; the short plan is not yet shown):

1. Every owner message is checked, not only strong words. A bare «?», «що?», «ще раз», a repeated question and the
   present strong pattern all count as a re-ask or correction. No per-run cap drops owner messages (today
   PACKETS_MAX 20 in `rules-kit parts`), the check runs even on days with no other findings, and the first message
   of an `M:` / `Discuss:` session stays skipped (it is the task, not a reply). Corrections are counted per session
   in the scan, not only inside a retro session's `parts` run.
2. Each step's model and reasoning level are recorded (transcript fields `message.model`, `requestedModel`,
   `effort`, `perTurnEffort`; main session and every subagent file) and a mismatch with the work is flagged: an
   expensive model or high reasoning on mechanical or read-only work, and a cheap model or low reasoning whose step
   was then redone (a correction or a repeated `Agent` call for the same task). Also flagged: a subagent's actual
   effort or model differing from its agent file's `effort:` / `model:`.
3. The tokens from an owner correction to its fix are counted (spend-kit units over that line range, e.g.
   `range_units`), per session and per task, as rework. Each retro item carries the rework tokens behind it, and the
   retro fixes the costliest items first (today the order is by sightings only).

2026-11-27, owner «Так» to questions 7-9:

4. Duplicated work is flagged: several helpers (subagents) of one session or task reading the same files, and a
   session redoing what its helper already did (it reads again the files the helper read and reported on, or starts
   the same `Agent` task again). The data is already in the transcripts (`Read` / `Grep` inputs, `Agent` calls).
5. Once a week the owner sees one number: the share of tokens spent on rework (point 3) this week, next to last
   week's, so he sees whether the changes work. Shown where the weekly spend stats already reach him (`spend-kit
   stats`, the Lead's status), not as an extra push.
6. Reasoning lowered from high to medium now for `dev-kit:investigator`, `dev-kit:reviewer` and
   `rules-kit:rule-reviewer` (their `effort:` lines); `dev-kit:coder` stays high (its mistakes cost more). Each of the
   three goes back to high when the rework count (point 3) shows its runs led to rework; the retro raises that as
   an item, with the rework tokens behind it.

2026-11-27, owner «Так» to question 10, after the short plan was first shown (reopened the talk). Owner's own
picture: «автозапуски службових ретросесій в проектах на регулярній основі і запуск основной ретро сесії з якой я
можу комунікцвать раз на тиждень або за вимогой»; on the content: «Має вказуватись основна статистика і важливі
ретроайтеми як пофікшені так і заплановані».

7. A main retro session the owner can talk with: started once a week and on his request. It opens with the main
   statistics (the rework share of point 5 with last week's, the token spend summary from `spend-kit stats`, the
   counts of re-asks and flagged model / reasoning / duplicated-work cases) and the important retro items, both
   fixed (what changed, and whether later sessions confirmed it) and planned (waiting for a repeat or a fix),
   costliest first. It asks the owner nothing on its own (the 2026-11-24 rule of `plans/retro-auto-rules-check.md`
   stays: the retro fixes by itself); he reads it and may ask. The per-project service retro sessions stay as they
   are. Point 5's weekly number is shown here.

2026-11-27, owner «Так» to question 13 (and to 15, a comparison run during the talk; questions 12 and 14 stay open):

8. No per-step model micromanagement. Only helpers whose work fills a large context but is not hard (reading and
   mapping a lot of code or data, e.g. `dev-kit:investigator`, sweeps, inventories) run on Sonnet, never on Opus or
   Fable by a caller's override; the rest keeps its current model rules.

2026-11-27, owner «Так» to questions 12 and 14, with: «Але чистку треба зробить розумнішой, щоб відбувалась без
втрати проміжних данних, якщо іде якась робота»:

9. The main retro session (point 7) shows where the tokens went by cause: large context, cold restarts after a pause,
   expensive models (Opus / Fable helpers), duplicated work, rework, each as a share with last week's next to it;
   computed by a script (`spend-kit stats` grows these groups), not by the model. This replaces point 5's single
   rework share; question 11 (per-fix before/after counts) is dropped.
10. Sessions move to a fresh context earlier and before a long pause, through the existing handoff route
   (`dev-kit:project-lead` "Restart the Lead" self-move: save a handoff, `/clear`, load it; its fallback keeps the
   old session when the move fails; for Managers "Refresh an overfull Manager"). No intermediate data is lost: the
   move happens only at a safe point (no helper, background job or build running, the work's state written into
   the handoff: open questions, files touched, the step in progress); while work runs it waits.

2026-11-27, owner on question 16: «Зроби відразу що відмова від стискання має чітко пояснюватись і мати критичний
ефект. Все інше стискається.»

11. Checked first: Pult's watcher today sends a keep-warm ping only to an idle Lead whose Manager works, after 50
   minutes of silence (`plugins/pult/scripts/watch-servers.ps1:134-137, 303`), and moves a Lead to a fresh context
   only when its context is a third full (`watch-servers.ps1:186-201`). New: every other live session (Managers,
   Pult, a Lead with no working task, «Discuss:» sessions) idle about 50 minutes, before its cache expires, is
   moved to a fresh context through the handoff route of point 10, at a safe point. A session may refuse only with a
   clear written reason whose effect is critical (work or a decision would be lost or redone that the handoff
   cannot carry); the refusal and its reason are logged, and the retro reviews refusals as findings. Everything
   else is moved.

## Goal of the talk

Agree with the owner what changes so the 5-hour limit lasts (for example a cap on parallel Opus sessions, cheaper
models for some roles, smaller contexts, a per-window budget). The outcome goes into «Owner's approval» below.
