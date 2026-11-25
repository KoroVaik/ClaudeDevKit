# How the owner reviews a built screen

Status: built (dev-kit 0.1.132, web-kit 0.4.3).

Spend (build): ~0.3% of the weekly limit, estimate; API: 0 USD.

Owner's words in P: Zhratva, relayed by P: Zhratva on 2026-11-25: «Не дуже мені подобається те що через керівника я буду обговорювать мокап.... давай обговорення як це краще вирішить». Owner «Так» in P: ClaudeDevKit to starting this talk.

Today: dev-kit:project-lead, «Build a designed screen», steps 2-4: after a C builds a screen, P puts a «так» / «є питання» question in its queue and shows shots of the built screen next to the mockup in P's chat; «є питання» starts an «Обговорення:» for the polish.

Example: Zhratva «C: Причини відповідей у Перевірці» built screens; P: Zhratva sent 6 shots and the question; the owner does not want to judge them through the lead. That branch waits unmerged in Zhratva; read only, never message Zhratva sessions (P: ClaudeDevKit relays the outcome to P: Zhratva).

Success criterion: the owner's «так» to the short plan, with the agreed points written in «Owner's approval» below.

## Owner's approval

Owner «Так. Це найкращий варіант. Керівник дає дозвіл чайлд сесія спілкуваться», 2026-11-25, to: the review moves to a new «Обговорення:» session, the C that built the screen makes the fixes, P shows only the launch line. Accepted weak spots: a new session for every built screen, even when the owner just says «так»; the C's context grows with each fix.

Agreed points for the builders (dev-kit:project-lead «Build a designed screen» steps 2-4, the picture line in «Message templates» about the «так» / «є питання» check, `messages.md`, dev-kit:manager for the C side):

1. On the C's done report for a designed screen, P does not put the «так» / «є питання» question or the shots in its own queue or chat. P starts an «Обговорення: <feature>» session for the review and writes in its own chat only the launch line «Відкрий сесію «Обговорення: <feature>» - там обговориш усе по задачі.».
2. P does not stop the C. P sends the C a `ВКАЗІВКА` that grants «May message: «Обговорення: <feature>»» and says: wait for fixes from that session. The discussion's first prompt names the C session, the feature file and where the C's shots and mockup are; it may message that C.
3. The discussion shows the built screen's shots next to the mockup (one picture per state, as the owner's global picture rules say) and asks «так» / «є питання».
4. The owner's remarks: the discussion passes them to the C by SendMessage with his words and what to change. The C fixes on its own branch, runs its checks of the look as in step 1 of «Build a designed screen», and sends new shots next to the mockup back to the discussion, which shows them. This repeats until the owner's «так».
5. On the owner's «так» to the result: the discussion updates the feature file's «Approved design» if a remark changed it, then sends P its `ЗАКРИТО` (after the usual short plan and its «так»). P merges the C's branch as in step 3 of «Build a designed screen» and closes both sessions.
6. When the C's context gets too full during the fixes, P refreshes it as in «Refresh an overfull C»; the new C gets the same «May message» line and P tells the discussion its name.
