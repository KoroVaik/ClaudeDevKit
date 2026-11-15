# Fixes from the live test in Zhratva (2026-11-15)

Owner's yes, P: ClaudeDevKit chat. Source: P: Zhratva's live-test report of dev-kit 0.1.28.

1. Missing agent type. P: Zhratva could not launch `dev-kit:overlap-checker`: a session gets new agent
   types only at its start, so a lead or session older than the plugin update lacks them. Rule (in
   project-lead and manager, wherever a dev-kit agent type is launched; best one general sentence): if the
   agent type is not available, launch a general read-only agent on the same model (e.g.
   `dev-kit:investigator`, or the cheapest available) and give it the missing agent's file text
   (`plugins/dev-kit/agents/<name>.md` body) as its instructions plus the brief. Note the gap to the owner
   only if no agent can be launched at all.
2. Local setup of a fresh worktree. Zhratva's `data/` is gitignored and needed by the docs check on
   commit; P linked it with a junction by hand, and `git worktree remove` would follow the junction (risk
   of deleting the main data). Add a profile slot in `.claude/dev-kit.md` (see `plugins/dev-kit/slots.md`
   and how other profile sections are read) where a project lists the ignored paths a worktree needs and
   how: `copy` or `link`. P applies it after `git worktree add`; for `link`, the clean-up removes the
   links first (never follow them) before `git worktree remove`. Without the slot, the current rule
   (copy candidates from `git status --ignored`) stays. Tell Zhratva's agent nothing; propose its profile
   lines in your report so P can pass them on.
3. Tests, lint, dev-kit version bump, README if it describes this.

Success criterion: the rules cover both cases; a test for any script change; lint green.
