# Rules subscription: dev-kit

The development-process plugin: its skills, agents, slots, message kinds, Claude app facts and the hooks and scripts
that enforce them. `rules-kit` (the retro) reads this file; format: `plugins/rules-kit/scripts/subscriptions.py`.

| Setting | Value |
|---|---|
| set | dev-kit |
| reviewed by | ClaudeDevKit |
| lands by | branch merged by L: ClaudeDevKit; bump plugins/dev-kit version with a release mark in plugins/dev-kit/releases.json |
| special editor | claude-facts.md: dev-kit:facts-keeper (the retro passes findings, never edits) |

## Files

| Path (glob, relative to the set root) | Type | Part kinds | Section |
|---|---|---|---|
| skills/project-lead/SKILL.md | talk | skill dev-kit:project-lead | Message templates |
| skills/project-lead/SKILL.md | talk | skill dev-kit:project-lead | Owner queue and critical items |
| skills/project-lead/SKILL.md | talk | skill dev-kit:project-lead | Push test with the owner |
| skills/project-lead/SKILL.md | process | skill dev-kit:project-lead | |
| skills/manager/SKILL.md | talk | skill dev-kit:manager | Stating the cost of work |
| skills/manager/SKILL.md | talk | skill dev-kit:manager | Quiet about background work |
| skills/manager/SKILL.md | process | skill dev-kit:manager | |
| skills/brainstorm/SKILL.md | process | skill dev-kit:brainstorm | |
| skills/discovery-round/SKILL.md | process | skill dev-kit:discovery-round | |
| skills/documentation/SKILL.md | process | skill dev-kit:documentation | |
| skills/fix-bug/SKILL.md | process | skill dev-kit:fix-bug | |
| skills/maintain-project-docs/SKILL.md | process | skill dev-kit:maintain-project-docs | |
| skills/migrate-docs/SKILL.md | process | skill dev-kit:migrate-docs | |
| skills/new-feature/SKILL.md | process | skill dev-kit:new-feature | |
| skills/prune-tests/SKILL.md | process | skill dev-kit:prune-tests | |
| skills/showcase/SKILL.md | process | skill dev-kit:showcase | |
| skills/test-change/SKILL.md | process | skill dev-kit:test-change | |
| agents/question-reader.md | talk | agent dev-kit:question-reader | |
| agents/coder.md | process | agent dev-kit:coder | |
| agents/core-engineer.md | process | agent dev-kit:core-engineer | |
| agents/facts-keeper.md | process | agent dev-kit:facts-keeper | |
| agents/investigator.md | process | agent dev-kit:investigator | |
| agents/mechanical-editor.md | process | agent dev-kit:mechanical-editor | |
| agents/overlap-checker.md | process | agent dev-kit:overlap-checker | |
| agents/reviewer.md | process | agent dev-kit:reviewer | |
| messages.md | process | | |
| slots.md | process | | |
| migrations.md | process | | |
| claude-facts.md | process | | |
| hooks/hooks.json | technical | hook dev-kit | |
| hooks/*.py | technical | hook dev-kit | |
| scripts/docs_weekly.py | technical | hook dev-kit | |
| scripts/sessions.py | technical | skill dev-kit:project-lead, skill dev-kit:manager | |
| scripts/migrations.py | technical | skill dev-kit:project-lead | |
| scripts/hard_bans.py | technical | skill dev-kit:project-lead | |
| scripts/dev_kit_state.py | technical | skill dev-kit:project-lead | |
| scripts/run_app.py | technical | skill dev-kit:project-lead, skill dev-kit:test-change | |
| scripts/check_docs.py | technical | skill dev-kit:documentation, skill dev-kit:maintain-project-docs | |
| scripts/check_tests.py | technical | skill dev-kit:test-change, skill dev-kit:prune-tests | |
| scripts/*.py | technical | | |
| bin/* | technical | | |

## Signs

| Sign | Kind | Pattern |
|---|---|---|
| Lead asked what a rule says the Lead decides | process | the owner is asked whether to merge, clean up a branch or commit, which "Acceptance and merge" gives to the Lead: «(?i)(змерджит|змержит|мерджимо|мержимо|видаляємо гілку|видалити гілку|закомітит|комітимо|merge it|shall i merge|commit it)[^\n?]{0,60}\?» |
| hook blocks the same call again | technical | a dev-kit PreToolUse hook (narrow-agents, windows-traps, long-commands) denies a call and the next calls repeat it nearly unchanged |

## May change itself

| Path | Changes |
|---|---|
| skills/** | word, sentence, new sign |
| agents/** | word, sentence, new sign |
| slots.md | word, sentence |
| messages.md | word, sentence |
