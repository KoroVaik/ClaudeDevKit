# Research: plugins similar to dev-kit (2026-11-07)
Marks: [R] read in source, [I] inferred, [S] secondhand (blog/search snippet, not verified in source).
Method: raw files + api.github.com listings + issue search API. WebFetch summaries are small-model output, so [R] means "read via fetch of the file", not a byte check.

## 1. Projects
| Project | Link | Relevance to dev-kit | Maturity |
|---|---|---|---|
| feature-dev, pr-review-toolkit, claude-md-management, plugin-dev | github.com/anthropics/claude-plugins-official/tree/main/plugins | High: closest to our core agents, reviewer and docs audit. plugin-dev/skills/plugin-settings is the per-project config pattern [R] | Official, stable |
| obra/superpowers | github.com/obra/superpowers | High: process skills, subagent roles, skill-writing rules, evals [R] | Mature, v6 (2026-06), 2 eval repos |
| wshobson/agents | github.com/wshobson/agents | Medium: plugin layout, lints, version bump CI, model tiers [R] | Large (94 plugins), CI-gated |
| BMAD-METHOD | github.com/bmad-code-org/BMAD-METHOD | High for slots and profile: persona skills, team/user TOML overrides, managed block in AGENTS.md [R] | v6.12 stable, v7 alpha, validator in tools/ |
| github/spec-kit | github.com/github/spec-kit | High for slots: extensions + presets + before/after hooks + layered config [R] | Mature, catalogs, compat constraint |
| buildermethods/agent-os | github.com/buildermethods/agent-os | Medium: v3 dropped orchestration, kept only standards [R changelog] | Small, 3 major rewrites |
| automazeio/ccpm | github.com/automazeio/ccpm (skill/ccpm) | Low-medium: one skill + references/ + "script-first" rule [R] | Small, now a single skill |
| SuperClaude | github.com/SuperClaude-Org/SuperClaude_Framework | Low: 30 commands, 20 agents, modes; KNOWLEDGE.md lists its own pitfalls [R] | Large but heavy, partly marketing numbers |

## Per-project notes (generic vs project-specific, routing, docs, extension, testing, complaints)
- feature-dev [R]: no project/generic split; agents (code-explorer/architect/reviewer, sonnet, fixed tools) read CLAUDE.md implicitly. Routing = one command with 7 phases + user gates. No tests seen.
- pr-review-toolkit [R]: 6 narrow reviewers (code, simplifier, comments, tests, silent-failure, types). code-reviewer scores 0-100, reports only >=80, groups Critical/Important.
- claude-md-management [R]: improver skill = 6 weighted criteria, grade A-F, report first, diffs, edit only after approval; refuses obvious/generic/one-off text.
- plugin-dev [R]: settings in `.claude/<plugin>.local.md` (YAML frontmatter + body), gitignored, hooks read it, restart needed. validator agent lints manifest, agent frontmatter, skill names.
- superpowers [R]: generic only; project rules come from user CLAUDE.md. Routing = skill descriptions + "1% rule". Model tier table in subagent-driven-development, model always set explicitly. Skills tested RED/GREEN/REFACTOR with pressure scenarios. Complaints [R issue list]: #743 slowness (27 comments), #895 plans over-specified (closed), #512 plan file re-read cost, #2530 v7 brainstorm questions annoying, #189 disable-model-invocation error. [S] #190 22k tokens startup cost.
- wshobson [R]: generic only, no routing; static model per agent; `plugin-eval` lints (MISSING_TRIGGER, SKILL_OVER_CODEX_CAP, ARGUMENTS_UNFRAMED), `make generate-all` + CI drift check, patch bump per change. Issues [R list]: #500/#643 duplicate agent names across plugins, #52 agent file parse failure.
- BMAD [R]: persona skills (bmad-agent-dev etc.) resolve base -> team `.toml` (committed) -> user `.user.toml` (gitignored); sparse overrides; menu items keyed by code/id dispatch to skills; project context = managed block in AGENTS.md with provenance (date + SHA), audit "ends smaller or equal". `tools/validate_skills.py --strict`. Issues [R list]: installer failures, missing agents after install, many harness requests.
- spec-kit [R]: core stays generic; extensions add commands `speckit.<ext>.<cmd>`, hooks `before_/after_<core command>` in `.specify/extensions.yml` (optional = ask, mandatory = auto), config layers default < project < local < env, `requires.speckit_version`. Presets override templates/commands with priority. Constitution = project principles file [I: gate use not confirmed, template only].
- agent-os [R]: v3 = standards only (discover/inject, index.yml), orchestration and "Roles" removed as too complex/duplicated by tools.
- ccpm [R]: SKILL.md routes 5 phases to references/*.md; deterministic reads go to bash scripts, LLM only for reasoning.
- SuperClaude [R]: KNOWLEDGE.md admits: docs drift (README described a plugin system that did not exist), version files disagree, only 1 skill; headline savings numbers lack method.

## 2. Facts that bear on a plugin set like dev-kit
- Every mature project checks its skills and agents by script, not by hand: wshobson `plugin-eval`, BMAD `validate_skills`, superpowers-evals [R]. A hand-checked plugin set has no signal when one edit breaks a skill.
- A description that summarises the workflow makes the agent follow the summary and skip the skill body (superpowers `skills/writing-skills/SKILL.md`) [R]. A description names its trigger only ("Use when ...").
- BMAD and spec-kit wire extensions to slots declaratively (menu `code/id` dispatch, `extensions.yml` hooks) [R]; matching a slot by description is the weakest link [I]. Skills not triggering is the top complaint class [R #54, #58, #446]; the description budget is about 15k chars and the overflow is dropped silently [S]. With several plugins the budget matters; the exact current limit is not checked.
- agent-os v3 removed its orchestration layer ("tools now do it") and v2.1 retired Roles as too complex [R changelog]. A manager over plain skills adds model routing, which no other project does, but its value over plain skills is unproven [I]; keep it thin.
- Every large project guards drift with versions, CI or compat fields (spec-kit `requires.speckit_version`, wshobson patch bump and CI drift check) [R]. With no version pinning, one edit can break several projects with no signal.
- superpowers #895 shows that over-specified plans (code in the plan) hurt [R issue]; a plan is contracts and acceptance, not code. The token cost of a heavy process is the main user complaint (#743, #512, [S] #190), so small tasks should skip the chain [S: Reddit/V2EX comments seen in search results].
- Handing work over through files (brief in a file, report in a file with status and one line back, a pre-built diff for the reviewer) is superpowers practice (subagent-driven-development); the Superpowers 6 post claims about -15% to -25% cost [S].
- Installing third-party skills instead of copying them is plugins-official practice [I]. Name collisions across plugins are a real bug class (wshobson #500, #643) [R]; `<plugin>:<agent>` naming avoids it.
- Not found: any project that splits "generic core + stack extension + per-project profile" exactly as dev-kit does; the closest is spec-kit (core + extensions + presets) [I]. The profile contract is dev-kit's own design.
