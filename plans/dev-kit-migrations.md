# dev-kit migrations for this repo

Pending entries: 3 («Propose the hard bans once»), from plugins/dev-kit/migrations.md.

Apply the entries in order; for each, follow its `How` under this project's rules, check its `Done when`, then run `dev-kit-migrations record <n>` in this worktree. An entry with an `Owner choice` goes to P (P: ClaudeDevKit) as a question before it is applied: send P the exact deny lines filled for this repo and wait for the answer; never record past an entry not applied.

Facts for entry 3 in this repo: main does not deploy (push to main is routine here), there are no owner data folders, owner database or containers; `.claude/settings.json` holds only enabledPlugins.
