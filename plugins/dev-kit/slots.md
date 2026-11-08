# Slots

Fixed steps of the development process. An extension fills a slot in its own `slots.md`; a project
may override a slot in the `## Slots` section of its `.claude/dev-kit.md`. The manager reads these
tables, never skill descriptions, to find who does a step.

| Slot | What it must do |
|---|---|
| run-tests | Run the automated tests the change affects and report the real result |
| run-app | Start or restart the application so a change can be checked in it |
| check-ui | Check that a user scenario works in the running application |
| check-layout | Check how screens look against a mockup or at the agreed screen sizes |
| check-docs | Check the project's docs against the documentation standard |
| show-idea | Show an idea visually during brainstorming |
