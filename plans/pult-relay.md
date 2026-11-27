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
