# Work through a project lead

Part of the [ClaudeDevKit product](../product.md).

## What it gives

You are the CEO of the project: one session per project, the project lead (P), starts task sessions (C)
each in its own worktree, merges their finished work into main and tells you the result. It does no task
work itself. P collects what needs you in a queue, so you get decisions in order instead of a flood of
messages. The same epic holds the sessions you start yourself, the changes every project must make after
a dev-kit update (migrations) and each project's retro, which fixes small gaps in the rules by itself and
brings you the rest once a week.

The plugin covers work inside one repository. Starting P, the project list, the phone flow and the list of
all your sessions belong to [Run all projects from the phone](run-all-projects-from-the-phone.md).

## Features

- [Hand work to the project lead](../features/hand-work-to-the-project-lead.md)
- [Take over a session I started](../features/take-over-a-session-i-started.md)
- [Log and reconcile API spend](../features/log-and-reconcile-api-spend.md)

## Not written yet

Migrations (`dev-kit-migrations`, `plugins/dev-kit/migrations.md`) and the retro (`dev-kit-retro`, the
`dev-kit:retro` skill) have no feature files of their own; the README sentences about them are kept in
[project lead tools](../tech/project-lead.md). The rules for P stay in
`plugins/dev-kit/skills/project-lead/SKILL.md` until features are written from them.
