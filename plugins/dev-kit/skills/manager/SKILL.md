---
name: manager
description: Use when a development task starts in a project that enables dev-kit - a feature, a bug, a check, a review or a cleanup. Not for pure discovery chat.
---

# Manager

The project's rules are in its `CLAUDE.md`. This skill only routes work; the procedures stay in the
skills below. Read the profile section `## manager` of `.claude/dev-kit.md` first, if it exists:
it adds the project's own skills and subagent types and overrides the defaults here.

The manager is the main session. It owns the decision, the agreement with the owner, small code
changes, the final conclusion, the docs (kept as the `dev-kit:documentation` skill says) and the
commits. Subagents gather, run or change a bounded piece and return; the manager checks the result
before telling the owner.

## A task from the project lead

A session the project lead started (its first prompt names `P: <project>`) hands its finished work to
P, which merges it and closes the session. Its last turn after the "done" report ends with the line
«Готово, керівник зіллє роботу й закриє цю сесію» (in the reply's language) and asks the owner
nothing: the merge is P's step, so the owner sees in this chat why the session closes. Such a session
(a C) works under these rules:

- It never asks the owner in its own chat and does not use `AskUserQuestion`. Every question,
  decision and consent request goes to P by `SendMessage` (P's name is in the first prompt); then it
  waits for P's answer. This covers every step a rule says needs the owner's consent or yes:
  `check-ui`, `check-usability`, `check-look`, the do-it-now yes/no for new work, and the same steps in
  `fix-bug`, `test-change` and the extension plugins (`web-kit`, `unity-kit`). P decides or asks the
  owner.
- It asks P first before: starting the owner's app in the main checkout, loosening a validation or
  safety guard, deleting tracked files, a paid call that would take the task's total past $1 (P also
  lists these in the first prompt). The C keeps a running total of paid spend in its task file; spend
  below $1 is never asked.
- Within the approved acceptance criteria it decides alone. Before handing in, it checks the result
  against the feature's criteria (and the approved mockup, if any) and fixes the gaps.
- An independent part found mid-work goes to P as a new task, in one line. Dependent parts stay in
  this C: it fixes in the task file how the parts fit, then runs parallel subagents. A C never starts
  sessions of its own.
- A hard ban (a deny rule in the project's settings) is never edited or worked around.
- A SendMessage to P that fails with "not reachable" means P is being restarted. The C keeps the
  report and goes on with its work; P asks for missed reports after its restart, and the C then sends
  the report again.
- A session named «Обговорення: ...» is the exception: it talks with the owner directly, settles the
  meaning of the page and the mockups through `dev-kit:discovery-round` and the `show-idea` slot, ends
  with acceptance criteria and the approved mockup in the feature file, reports done to P and builds
  nothing.

A session the owner started that P took over (after the owner's yes) is not a C: it keeps talking with
the owner, P sends it nothing, and P watches it by reading its state. A plugin hook tells it at each
owner message that it is watched and ends with the separate line «Роботу завершено» when fully done. A
session on main (not in a worktree) commits its own work to main after each finished step. P does not
merge it.

Why: the owner decided on 2026-11-15 to be the CEO who takes only global and irreversible decisions;
P is the single channel, so a C's questions do not scatter over its own chat, and a yes P relays is
not lost to a permission check.

## Overlap check at task start

Before any work on a new task, small ones included, check that no other live session of this
repository already does it: the owner may start sessions without the project lead. Skip it when the
task came from the project lead with "P ran the overlap check", and when the session goes on with a
task it already started. Run `dev-kit-sessions others` (Bash tool; if the command is not found,
`python <this plugin>/scripts/sessions.py others`). On `no other sessions` go on. Otherwise launch a
`dev-kit:overlap-checker` subagent (model haiku) with the task in the owner's words, the files or
area it will touch if known, and the project folder. On "no overlap" go on. On an overlap do not
start: tell the owner which session does the same task or touches the same files, and ask whether
to go on anyway, with a recommendation. Exit code 3 (the session list unreadable): say so in one
line and go on.

Why: the owner decided on 2026-11-15 that two sessions must not take the same task unnoticed; the
check reads only session names, first messages, branches and changed files, never code, so it stays
fast.

## Size check first

A small task - a few known places, no design or rule change - skips the `new-feature` and `fix-bug`
chains and the subagents: the manager makes the change itself and keeps what the project's rules
require anyway (checks that fit, docs the change touches, the commit). Anything larger goes through
the tables below. Any edit of rule text, small or not, runs `dev-kit:edit-rules`.

## How routing reads

Route by tables, never by skill or agent descriptions. Read, in this order of weight (later wins):

1. Core slots: `${CLAUDE_PLUGIN_ROOT}/slots.md` (slot -> what the step must do).
2. Each enabled extension's slots: `slots.md` of the sibling plugin folder, e.g.
   `${CLAUDE_PLUGIN_ROOT}/../web-kit/slots.md` (slot -> skill). A plugin without `slots.md` fills
   no slot. If the sibling folder is missing (a plugin copied into the cache), take the extension's
   folder from its `installPath` in `~/.claude/plugins/installed_plugins.json`.
3. The project profile `.claude/dev-kit.md`, section `## Slots`: overrides a slot for this project.
4. The profile section `## manager`: `| Task | Skill |` with the project's own skills and
   `| Type | Model | When | Returns |` with its own subagent types. A project row wins over a
   dev-kit row for the same task.

A slot nobody fills is told to the owner; do not guess a command for it.

## Which skill

| Task | Skill |
|---|---|
| New functionality, a step of a plan in `plans/` (ends with feature, epic and tech docs updated) | `dev-kit:new-feature` |
| Something broken (same docs step) | `dev-kit:fix-bug` |
| Which tests to run for a change, and in which order with the other checks | `dev-kit:test-change` |
| Writing, changing or checking project docs | `dev-kit:documentation` |
| Shaping the product idea, answering numbered questions (accepted rules go to the feature, epic or standard) | `dev-kit:discovery-round` |
| Generating ideas without deciding (ends in `BACKLOG.md` entries) | `dev-kit:brainstorm` |
| Periodic audit of the docs against the `dev-kit:documentation` skill, only on the owner's request | `dev-kit:maintain-project-docs` |
| Moving an existing project's docs onto the `dev-kit:documentation` standard (a dry run first) | `dev-kit:migrate-docs` |
| A public showcase repo for a private project: create it or bring it up to date | `dev-kit:showcase` |
| Prune a project's existing tests or mark old tests with what they protect | `dev-kit:prune-tests` |
| Editing rule text: `CLAUDE.md`, `.claude/`, skills, agents, rule docs, the owner's global rules, notes | `dev-kit:edit-rules` |

| Step | Slot |
|---|---|
| Run the tests a change affects | `run-tests` |
| Start or restart the application for a check | `run-app` |
| Stop what `run-app` started, when the owner says the work is done | `stop-app` |
| Does a scenario work in the running application (needs the owner's consent) | `check-ui` |
| Can an ordinary user reach the goal, what gets in the way (needs consent) | `check-usability` |
| Does it look like the mockup, do the screens hold at the agreed sizes (needs consent) | `check-look` |
| Check the docs against the standard | `check-docs` |
| Show an idea visually while brainstorming | `show-idea` |

## Which subagent type

Always pass the type and `model` explicitly. Built-in types (`general-purpose`, `Explore`, no type)
are blocked by the dev-kit hook: they load every session tool, about 67K tokens of cold start against
15-25K for the types below. When no row fits, tell the owner which role is missing.

A session gets agent types only at its start, so one older than a plugin update may lack a newer type.
If the type is not available, launch the cheapest available dev-kit type whose tools cover the
missing one's (the `tools:` line of `agents/<name>.md` in this plugin's folder; `dev-kit:investigator` covers
the read-only ones), on the model the table gives, with the body of that file as its instructions
before the brief. Tell the owner only if no agent can be launched at all.
Why: the Zhratva lead could not launch `dev-kit:overlap-checker` on 2026-11-15 after a plugin update.

| Type | Model | When | Returns |
|---|---|---|---|
| `dev-kit:investigator` | sonnet | the cause is unknown, or a survey of code needs reading a lot | cause or ranked hypotheses, `file:line`, confirmed vs assumed |
| `dev-kit:reviewer` | sonnet | an independent read-only look at a change, plan, claimed cause or changed feature rules | ranked problems with places, doubts that need a run |
| `dev-kit:coder` | sonnet; opus when the manager passes it for a large or delicate change | a step with a lot of code to read or write | the change, rationale, risks, checks to run |
| `dev-kit:overlap-checker` | haiku | at task start, when `dev-kit-sessions others` lists sessions (see "Overlap check at task start") | "no overlap" or the overlapping sessions with the reason |
| `dev-kit:mechanical-editor` | haiku | a fully specified edit across named files (rename, replace references, move a block) | files and edit counts, skipped places, a Grep proving nothing is left |

The project's own types come from its `## manager` section.

- Do it yourself when the problem is small or the answer is in a few named places. A subagent
  starts cold and rereads the rules; on a small task that costs more than doing it.
- After a `dev-kit:investigator`, read only the places it named before deciding; do not repeat its
  search. Restarts and checks of the running application (the `run-app` slot) the manager runs
  itself, and when the owner says the work is done (or at a handoff) it runs the `stop-app` slot (`dev-kit-app stop` when the
  profile lists commands); a failed check does not end the work. Run `dev-kit-app start` in the background:
  it may wait up to 15 minutes while another session uses the app. On a queue timeout (exit 3) report
  yourself stuck, naming the holder. Always run `stop`, so the next session can start.
- A subagent cannot start other subagents. What it needs from another role, the manager does
  between their turns.
- Continue a subagent that has the context (`SendMessage`) instead of starting a new one.
- Launch line and approval of an expensive model: the owner's global rules.

## A hypothesis before a fix

If the cause is not confirmed, do not propose the fix as the next step. Propose the smallest
check that confirms or disproves it, and only after it the fix.

## Less of the owner's involvement over time

The plugin's main goal is autonomous development: the owner's involvement shrinks step by step.
Decisions on what the owner gets, money (over $1 per task) and hard-to-undo steps stay with the owner. Checks, hand
actions and small questions move to the agents: before asking the owner to check or do something,
look for a way an agent can do it (a test, a headless or emulator run, a script). Where none exists
yet, do the step with the owner and name the missing tool as a follow-up item in the project's plans.

## Long-term quality over speed

The owner cares about the durable result, not how fast a step finishes. When a step needs tooling,
build the proper, reusable piece (a first-class command, validated, documented) instead of a one-off
hack or a throwaway helper, and do not offer the quick hack as the first option. Prefer the data
source and model that stay right at full scale over the one that is merely available today.
This principle chooses the design of what the plan lists. It adds no fixes, steps or review rounds
beyond the plan and the owner's global cap on fix rounds ("One yes per plan"): a reviewer doubt below
the report threshold is recorded, not fixed.

## Say who does the work

Each step of a plan for the owner's yes names its doer in the format of the owner's global rule
"One yes per plan": the manager itself, a subagent (type and model) or the owner. Pick the doer by
cost (the owner's global "Subagents" rule) and the table above. A proposal that is not a plan
carries one real example, as the project's rules say; routine yes/no questions are excepted there.
The owner's global "Chat replies" caps win over this: the example becomes a list item or sits in the
question's brackets, within the same word limits. Never a paragraph outside the list.

## A brief

Give the goal, the success criterion, the known facts (confirmed and assumed, separately), the
files, the exact commands the subagent may run, and what to return. Do not paste the
conversation. The success criterion is a visible result; a check that passes over zero items proves
nothing.

## After a subagent

Check the diff or rerun the check before reporting; a subagent's "done" is not evidence. A
`dev-kit:coder` runs the builds and tests its change needs while it works and fixes what fails, so
test output stays out of the manager's context. The manager runs the verification once, on the
finished work before reporting, and sends failures back to the same subagent. Pass the result
to the owner as a conclusion of at most 3 sentences, not the subagent's full report, inside the
owner's "Chat replies" caps.

## One task in the session

The session does only the task the owner is working on. Work that surfaces on the way (a defect, an
agreed change in another area, an idea) is not started here. It is recorded or proposed as "Where
things go" in the `dev-kit:documentation` skill says: a defect is recorded without asking; a task
becomes an Open item only once the owner has agreed it (until then it is proposed in one line); an
idea the owner has not agreed goes to the project's `BACKLOG.md` (an idea for the plugins goes to the
plugin repo's, see "A change to the plugins themselves"). When the owner raises new work in the middle of
a task, first ask one yes/no: do it now, or record it for later (in a session the project lead
started, the question goes to P, which also takes an independent part as a new task). Offer a session
only after "now". Its subagent reports would otherwise fill this session and bury the owner's task. Example: while
going through open questions the owner decides to remove a tool feature; that is an agreed task, so
it becomes an Open item, and the questions go on.

## A change to the plugins themselves

An agent working outside the plugin repo never edits the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`:
skills, agents, hooks, scripts) directly, not even to fix a process mistake or a plugin defect. It adds
an entry to the plugin repo's own `BACKLOG.md` (not the project's), at
`C:/Users/korov/MyRepositories/ClaudeDevKit/BACKLOG.md`. A session working in that repo decides and
builds the entry, only after the owner's yes. A project's own files (`CLAUDE.md`, `.claude/`) are edited
in the project as before, through `dev-kit:edit-rules`. The agent still fixes its own work in the current task as before; the entry
is only for the plugin rule, and the agent tells the owner (in a P-started session, tells P) in one line that it added one.

Entry format, appended at the end of the file, 2-4 lines under a `##` title:

- `What:` the change wanted.
- `Why:` the concrete case that showed the need (project, date, what went wrong).
- `Cheapest test:` the smallest check that shows the change works.

Commit only that file (`git add BACKLOG.md`; the repo may hold other uncommitted work) and do not push.
Then, if `ListAgents` shows a session named `P: ClaudeDevKit`, send it the entry's title in one line
with `SendMessage`, so it wakes and reviews the entry. With no such session send nothing: that P reads
the backlog when it starts.
A git conflict in it is resolved by keeping both entries.

Why: the owner decided on 2026-11-14 that plugin changes are decided in one place, so a fix made in
one project's session does not bend the process for all the others.

## Quiet about background work

Subagent and session notices are for the manager, not the owner. Never relay an intermediate status
or that work is still running. When and how a result is given: the owner's global rule on background
work. Do not ask first whether to show it. A separate session the owner can open and follow is not relayed while it works or
waits on the owner (the app shows that). When it finishes its task, give one line with the session link and
the outcome (the owner's global rule on background work sets the timing). Never answer with a bare
"nothing waits on you here". Not relaying means no status chatter: the one-line start message of a wait
that blocks the owner's tool (the editor busy, a build) still says what runs and the estimate.
