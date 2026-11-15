# Launch fixes from the second Zhratva live test (2026-11-15)

Owner's yes, P: ClaudeDevKit chat. Source: P: Zhratva's report on dev-kit 0.1.30.

1. `--add-dir <path> -- <prompt>` swallowed the prompt (variadic flag); the C started idle. `--add-dir=<path>`
   works (checked by P: Zhratva). Fix the launch command in project-lead SKILL.md to the `=` form for every
   link entry.
2. `git worktree remove` left an empty folder locked, because P's own PowerShell cwd was inside it after
   the launch. Fix: the launch rule returns the shell to the main checkout (Push-Location/Pop-Location or
   Set-Location back) before anything else; the clean-up does the same before `git worktree remove`.
   P: ClaudeDevKit saw the same 'Permission denied' on folder delete several times today.
3. `dev-kit-sessions watch` reportedly dies at the Bash tool's 10-minute timeout long before its 2-hour
   limit, and nothing tells P. First verify: does a `run_in_background` Bash command get killed at the
   tool timeout? (In P: ClaudeDevKit a watcher started with run_in_background seemed to survive longer;
   check its start and the later 'already watching' exit.) If it is killed: make the watcher's default
   limit fit under the real cap and have P re-arm it on that exit, or document the right way to run it.
4. Tests where a script changes, lint, dev-kit version bump.

Out of scope (goes to the «Керівник як CEO» discussion): taking over a session the owner started on main;
whether the owner's yes relayed by P counts for a C's auto-mode classifier.
