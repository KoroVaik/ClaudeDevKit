# Weekly docs upkeep after the retro

## Owner's words (2026-11-22)
- «давай додамо автоматичний запуск упорядкування документації раз на тиждень»
- «може якось інтегрувати в ретро сесії, типу після них запускати впорядкування використовуючи оновлені правила?»
- «є сенс щоб вона завершувала роботу і лишала пункти відкритимі і фіксились вони окремо, щоб не тримати відкритой сесійой. Також треба щоб виносились тіки дійчно ажливі пункти»

## Owner's answers («так» to all, 2026-11-22)
1. Once a week, after the project's retro session («Ретро: <project>»), a separate background session runs the docs upkeep (`dev-kit:maintain-project-docs`) against the freshly updated rules. If no retro ran that week, the docs session starts on its own (same start mechanism as the retro: hooks, no Pult or OS scheduler). Every dev-kit project with a lead.
2. The docs session applies trivial fixes itself, records the rest as items (like retro items: local folder, one file per item, status line) and ends; it never stays open. Only important items reach the owner: a change of a rule or of the product description. Approved items are fixed later, separately (as a small rule edit by P, or a C).
3. Important docs items are asked together with the weekly retro ask (one question a week, not two).

## Facts checked by P
- `plugins/dev-kit/skills/maintain-project-docs/SKILL.md`: today it edits only after the owner's yes on the whole proposed list (step 3); this task changes that for trivial fixes, as `plans/retro-scope.md` did for the retro.
- Retro per project: `plans/retro-scope.md`, `plugins/dev-kit/scripts/retro.py` (hooks, item folders, `dev-kit-retro asked`).
- Background sessions start without remote control (no phone push).

## Success criterion
In a project with a lead, after a retro session ends (or a week passes with none), a docs session runs once, applies trivial fixes, leaves the other items as files and ends; P's weekly ask counts the important docs items together with the retro items.
