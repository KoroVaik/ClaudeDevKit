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

## Size check first

A small task - a few known places, no design or rule change - skips the `new-feature` and `fix-bug`
chains and the subagents: the manager makes the change itself and keeps what the project's rules
require anyway (checks that fit, docs the change touches, the commit). Anything larger goes through
the tables below.

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

| Step | Slot |
|---|---|
| Run the tests a change affects | `run-tests` |
| Start or restart the application for a check | `run-app` |
| Stop what `run-app` started, before the task ends | `stop-app` |
| Does a scenario work in the running application (needs the owner's consent) | `check-ui` |
| Can an ordinary user reach the goal, what gets in the way (needs consent) | `check-usability` |
| Does it look like the mockup, do the screens hold at the agreed sizes (needs consent) | `check-look` |
| Check the docs against the standard | `check-docs` |
| Show an idea visually while brainstorming | `show-idea` |

## Which subagent type

Always pass the type and `model` explicitly. Built-in types (`general-purpose`, `Explore`, no type)
are blocked by the dev-kit hook: they load every session tool, about 67K tokens of cold start against
15-25K for the types below. When no row fits, tell the owner which role is missing.

| Type | Model | When | Returns |
|---|---|---|---|
| `dev-kit:investigator` | sonnet | the cause is unknown, or a survey of code needs reading a lot | cause or ranked hypotheses, `file:line`, confirmed vs assumed |
| `dev-kit:reviewer` | sonnet | an independent read-only look at a change, plan, claimed cause or changed feature rules | ranked problems with places, doubts that need a run |
| `dev-kit:coder` | sonnet; opus when the manager passes it for a large or delicate change | a step with a lot of code to read or write | the change, rationale, risks, checks to run |
| `dev-kit:mechanical-editor` | haiku | a fully specified edit across named files (rename, replace references, move a block) | files and edit counts, skipped places, a Grep proving nothing is left |

The project's own types come from its `## manager` section.

- Do it yourself when the problem is small or the answer is in a few named places. A subagent
  starts cold and rereads the rules; on a small task that costs more than doing it.
- After a `dev-kit:investigator`, read only the places it named before deciding; do not repeat its
  search. Restarts and checks of the running application (the `run-app` slot) the manager runs
  itself, and before the task ends it runs the `stop-app` slot (`dev-kit-app stop` when the
  profile lists commands), also after a failed check.
- A subagent cannot start other subagents. What it needs from another role, the manager does
  between their turns.
- Continue a subagent that has the context (`SendMessage`) instead of starting a new one.
- Launch line and approval of an expensive model: the owner's global rules.

## A hypothesis before a fix

If the cause is not confirmed, do not propose the fix as the next step. Propose the smallest
check that confirms or disproves it, and only after it the fix.

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
idea the owner has not agreed goes to `BACKLOG.md`. When the owner raises new work in the middle of
a task, first ask one yes/no: do it now, or record it for later. Offer a session only after "now".
Its subagent reports would otherwise fill this session and bury the owner's task. Example: while
going through open questions the owner decides to remove a tool feature; that is an agreed task, so
it becomes an Open item, and the questions go on.

## Quiet about background work

Subagent and session notices are for the manager, not the owner. Never relay an intermediate status
or that work is still running. When and how a result is given: the owner's global rule on background
work. Do not ask first whether to show it. A separate session the owner can open and follow is not relayed while it works or
waits on the owner (the app shows that). When it finishes its task, give one line with the session link and
the outcome (the owner's global rule on background work sets the timing). Never answer with a bare
"nothing waits on you here".
