# Sessions log their problems; an agent finds rule gaps

Owner's words (2026-11-19): «Давай подумаємо над тим щоб кожна сесія записувала проблеми з якими зіткнулась і вкінці запускала якогось агента щоб розбирав ці проблеми і виявляв потенційні гепи в правила, скілах, агентах. Тобто мають трекаться кількість надлишкових викликів, невірний флоу, падіння продуктивності, можливість використання скриптів для повторюваних дій і тд. Запускай обговорення».

## Questions to settle with the owner
- What counts as a problem worth logging (extra calls, wrong flow, slowdowns, repeated actions a script could do, more?), and who notices it (the session itself, a hook, transcript analysis).
- Where the log lives and in what form; per session, per project or shared.
- When the review agent runs (end of each session, end of a task, on a schedule), on which model, and what it costs.
- What the review returns and where it goes (BACKLOG.md entries, a report to the owner, proposals for P), and what the owner sees.
- How it fits the existing process-mistake flow (owner's global docs/process-mistakes.md) and dev-kit:edit-rules.

## Owner's approval

Approved by the owner on 2026-11-19 («Так»). It replaces the earlier drafts in this discussion (a
review agent writing straight into the backlog, a cap of 3 entries a day).

1. Every day a script with no model reads the transcripts of all sessions and counts extra calls,
   repeated identical commands, failed calls and long pauses.
   Lives in: a new script in `plugins/dev-kit/scripts/`; it reads the local transcripts under
   `~/.claude/projects/` (including `subagents/`). Its findings file stays local, outside any repo.
2. A session itself notes only what the script cannot see: the owner's corrections and a wrong order
   of steps.
   Lives in: the owner's global `docs/process-mistakes.md` flow (one appended line per case) into the
   same local findings folder.
3. When there are new findings, the dev-kit lead (P: ClaudeDevKit) only proposes a retro session; it
   starts it only after the owner's «так». No new findings, no proposal. The owner can also ask for
   one at any time.
   Lives in: `plugins/dev-kit/skills/project-lead/SKILL.md`, a daily check plus a proposal through
   the owner queue, like the existing «Обговорення:» proposal.
4. In the retro session a subagent (sonnet, `dev-kit:reviewer`) first checks every finding; the owner
   then says «так» or «ні» to each.
   Lives in: a retro variant of "Start an «Обговорення:» session" in the project-lead skill (or its
   own skill, decided when building).
5. Easy decisions (wording of rules, skills, agents, no code) are edited right in the retro session
   through `dev-kit:edit-rules`; P merges them like any session's work. Scripts, hooks, new agents go
   to ClaudeDevKit `BACKLOG.md` and are built in a separate session.
   Lives in: the retro session's worktree of ClaudeDevKit; global rules edited in place after the yes.

## Decided so far
- The review runs every day to start with (owner, 2026-11-19; weekly was too rare).
- Findings reach the backlog or a rule only through the owner's yes in the retro session.

## Facts checked
- Transcripts (`~/.claude/projects/<repo>/<session>.jsonl`) hold per-message timestamps, tool name and input, tool errors and token usage; subagent transcripts sit in `<session>/subagents/`. A script can count calls, repeats, errors and pauses with no model.
- No Stop, SessionEnd or PostToolUse hook exists in dev-kit or pult today.
- The global process-mistakes flow is per event and manual; it has no counting.

## Success criterion
The owner's «так» to the approved idea, written in the section «Owner's approval» below, with where each part lives.
