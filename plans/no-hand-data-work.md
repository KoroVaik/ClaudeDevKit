# No hand data work for the owner when a session has the whole task

Source: BACKLOG.md entry «project-lead and manager: no hand data work for the owner when he handed the whole task to a session» (from P: Zhratva, 2026-11-24). Owner approved the idea there («Які нафіг 60?! Мені зайнятись нічим?!», then «так» to the rule); the wording is the builder's, through `dev-kit:edit-rules`.

Success criterion: the rule sits in its one right home (likely project-lead "Owner queue and critical items" and manager "A task from the project lead", with no duplicates), the entry is removed from BACKLOG.md, dev-kit version bumped with a release mark, lint passes.

Done (2026-11-24): manager "Less of the owner's involvement over time" (data work goes to agents when the owner handed the session the task; a product-choice label still goes to the owner) and project-lead "Owner queue and critical items" (such an ask never enters the queue; P sends it back and decides leftovers inside the criteria), with a pointer from the «Зробиш» line. Reviewer (sonnet) findings 1-4 fixed; 5 (no extra C-side line) left: manager loads for every C. dev-kit 0.1.118, routine. Lint: 0 errors.

Spend: <0.1% of the weekly limit, estimate; API: 0 USD
