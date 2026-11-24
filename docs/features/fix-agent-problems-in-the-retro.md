# Fix agent problems in the retro

Epic: [Work through a project lead](../epics/work-through-a-project-lead.md)

## Purpose
Each project with a lead learns from its own sessions: problems of agent work are collected with no model, a
background session reviews them with the project's rules in view, fixes the rules itself and reverts what did not
work, and asks you nothing; Pult's «статус» lists what it did. How it runs and its commands: [project lead
tools](../tech/project-lead.md).

## Rules
### The retro catches every problem of agent work, and only that
A project with a lead (its profile has a `## project-lead` section) gets its own retro for its own rules, docs
and profile (an old doc that sends agents to the wrong file is agent work and is fixed there). A bug in the
project's code (a flaky test) is not: it goes to the project as a defect and the retro stops there. A cause in a
plugin's rules (dev-kit, web-kit, unity-kit, pult, rules-kit, spend-kit) or in your global rules
(`C:/Users/korov/.claude/`, chat style included) is handled only by the ClaudeDevKit retro, so two projects never
fix the same thing. Projects with no lead (Pult, KnowledgeBase, a design sandbox) have no retro of their own, but
their sessions are still read for the plugin and global sets: the talk, part and spend findings of every
transcript go to those sets, and their Claude app errors go to ClaudeDevKit ([Keep Claude app
facts](keep-claude-app-facts.md)).
Why: owner, 2026-11-21 and 2026-11-22: the retro fixes the problems of the projects, not only of the plugin, and
stayed in dev-kit (no separate plugin); it did not run on sessions with no dev-kit, since they would give little (the
scans of 2026-11-19..21 named only dev-kit projects). Owner, 2026-11-24: it is now its own plugin, `rules-kit` (the
plugin about rules; dev-kit, web-kit, unity-kit, pult, the owner's global rules and each project's own rules
subscribe to it), reviewed from ClaudeDevKit, and the global rules are checked in the sessions of every project, those
without a lead too.

### Items are local files, one per cause, one folder per rule set
Each finding becomes an item file in a local folder of the rule set it concerns (a plugin, your global rules or a
project's own rules; outside any repository, under the retro folder of the user's `.claude`). The set's subscription
file names the project whose retro handles it, the one where its files are edited (today ClaudeDevKit for the plugins
and your global rules); a run in a project handles only the sets that project reviews. Any session may add an item to
any set's folder, marked with its source; a retro may pass an item to the set's reviewer (rare).
Why: writes into a project's main checkout are blocked for P, items on unmerged branches would be lost, the scan
from ClaudeDevKit would write into other repositories, and two sessions writing one shared file overwrite each other.
One folder per set and not per project: owner, 2026-11-24 («Звучить ок»): web-kit has one folder although it runs in
three projects.

### Collected and started by hooks, no model and no scheduler
A SessionEnd hook scans the ending session's transcript; a SessionStart hook runs the full scan once a day (it
also catches sessions killed by force, which end with no event) and, when new findings wait and the last review is
old enough, starts a background session «Ретро: <project>» that ends after it reports to P.
Why: owner, 2026-11-22: not Pult («його призначення дещо інше»), no Windows scheduled task, a fixed time not
required. Leads never wake by themselves, so a step "started by the lead" would not run while you are silent.

### A fix needs a repeat
A first sighting that is not urgent waits; a fix needs the same cause in a second session or on a second day (a
lead and its own subagents are one session). Lost work and a critical token problem are urgent and fixed at once.
A cause seen once and not again in 2 weeks closes by itself. A cause that is a rule agents ignore is not reworded:
it gets another means (a hook, a check, a script), built by a task session P starts. Every rule fix also removes or
merges something, so the rules do not keep growing; at most 5 fixes land per rule set a week. Why: owner,
2026-11-21: avoid fixes for problems that arose by chance and not through bad rules, skills or agents; the 2-week
expiry: owner, 2026-11-24.

