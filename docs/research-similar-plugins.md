# Research: plugins similar to dev-kit (2026-11-07)
Marks: [R] read in source, [I] inferred, [S] secondhand (blog/search snippet, not verified in source).
Method: raw files + api.github.com listings + issue search API. WebFetch summaries are small-model output, so [R] means "read via fetch of the file", not a byte check.

## 1. Projects
| Project | Link | Relevance to our plan | Maturity |
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

## 2. Improvement ideas (max 8)
1. Mechanical lint in the repo: names = dir, description has "Use when", agent frontmatter, slot named in every extension skill description. Source: wshobson docs/authoring.md, BMAD tools/skill-validator.md. Changes: stage 0 (done criterion), stage 1+. Cost low (one Python script, we already port check-docs). Risk low.
2. Description rule: triggers only ("Use when..."), never a workflow summary (agent follows summary and skips body). Source: superpowers skills/writing-skills/SKILL.md. Changes: README contract, stage 3 manager/new-feature. Cost low. Risk low.
3. Explicit slot wiring as data, not description matching: slot -> skill table in the profile, extension declares its slot in frontmatter, manager reads both. Source: BMAD menu `code/id` dispatch, spec-kit extensions.yml hooks. Changes: Slots section, stage 3 pilot. Cost medium. Risk: lowers the "untested slot idea" risk; descriptions stay as fallback.
4. Files for hand-offs: brief in a file, subagent writes report to a file and returns status + one line; reviewer gets a pre-built diff file; one reviewer returns two verdicts (spec + quality). Source: superpowers subagent-driven-development, Superpowers 6 post (about -15% to -25% cost [S]). Changes: stage 1 coder/reviewer text, stage 3 new-feature. Cost low. Risk: low.
5. Reviewer output contract: confidence 0-100, report only >=80, Critical/Important groups, "state what you reviewed". Source: feature-dev/agents/code-reviewer.md. Changes: stage 1 reviewer. Cost low. Risk: may hide real minor findings; keep threshold in profile.
6. Docs skills with provenance: managed block with date + SHA, "audit ends smaller", adopt mode with a ledger mapping each old instruction to a decision, "would a hook/lint enforce this better than prose?". Source: bmad-project-context/SKILL.md, claude-md-improver. Changes: stage 4 migrate-docs, maintain-project-docs. Cost medium. Risk: more ceremony for a large migration.
7. Two-layer profile: `.claude/dev-kit.md` committed + optional gitignored `dev-kit.local.md`; sparse override. Source: BMAD customize (team/user toml), plugin-dev plugin-settings. Changes: stage 0 profile contract. Cost low. Risk: low (hooks need restart).
8. Compat field and drift check: `requires: dev-kit >=X` in profile, semver bump per change in plugin.json, one test that the projects' profiles still satisfy the contract. Source: spec-kit `requires.speckit_version`, wshobson patch-bump CI. Changes: Decided section (no pinning), stage 0. Cost low-medium. Risk: need discipline; no pinning stays, this only detects breakage.

## 3. Things in our draft that these projects suggest are wrong or solved better
- No automated check of skills/agents: every stage "done" is a manual launch. All mature projects have a validator or evals (wshobson plugin-eval, BMAD validate_skills, superpowers-evals) [R]. Add a lint (idea 1) and one routing eval for the manager [I].
- Slot matching by description is the weakest link [I]. BMAD and spec-kit wire it declaratively [R]. Skills not triggering is the top complaint class [R #54, #58, #446; S description budget ~15k chars, dropped silently] - with 3 plugins of skills the budget matters; check `/doctor` in the pilot (not checked: exact current limit).
- A manager + new-feature + fix-bug orchestration layer is what agent-os v3 removed ("tools now do it") and v2.1 retired Roles as too complex [R changelog]. Our manager adds model routing, which nobody else does, but its value over plain skills is unproven [I]: keep it thin, measure on the stage 3 task.
- "No version pinning, live folder" is accepted, but every large project guards drift with versions, CI or compat fields [R]. One edit can break three projects with no signal (idea 8).
- Plans in new-feature "plan to docs": superpowers #895 shows over-specified plans (code in plan) hurt; plan = contracts + acceptance, not code [R issue]. Token cost of heavy process is the main user complaint (#743, #512, [S] #190); small tasks should skip the chain [S: Reddit/V2EX comments seen in search results].
- Draft says third-party skills are installed, not copied: consistent with plugins-official practice [I]. Name collisions across plugins are a real bug class (wshobson #500, #643) - our `<plugin>:<agent>` naming already avoids it [R].
- Not found: any project that splits "generic core + stack extension + per-project profile" exactly as ours; closest is spec-kit (core + extensions + presets) [I]. So the profile contract is our own design risk.
