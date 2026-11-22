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

## Build (2026-11-22, C «weekly-docs»)
Design chosen within the owner's answers:
- Start: the retro's SessionStart hook (`retro.py`, `docs_start_command`), when it starts no retro session, starts `claude --bg --name "Документація: <project>" --model opus --effort medium -- "/dev-kit:maintain-project-docs weekly"` in the main checkout when: the last docs run (`docs_done`) is 7+ days old or missing, no docs start in the last 6 hours, no retro session may still run, and the retro's branch (`dev-kit-retro done --branch`) is merged into main or gone, or 48 hours passed since the retro. So it runs on the freshly fixed rules, or on its own in a week with no retro. Opus, as the retro: it applies trivial fixes with no owner.
- Trivial (fixed by the docs session in a worktree): docs edits with no change of meaning. Rule text is never trivial there, so the docs session bumps no plugin version.
- Items: `docs-items/<key>.md` in the project's retro folder; `status: owner` (changes a rule or the product description) or `open` (the rest). `owner` items count in the lead's `retro: N items due` line, so one weekly question; `open` items P hands to one C after the docs session's ГОТОВО.
- `dev-kit-retro docs-done` stamps the run; `items` lists the docs items; «Документація:» sessions are left out of `dev-kit-sessions others` and their start does nothing in the hook.
- Migrations: none; the hook comes with the plugin, projects change no files.
- First run: each project with a lead gets its first docs session at its next session start after the update (no docs run recorded yet).
- Reviewer's fixes applied: the docs session's own findings are not fed to the retro; the retro also waits while a docs session may run; a docs run that ended without `docs-done` is retried once a day; git calls in the hook capped at 2 s; the weekly mode turns every "owner's yes" of steps 2-3 into an item; `fixed` and `rejected` items are not reopened.
- dev-kit 0.1.97 (main had 0.1.96). After the merge of main the full tests passed on a rerun; the first run had one failure that did not repeat (which test was not recorded; the retro, sessions and hook tests pass every run).
- Spend: ~0.4% of the weekly limit, estimate; API: 0 USD.
