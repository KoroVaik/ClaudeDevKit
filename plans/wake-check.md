# Check that Pult does not wake leads for nothing

Status: done; phone checks left open in the feature (C: Перевірка, що Pult не будить керівників дарма).

Owner «так» 2026-11-23 to the start proposal, P: ClaudeDevKit chat.

Scope: the two «Open» checks of `docs/features/start-leads-at-logon-and-heal-them.md`: (1) from the watcher's logs and transcripts, Pult and a lead with no events show no wakes for a day; one forced GIVEUP gives one push and the fix line in Pult; a push relayed by a live lead (Pult down) reaches the phone; (2) whether `claude attach <id>` to a P still works from a terminal, and the session list wording in the phone app. Fix what fails, or file it as a defect.

The owner's phone: never ask the owner; send P a ПИТАННЯ with one step at a time (what to do, what to look for, answer + or -), P relays. Never stop Pult, its watcher or a real lead: throwaway test sessions only.

Success criterion: each check marked passed or a defect filed with its cause; open items updated.

## Findings (2026-11-23)

- Pult wakes: the log (servers.log, 2026-11-16..23) has one Pult wake ever, the one-time note of 2026-11-20. No Pult event happened since, so no wake: holds.
- Lead wakes: every lead wake in the log has a cause (event restart/stale/limited, or a keep-warm ping for a busy task silent 50 min). No lead had a day with no events, so "no wakes on a quiet day" is shown only by the code path (no event, no ping, no wake).
- DEFECT, fixed here: the watcher looked up the Pult hub by the exact name "Pult", but the hub's session is listed by `claude agents` under a system name ("korov-e9" since the 2026-11-21 restart; see claude-facts "The Remote Control server's own session has a system name"). So Pult counted as down: a GIVEUP would never reach Pult (no fix line) and after 10 min went as a false «Pult не піднявся» push via a lead. The 2026-11-20 note reached it only because the hub had renamed itself then. Fix: the watcher finds the hub by name "Pult" or by home-folder cwd (parent = the hub server) and sends to its real name.
- Lead relay: live once, 2026-11-23 17:27, phone item via P: Zhratva; its PushNotification returned "Terminal notification sent. Mobile push requested." Arrival on the phone: asked the owner via P.
- `claude attach <id>`: works on Claude Code 2.1.330. A throwaway background session was attached from a fresh console and stayed attached (no error); a P is the same kind of background session. The real P was not attached (no touching real leads).
- Forced GIVEUP, 2026-11-23 19:57, throwaway watcher (own config with a dead server row, own state, -MaxHeals 0, worktree code): GIVEUP logged once; the hub was found as "korov-e9" and messages were sent to it (the one-time note first, since the throwaway state had no PultNote; the GIVEUP waited behind it). Not seen as taken: the hub's local transcript (`projects/C--Users-korov/7966c247...jsonl`) has not been written since its 2026-11-21 17:47 restart, and the event id is in no transcript. Open: does the hub get the message at all (asked the owner via P), and where its transcript goes now. Until that, a Pult event is resent 3 times and then pushed as «Pult не піднявся».
- Owner via P, 20:40: the 20:32 test push (lead P: ClaudeDevKit, "Mobile push requested") did not show on the phone; the watcher's 19:57/19:59 messages are not in the Pult chat.
- Push cause, hypotheses: (H1) no push shows while the phone app is open (claude-facts, checked 11-20; the owner was writing to P from the phone at 20:32); (H2) tool pushes stopped arriving after the 11-21 Claude Code update (2.1.330): owner answered "-" to four pushes on 11-23 12:01-12:23 with the app closed. The tool side is clean: "Mobile push requested" means handed to the server; `agentPushNotifEnabled` is on; no hook touches it. Check: app fully closed, one push from P.
- Pult chat cause, hypotheses: the hub's child (pid 12152, `--print --sdk-url ... stream-json`) has run no turn since its 11-21 17:47 start (its session file never went busy). (H1) it holds peer messages for its host: since edf9472 (11-21) wakes are sent in bypassPermissions mode; the 11-20 note went in auto mode and was taken. (H2) such a child never turns a socket message into a turn. Check: P sends "korov-e9" a message and reads the delivery notice; the owner types in the Pult chat and we see whether its transcript moves.
- Confirmed 20:42: P's bypass message to the hub got a delivery notice "held by that session"; a default-mode one-shot message was taken at once, and the hub's transcript shows `permissionMode: auto` (the server runs with bypassPermissions, its session does not). Fixed: the watcher sends Pult's messages (wakes and pushes relayed through Pult) in default mode; leads stay in bypass.
- Final notice to P's ping: "not approved before expiry ... while the two sessions' permission modes differ a resend is only held again". This is the cause of the Pult-chat defect (mode mismatch: hub auto, watcher bypass).
- Test push 2 (app closed, via P, 20:42): "Mobile push requested"; the owner gave no answer. Phone checks stopped on P's word; left as Open items in the feature.
- `claude attach`: passed. Pult wakes: passed. Lead quiet day, phone push arrival, Pult chat arrival, phone list wording: Open in the feature.

Spend: ~0.4% of the weekly limit, estimate; API: 0 USD
