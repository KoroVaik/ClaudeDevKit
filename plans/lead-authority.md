# Lead authority: the owner as CEO (discussion)

Started 2026-11-15 from the P: ClaudeDevKit chat. This is a discussion first; build nothing without
the owner's yes on a written proposal.

## Owner's words (verbatim)

1. «Давай по іншому. Керівник не пише відразу інфу по сесії, а збирає цю інфу і визначає пріоритети
   які потрібно вирішити першими і інформує по черзі, або запитує. Тоді не буде помийки, просто деякі
   рішення будуть ухвалюватись із запізненням. Звісно критичні айтеми мають публікувать відразу.»
2. «І тут потрібно вирішить які питання має право резолвить керівник без моєї участі. Не здря ж він
   керівник, то нехай керує. А я фактично буду типу CEO який приймає тільки глобальні рішення і те що
   призведе до незворотніх змін (і більш нічого не робитиму, бо CEO зазвичай не лізуть в
   мікроменеджмент.»
3. «Звісно частину цієї ідеї мають перехопить і менеджери, щоб вони мали більше свободи дії в
   контексті їхніх фічів разом із саб менеджерами. Тобто коли менеджер переймає частину обов'язків
   керівника створюючи саб менеджера для своїх потреб.»
4. «Створи саб сесію де ми це обговоримо окремо.»

## Context

- Seen in P: Zhratva, 2026-11-15: within minutes P wrote six messages about three sessions, with
  history and explanations, repeating questions (transcript
  C:/Users/korov/.claude/projects/C--Users-korov-MyRepositories-Zhratva/2d56121f-d0a4-402c-882d-63fdb3b7856e.jsonl).
- P's proposal the owner was answering (not yet accepted): a queue - one question at a time under the
  session's title, «У черзі ще N питань»; critical = the session cannot go on without the owner, a
  session crashed, or a risk to data or money; everything else waits in the queue.
- Rules in force: plugins/dev-kit/skills/project-lead/SKILL.md (P), plugins/dev-kit/skills/manager/SKILL.md
  (the manager, section "Less of the owner's involvement over time" states the plugin's goal),
  the owner's global rules C:/Users/korov/.claude/CLAUDE.md ("Check before you act or agree": an approved
  goal covers the method; ask only a fork that changes what the owner gets, costs money or is hard to undo).
  P-P-C (a manager starting its own sub-sessions) is listed under "Not supported yet" in project-lead.

## Agreed decisions

1. Queue (owner: «Так», 2026-11-15). P collects the owner's questions in a queue and shows them one at
   a time. Only critical items go out at once: a session cannot go on without the owner, a session
   crashed, or a risk to data or money.
2. C asks only P (owner, in the P chat, relayed by P on 2026-11-15: «Ті сесії не повинні мати питань
   до мене, вони знають тіки про керівника і йому задають всі питання», then «Так»). A task session
   never asks the owner in its own chat; it sends every question to P by SendMessage. P decides
   itself or asks the owner and sends the answer back. Replaces the project-lead rule «A decision C
   asks also goes in C's own chat». Weak spot the proposal must cover: C's auto-mode classifier did
   not count the owner's yes relayed by P as approval (see open points).
   Context, built by P itself: sessions made to talk with the owner get the prefix «Обговорення:»
   instead of «C:»; P writes session names exactly as in the app and names new sessions in Ukrainian.
3. Feature talk before the build (owner: «Окей», 2026-11-15). Before each feature P opens an
   «Обговорення:» session with the owner; one session plays analyst and mockup designer (meaning of
   the page plus mockups) and ends in the feature file with acceptance criteria and the approved
   mockup. After the owner's yes, P starts a C that builds it without the owner. Proposed with it and
   not objected to: the style is approved once per project as a design standard; small changes skip
   the talk and go straight to a C. Still open: what counts as a small change.
4. P decides alone within the approved criteria (owner, 2026-11-15, verbatim: «Тіки дійсно критичне.
   Якщо потрібно запустити апі реквест на 10 центів то мене не треба питати про це. Скажем так що
   порогом буде сумарно 1 дол вихід за який і буде причиной повідомить мені»). The owner gets only
   what is truly critical: leaving the approved criteria, an irreversible step, or paid spend over
   $1 in total. Spend under the threshold is not asked. The $1 is counted per task (owner: «Так»).
5. No sub-sessions for a C (owner: «Так», 2026-11-15). Dependent parts of a feature stay in one C,
   which fixes how they fit in the task file and runs parallel subagents. An independent part found
   mid-work goes to P as a new task (the manager's existing new-task rule, now sent to P instead of
   the owner); P decides when to start it. P-P-C stays unsupported; no new mechanics.
6. Triage before a task (owner, 2026-11-15, verbatim: «Давай тоді лишим тип сесії обговорення так
   буде чистіше. Просто поьрібно чітко виявляти ті задачі, які детального обговорення не потребують
   і можуть бути вирішені менеджером, або керівником і менеджером, або в крайньом випадку керфвник
   задасть пару питань мені. І якщо буде більше ніж декілька питань, тоді знову ж таки є сенс для
   створення обговорення окремо.», then «Так» to the threshold). Decision 3 stays: a separate
   «Обговорення:» session; the revision with one C per feature is dropped. P sorts each task: the C
   alone; P and the C; P asks the owner up to 3 text questions through the queue; more than 3, or any
   question about how a screen looks (needs pictures), goes to an «Обговорення:» session. Replaces
   question 7.
7. No permission prompts in C (owner: «Окей», 2026-11-15). A C starts in a mode that asks the owner
   nothing; its normal work is allowed by settings. Actions on an ask-P list (in C's first prompt
   and the manager skill) need P's yes; P asks the owner only for money over the threshold,
   hard-to-undo steps or a product choice. Whatever is costly to get wrong is a hard ban as a deny
   rule in the project's settings, which neither P nor C can lift. Replaces question 10.
8. Taking over a session the owner started (owner: «Так», 2026-11-15). P registers it only after the
   session's first reply; until then it stays under «Сесії, які ти запустив сам» marked
   «ще не під керуванням: сесія не відповіла» (the owner rejected «ще не підтверджено» as unclear).
   One correction line if P's message was held or expired.
9. A taken-over session on main (owner: «Так», 2026-11-15) commits its own work to main after each
   finished step; P does not merge it, so main stays clean and P's merges of other C sessions do not
   wait.

## Proposal (waiting for the owner's yes)

Also covered by the yes, proposed with decision 3 and not objected to: the style is approved once per
project as a design standard; after the build the C checks the result against the feature's criteria
before the owner sees it.

Changes:
- project-lead: queue and critical items (1); P decides alone, $1 per task (4); triage and the
  «Обговорення:» session (3, 6); C asks only P, replacing «A decision C asks also goes in C's own
  chat» (2); the ask-P list, which P answers itself (7); C started with no permission prompts; first
  prompt carries the ask-P list; taking over owner-started sessions with the new label (8); a session
  on main commits itself, P does not merge it (9); P-P-C stays unsupported, an independent part
  comes back as a new task (5).
- manager: questions only to P by SendMessage, never in own chat (2); new task mid-work goes to P
  (5); the ask-P list; check against the feature's criteria before handing in; in an «Обговорення:»
  session it ends with criteria and the approved mockup in the feature file (3).
- Hard bans: P proposes to the owner once per project a set of deny rules in the project's
  settings (push to main where it deploys, deleting data or the owner's database, stopping the
  owner's containers, editing permission settings). Only the owner adds them.
- Plugin version, README and changelog.

Risks:
- No-prompt mode: bypassPermissions is documented for isolated environments; a worktree is not one.
  The deny rules are the lock; the ask-P list holds only by the model's discipline.
- Not checked yet: that `claude` started by P accepts the permission mode flag for a bg session; the
  build checks it on one live start before relying on it.

## Open points to settle with the owner

- The queue and what counts as critical: settled, decision 1.
- What P may decide alone, and what stays with the owner (global direction, irreversible changes, money).
- Question 2 (P decides session questions; owner keeps direction, money, irreversible): settled by
  decisions 3 and 4. Owner's
  answer (verbatim): «Потрібно подумати над детальнішим проробленням аксептанс критеріїв. Бо те що
  затвердить керівник не оьовязково сподобається мені. Гадаю ця проьлема восновному відноситься до
  дизайну юай, але і бек може бути проблемой. Тому треба видумати бізнес аналітика якогось, який
  верифікуватиме фічі, створюватиме нові фічі із списку ідей ітд. Щоб менеджери чітко розуміли
  задачу. Не певен як це лягатиме на поточний флоу». Checked: new-feature step 2 already settles
  the design with the owner (show-idea variants, yes before code), but per task, mid-work. Proposal
  under discussion: an analyst stage before a C starts - acceptance criteria plus UI pictures in the
  feature file, one owner yes; inside that, P and C decide alone; after the build, a check against
  the criteria before the owner sees it.
  Owner's follow-up (verbatim): «Моде варто керівнику надавати мені сесію з дизайнером мокапів і
  бізнес аналітиком, де ми обговорим стиль і сенс сторінки і після затвердження менеджер візьме це в
  роботу? Чи як краще ще можна?». Proposed answer: yes, one «Обговорення:» session per feature that
  plays both roles (discovery-round for the meaning, show-idea mockups for the look) and ends in the
  feature file with criteria and the approved mockup; P then starts a C. Style is fixed once in a
  project design standard, so a page talk covers meaning and layout only. Small changes skip it.
- Revision of decision 3: dropped by the owner (decision 6). Owner (verbatim): «Так керівнтк відкриває мені сесію
  менеджера, і якій я обговорюю мокап і затверджую його, а потім юзаю скіл і потім клір і таким чином
  є всі файли і чистий коньекст менеджера. Єдине чому я хочу так це те, що юагато фічів можуть
  виявитись дрібязковими і буде постійно нова сесія для обговорення...». Checked: project-lead
  "Refresh an overfull C" already does save-handoff plus a fresh C in the same worktree with the same
  name, registered with --predecessor. A manual /clear by the owner would give a new session the
  registry does not know. Proposal: one C per feature; it first talks with the owner (meaning,
  mockups), writes criteria and mockup into the feature file, and after the owner's yes tells P;
  P refreshes it into a clean C that builds. The talk phase is the one exception to decision 2.
  Small changes (question 7, open) skip the talk phase.
- From P (second Zhratva live test): how P takes over a session the owner started himself on main
  with no worktree - the registry accepts it, but the merge flow does not fit.
- From P (same test): whether the owner's yes relayed by P counts as approval for that C - the
  auto-mode classifier refused a C's app start in the main checkout despite the owner's yes relayed
  by P.
- Question 6: settled, decision 5. Discussion kept for the record. Owner (verbatim):
  «Мммм. Облумай як виглядатиме цей флоу в реальності. Чи не буде через керівника іти безкінечний
  потік переписки двох менеджерів?». Checked: project-lead already says dependent tasks go to one C,
  separate C only for independent ones. Dependent parts (backend and screen of one feature) stay in
  one C: it fixes the contract in the task file, then runs parallel coder subagents, which return
  results and do not correspond. An independent part has nothing to discuss with the first C, so P
  gets only its done report. Not proposed now: a sub-C under a C for a huge dependent part (would
  keep the chatter between the two, away from P); revisit if a subagent's context proves too small.
- From P (to discuss): owner decisions do not reach a C through P; C's auto-mode check ignores a yes
  relayed by SendMessage, by design. Seen twice in Zhratva (app.ps1 start in the main checkout; a
  one-line code change). P's proposal: recurring actions allowed once by the owner in the project's
  settings (permission allow rules); a rare risky action asked in C's own chat with AskUserQuestion,
  P gives the owner a link and what to press. Also: P's messages to a session the owner started are
  held and expire because of a permission mode mismatch. Question 10 (open) combines this with the
  first-prompt idea: known approvals go into C's first prompt, recurring ones into allow rules, a
  rare unforeseen one is asked in C's chat (a narrow exception to decision 2).
- From P: Zhratva via P (to discuss, owner's yes to pass it): the owner wants no permission prompts
  in C sessions («the owner presses yes without reading them anyway»). Owner's model: a C has a
  list of actions it may not do without P's permission; P decides itself whether an action needs
  the owner; only P steers a C. P: Zhratva's weak spots: C must start with settings that allow its
  normal work, plus the ask-P list in its first prompt and the manager skill; a few hard bans stay
  in settings neither P nor C can lift (push to main where it deploys, deleting data/ or the
  owner's database, stopping the owner's containers, editing permission settings). Everything else
  on the ask-P list (starting the owner's app, loosening a validation guard, deleting tracked files,
  paid calls over the budget) is P's call. P's note: hard bans as deny rules in settings.
  Checked (code.claude.com/docs/en/permissions): deny rules keep deny-first precedence, even over
  hooks; bypassPermissions skips all prompts except a few built-in ones and is meant for isolated
  environments; dontAsk mode never prompts and denies what is not allowed. So the ask-P list holds
  only by the model following its prompt, not by a lock; whatever is costly to get wrong must be a
  deny rule. This supersedes question 10's «rare ones asked in C's chat».
- From P (to discuss): taking over a session the owner started - register only after delivery is
  confirmed, say «ще не підтверджено» until then, one correction line if the message was held or
  expired, the session stays under «Сесії, які ти запустив сам» until its first reply.
- How a manager (C) gets the same freedom inside its feature, and starts its own sub-sessions.
