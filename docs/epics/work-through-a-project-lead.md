# Work through a project lead

Part of the [ClaudeDevKit product](../product.md).

## What it gives

You are the CEO of the project: one session per project, the project lead (the Lead), starts task sessions (Managers)
each in its own worktree, merges their finished work into main and tells you the result. It does no task
work itself. The Lead collects what needs you in a queue, so you get decisions in order instead of a flood of
messages. The same epic holds the sessions you start yourself, the changes every project must make after
a dev-kit update (migrations) and each project's retro, which fixes gaps in the rules by itself; you see a
passive list of what it did in Pult's status and may say «поверни».

The plugin covers work inside one repository. Starting the Lead, the project list, the phone flow and the list of
all your sessions belong to [Run all projects from the phone](run-all-projects-from-the-phone.md).

## Features

- [Hand work to the project lead](../features/hand-work-to-the-project-lead.md)
- [Take over a session I started](../features/take-over-a-session-i-started.md)
- [Log and reconcile API spend](../features/log-and-reconcile-api-spend.md)
- [State cost as a share of the weekly limit](../features/state-cost-as-a-share-of-the-weekly-limit.md)
- [Fix agent problems in the retro](../features/fix-agent-problems-in-the-retro.md)
- [Keep Claude app facts](../features/keep-claude-app-facts.md)
- [Show where the weekly limit went](../features/limit-usage-stats.md)
- [Catch wasted work](../features/catch-wasted-work.md)

## Not written yet

Migrations (`dev-kit-migrations`, `plugins/dev-kit/migrations.md`) have no feature file of their own; the README
sentences about them are kept in [project lead tools](../tech/project-lead.md). The rules for the Lead live in
[Hand work to the project lead](../features/hand-work-to-the-project-lead.md); the skill keeps the how.
