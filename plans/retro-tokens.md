# Token spend in the retro

Owner's words (2026-11-19): «Треба подумати над тим, як трекати кількість токенів які витрачаються на всі діяльності, щоб потім юзати це в ретро сесіях»; then «Запусти обговорення. Хочу деталі обговорить».

## Checked facts
- Session transcripts (`~/.claude/projects/<repo>/<session>.jsonl`, subagents in `<session>/subagents/`) hold token usage per message; no model is needed to count it.
- The daily scan exists: plugins/dev-kit/scripts/retro.py (`dev-kit-retro`), run by P: ClaudeDevKit; the retro session is the dev-kit:retro skill (plans/session-retro.md).
- There is no task label in transcripts; an activity can be told only by project, session name, subagent type or tool.

## Questions to settle with the owner
- Which breakdown matters (project, session, task, subagent, model, tool, kind of activity), and over what period.
- Tokens only or also money, and how the price per model is kept current.
- What counts as too much (thresholds, comparison with past days), and what the retro does with it.
- Where the numbers are shown (retro session only, P's status, a page).

## Success criterion
The owner's «так» to the approved idea, written in the section «Owner's approval» below, with where each part lives.
