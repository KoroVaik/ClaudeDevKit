# Sessions log their problems; an agent finds rule gaps

Owner's words (2026-11-19): «Давай подумаємо над тим щоб кожна сесія записувала проблеми з якими зіткнулась і вкінці запускала якогось агента щоб розбирав ці проблеми і виявляв потенційні гепи в правила, скілах, агентах. Тобто мають трекаться кількість надлишкових викликів, невірний флоу, падіння продуктивності, можливість використання скриптів для повторюваних дій і тд. Запускай обговорення».

## Questions to settle with the owner
- What counts as a problem worth logging (extra calls, wrong flow, slowdowns, repeated actions a script could do, more?), and who notices it (the session itself, a hook, transcript analysis).
- Where the log lives and in what form; per session, per project or shared.
- When the review agent runs (end of each session, end of a task, on a schedule), on which model, and what it costs.
- What the review returns and where it goes (BACKLOG.md entries, a report to the owner, proposals for P), and what the owner sees.
- How it fits the existing process-mistake flow (owner's global docs/process-mistakes.md) and dev-kit:edit-rules.

## Success criterion
The owner's «так» to the approved idea, written in the section «Owner's approval» below, with where each part lives.
