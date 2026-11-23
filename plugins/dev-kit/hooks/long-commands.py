"""PreToolUse hook for the Bash and PowerShell tools: refuses a known long command run in the foreground, so the
owner can still talk to the session while it runs (docs/features/run-long-commands-in-the-background.md).

A command passes when the call sets run_in_background. Known long commands:
- a wait of 60 s or more: sleep, Start-Sleep, timeout /t (the waits in one command are added up);
- a line of the project's profile, section "## long commands": `| `<regex>` | <why> |`.
Any error lets the command run, so a hook bug never stops the shell.
"""
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

# Heredoc bodies are text, not commands: reuse the windows-traps reader that cuts them out.
_SPEC = importlib.util.spec_from_file_location('windows_traps', Path(__file__).with_name('windows-traps.py'))
_TRAPS = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_TRAPS)

LIMIT_SECONDS = 60
UNITS = {'': 1, 's': 1, 'm': 60, 'h': 3600, 'd': 86400}
# A command position: start, after ; & | ( { newline, $( or a shell keyword.
START = r'(?:^|[;&|({\n]|\$\(|\b(?:then|do|else)\b)[ \t]*'
SLEEP = re.compile(START + r'sleep((?:[ \t]+\d+(?:\.\d+)?[smhd]?)+)(?=[ \t]*(?:[;&|)}\n]|$))', re.IGNORECASE)
SLEEP_ARG = re.compile(r'(\d+(?:\.\d+)?)([smhd]?)', re.IGNORECASE)
START_SLEEP = re.compile(
    START + r'Start-Sleep(?:[ \t]+-(?P<unit>Seconds|Milliseconds|s|ms)\b)?[ \t]+(?P<n>\d+(?:\.\d+)?)'
    r'(?:[ \t]+-(?P<unit2>Seconds|Milliseconds|s|ms)\b)?',
    re.IGNORECASE)
TIMEOUT_T = re.compile(START + r'timeout(?:\.exe)?[ \t]+/t[ \t]+(\d+)', re.IGNORECASE)
PROFILE_ROW = re.compile(r'^\|\s*`([^`]+)`\s*\|\s*(.*?)\s*\|\s*$')

FIX = ('run it with run_in_background: true and a hard time limit inside the command, so the owner can talk to the '
       'session while it runs')


def wait_seconds(command):
    """Seconds the command spends in sleep, Start-Sleep and timeout /t, added up."""
    total = 0.0
    for match in SLEEP.finditer(command):
        for number, unit in SLEEP_ARG.findall(match.group(1)):
            total += float(number) * UNITS[unit.lower()]
    for match in START_SLEEP.finditer(command):
        unit = (match.group('unit') or match.group('unit2') or 's').lower()
        total += float(match.group('n')) / (1000 if unit in ('ms', 'milliseconds') else 1)
    for match in TIMEOUT_T.finditer(command):
        total += float(match.group(1))
    return total


def profile_patterns(project_dir):
    """(regex, why) rows of the profile's "## long commands" section; a bad regex is skipped."""
    try:
        text = (Path(project_dir) / '.claude' / 'dev-kit.md').read_text(encoding='utf-8')
    except OSError:
        return []
    rows, inside = [], False
    for line in text.splitlines():
        if line.startswith('## '):
            inside = line[3:].strip().lower() == 'long commands'
            continue
        match = PROFILE_ROW.match(line.strip()) if inside else None
        if match:
            try:
                rows.append((re.compile(match.group(1)), match.group(2)))
            except re.error:
                pass
    return rows


def reason(command, patterns):
    """Why the command is long, or None."""
    command, _ = _TRAPS.strip_heredocs(command)
    seconds = wait_seconds(command)
    if seconds >= LIMIT_SECONDS:
        return 'it waits %d s' % seconds
    for pattern, why in patterns:
        if pattern.search(command):
            return why or 'the project lists it as long (`%s`)' % pattern.pattern
    return None


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    try:
        call = json.loads(sys.stdin.buffer.read().decode('utf-8-sig'))
    except ValueError:
        return
    tool_input = call.get('tool_input') if isinstance(call, dict) else None
    if not isinstance(tool_input, dict) or tool_input.get('run_in_background') is True:
        return
    command = tool_input.get('command')
    if not isinstance(command, str):
        return
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR') or call.get('cwd') or os.getcwd()
    why = reason(command, profile_patterns(project_dir))
    if why:
        json.dump({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
            'permissionDecisionReason': 'Long command in the foreground (%s): %s.' % (why, FIX)}}, sys.stdout)


if __name__ == '__main__':
    main()
