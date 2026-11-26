# Stop the known Windows shell traps

Epic: [Run a task through the process](../epics/run-a-task.md)

## Purpose
On Windows a shell command with one of four known traps fails after it runs and costs the agent a turn or more.
The command is stopped before it runs, with the working form named, so the next call works. The rule itself
lives in the owner's global `tools.md` (Python section, in the `docs` folder of the owner's `.claude`); the hook enforces the narrower forms below, the ones the
2026-11-20/21 sessions showed to fail.

## Rules
### Python without UTF-8 mode
A command that launches `python`, `python3` or `py` without `-X utf8` is refused ([Claude facts](../../plugins/dev-kit/claude-facts.md), "Python on Windows crashes printing Cyrillic, and `-I`
ignores the UTF-8 variables"). `PYTHONUTF8=1` counts only without `-I` or `-E`, which ignore it.
`PYTHONIOENCODING` does not count: it fixes printing, not reading files.
Why: owner, retro of 2026-11-21: every launch without `-X utf8` is refused, working ones too (about 1390 of 7201
calls in the 2026-11-20/21 sessions, about one refusal per context since agents adapt); the owner approved this
wording, and it stops 129 of the 130 encoding failures. The hook is on Bash
only: PowerShell had 0 encoding failures in 302 calls. The plugin's own docs say `python -X utf8 ...`, so the hook
never refuses the plugin's commands.

### A large heredoc
A heredoc body over 7000 characters is refused with "write the file with the Write tool" ([Claude facts](../../plugins/dev-kit/claude-facts.md), "A large heredoc
in the shell fails with "unexpected EOF while looking for matching quote""). The size, not non-ASCII text, decides: in the
2026-11-20/21 sessions every such failure was over that size, while hundreds of small heredocs and `python -c`
strings with Cyrillic worked.

### /tmp inside Python code
`/tmp` inside Python code (a heredoc fed to `python` or written to a `.py` file, or a `python -c` string) is refused ([Claude facts](../../plugins/dev-kit/claude-facts.md), "Git Bash's `/tmp` and Python's `/tmp` are different folders"). `/tmp` as a plain shell argument passes, since the shell maps it for every program.

### A plugin command in the PowerShell tool
A PowerShell tool call that runs a plugin `bin` command (`dev-kit-app`, `dev-kit-sessions`, `rules-kit`, `spend-kit-api`
and the other extensionless files in `plugins/*/bin`) is refused with "run it in the Bash tool" ([Claude facts](../../plugins/dev-kit/claude-facts.md),
"Plugin `bin` commands run only in the Bash tool"). Windows cannot run such a file and opens its «Pick an app» window
instead, and `2>$null` hides the error from the agent. A name in quoted text or as an argument (a commit message, a path
to read) passes. Why: owner, 2026-11-26 (`plans/pick-an-app.md`): «у мене постійно це вилазить, чому?»; L: Prishch ran
`dev-kit-app stop` in PowerShell during a merge clean-up. The other three checks stay on the Bash tool only.

### What passes
Read-only inline Python with `-X utf8`, any command on other systems, and `python` written inside text (a heredoc
body, a commit message).

How the hook works: [hooks](../tech/hooks.md).

## Acceptance criteria
- `python x.py` in a Bash call on Windows: refused, the reason names `python -I -X utf8`.
- `python -I -X utf8 - <<'EOF'` with Cyrillic in a short body: runs.
- A `cat > gen.py <<'EOF'` body over 7000 characters: refused, the reason names the Write tool.
- `open('/tmp/x.json')` in a Python heredoc body: refused; `npm ci > /tmp/npm.log`: runs.
- `bash -c "cd /tmp && ls"` and `git commit -F - <<'EOF'` mentioning `/tmp`: run.
- `dev-kit-app stop --project x` in a PowerShell call: refused, the reason names the Bash tool; the same in Bash: runs.

## Built in
- `plugins/dev-kit/hooks/windows-traps.py`
- `plugins/dev-kit/hooks/hooks.json`
- `tools/tests/test_windows_traps.py`

## Open
- [ ] Run a 20-call batch of the catalogue judge in Zhratva with the hook on and count the failed shell calls, the live half of the check that the refusals cut the failures; needs a Zhratva run
