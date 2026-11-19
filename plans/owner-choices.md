# What the lead takes to the owner before starting work

Owner (P: ClaudeDevKit chat, 2026-11-19): «Гадаю таке варто обговорити. Бачиш, отже іще раз помилився створюючи відразу сесію імплементації». Earlier: «А чому не обговорили це спочатку чи це поки тестовий варіант?», «схоже потрібні правки до правил внести».

## Cases (2026-11-19, P: ClaudeDevKit)
1. The owner said «Так» to «C: Сповіщення про термінове (на телефон приходять лише важливі події)». P started a build C at once (triage branch 2: «a choice remains inside the approved criteria»), leaving to P and C which events push to the owner's phone. The owner asked why it was not discussed first; P then had the C send the event list, and the owner approved it.
2. P then proposed the rule fix itself as another build C («C: Твій вибір того, що приходить»), again without a discussion; the owner: «таке варто обговорити ... іще раз помилився».

## Questions to settle with the owner
- Which choices P must bring to the owner before a C starts (for example: what the owner receives - messages, notifications, their timing; how a rule changes the lead's behaviour), and which stay with P and C.
- When P proposes a discussion session instead of a build session (triage in plugins/dev-kit/skills/project-lead/SKILL.md, "Before a task: triage").
- Where the rule lives (project-lead triage, dev-kit:manager, the owner's global rules) - run dev-kit:edit-rules steps 1-2 for the proposal.

## Success criterion
The owner approves, in this file, the rule idea and its home. Building happens after that, in a C P starts from this file.

## Owner's approval

Approved 2026-11-19 in «Обговорення: Твій вибір того, що приходить» (owner's «Так» to the list below).

Cause found: the owner's global rules already say an approved goal does not cover a fork that changes
what the owner gets (global CLAUDE.md, "An approved goal ... covers the method"; also
plugins/dev-kit/skills/manager/SKILL.md:168, README.md:9). Triage branch 2 in
plugins/dev-kit/skills/project-lead/SKILL.md:187 («a choice remains inside the approved criteria»)
let P read a «Так» to a task title as approval of what the owner receives.

Approved idea (owner's words in brackets):
1. A feature already agreed: P asks nothing; technical details the agent decides alone («Якщо фіча
   уже погоджена, то звісно що обговорювати нічого», «всякі тех деталі агент сам може вирішить»).
2. What the owner gets is not decided yet (which events reach him, when, how P talks to him): P asks
   before a C starts, up to 3 questions through the queue; a «Так» to a task title does not cover it.
3. Several questions: each worded so the recommended answer is «так», so «так всім» always means
   agreeing with every recommendation; a question that would get «Рекомендую: ні» is turned around
   («Лишаємо як є?» instead of «Міняємо?»).
4. Any doubt from the owner on a question, or more than 3 questions, or a question about how a screen
   looks: P proposes an «Обговорення:» session instead of discussing in P's chat, and starts it only
   after the owner's «так» («краще перепитать, бо я можу помилиться»).
5. Rule change tasks (case 2) follow the same scale: the rule idea is what the owner gets.

Homes (edit-rules steps 1-2):
- Point 3: the owner's global rules, "Chat replies", the "Question" and "Batches of questions"
  bullets (they now allow «Рекомендую: так/ні»); a batch item's recommendation becomes «так» only.
  Global file is outside this repo: the build C edits it through the owner's yes already given.
- Points 1, 2, 4, 5: project-lead SKILL.md "Before a task: triage" - reword branch 2 (exclude what the
  owner gets), branch 3 (doubt → propose discussion), branch 4 (ask before launching). Check
  "Start an «Обговорення:» session" (line ~320) for the launch step, and lines 10, 166-168
  ("within the approved criteria") so they do not contradict the new branch 2.
- Duplicates to keep as is: manager SKILL.md:168, README.md:9 (same idea, already correct).
- Conflict to watch: another C («C: Сповіщення про термінове») edits project-lead SKILL.md now; build
  after it merges.
