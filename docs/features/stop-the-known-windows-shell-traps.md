# Stop the known Windows shell traps

Epic: [Run a task through the process](../epics/run-a-task.md)

## Purpose
On Windows a shell command with one of three known traps fails after it runs and costs the agent a turn or more.
The command is stopped before it runs, with the working form named, so the next call works. The rule itself
lives in the owner's `docs/tools.md` (Python section); the hook enforces the narrower forms below, the ones the
2026-11-20/21 sessions showed to fail.

## Rules
### Python without UTF-8 mode
A command that launches `python`, `python3` or `py` without `-X utf8` is refused: the console uses cp1252, so
Cyrillic text fails with UnicodeEncodeError. `PYTHONUTF8=1` counts only without `-I` or `-E`, which ignore it.
`PYTHONIOENCODING` does not count: it fixes printing, not reading files.

### A large heredoc
A heredoc body over 7000 characters is refused with "write the file with the Write tool": such commands fail
with "unexpected EOF while looking for matching quote". The size, not non-ASCII text, decides: in the
2026-11-20/21 sessions every such failure was over that size, while hundreds of small heredocs and `python -c`
strings with Cyrillic worked.

### /tmp inside Python code
`/tmp` inside Python code (a heredoc fed to `python` or written to a `.py` file, or a `python -c` string) is refused: Python reads it as `C:\tmp`, the shell as its own
temp folder. `/tmp` as a plain shell argument passes, since the shell maps it for every program.

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

## Built in
- `plugins/dev-kit/hooks/windows-traps.py`
- `plugins/dev-kit/hooks/hooks.json`
- `tools/tests/test_windows_traps.py`
