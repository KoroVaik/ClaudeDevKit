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

## Goal of the talk

Agree with the owner what changes so the 5-hour limit lasts (for example a cap on parallel Opus sessions, cheaper
models for some roles, smaller contexts, a per-window budget). The outcome goes into «Owner's approval» below.
