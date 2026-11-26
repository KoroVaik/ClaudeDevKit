"""PreToolUse hook for the Bash and PowerShell tools on Windows: refuses a command with one of the known traps of the owner's
docs/tools.md (Python section) and names the working form in one line. The rule's home stays docs/tools.md; the hook
checks the narrower forms that the 2026-11-20/21 sessions showed to fail (docs/features/stop-the-known-windows-shell-traps.md).

(a) Python run without UTF-8 mode (plugins/dev-kit/claude-facts.md, "Python on Windows crashes printing Cyrillic,
    and `-I` ignores the UTF-8 variables").
(b) A large heredoc (plugins/dev-kit/claude-facts.md, "A large heredoc in the shell fails with "unexpected EOF while looking for matching quote"").
(c) /tmp inside Python code (plugins/dev-kit/claude-facts.md, "Git Bash's `/tmp` and Python's `/tmp` are different
    folders").
(d) PowerShell tool only: a plugin bin command (dev-kit-app, rules-kit, ...). The bin files have no extension, so
    Windows opens the "Pick an app" window instead of running them (plugins/dev-kit/claude-facts.md, "Plugin `bin`
    commands run only in the Bash tool"). Checks (a)-(c) are for the Bash tool only.
"""
import json
import re
import sys

# A heredoc opener (<<EOF, <<'EOF', <<-"EOF"), not a here-string (<<<); it counts only if its closing line exists.
HEREDOC = re.compile(r'(?<!<)<<(?!<)-?[ \t]*([\'"]?)([A-Za-z_][\w.-]*)\1')
# A python launcher in command position: start, after ; & | ( { ! ` $( newline or a shell keyword, then optional
# prefixes such as env VAR=x, timeout 60, xargs, uv run. A path before the name (/usr/bin/python3) is allowed.
PYTHON = re.compile(
    r'(?:^|[;&|(`{!\n]|\$\(|\b(?:then|do|else|elif|if|while|until)\b)[ \t]*'
    r'(?:(?:env|exec|time|nohup|xargs|sudo|winpty|uv[ \t]+run|poetry[ \t]+run|timeout(?:[ \t]+-\S+)*[ \t]+\S+'
    r'|[A-Za-z_]\w*=\S*)[ \t]+)*'
    r'(?:\S*[/\\])?(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?(?=[ \t\n;&|)`]|$)',
    re.IGNORECASE)
SEPARATOR = re.compile(r'[;&|\n`]|\$\(')
UTF8_FLAG = re.compile(r'(?:^|\s)-X[ \t]*utf8\b')
UTF8_ENV = re.compile(r'\bPYTHONUTF8=1\b')
ISOLATED = re.compile(r'(?:^|\s)-[A-Za-z]*[IE][A-Za-z]*(?=\s|$)')
# A quoted string with no command substitution in it: plain text, never a launch.
QUOTED = re.compile(r'"(?:[^"\\$`]|\\.)*"|\'[^\']*\'')
# /tmp at the start of a path: not .../jobs/<id>/tmp, not C:/tmp, not tmp_unused.
TMP = re.compile(r'(?:^|[\s\'"=(<>,;|&`])/tmp(?=/|[\s\'";|&)`]|$)')
# The code string of python ... -c '...' or -c "..." (only after a python launcher).
INLINE_CODE = re.compile(r'(?:python(?:3(?:\.\d+)?)?|py)(?:\.exe)?\b[^;&|\n]*?\s-c[ \t]+([\'"])(.*?)(?<!\\)\1',
                         re.DOTALL | re.IGNORECASE)
PY_FILE = re.compile(r'\.py\b')
HEREDOC_LIMIT = 7000
# A plugin bin command in PowerShell command position: start, after ; | & ( { or a newline, or after the call
# operator &; optionally quoted and with a folder before it. The names are the extensionless files in plugins/*/bin.
PS_BIN = re.compile(
    r'(?:^|[;|&({\n])[ \t]*(?:&[ \t]*)?[\'"]?(?:[^\s\'";|&]*[/\\])?'
    r'((?:dev-kit|spend-kit|rules-kit|web-kit|unity-kit)(?:-[a-z]+)*)(?=[\'"]?(?:[ \t;|&)}\n]|$))',
    re.IGNORECASE)
