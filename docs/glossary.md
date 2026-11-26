# Glossary

One name per concept. Chat, docs, skills, agent files and UI text use these names. The names are
approved by the owner on 2026-11-19.

| Name | Meaning | Do not say |
| --- | --- | --- |
| Run a task through the process | Epic: an agent follows the fixed process (plan, code, review, test, update the docs) for a task. | - |
| Work through a project lead | Epic: one lead session per project starts task sessions, merges their work and keeps the owner's queue. | - |
| Keep docs and tests in order | Epic: the documentation standard, its check, and tests that say what they protect. | - |
| Check and design screens in the browser | Epic: the `web-kit` browser checks and the design of screens. | - |
| Check and show Unity play | Epic: the `unity-kit` checks, sketches and GIFs of play in the open editor. | - |
| Run all projects from the phone | Epic: the `pult` hub that starts the leads at logon and shows all projects on the phone. | - |
| Check that a test says what it protects | Feature: every added test carries a mark of what it protects. | - |
| Start and stop the app | Feature: the project's run-app and stop-app commands run in order and in reverse. | - |
| Launch only the project's own agents | Feature: a project can start only its own agents and those of its enabled plugins. | - |
| Hand work to the project lead | Feature: the owner gives work to the Lead, who starts task sessions and merges them. | - |
| Take over a session I started | Feature: the lead watches a session the owner started on their own; it ends its work with "Роботу завершено". | - |
| Design a screen | Feature: a mockup the owner approves, then polish on real components in the design sandbox. | - |
| Take a wide screenshot | Feature: a headless full-resolution screenshot of a wide screen. | - |
| Show a GIF of play | Feature: a short GIF of a moment of play for the owner to judge. | - |
| Play a recipe as a user | Feature: a scripted recipe of play run in the editor, with a report. | - |
| Start leads at logon and heal them | Feature: the Pult hub starts the leads at Windows logon and brings a dead one back. | - |
| Stop the known Windows shell traps | Feature: a shell command with a known Windows trap is stopped before it runs, with the working form named. | - |
| Run long commands in the background | Feature: a known long command run in the foreground is refused, so the owner can still talk to the session. | - |
| Log and reconcile API spend | Feature: every paid API call leaves one line in one local log, and a weekly check compares the log with the Console. | - |
| Fix agent problems in the retro | Feature: each project's problems of agent work are collected and fixed by a background retro session by itself; the owner sees a passive list in Pult's status and may say «поверни». | - |
| State cost as a share of the weekly limit | Feature: agents state the cost of subscription work as a share of the weekly limit, never in dollars. | - |
| Tidy the docs once a week | Feature: a background session audits a project's docs weekly, fixes the trivial and leaves the rest as items. | - |
| Project lead (Lead) | The one session per project that starts task sessions and merges their work; it does no task work itself. | - |
| Task session (Manager) | A session the project lead starts for one task, in its own worktree. | - |
| Owner queue | What waits on the owner, kept in PROGRESS.md "Open questions"; the Lead's messages show the 2 oldest open questions in full (urgent first) with a counter «і ще N питань» for the rest, and the window changes only after the owner's answer. | - |
| Discussion session («Discuss:») | A session where the owner settles the meaning and the mockup of a feature with one agent. | - |
