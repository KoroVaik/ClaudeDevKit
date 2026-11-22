# Fix agent problems in the retro

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
Each project with a lead learns from its own sessions: problems of agent work are collected with no model, a
background session reviews them with the project's rules in view and fixes the small gaps itself, and you decide
only the few that are yours, once a week. How it runs and its commands: [project lead tools](../tech/project-lead.md).

## Rules
### The retro catches every problem of agent work, and only that
It works for each project that has a lead (the project's profile has a `## project-lead` section); sessions in
other folders are skipped. A cause in the project's own rules, docs or profile (an old doc that sends agents to the
wrong file) is agent work and is fixed there. A bug in the project's code (a flaky test) is not: it goes to the
project as a defect and the retro stops there. A cause in a dev-kit plugin's rules or in your global rules
(`C:/Users/korov/.claude/`, chat style included) is handled only by the ClaudeDevKit retro, so two projects never
ask you the same thing. Projects with no lead (Pult, KnowledgeBase, a design sandbox) are not covered.
Why: owner, 2026-11-21 and 2026-11-22: the retro stays in dev-kit (no separate plugin) and fixes the problems of the
projects, not only of the plugin; it does not run on sessions with no dev-kit, since they would give little (the
scans of 2026-11-19..21 named only dev-kit projects).

### Items are local files, one per cause, one folder per project
Each finding becomes an item file in a local folder of the project (outside any repository, under the retro folder
of the user's `.claude`). Any session may add an item to any project's folder, marked with its source; a lead's
retro may pass an item to another project (rare).
Why: writes into a project's main checkout are blocked for P, items on unmerged branches would be lost, the scan
from ClaudeDevKit would write into other repositories, and two sessions writing one shared file overwrite each other.

### Collected and started by hooks, no model and no scheduler
A SessionEnd hook scans the ending session's transcript; a SessionStart hook runs the full scan once a day (it
also catches sessions killed by force, which end with no event) and, when new findings wait and the last review is
old enough, starts a background session «Ретро: <project>» that ends after it reports to P. P's weekly question
is prompted by a line the lead's prompt hook adds.
Why: owner, 2026-11-22: not Pult («його призначення дещо інше»), no Windows scheduled task, a fixed time not
required. Leads never wake by themselves, so a step "started by the lead" would not run while you are silent.

### A fix needs a repeat
A first sighting that is not urgent waits; a fix needs the same cause in a second session or on a second day (a
lead and its own subagents are one session). Lost work and a critical token problem are urgent and fixed at once.
A cause that is a rule agents ignore is not reworded: it gets another means (a hook, a check, a script). Every
rule fix also removes or merges something, so the rules do not keep growing. Why: owner, 2026-11-21: avoid fixes
for problems that arose by chance and not through bad rules, skills or agents.

### Every change is checked by later sessions
Each plugin change that alters agent behaviour gets a check by reading the sessions started after it: worked, did
not work or not met yet. A change that did not work becomes a disputed item, never a rewording.

### What you see
You see only disputed items, high-impact ones, urgent ones and anything about how sessions talk to you; the
reviewer decides the trivial ones itself (one place, a word or a sentence made clearer, no clash; at most 5 a week
per project; in ClaudeDevKit one plugin update a day, because each update restarts every lead). You get them in
the weekly list and any one is reverted with one word. P asks once a week «розібрати N пунктів?»; after a «ні» it
asks again the next day. Urgent items reach you at once. Why: owner, 2026-11-22: the reviewer applies trivial
fixes itself; this replaces, for trivial fixes only, the 2026-11-19 decision that nothing reaches a rule without
your «так».

### Token spend is counted in units and shown as ordinary items
The scan counts spend in units, not dollars (weights and the weekly limit: [token units and the weekly
limit](../findings/token-weights-and-weekly-limit.md)). A too-long main session (100+ turns) and an Opus coder
subagent become findings with their numbers as evidence; the retro proposes spend rules like any other, never as a
hunt for the biggest spender. A session that spent over 2% of the weekly limit in a day, or wasted over 0.5% in
it (idle wakes, cold restarts, a bloated context), is a critical token problem: Pult's «статус» shows it once and
again only after it grew 1.25 times. Smaller ones go first in the retro's list. Why: owner, 2026-11-19 and 2026-11-20:
a subscription, so money is the wrong measure; the goal is better ways of working, spend is evidence of a pattern.

Known limits: items that happen once are kept and not yet expired; decision items that other projects' retros
reuse are not built (`BACKLOG.md`).

## Acceptance criteria
- A session of a project with a lead ends: its problems reach that project's item folder; one of another folder does not.
- A cause seen in one session waits; seen in a second session, a trivial fix is applied and shows in the weekly list.
- A code bug found in a session is handed to the project as a defect and gets no rule fix.
- A cause in your global rules is handled only in ClaudeDevKit, not asked twice.
- A fix that did not stop the same problem comes back as a disputed item, not a reworded rule.
- A session spends over 2% of the weekly limit in a day: Pult's «статус» shows it once.

## Built in
- `plugins/dev-kit/scripts/retro.py`
- `plugins/dev-kit/bin/dev-kit-retro`
- `plugins/dev-kit/hooks/retro-start.py`
- `plugins/dev-kit/hooks/retro-end.py`
- `plugins/dev-kit/hooks/hooks.json`
- `plugins/dev-kit/skills/retro/SKILL.md`
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `tools/tests/test_retro.py`