# PowerShell quoted text: '...' ('' inside) and "..." (` escapes).
PS_QUOTED = re.compile(r"'(?:[^']|'')*'|\"(?:[^\"`]|`.)*\"")

TMP_FIX = 'use the job tmp folder as a C:/ path ($CLAUDE_JOB_DIR/tmp), not /tmp: Python and the shell see different /tmp folders'
HEREDOC_FIX = ('write the file with the Write tool, then run it: a heredoc this large fails with '
               '"unexpected EOF while looking for matching quote"')
BIN_FIX = ('run {name} in the Bash tool, not PowerShell: plugin bin files have no extension, so Windows opens '
           'the "Pick an app" window instead of running them')
PYTHON_FIX = ('run Python as python -I -X utf8 ...: without UTF-8 mode, Cyrillic text fails with UnicodeEncodeError '
              '(PYTHONUTF8=1 is ignored under -I)')


def strip_heredocs(command):
    """Return (command without heredoc bodies, list of (opener line, body))."""
    lines = command.split('\n')
    kept, bodies = [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        i += 1
        for match in HEREDOC.finditer(line):
            tag, strip_tabs = match.group(2), line[match.start() + 2:match.start() + 3] == '-'
            end = i
            while end < len(lines) and (lines[end].lstrip('\t') if strip_tabs else lines[end]).rstrip('\r') != tag:
                end += 1
            if end == len(lines):
                continue  # no closing line: not a heredoc (e.g. $((1 << n)))
            bodies.append((line, '\n'.join(lines[i:end])))
            kept.append(lines[end])
            i = end + 1
    return '\n'.join(kept), bodies


def segment(shell, start, end):
    """The simple command around shell[start:end]: from the previous separator to the next one."""
    before = [m.end() for m in SEPARATOR.finditer(shell, 0, start)]
    after = SEPARATOR.search(shell, end)
    return shell[before[-1] if before else 0:after.start() if after else len(shell)]


def python_without_utf8(shell):
    """True if some python launcher in the shell text (heredoc bodies and quoted text removed) runs without UTF-8 mode."""
    text = QUOTED.sub('""', shell)
    exported = bool(re.search(r'\bexport[ \t]+PYTHONUTF8=1\b', text))
    for match in PYTHON.finditer(text):
        part = segment(text, match.end(), match.end())
        stop = SEPARATOR.search(text, match.end())
        args = text[match.end():stop.start() if stop else len(text)]
        if UTF8_FLAG.search(args):
            continue
        if (exported or UTF8_ENV.search(part)) and not ISOLATED.search(args):
            continue
        return True
    return False


def trap(command):
    """The fix line for the first trap in command, or None."""
    shell, bodies = strip_heredocs(command)
    # The shell maps /tmp in a command argument to its own folder for every program, Python included; /tmp breaks
    # only inside Python code: a heredoc fed to python or written to a .py file, or a python -c string.
    if any(TMP.search(body) for opener, body in bodies if PYTHON.search(opener) or PY_FILE.search(opener)) \
            or any(TMP.search(m.group(2)) for m in INLINE_CODE.finditer(shell)):
        return TMP_FIX
    if any(len(body) > HEREDOC_LIMIT for _, body in bodies):
        return HEREDOC_FIX
    if python_without_utf8(shell):
        return PYTHON_FIX
    return None


def powershell_trap(command):
    """The fix line if the PowerShell command runs a plugin bin command, or None. Quoted text is blanked unless it
    stands in command position (a quoted path after & or at the start), so a name in a message is not a launch."""
    def blank(match):
        before = command[:match.start()].rstrip(' \t')
        return match.group(0) if not before or before[-1] in ';|&({\n' else "''"
    found = PS_BIN.search(PS_QUOTED.sub(blank, command))
    return BIN_FIX.format(name=found.group(1)) if found else None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        call = json.loads(sys.stdin.buffer.read().decode('utf-8-sig'))
    except ValueError:
        return
    tool_input = call.get('tool_input') if isinstance(call, dict) else None
    command = tool_input.get('command') if isinstance(tool_input, dict) else None
    if not isinstance(command, str) or sys.platform != 'win32':
        return
    fix = powershell_trap(command) if call.get('tool_name') == 'PowerShell' else trap(command)
    if fix:
        json.dump({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
            'permissionDecisionReason': 'Windows trap (docs/tools.md): ' + fix}}, sys.stdout)


if __name__ == '__main__':
    main()
