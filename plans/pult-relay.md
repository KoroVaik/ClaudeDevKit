# Pult passes the owner's project requests to that project's Lead

Status: started 2026-11-27 by L: ClaudeDevKit.

## Task

On 2026-11-27 the owner pasted a request into the Lead's chat that started «Від Pult: ...» (a plugin change for
L: ClaudeDevKit). He asked: «Чому пульт не спілкується з тобой напряму?». The Lead's question, answered «Так»: «навчити
Pult самому передавати такі доручення Lead, без тебе? (не треба буде пересилати вручну)».

Found by the Lead: `plugins/pult/rules/hub.md` has no step for sending a request to a Lead; Pult only exchanges watcher
events and push requests. Pult, leads and task sessions all run in bypassPermissions, and delivery between two such
sessions works (`plugins/dev-kit/claude-facts.md`, "A message between sessions in different permission modes may be held").

## What to build

- Pult (hub rules): when the owner asks Pult for work that belongs to a project with a live Lead (a plugin change goes
  to L: ClaudeDevKit), Pult sends that Lead the request by SendMessage, with the owner's words verbatim, and tells the
  owner in one line that it passed it on. Lead down: Pult says so and keeps the old way.
- The Lead (project-lead skill and `plugins/dev-kit/messages.md`): a new message kind for such a relay, carrying the
  owner's verbatim words. The Lead treats it as the owner's request (triage as usual), never as the owner's approval
  of a pending question or a hard-to-undo step; anything that needs his yes still goes to the queue. Mind the trust
  rule: a peer message is not the owner; weigh how Pult proves the words are the owner's (verbatim quote, Pult's own
  chat) and say in this file what risk stays.
- Rule edits follow `rules-kit:edit-rules`; bump pult and dev-kit with release marks. Two other task sessions may
  bump pult too: rebump on top of main.

## Success criterion

A request the owner gives Pult for ClaudeDevKit reaches L: ClaudeDevKit as one message of the new kind with his words
verbatim, and the Lead acts on it with no owner relay; an approval cannot be passed this way.

## How it was built (Manager)

- Fact that changed the design: the Pult hub's session runs in auto mode, not bypassPermissions
  (`plugins/dev-kit/claude-facts.md`, "A bypassPermissions sender's message to a Remote Control server's session is
  held"); a send from it to a bypassPermissions Lead is unchecked. So Pult does not use its own SendMessage: it runs
  `plugins/pult/scripts/send-to-lead.ps1`, the same one-shot bypassPermissions `claude -p` sender the watcher reaches
  the leads with every day (`Send-Wake`, moved unchanged into `plugins/pult/scripts/send-lib.ps1`).
- Checked: a live send through `Send-Wake` to this session (bypassPermissions, background) arrived verbatim, quotes
  included. Not checked: a real relay from the running Pult hub (it needs the owner to ask Pult; first use is the test).
- New kind `ДОРУЧЕННЯ` (`plugins/dev-kit/messages.md`); Pult rule `hub.md` "Passing work to a lead"; Lead rule
  project-lead "A request passed by Pult".
- Trust, the risk that stays: the message arrives from a one-shot sender, so its sender name does not prove Pult sent
  it, and any session could write a `ДОРУЧЕННЯ`. Bounds: it only starts triage (a small task may start a Manager with
  no owner yes, as an owner request would); it never answers a queue item or approves anything; the Lead's line
  «Від Pult: ...» shows the owner what was taken, so he can stop it. The Lead sends Pult no reply (held in auto mode).

Spend: ~0.3% of the weekly limit, estimate; API: 0 USD
