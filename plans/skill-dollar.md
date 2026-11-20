# Money sums lost in skill text

Owner's words: «Так оба» to P's «Запустити нову сесію «C: Сума в правилах керівника»? (зараз замість «$1» видно слово «plugin»)» (2026-11-20).

## Cause (seen by P)
`/dev-kit:project-lead restart: plugin update` loaded the skill with `$1` in its text replaced by the argument word `plugin` («paid spend would pass plugin in total per task»). Claude Code substitutes `$1`, `$2`, `$ARGUMENTS` and similar in skill bodies when the skill gets arguments.

## Task
Find every place in the plugins' skills (and agents, if the same applies) where text like `$1` or `$<digit>` could be replaced by arguments, and reword it so it survives (for example «1 USD»). Do not change meaning. Bump the plugin version(s) touched.

## Success criterion
No `$<digit>` or `$ARGUMENTS` left in skill or agent text unless it is meant as an argument; lint passes.

## Paid spend
Total: $0
