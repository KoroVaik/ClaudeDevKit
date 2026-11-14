---
name: showcase
description: Use when the owner wants a public showcase repo for a private project, or wants it brought up to date - "створи вітрину", "онови вітрину", "showcase", "update showcase", "public repo for employers".
---

# Showcase

Keeps a PUBLIC repo (`<Project>-showcase`) for a PRIVATE project, so an employer sees what the project
is and how it is built, without the core code. Two modes: `create` (first time) and `update` (whenever
the owner asks). The project's rules are in its `CLAUDE.md`. Read the profile section `## showcase` of
`.claude/dev-kit.md` if it exists; it adds to these rules and overrides them.

## The manifest

`docs/showcase.md` in the private project, committed there. `create` writes it, `update` reads it.

- showcase repo name and the local folder of its clone;
- sections of the showcase README, and for each fact where it comes from (a file or a command);
- allowlist of files that may be copied into the showcase (default: none);
- image sources (existing project artifacts, or a safe run on demo data);
- date of the last update.

## Writing rules

- Content that ages slowly: what the project is, architecture, decisions and why, the testing APPROACH.
- No test counts and no other numbers that change weekly; they mislead.
- Screenshots are refreshed only at milestones or when the owner asks.
- A section "How it was built" links ClaudeDevKit and says in a few lines how the process works.
- Plain English, short sentences, concrete facts. No buzzwords. Never an em dash or an en dash.
- Never copy core code, prompts, agent rules, tuned numbers or internal docs verbatim: describe them.

## Privacy guard

Run before every publish and report the result.

1. Only files from the manifest allowlist were copied.
2. Grep the whole showcase (text and image metadata) for: local paths (`C:/`, `/Users/`), user names,
   emails, hostnames, cloud ids, tokens, and client or employer names taken from the project docs.
   Any hit is fixed before the owner sees the draft.
3. A new showcase repo starts with fresh history: `git init` in a new folder, never a copy of the
   private history or a fork.

## Images

- From existing project artifacts, or from a safe local run on demo data. Never from a run against real
  personal data.
- Look at each image yourself before use; reject one that shows names, paths, tokens or real data.

## Flow

**create**
1. Read the project's product, architecture and testing docs and the code layout. Propose the sections
   and the manifest; the owner says yes or edits.
2. Write `docs/showcase.md` in the project. Draft the showcase README and the allowlisted files in a new
   folder with fresh history. Pick images by the rules above.
3. Run the privacy guard. Show the draft and the guard result.
4. Creating the public repo needs the owner's explicit yes. On the yes, create it with `gh`; the owner
   acts on GitHub only where a site needs his login. Push follows the showcase repo's `Push:` rule in its
   `CLAUDE.md`; with no such line, ask once which mode to write there.

**update**
1. Read `docs/showcase.md`, then re-read the sources it names.
2. Compare them with the showcase README. List what changed: new features, architecture changes, stale
   facts, new images worth adding (only at a milestone or on request).
3. Draft the edits and run the privacy guard. Show the list and the draft to the owner.
4. Only after the owner's yes: commit to the showcase repo, set the date in the manifest, commit that in
   the project. Push by the showcase repo's `Push:` rule.
