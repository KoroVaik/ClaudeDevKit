# Slots

Fixed steps of the development process. An extension fills a slot in its own `slots.md`; a project
may override a slot in the `## Slots` section of its `.claude/dev-kit.md`. The manager reads these
tables, never skill descriptions, to find who does a step.

| Slot | What it must do |
|---|---|
| run-tests | Run the automated tests the change affects and report the real result |
| run-app | Start or restart the application so a change can be checked in it |
| stop-app | Stop what the run-app step started, when the owner says the work is done or at a handoff |
| check-ui | Check that a user scenario works in the running application |
| check-usability | Let an ordinary user go after a goal in the running application and report what got in the way |
| check-look | Check how screens look against a mockup or at the agreed screen sizes |
| check-docs | Check the project's docs against the documentation standard |
| show-idea | Show an idea visually during brainstorming |

`run-app` and `stop-app` may each hold several rows in the profile, one command in backticks per row, both written
in start order. `dev-kit-app start` runs the run-app rows in order and stops at the first failure; `dev-kit-app stop`
runs the stop-app rows in reverse and goes on after a failure; `dev-kit-app list` shows both. A project that fills
run-app with a skill or prose follows it by hand, and its teardown too. What a command may stop - the owner's own
processes, a service another launcher started - is decided by the project's helpers, never by the plugin. Every
skill that ran run-app runs stop-app when the owner says the work is done, or before a handoff or the end of the session. While the owner's work on the change continues, the app and its test data keep running between replies and checks, a failed check included; the end of a reply or of one check is not "done".
