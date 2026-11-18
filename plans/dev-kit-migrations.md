# dev-kit migrations for this repo

Pending entries: 3 («Propose the hard bans once»), from plugins/dev-kit/migrations.md.

Apply the entries in order; for each, follow its `How` under this project's rules, check its `Done when`, then run `dev-kit-migrations record <n>` in this worktree. An entry with an `Owner choice` goes to P (P: ClaudeDevKit) as a question before it is applied: send P the exact deny lines filled for this repo and wait for the answer; never record past an entry not applied.

Facts for entry 3 in this repo: main does not deploy (push to main is routine here), there are no owner data folders, owner database or containers; `.claude/settings.json` holds only enabledPlugins.

## Progress

- Entry 3: filled set for this repo is only `Edit(.claude/settings.json)` and `Edit(.claude/settings.local.json)` (no deploy from main, no data folders, database or containers). Owner said yes (via P); profile row `hard bans | accepted 2026-11-19` added, level 3 recorded, `pending` prints none. Owner adds the deny lines by hand. Done.
- Paid spend: $0.
