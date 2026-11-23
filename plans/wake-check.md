# Check that Pult does not wake leads for nothing

Status: check (C: Перевірка, що Pult не будить керівників дарма).

Owner «так» 2026-11-23 to the start proposal, P: ClaudeDevKit chat.

Scope: the two «Open» checks of `docs/features/start-leads-at-logon-and-heal-them.md`: (1) from the watcher's logs and transcripts, Pult and a lead with no events show no wakes for a day; one forced GIVEUP gives one push and the fix line in Pult; a push relayed by a live lead (Pult down) reaches the phone; (2) whether `claude attach <id>` to a P still works from a terminal, and the session list wording in the phone app. Fix what fails, or file it as a defect.

The owner's phone: never ask the owner; send P a ПИТАННЯ with one step at a time (what to do, what to look for, answer + or -), P relays. Never stop Pult, its watcher or a real lead: throwaway test sessions only.

Success criterion: each check marked passed or a defect filed with its cause; open items updated.
