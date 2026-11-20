# Review of the plugin backlog

Owner's words (2026-11-20, P: ClaudeDevKit): «Так» to «Запустити нову сесію «C: Розбір беклогу плагінів»?
(7 нових ідей отримають оцінку й рекомендацію)».

## Scope
Every `##` entry of `BACKLOG.md` that has no `Verdict:` line (8 entries on 2026-11-20, from «Pult: own
remote client for agents» to «Pult hub: current state instead of an empty turn»). Some are partly
built or overtaken by later work (check the code, skills and plans/ before judging).

## What to do
1. For each entry: check what is already built (file:line), steps 1-2 of `dev-kit:edit-rules`, and
   judge it: build now, keep as an idea, merge with another entry, or drop. Write a `Verdict:` line
   under the entry with the recommendation and its reason.
2. Send P one batch of yes/no questions on the ideas, not the wording: each item is the idea in one
   plain line in the owner's words (Ukrainian) plus `Рекомендую: так - <reason>`, worded so the advice
   is «так». Drop entries that are fully built or overtaken without asking (remove them, say so in
   the report in one line each).
3. Wait for P's answers. Build nothing before them. On answers: simple entries you build in this
   session (dev-kit:edit-rules, version bump, lint); a complex one (new script, P/C flow) you report
   back to P as its own task.

## Success criterion
Every entry has a `Verdict:` line or is removed as built; the owner's answers are applied; lint clean.
