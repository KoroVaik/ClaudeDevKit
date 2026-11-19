# ClaudeDevKit

Four plugins for [Claude Code](https://claude.com/claude-code) that give AI coding agents a fixed
development process: plan, code, review, test, update the docs. It is a personal tool for solo
developers who let agents write most of the code and want to stay in charge of the decisions.

## The problem

An agent left alone on a project skips steps. It changes code without a test, forgets the docs, or
reviews its own work. These plugins write the process down as skills and agents, and a small amount of
Python code enforces the parts that can be checked by a program.

## Purpose

The main goal is autonomous development: the owner's involvement shrinks over time, while decisions on
what the owner gets, money and hard-to-undo steps stay with the owner.

## Principles

### Plugins hold no project facts
Each project describes itself in one file, `.claude/dev-kit.md`; the sections are listed in
[the project profile](tech/project-profile.md).

### Enforce by program what a program can check
The process is written down as skills and agents; the parts that can be checked mechanically are
enforced by Python code (see [the map](tech/map.md)).

## Plugins and epics

- `dev-kit` - the core: the process, generic agents (coder, reviewer, investigator), the documentation
  standard and its checker. It gives three epics:
  - [Run a task through the process](epics/run-a-task.md)
  - [Work through a project lead](epics/work-through-a-project-lead.md)
  - [Keep docs and tests in order](epics/keep-docs-and-tests-in-order.md)
- `web-kit` - browser checks: end-to-end scenarios, layout checks, mockups, wide screenshots.
  Epic: [Check and design screens in the browser](epics/check-and-design-screens-in-the-browser.md).
- `unity-kit` - Unity: a bridge to the open editor, a scripted "user check" of play, scene sketches, GIFs.
  Epic: [Check and show Unity play](epics/check-and-show-unity-play.md).
- `pult` - the hub across projects (enable at user scope): starts the project leads at logon, runs a Remote
  Control server in the home folder for the phone and shows read-only status. It acts only in a session
  whose cwd is exactly the home folder.
  Epic: [Run all projects from the phone](epics/run-all-projects-from-the-phone.md).
