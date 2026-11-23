# Sessions resume by themselves after the usage limit resets

Status: build (C: Сесії самі продовжують після ліміту).

Owner's words (2026-11-23, P: ClaudeDevKit chat): «Також Потрібно попрацювать над відновлення роботи після поновлення лімітів, бо зараз сесії чекають поки я щось напишу».

Known: the Pult watcher logs `LIMIT <name> <id> (resets <time>)` and sends the lead a `limited:` event (`plugins/pult/scripts/watch-servers.ps1` ~:543-554); project-lead SKILL.md says a limited C «is alive and goes on after the reset», but nothing wakes it, so it stands until someone writes to it. Applies to every session P or Pult manages (C, discussions, leads); check how the limit stop looks in `plugins/dev-kit/claude-facts.md` and add what you learn through the facts-keeper agent.

Success criterion: after the reset time, a session stopped by the limit is woken with a short «continue» message (once, logged), carries on its task with no owner message, and a lead gets no extra noise; tested on a throwaway session where possible; the skill line made true.
