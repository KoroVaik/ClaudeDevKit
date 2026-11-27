---
name: manager
description: Use when a development task starts in a project that enables dev-kit - a feature, a bug, a check, a review or a cleanup. Not for pure discovery chat.
---

# Manager

The project's rules are in its `CLAUDE.md`. This skill only routes work; the procedures stay in the
skills below. Read the profile section `## manager` of `.claude/dev-kit.md` first, if it exists:
it adds the project's own skills and subagent types and overrides the defaults here.

The Manager is the main session. It owns the decision, the agreement with the owner, small code
changes, the final conclusion, the docs (kept as the `dev-kit:documentation` skill says) and the
commits. Subagents gather, run or change a bounded piece and return; the Manager checks the result
before telling the owner.

## A task from the project lead

A session the project lead started (its first prompt names `L: <project>`; an older Lead writes `P: <project>`) hands its finished work to
the Lead, which merges it and closes the session. Its last turn after the "done" report ends with the line
«Готово, Lead зіллє роботу й закриє цю сесію» (in the reply's language) and asks the owner
nothing: the merge is the Lead's step, so the owner sees in this chat why the session closes. Such a session
(a Manager) works under these rules:

- It never asks the owner in its own chat and does not use `AskUserQuestion`. Every question,
  decision and consent request goes to the Lead by `SendMessage` (the Lead's name is in the first prompt); then it
  waits for the Lead's answer. This covers every step a rule says needs the owner's consent or yes:
  `check-ui`, `check-usability`, `check-look`, the do-it-now yes/no for new work, and the same steps in
  `fix-bug`, `test-change` and the extension plugins (`web-kit`, `unity-kit`). The Lead decides or asks the
  owner. A screen's approved mockup already gives the consent for its checks (`dev-kit:test-change`).
- The owner sees every Manager in the Claude app and may write in its chat. A message there that is not from
  another session (not a cross-session message, not a subagent or tool notice) is the owner's: the Manager
  follows it as an instruction for its task, as it would the Lead's `ВКАЗІВКА`, and at once sends the Lead a
  `ВЛАСНИК ВІДПОВІВ` message with the owner's words verbatim. It answers the owner in its chat in short,
  under the owner's chat rules, and still asks him nothing: a question goes to the Lead as above, and a step on
  the ask-the-Lead list below still waits for the Lead's yes. Why: owner, 2026-11-24 («Discuss: Видимість сесій
  Manager», `plans/c-session-visibility.md` of the plugin repo).
- It asks the Lead first before: starting the owner's app in the main checkout, loosening a validation or
  safety guard, deleting tracked files, a paid API call (`spend-kit-api`) that would take the task's API
  total past 1 USD (the Lead also lists these in the first prompt). The Manager keeps the task's spend line in its
  task file (see "Stating the cost of work"); API spend below 1 USD and subscription use are never asked.
- Within the approved acceptance criteria it decides alone. Before handing in, it checks the result
  against the feature's criteria (and its «Approved design», if any) and fixes the gaps.
- An independent part found mid-work goes to the Lead as a new task, in one line. Dependent parts stay in
  this Manager: it fixes in the task file how the parts fit, then runs parallel subagents. A Manager never starts
  sessions of its own.
- A hard ban (a deny rule in the project's settings) is never edited or worked around. A Manager never writes
  a ban or `.claude/hard-bans.json`; the Lead (or the Pult hub when no Lead runs) writes that file and adds it with
  `dev-kit-bans add-approved` on the owner's «так»; removing a ban stays the owner's.
- It sends a message only to its own Lead (this limits messages to sessions, not to its own subagents). Another session
  only when its first prompt, or a later `ВКАЗІВКА` from the Lead, names it in a line «May message: <sessions>». A
  Manager so allowed to message a review session of its screen follows that session's `ВКАЗІВКА` as the Lead's and
  replies to it with a `ВІДПОВІДЬ` (`dev-kit:project-lead`, "Build a designed screen").
- Every message to the Lead starts with its kind word (`ГОТОВО`, `ПИТАННЯ`, `ЗАСТРЯГ`, `ЧЕКАЮ`, `ПРОДОВЖУЮ`,
  `ВІДПОВІДЬ`, `ВЛАСНИК ВІДПОВІВ`), as `${CLAUDE_PLUGIN_ROOT}/messages.md` sets.
- A wait of more than 1 minute on something other than the Lead or the owner (low memory, a retry timer, a
  store cool-off, another session, the app queue), with the Manager itself idle (not its own build, test run or
  subagent), is not "stuck": once it sees such a wait the Manager sends the Lead `ЧЕКАЮ` with
  the reason in plain words and the time it resumes, if known (`ЧЕКАЮ - мало пам'яті для запуску
  застосунку, повтор о 14:30`), and `ПРОДОВЖУЮ` when it goes on. A wait for the Lead's answer is not one.
  Why: owner, 2026-11-23 (Zhratva): a Manager reported a 30-minute retry wait and the Lead still showed it as
  `працює`; «сесія не застрягла, а просто очікує на щось, то так і писати з причиною очікування».
- A SendMessage to the Lead that fails, with any error (the known ones: `plugins/dev-kit/claude-facts.md`, "A send to a
  stopped session fails at the sender and is not queued"), usually means the Lead is being restarted (about 10 seconds). The Manager keeps the message,
  goes on with its work and retries by itself: it starts `sleep 60` as a background command (never a
  foreground wait) and sends the message again when that ends, up to three retries. After the third
  failed retry it stops retrying, keeps the message and sends it, as a message of its own, right before
  its next message to the Lead or when the Lead next writes to it. This holds for every kind a Manager sends the Lead. The Lead sends no resend request after a restart.
  Why: owner, 2026-11-23 (`plans/restart-notice.md` of the plugin repo): a warning before the restart
  misses the silent restart and costs every session a turn.
- A session named «Discuss: ...» is the exception: it talks with the owner directly and builds
  no product code; how it works and ends is in `dev-kit:project-lead`, "Start a «Discuss:» session".
- A background session named «Retro: <project>» is started by a rules-kit hook, not by the Lead, and follows
  `rules-kit:retro`; it never talks with the owner and sends its Lead only one `ГОТОВО` (never a `ПИТАННЯ`).
  The weekly «Docs: <project>» session, started by a dev-kit hook, follows `dev-kit:maintain-project-docs`,
  "Weekly background run", and sends its Lead only one `ГОТОВО`.

A session the owner started that the Lead took over (after the owner's yes) is not a Manager: it keeps talking with
the owner, the Lead sends it nothing, and the Lead watches it by reading its state. A plugin hook tells it at each
owner message that it is watched and ends with the separate line «Роботу завершено» when fully done. A
session on main (not in a worktree) commits its own work to main after each finished step. The Lead does not
merge it.

Why: the owner decided on 2026-11-15 to be the CEO who takes only global and irreversible decisions;
the Lead is the single channel, so a Manager's questions do not scatter over its own chat, and a yes the Lead relays is
not lost to a permission check.

## Overlap check at task start

Before any work on a new task, small ones included, check that no other live session of this
repository already does it: the owner may start sessions without the project lead. Skip it when the
task came from the project lead with "the Lead ran the overlap check" (an older Lead writes "P ran the overlap check"), and when the session goes on with a
task it already started. Run `dev-kit-sessions others` (Bash tool; if the command is not found,
`python -X utf8 <this plugin>/scripts/sessions.py others`). On `no other sessions` go on. Otherwise launch a
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
chains and the subagents: the Manager makes the change itself and keeps what the project's rules
require anyway (checks that fit, docs the change touches, the commit). Anything larger goes through
the tables below. Any edit of rule text, small or not, runs `rules-kit:edit-rules`.

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
| Periodic audit of the docs against the `dev-kit:documentation` skill, on the owner's request (the weekly background run starts by itself) | `dev-kit:maintain-project-docs` |
| Moving an existing project's docs onto the `dev-kit:documentation` standard (a dry run first) | `dev-kit:migrate-docs` |
| A public showcase repo for a private project: create it or bring it up to date | `dev-kit:showcase` |
| Prune a project's existing tests or mark old tests with what they protect | `dev-kit:prune-tests` |
| Editing rule text: `CLAUDE.md`, `.claude/`, skills, agents, rule docs, the owner's global rules, notes | `rules-kit:edit-rules` |

| Step | Slot |
|---|---|
| Run the tests a change affects | `run-tests` |
| Start or restart the application for a check | `run-app` |
| Stop what `run-app` started, when the owner says the work is done | `stop-app` |
| Does a scenario work in the running application (needs the owner's consent) | `check-ui` |
| Can an ordinary user reach the goal, what gets in the way (needs consent) | `check-usability` |
| Does it look like the mockup, do the screens hold at the agreed sizes (needs consent) | `check-look` |
| Check the docs against the standard | `check-docs` |
| Show an idea or a screen's design visually (brainstorming, a feature's mockup, polish) | `show-idea` |

## Which subagent type

Always pass the type and `model` explicitly. Built-in types (`general-purpose`, `Explore`, no type)
are blocked by the dev-kit hook: they load every session tool, a far larger cold start than the types below
(`plugins/dev-kit/claude-facts.md`, "Built-in agent types load every session tool"). When no row fits, tell the owner which role is missing.

A session may lack a type added by a plugin update after its start (`plugins/dev-kit/claude-facts.md`, "A running session sees a new agent or skill only after `/reload-plugins`").
If the type is not available, launch the cheapest available dev-kit type whose tools cover the
missing one's (the `tools:` line of `agents/<name>.md` in this plugin's folder; `dev-kit:investigator` covers
the read-only ones), on the model the table gives, with the body of that file as its instructions
before the brief. Tell the owner only if no agent can be launched at all.
Why: the Zhratva lead could not launch `dev-kit:overlap-checker` on 2026-11-15 after a plugin update.

| Type | Model | When | Returns |
|---|---|---|---|
| `dev-kit:investigator` | opus (reasoning low, from its file) | the cause is unknown, or a survey of code needs reading a lot | cause or ranked hypotheses, `file:line`, confirmed vs assumed |
| `dev-kit:reviewer` | sonnet | an independent read-only look at a change, plan, claimed cause or changed feature rules | ranked problems with places, doubts that need a run |
| `dev-kit:coder` | sonnet; opus only after a sonnet run of this step failed, with the one-line reason in the launch line | a step with a lot of code to read or write | the change, rationale, risks, checks to run |
| `dev-kit:overlap-checker` | haiku | at task start, when `dev-kit-sessions others` lists sessions (see "Overlap check at task start") | "no overlap" or the overlapping sessions with the reason |
| `dev-kit:question-reader` | haiku | the project lead, before it first writes new questions to the owner in full (`dev-kit:project-lead`, "The reader check") | per question `ok`, or the flagged words and a plain rewrite |
| `dev-kit:mechanical-editor` | haiku | a fully specified edit across named files (rename, replace references, move a block) | files and edit counts, skipped places, a Grep proving nothing is left |
| `dev-kit:core-engineer` | fable (in its file) | only in a project whose profile has a `## core-engineer` section, and only after the owner's yes for that launch (see "A core engineer and its helpers") | the change or an approach described without code, its rationale, risks, checks to run, helper questions |

The project's own types come from its `## manager` section.

spend-kit's hook on every helper launch may change the model you pass; pass it as usual
(`docs/features/catch-wasted-work.md` in the plugin repo). For `dev-kit:coder`, `dev-kit:reviewer` and
`rules-kit:rule-reviewer` it sets the model and reasoning of its running experiment, unless you chose a model other
than the one in the table. A choice of Opus or Fable for a helper whose work fills a large context but is not hard
(overlap checks, question reads, mechanical edits, part reads, replays) goes back to the helper's own model. Why:
owner, 2026-11-27 (`plans/limit-spend.md`, points 8 and 13): «Не хочу мікроменеджити опус і сонет».

- Do it yourself when the problem is small or the answer is in a few named places. A subagent
  starts cold and rereads the rules; on a small task that costs more than doing it.
- After a `dev-kit:investigator`, read only the places it named before deciding; do not repeat its
  search. Restarts and checks of the running application (the `run-app` slot) the Manager runs
  itself, and when the owner says the work is done (or at a handoff) it runs the `stop-app` slot (`dev-kit-app stop` when the
  profile lists commands); a failed check does not end the work. Run `dev-kit-app start` in the background:
  it may wait up to 15 minutes while another session uses the app. On a queue timeout (exit 3) report
  yourself stuck, naming the holder. Always run `stop`, so the next session can start.
- A subagent cannot start other subagents (`plugins/dev-kit/claude-facts.md`, "A subagent cannot start other subagents"). What it needs from another role, the Manager does
  between their turns.
- Continue a subagent that has the context (`SendMessage`) instead of starting a new one.
- Launch line and approval of an expensive model: the owner's global rules.

## A core engineer and its helpers

A project whose profile has a `## core-engineer` section (its core areas, what the engineer reads first and
never does there) may use `dev-kit:core-engineer` for one hard, bounded subproblem in those areas.

- When: only after a `dev-kit:investigator` could not find the cause with confidence, or two fix attempts
  failed, unless the profile section says otherwise. Every launch, a test launch and a fresh run after a
  finished one included, needs the owner's yes for that launch (a Manager asks the Lead). A continuation of the same run
  by `SendMessage` (helper answers, check results, the go-ahead below) needs none.
- Brief: as in "A brief", plus what the investigator and the failed attempts found, and a short `<task>`
  name for its note files.
- A continuation after more than an hour is cold and costly: start a fresh run from the engineer's handoff
  note instead (a new launch, so a new yes). Near about 85% of its context window, tell it to write the note
  and stop (the owner's global rules on Fable subagents).
- A new approach or an architecture change comes back described without code. Check it, get the owner's
  yes, then send the go-ahead to the same run by `SendMessage` within the hour while its cache is warm.
- Helper questions: for each, launch a `dev-kit:investigator` (haiku for a lookup, its own model for a cause) with
  the question and a note file `.claude/helper-notes/<task>-<n>.md`; it writes there only its conclusions,
  about 2k tokens at most, never raw logs or results, and returns only the path. Read none of the note
  yourself; send the engineer only the paths. The folder keeps a `.gitignore` of `*`, so notes are never
  committed; a worktree's notes go with it.
- If the type is missing in the session, launch no stand-in (it would lack the 1-hour cache): ask the
  owner (a Manager asks the Lead) to run `/reload-plugins` or start a new session.

Why: owner, 2026-11-23 (Zhratva «Discuss: Інженер ядра аналізу»): projects need Prishch's core engineer,
shared from dev-kit with project tuning, and helpers whose results pass as file paths so neither the
session's nor the engineer's context fills with side research.

## A hypothesis before a fix

If the cause is not confirmed, do not propose the fix as the next step. Propose the smallest
check that confirms or disproves it, and only after it the fix.

## Less of the owner's involvement over time

The plugin's main goal is autonomous development: the owner's involvement shrinks step by step.
Decisions on what the owner gets, API money (over 1 USD per task) and hard-to-undo steps stay with the owner. Checks, hand
actions and small questions move to the agents: before asking the owner to check or do something,
look for a way an agent can do it (a test, a headless or emulator run, a script). When the owner
handed the session the task, data work is not his: labelling, spot-checking rows or settling disputes
over data goes to independent agents (a second labeller on another model, an arbiter); what they leave
open the session decides, and a Manager sends it to the Lead. Only a label that is really a product choice goes to
the owner as a question. Where no agent way exists yet for another step, do it with the owner and name the missing tool
as a follow-up item in the project's plans. Why: owner, 2026-11-24 (Zhratva, «M: Переробка ядра
аналізу»): a design had the owner check 60 random labels; «Які нафіг 60?! Мені зайнятись нічим?!».

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
"One yes per plan": the Manager itself, a subagent (type and model) or the owner. Pick the doer by
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
test output stays out of the Manager's context. The Manager runs the verification once, on the
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
started, the question goes to the Lead, which also takes an independent part as a new task). Offer a session
only after "now". Its subagent reports would otherwise fill this session and bury the owner's task. Example: while
going through open questions the owner decides to remove a tool feature; that is an agreed task, so
it becomes an Open item, and the questions go on.

## A change to the plugins themselves

An agent working outside the plugin repo never edits the plugins (`dev-kit`, `web-kit`, `unity-kit`, `pult`:
skills, agents, hooks, scripts) directly, not even to fix a process mistake or a plugin defect (one exception: the
project's own kit, below). It adds
an entry to the plugin repo's own `BACKLOG.md` (not the project's), at
`C:/Users/korov/MyRepositories/ClaudeDevKit/BACKLOG.md`. A session working in that repo decides and
builds the entry, only after the owner's yes. A project's own files (`CLAUDE.md`, `.claude/`) are edited
in the project as before, through `rules-kit:edit-rules`. The agent still fixes its own work in the current task as before; the entry
is only for the plugin rule, and the agent tells the owner (in a Lead-started session, tells the Lead) in one line that it added one.

Entry format, appended at the end of the file, 2-4 lines under a `##` title:

- `What:` the change wanted.
- `Why:` the concrete case that showed the need (project, date, what went wrong).
- `Cheapest test:` the smallest check that shows the change works.

Commit only that file (`git add BACKLOG.md`; the repo may hold other uncommitted work) and do not push.
Send no message to `L: ClaudeDevKit`: it finds entries with no `Verdict:` line itself
and names them to the owner (`dev-kit:project-lead`, "Plugin backlog").
A git conflict in it is resolved by keeping both entries.

Why: the owner decided on 2026-11-14 that plugin changes are decided in one place, so a fix made in
one project's session does not bend the process for all the others. No message, since 2026-11-19: the Lead
finds the entries itself, and a session messages only its own Lead (owner, 2026-11-21).

### Exception: a project's own kit plugin

Any session (Lead, Manager, «Discuss:») of a project whose `.claude/settings.json` enables `web-kit` or `unity-kit`
changes and releases that kit itself (`plugins/web-kit` or `plugins/unity-kit` in
`C:/Users/korov/MyRepositories/ClaudeDevKit`), with no `BACKLOG.md` entry and no message to L: ClaudeDevKit. Only
the kit the project enables. dev-kit, pult, rules-kit, spend-kit and the repo's shared files
(`.claude-plugin/marketplace.json`, `tools/`, `docs/` outside the kit's own feature text) stay with the backlog above.

1. Make a fresh worktree of ClaudeDevKit's main (`git worktree add`, one branch per change), never the main checkout
   (`plugins/dev-kit/claude-facts.md`, "The host's worktree guard blocks writes to the main checkout from another worktree").
2. Read ClaudeDevKit's `CLAUDE.md` and `.claude/dev-kit.md` first. Edit rule text through `rules-kit:edit-rules`; a
   script change goes to a `dev-kit:coder` (sonnet), its brief naming the worktree's path.
3. Run the repo checks there: `python -I -X utf8 tools/lint.py` and `python -I -X utf8 -m unittest discover tools/tests`
   (that repo's `README.md`, "Develop").
4. A `rules-kit:rule-reviewer` (sonnet) reviews the diff (steps 5-6 of `rules-kit:edit-rules`); its confident problems
   are fixed before the merge.
5. Bump `plugins/<kit>/.claude-plugin/plugin.json` and add the release mark to `plugins/<kit>/releases.json`, as that
   repo's `.claude/dev-kit.md` says.
6. Commit, rebase on a newer main if there is one, merge `--ff-only` into ClaudeDevKit's main, push (that repo pushes
   on its own) and remove the worktree. If the main checkout is not on `main`, has uncommitted changes, or the
   merge still refuses after one rebase, do not merge: tell the owner in one line (a Manager tells its Lead). L: ClaudeDevKit does not check the change afterwards; the Pult watcher
   restarts the leads that enable the kit as for any release.
7. Run `/reload-plugins` so the change works in the same talk (`plugins/dev-kit/claude-facts.md`, "A running session
   sees a new agent or skill only after `/reload-plugins`"); if it does not take, tell the owner in one line (a
   Manager tells its Lead).

A kit change that needs a dev-kit change (a slot in `plugins/dev-kit/slots.md`, a dev-kit skill, agent or command it
relies on, a profile-section doc) lands as above only if the kit part works without it; the dev-kit part is a
`BACKLOG.md` entry as above. The session's own task rules still hold (a Manager stays within its task and asks its
Lead what its rules send there).

Why: owner, 2026-11-26 («Discuss:» on direct kit edits, `plans/kit-direct-edits.md` of the plugin repo): «в
обговорення тих проектів я часто потребую апдейта відразу, а сесії починають спілкуватись одна з іншой фактично
втрачаючи контекст нашой розмови»; the review before the merge replaces L: ClaudeDevKit's check afterwards.

## Claude API calls

An agent (main session or subagent) calls the paid Claude API only through `spend-kit-api call`, never by
`curl`, a fetch tool or its own script, so each call leaves a spend line in the one local log
(`spend-kit-api report` sums it). A project's own program that calls the API from its single call point
appends the same line itself (format: the docstring of `scripts/api_client.py` in the spend-kit plugin; rules: `docs/features/log-and-reconcile-api-spend.md` in the plugin repo).
The call needs the project's own API key in env `DEV_KIT_API_KEY` and its Console name (`--key-name` or env
`DEV_KIT_API_KEY_NAME`). Never set `ANTHROPIC_API_KEY` in an agent's environment: a headless `claude -p` would
then bill that key with no log line (`plugins/dev-kit/claude-facts.md`, "A headless `claude -p` bills
`ANTHROPIC_API_KEY` if it is set"); without it, `claude -p` is not such a call.
Deny rules back this where the owner added them. Why: owner, 2026-11-21 (`docs/features/log-and-reconcile-api-spend.md` in the plugin
repo): the API credit was spent unseen by one project's keys; every call is to be logged and reconciled weekly.

## Stating the cost of work

Work on the owner's subscription (sessions, subagents, `claude -p` on the subscription login) is not billed
in money: a report or plan states its cost as a share of the owner's weekly subscription limit, marked as an
estimate, never in USD: «~2% тижневого ліміту, оцінка» (in English «~2% of the weekly limit, estimate»). The
figure comes from `spend-kit session` (the session that runs it and its subagents; `--id` or `--path` for
another). Its uncertainty, about a third, is carried by the word «оцінка», not by a number. Claude Code's own
USD figure (`/cost`, `costUSD` in session records) is never quoted, labelled or
not (`plugins/dev-kit/claude-facts.md`, "Claude Code's own USD figure prices tokens at API rates"). Real money, calls through `spend-kit-api`, stays in USD; a report with both writes them apart: «~1%
тижневого ліміту, оцінка; API: 0.40 USD». A task file's spend line takes the same form: `Spend: ~N% of the
weekly limit, estimate; API: N USD`. Finished plans keep their old lines.

Why: owner, 2026-11-21 (`docs/features/state-cost-as-a-share-of-the-weekly-limit.md` in the plugin repo): the retro counts tokens closely enough to state cost as a
share of the subscription, and an API-priced dollar figure is not what the subscription costs.

## Quiet about background work

Subagent and session notices are for the Manager, not the owner. Never relay an intermediate status
or that work is still running. When and how a result is given: the owner's global rule on background
work. Do not ask first whether to show it. A separate session the owner can open and follow is not relayed while it works or
waits on the owner (the app shows that). When it finishes its task, give one line with the session link and
the outcome (the owner's global rule on background work sets the timing). Never answer with a bare
"nothing waits on you here". Not relaying means no status chatter: the one-line start message of a wait
that blocks the owner's tool (the editor busy, a build) still says what runs and the estimate.