### Two checks replace your yes
Each fix is approved by an independent agent on another model than the one that wrote it (the retro session is a
helper session the owner is not in, so it runs on Sonnet and the approver on Opus; a deleted rule and a change of
what the agent may change itself included), then replayed on past session parts: it lands only if it covers every part where the
problem happened and breaks none of up to 5 parts of the same skill or agent that went well. Each fix is its own
commit. Why: owner, 2026-11-24 («Мінімізуй мою участь, я всеодно буду бездумно апрувать. Краще додай більш надійні
верифікації»). Weak spot accepted: an agent checking an agent may share its blind spots; a bad change to how
sessions talk to you shows only in chat.

### Every change is checked by later sessions and reverted when it failed
Each fix, and each plugin change that alters agent behaviour, is checked by reading the sessions started after it
reached main: worked, did not work or not met yet. A fix that did not work is reverted by the retro itself and gets
one second try by other means; after a second failure it is parked. A new problem in a file a recent fix touched is
linked to that fix as a possible breakage.

### What you see
Nothing is asked. Pult's «статус» shows what the retros did in the last 7 days (fixed, reverted, parked, expired) as
a passive list. Your «поверни ...» to Pult or a lead reverts that change at the next retro run. Each run stops at
2% of the weekly limit and leaves the rest for the next one. Why: owner, 2026-11-24 (`plans/retro-auto-rules-check.md`):
this replaces the weekly «розібрати N пунктів?» question of 2026-11-22.

### Token spend is counted in units and shown as ordinary items
The scan counts spend in units, not dollars (weights and the weekly limit: [token units and the weekly
limit](../findings/token-weights-and-weekly-limit.md)). A too-long main session (100+ turns) and an Opus coder
subagent become findings with their numbers as evidence; the retro proposes spend rules like any other, never as a
hunt for the biggest spender. A session that spent over 2% of the weekly limit in a day, or wasted over 0.5% in
it (idle wakes, cold restarts, a bloated context), is a critical token problem: Pult's «статус» shows it once and
again only after it grew 1.25 times. Smaller ones go first in the retro's list. Why: owner, 2026-11-19 and 2026-11-20:
a subscription, so money is the wrong measure; the goal is better ways of working, spend is evidence of a pattern.

Known limits: decision items that other projects' retros reuse are not built (`BACKLOG.md`).

## Acceptance criteria
- A session of a project with a lead ends: its problems reach that project's own rule set folder; one of another folder does not.
- A cause seen in one session waits; seen in a second session, a fix that the approver and the replay pass lands and shows in Pult's «статус».
- A cause seen once and not again in 2 weeks closes by itself and shows in Pult's «статус».
- No retro step asks you anything.
- A code bug found in a session is handed to the project as a defect and gets no rule fix.
- A cause in your global rules is handled only in ClaudeDevKit, not fixed twice.
- A fix that did not stop the same problem is reverted, tried once more by other means, then parked.
- Your «поверни» about a listed change reverts it at the next retro run.
- A session spends over 2% of the weekly limit in a day: Pult's «статус» shows it once.

## Built in
- `plugins/rules-kit/scripts/retro.py`
- `plugins/rules-kit/scripts/subscriptions.py`
- `plugins/rules-kit/scripts/parts.py`
- `plugins/rules-kit/scripts/talk.py`
- `plugins/rules-kit/scripts/packets.py`
- `plugins/rules-kit/scripts/fixes.py`
- `plugins/rules-kit/agents/part-reader.md`
- `plugins/rules-kit/agents/approver.md`
- `plugins/rules-kit/agents/replayer.md`
- `plugins/rules-kit/templates/global-rules-subscription.md`
- `plugins/rules-kit/bin/rules-kit`
- `plugins/rules-kit/hooks/retro-start.py`
- `plugins/rules-kit/hooks/retro-end.py`
- `plugins/rules-kit/hooks/hooks.json`
- `plugins/rules-kit/skills/retro/SKILL.md`
- `plugins/rules-kit/agents/rule-reviewer.md`
- `plugins/dev-kit/skills/project-lead/SKILL.md`
- `plugins/pult/rules/hub.md`
- `plugins/pult/hooks/hub-rules.py`
- `tools/tests/test_retro.py`
- `tools/tests/test_fixes.py`
- `tools/tests/test_hub_rules.py`
- `tools/tests/test_subscriptions.py`
- `tools/tests/test_parts.py`
